'''
    Regression tests for the bug-fix pass.

    Each test maps to a specific finding from the audit:

      H1 - stored XSS via post.time_restrictions rendered with |safe
      M1 - posts_bulk_delete 500s on missing/non-JSON body
      M2 - feedpage bare except masked real failures
      M3 - postpage GET leaked post content to unauthorized users
      L2 - screendisplay passed an unvalidated template name to Jinja
      L3 - screens_posts_from_feeds unhandled json.loads
      L4 - user_files delete raised TypeError on missing filename field
'''

#pylint: disable=import-error,too-many-public-methods,too-few-public-methods
#pylint: disable=missing-docstring,invalid-name

import sys
import os

from flask import json

sys.path.append(os.path.dirname(__file__) + '/..')

import streetsign_server.models as models
from streetsign_server.logic.feeds_and_posts import post_form_intake
from streetsign_server.post_types import html as html_post_type

from unittest_helpers import StreetSignTestCase


USERNAME = 'admin'
USERPASS = '123'


class TestTimeRestrictionsXSS(StreetSignTestCase):
    ''' H1: time_restrictions must be stored as valid JSON and rendered
        safely so a feed writer cannot break out of the editor <script>
        block to run JS in an admin's session. '''

    def setUp(self):
        super().setUp()
        self.feed = models.Feed.create(name='xss feed')
        self.user = models.User(loginname=USERNAME,
                                emailaddress='a@b.org',
                                is_admin=True)
        self.user.set_password(USERPASS)
        self.user.save()
        self.feed.grant('Write', user=self.user)
        self.feed.grant('Publish', user=self.user)

    def test_normalizes_valid_json_on_save(self):
        ''' post_form_intake round-trips the value as JSON. '''
        post = models.Post(feed=self.feed, type='html',
                           content='{"content":"x"}', author=self.user)
        form = {'time_restrictions_json': '[{"start":"09:00","end":"10:00"}]',
                'times_mode': 'only_show'}
        post_form_intake(post, form, html_post_type)
        self.assertEqual(json.loads(post.time_restrictions),
                         [{"start": "09:00", "end": "10:00"}])

    def test_rejects_breakout_payload_stores_valid_json(self):
        ''' A payload containing </script> is valid JSON, so it is stored
            verbatim-as-normalized-JSON. The XSS defense lives at the
            template layer (|tojson escapes <), tested below. Here we just
            guarantee the stored value is valid JSON (parseable). '''
        payload = '["</script><script>alert(1)</script>"]'
        post = models.Post(feed=self.feed, type='html',
                           content='{"content":"x"}', author=self.user)
        form = {'time_restrictions_json': payload, 'times_mode': 'only_show'}
        post_form_intake(post, form, html_post_type)
        parsed = json.loads(post.time_restrictions)
        self.assertIsInstance(parsed, list)
        self.assertEqual(parsed, ['</script><script>alert(1)</script>'])

    def test_invalid_json_falls_back_to_empty_list(self):
        post = models.Post(feed=self.feed, type='html',
                           content='{"content":"x"}', author=self.user)
        form = {'time_restrictions_json': 'NOT JSON {{{', 'times_mode': ''}
        post_form_intake(post, form, html_post_type)
        self.assertEqual(json.loads(post.time_restrictions), [])

    def test_editor_page_does_not_emit_breakout(self):
        ''' End-to-end: saving a malicious post then opening the editor
            must not emit a raw </script> breakout in the page body. '''
        self.login(USERNAME, USERPASS)
        with self.ctx():
            resp = self.client.post(f'/posts/new/{self.feed.id}', data={
                'post_title': 'xss attempt',
                'post_type': 'html',
                'content': 'hello',
                'time_restrictions_json':
                    '["</script><script>alert(1)</script>"]',
                'times_mode': 'only_show',
            }, follow_redirects=False)
            self.assertEqual(resp.status_code, 302)
            post = models.Post.get(models.Post.feed == self.feed)

            page = self.client.get(f'/posts/{post.id}')
            self.assertEqual(page.status_code, 200)
            body = page.data.decode('utf-8', errors='replace')
            # |tojson escapes < as \u003c, so no raw </script><script
            # breakout sequence is emitted. (With the old |safe filter the
            # raw </script><script> markup would appear here, breaking out
            # of the editor's <script> block and executing attacker JS.)
            self.assertNotIn('</script><script', body)
            self.assertIn('window.TIME_RESTRICTIONS = [', body)
            self.assertIn('\\u003c', body)


