'''
    Focused regressions for security-sensitive display and deployment behavior.
'''

from os.path import dirname, join as pathjoin

import streetsign_server.post_types.external_webpage as external_webpage
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
