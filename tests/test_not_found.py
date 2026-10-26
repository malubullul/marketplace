"""HTTP error rendering must not turn missing URLs into successful/API HTML responses."""
import tempfile
import unittest
from unittest.mock import patch

from server import ROOT, configuration_app, create_app


class NotFoundTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.app = create_app({'TESTING': True, 'DATA_DIR': directory.name, 'DATABASE_URL': ''})
        self.client = self.app.test_client()

    def test_missing_pages_have_real_404_status_and_working_fallback_links(self):
        for path in ['/tidak-ada', '/koleksi/lama/produk', '/404.html', '/missing?next=https://evil.example/']:
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 404)
                self.assertEqual(response.mimetype, 'text/html')
                self.assertEqual(response.headers['Cache-Control'], 'no-store')
                self.assertEqual(response.headers['X-Robots-Tag'], 'noindex')
                html = response.get_data(as_text=True)
                self.assertIn('Halaman ini tidak ditemukan', html)
                self.assertIn('href="/"', html)
                self.assertIn('href="/produk.html"', html)
                self.assertIn('src="/js/generated/error-page.js?', html)
                self.assertNotIn('evil.example', html)
        head = self.client.head('/missing')
        self.assertEqual(head.status_code, 404)
        self.assertFalse(head.data)

    def test_api_errors_remain_json_and_method_errors_remain_405(self):
        for path in ['/api/missing', '/api/customer/missing', '/api']:
            response = self.client.get(path, headers={'Accept': 'text/html'})
            self.assertEqual(response.status_code, 404)
            self.assertEqual(response.mimetype, 'application/json')
            self.assertEqual(response.json, {'error': 'Data tidak ditemukan.'})
        response = self.client.post('/missing')
        self.assertEqual(response.status_code, 405)
        self.assertNotIn(b'error-page.js', response.data)

    def test_missing_assets_and_private_sources_do_not_become_public_files(self):
        for path in ['/js/absent.js', '/css/absent.css', '/assets/absent.webp']:
            response = self.client.get(path)
            self.assertEqual(response.status_code, 404)
            self.assertNotIn(b'error-page.js', response.data)
            self.assertEqual(response.headers['X-Content-Type-Options'], 'nosniff')
        for path in ['/server.py', '/package.json', '/package-lock.json', '/components/ui/button.tsx', '/lib/utils.ts', '/.env', '/node_modules/react/index.js']:
            response = self.client.get(path)
            self.assertEqual(response.status_code, 404)
            self.assertEqual(response.data, (ROOT / '404.html').read_bytes())

    def test_error_page_does_not_require_database_and_assets_are_available(self):
        with patch('server.sqlite3.connect', side_effect=AssertionError('404 must not connect to DB')):
            self.assertEqual(self.client.get('/missing').status_code, 404)
        for path, mime in [('/js/generated/error-page.js', 'text/javascript'), ('/css/generated/error-page.css', 'text/css')]:
            with self.client.get(path) as response:
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.mimetype, mime)
        self.assertIn("script-src 'self'", self.client.get('/missing').headers['Content-Security-Policy'])
        self.assertNotIn(b'/js/generated/error-page.js', self.client.get('/').data)

    def test_configuration_fallback_also_has_404_without_misreporting_api_status(self):
        pending = configuration_app().test_client()
        self.assertEqual(pending.get('/missing').status_code, 404)
        self.assertEqual(pending.get('/missing').data, self.client.get('/missing').data)
        self.assertEqual(pending.get('/api/products').status_code, 503)
        self.assertTrue(pending.get('/api/products').is_json)
        with pending.get('/css/generated/error-page.css') as css:
            self.assertEqual(css.status_code, 200)


if __name__ == '__main__':
    unittest.main()
