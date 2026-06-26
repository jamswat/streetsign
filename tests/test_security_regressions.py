'''
    Focused regressions for security-sensitive display and deployment behavior.
'''

from os.path import dirname, join as pathjoin

import streetsign_server.post_types.external_webpage as external_webpage
from streetsign_server.logic.urlsafety import check_fetch_url, UnsafeURL
from streetsign_server.models import Feed, User, Group
from streetsign_server.models.users import UserGroup
from unittest_helpers import StreetSignTestCase


class TestSecurityRegressions(StreetSignTestCase):
    def test_raw_html_renderer_uses_sandboxed_iframe(self):
        with open(pathjoin(dirname(__file__), '..',
                          'streetsign_server', 'post_types', 'raw_html',
                          'screen.js'), 'r', encoding='utf-8') as f:
            screen_js = f.read()

        self.assertIn(".attr('sandbox', 'allow-scripts')", screen_js)

    def test_external_webpage_rejects_non_http_urls(self):
        data = external_webpage.receive({'url': 'javascript:alert(1)'})

        self.assertEqual(data['url'], '')
        self.assertEqual(data['content'], '')

    def test_external_webpage_accepts_https_urls(self):
        data = external_webpage.receive({'url': 'https://example.com/page'})

        self.assertEqual(data['url'], 'https://example.com/page')

    def test_docker_context_keeps_thumbnail_script(self):
        with open(pathjoin(dirname(__file__), '..', '.dockerignore'),
                  'r', encoding='utf-8') as f:
            dockerignore = f.read().splitlines()

        self.assertNotIn('scripts/', dockerignore)

    # --- SSRF URL safety ------------------------------------------------

    def test_urlsafety_rejects_non_http_schemes(self):
        for url in ('file:///etc/passwd', 'gopher://x/', 'ftp://x/',
                    '/etc/passwd'):
            with self.assertRaises(UnsafeURL):
                check_fetch_url(url)

    def test_urlsafety_rejects_internal_hosts(self):
        for url in ('http://localhost/x', 'http://127.0.0.1/x',
                    'http://169.254.169.254/latest/meta-data/',
                    'http://10.0.0.5/x', 'http://192.168.1.1/'):
            with self.assertRaises(UnsafeURL):
                check_fetch_url(url)

    def test_urlsafety_accepts_public_http(self):
        # no DNS lookup - just check scheme/host parsing on an IP literal.
        self.assertTrue(check_fetch_url('http://8.8.8.8/feed', resolve=False))
        self.assertTrue(
            check_fetch_url('https://example.com/x', resolve=False))

    # --- group permission isolation ------------------------------------

    def test_group_permission_does_not_leak_across_groups(self):
        ''' A user must NOT inherit a permission granted to a group they are
            not a member of. '''
        feed = Feed(name='f')
        feed.save()
        user = User(loginname='u', passwordhash='x')
        user.save()
        group_a = Group(name='A')
        group_a.save()
        group_b = Group(name='B')
        group_b.save()

        # user is only in group A
        UserGroup(user=user, group=group_a).save()

        # but the read permission is granted to group B
        feed.grant('Read', group=group_b)
        self.assertFalse(feed.user_can_read(user))

        # granting to the user's own group does work
        feed.grant('Write', group=group_a)
        self.assertTrue(feed.user_can_write(user))
        self.assertFalse(feed.user_can_publish(user))

    def test_grant_does_not_revoke_other_permissions(self):
        ''' Granting Publish must not remove a previously-granted Write. '''
        feed = Feed(name='f')
        feed.save()
        user = User(loginname='u2', passwordhash='x')
        user.save()

        feed.grant('Write', user=user)
        feed.grant('Publish', user=user)

        self.assertTrue(feed.user_can_write(user))
        self.assertTrue(feed.user_can_publish(user))