class TestPostsBulkDelete(StreetSignTestCase):
    ''' M1: posts_bulk_delete must not 500 on a missing/invalid body. '''

    def setUp(self):
        super().setUp()
        self.user = models.User(loginname=USERNAME, emailaddress='a@b.org')
        self.user.set_password(USERPASS)
        self.user.save()

    def test_missing_body_returns_error_not_500(self):
        self.login(USERNAME, USERPASS)
        resp = self.client.post('/posts/bulk_delete')
        self.assertIn(resp.status_code, (400, 415))

    def test_non_json_body_returns_error_not_500(self):
        self.login(USERNAME, USERPASS)
        resp = self.client.post('/posts/bulk_delete',
                                data='not json at all',
                                content_type='text/plain')
        self.assertIn(resp.status_code, (400, 415))

    def test_non_list_post_ids_returns_error(self):
        self.login(USERNAME, USERPASS)
        resp = self.client.post('/posts/bulk_delete',
                                data=json.dumps({'post_ids': '3,4'}),
                                content_type='application/json')
        self.assertEqual(resp.status_code, 400)


class TestFeedpageErrorHandling(StreetSignTestCase):
    ''' M2: only Feed.DoesNotExist should redirect; other errors must not
        be silently swallowed as 'invalid feed id'. '''

    def test_nonexistent_feed_redirects(self):
        u = models.User(loginname=USERNAME, emailaddress='a@b.org',
                        is_admin=True)
        u.set_password(USERPASS)
        u.save()
        self.login(USERNAME, USERPASS)
        resp = self.client.get('/feeds/999999', follow_redirects=False)
        self.assertEqual(resp.status_code, 302)


class TestPostpageReadPermission(StreetSignTestCase):
    ''' M3: a logged-in user with no permission on a feed must not be able
        to open that feed's posts in the editor. '''

    def setUp(self):
        super().setUp()
        self.feed = models.Feed.create(name='private feed')
        self.owner = models.User(loginname='owner', emailaddress='o@b.org',
                                 is_admin=True)
        self.owner.set_password('p')
        self.owner.save()
        self.feed.grant('Write', user=self.owner)
        self.outsider = models.User(loginname='outsider',
                                    emailaddress='x@b.org')
        self.outsider.set_password('p')
        self.outsider.save()
        # outsider has NO grants on self.feed
        self.post = models.Post.create(
            feed=self.feed, type='html',
            content=json.dumps({'content': 'secret content'}),
            author=self.owner, published=True, title='secret')

    def test_outsider_cannot_view_post_editor(self):
        self.login('outsider', 'p')
        resp = self.client.get(f'/posts/{self.post.id}',
                               follow_redirects=False)
        self.assertEqual(resp.status_code, 302)
        resp = self.client.get(f'/posts/{self.post.id}',
                               follow_redirects=True)
        self.assertNotIn(b'secret content', resp.data)

    def test_owner_can_view_post_editor(self):
        self.login('owner', 'p')
        resp = self.client.get(f'/posts/{self.post.id}')
        self.assertEqual(resp.status_code, 200)


class TestScreenDisplayTemplateWhitelist(StreetSignTestCase):
    ''' L2: /screens/<template>/<name> must reject unknown template names
        instead of forwarding them to render_template. '''

    def setUp(self):
        super().setUp()
        s = models.Screen()
        s.urlname = 'RealScreen'
        s.save()

    def test_valid_template_renders(self):
        self.validate('/screens/basic/RealScreen')

    def test_invalid_template_returns_not_found(self):
        resp = self.client.get('/screens/bogus/RealScreen')
        self.assertIn(resp.status_code, (404, 400))

    def test_path_traversal_template_rejected(self):
        resp = self.client.get('/screens/../index.html/RealScreen')
        self.assertIn(resp.status_code, (404, 400, 403))


class TestScreensPostsFromFeedsJson(StreetSignTestCase):
    ''' L3: malformed JSON in the path must not cause an unhandled 500. '''

    def test_valid_empty_list(self):
        resp = self.client.get('/screens/posts_from_feeds/%5B%5D')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(json.loads(resp.data)['posts'], [])

    def test_malformed_json_returns_empty_not_500(self):
        resp = self.client.get('/screens/posts_from_feeds/not-json-at-all')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(json.loads(resp.data)['posts'], [])

    def test_non_list_json_returns_empty(self):
        # valid JSON but a dict, not a list
        resp = self.client.get(
            '/screens/posts_from_feeds/%7B%7D')  # {}
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(json.loads(resp.data)['posts'], [])


class TestUserFilesDeleteNoFilename(StreetSignTestCase):
    ''' L4: a delete POST with no filename field must not raise TypeError. '''

    def setUp(self):
        super().setUp()
        self.admin = models.User(loginname='admin', emailaddress='a@b.org',
                                  is_admin=True)
        self.admin.set_password(USERPASS)
        self.admin.save()

    def test_delete_without_filename_does_not_500(self):
        self.login(USERNAME, USERPASS)
        with self.ctx():
            resp = self.client.post('/user_files/',
                                    data={'action': 'delete'},
                                    follow_redirects=True)
            self.assertEqual(resp.status_code, 200)


if __name__ == '__main__':
    import unittest
    unittest.main()
