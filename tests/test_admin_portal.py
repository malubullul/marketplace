from order_workflow import advance
import importlib.util
import io
from pathlib import Path
import secrets
import tempfile
import threading
import unittest

from flask import Flask, redirect
from PIL import Image
from werkzeug.serving import make_server, WSGIRequestHandler
from server import create_app, create_owner

spec = importlib.util.spec_from_file_location('standalone_admin', Path(__file__).resolve().parents[1] / 'admin-portal/app.py')
portal_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(portal_module)


class QuietHandler(WSGIRequestHandler):
    def log_request(self, *args):
        pass


class AdminPortalTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.key, self.password = secrets.token_urlsafe(40), secrets.token_urlsafe(24)
        self.backend = create_app({'TESTING':True, 'DATA_DIR':self.directory.name,
                                   'ADMIN_GATEWAY_KEY':self.key, 'ADMIN_PORTAL_URL':'https://owner.example.test'})
        create_owner(self.backend, 'owner@example.test', self.password)
        self.http = make_server('127.0.0.1', 0, self.backend, threaded=True, request_handler=QuietHandler)
        self.thread = threading.Thread(target=self.http.serve_forever, daemon=True)
        self.thread.start()
        self.addCleanup(self.stop)
        self.portal = portal_module.create_app({'TESTING':True, 'BACKEND_URL':f'http://127.0.0.1:{self.http.server_port}',
                                                'SHOP_URL':'https://shop.example.test', 'ADMIN_GATEWAY_KEY':self.key,
                                                'SECURE_COOKIES':False})
        self.client = self.portal.test_client()
        self.public = self.backend.test_client()

    def stop(self):
        self.http.shutdown()
        self.thread.join(timeout=5)
        self.http.server_close()

    def login(self):
        session = self.client.get('/api/session')
        self.assertEqual(session.status_code, 200, session.json)
        response = self.client.post('/api/login', json={'email':'owner@example.test', 'password':self.password},
                                    headers={'X-CSRF-Token':session.json['csrf']})
        self.assertEqual(response.status_code, 200, response.json)
        return {'X-CSRF-Token':response.json['csrf']}

    def test_separate_routes_no_secret_exposure_and_public_admin_lock(self):
        for path in ['/', '/admin', '/admin.html', '/css/admin.css', '/js/admin.js', '/assets/archive-campaign.png']:
            response = self.client.get(path)
            self.assertEqual(response.status_code, 200, path)
            self.assertNotIn(self.key.encode(), response.data)
            response.close()
        self.assertEqual(self.client.get('/portal-config').json, {'shop_url':'https://shop.example.test'})
        for path in ['/produk.html', '/akun', '/api/customer/session', '/api/orders', '/server.py', '/.env', '/app.py']:
            self.assertEqual(self.client.get(path).status_code, 404, path)
        self.assertEqual(self.public.get('/api/products').status_code, 200)
        self.assertEqual(self.public.get('/admin').location, 'https://owner.example.test/')
        self.assertEqual(self.public.get('/admin.html').location, 'https://owner.example.test/')
        self.assertEqual(self.public.get('/css/admin.css').status_code, 404)
        for path in ['/api/session', '/api/admin/products', '/api/admin/orders']:
            self.assertEqual(self.public.get(path).status_code, 401)
        self.assertEqual(self.client.get('/api/health').json['status'], 'ok')

    def test_contacts_configuration_uses_authenticated_admin_gateway(self):
        self.assertEqual(self.client.get('/api/admin/contacts').status_code, 401)
        headers = self.login()
        payload = {'payment_whatsapp':'081234567890', 'support_whatsapp':'+62 823 4567 8901'}
        self.assertEqual(self.client.put('/api/admin/contacts', json=payload).status_code, 403)
        response = self.client.put('/api/admin/contacts', json=payload, headers=headers)
        self.assertEqual(response.status_code, 200, response.json)
        expected = {'payment_whatsapp':'6281234567890', 'support_whatsapp':'6282345678901'}
        self.assertEqual(self.public.get('/api/store/contacts').json['contacts'], expected)
        self.assertEqual(self.client.get('/api/admin/contacts').json['contacts'], expected)
        self.assertEqual(self.public.put('/api/admin/contacts', json=payload, headers=headers).status_code, 401)
        self.assertEqual(self.client.put('/api/admin/contacts', json=payload,
            headers={**headers, 'Origin':'https://untrusted.example.test'}).status_code, 403)

    def test_login_csrf_cookie_and_logout_revocation(self):
        self.assertEqual(self.client.get('/api/admin/products').status_code, 401)
        self.assertEqual(self.client.post('/api/login', json={}).status_code, 403)
        headers = self.login()
        self.assertTrue(self.client.get('/api/session').json['authenticated'])
        cookie = self.client.get_cookie('anredseller_admin')
        self.assertTrue(cookie.http_only)
        self.assertEqual(cookie.same_site, 'Lax')
        self.assertIsNone(self.client.get_cookie('session'))
        self.assertEqual(self.client.post('/api/logout').status_code, 403)
        # A cross-site request is rejected even when it contains a valid CSRF token.
        self.assertEqual(self.client.post('/api/logout', headers={**headers, 'Origin':'https://untrusted.example'}).status_code, 403)
        self.assertEqual(self.client.post('/api/logout', headers=headers).status_code, 200)
        replay = self.portal.test_client()
        replay.set_cookie('anredseller_admin', cookie.value)
        self.assertEqual(replay.get('/api/admin/products').status_code, 401)

    def test_product_drafts_photo_publish_and_delete_share_one_catalog(self):
        headers = self.login()
        image = io.BytesIO()
        Image.new('RGB', (40,40), '#6f765e').save(image, 'PNG')
        image.seek(0)
        response = self.client.post('/api/admin/uploads', data={'photo':(image,'photo.png')}, headers=headers)
        self.assertEqual(response.status_code, 201, response.json)
        photo = response.json['url']
        self.assertEqual(self.client.get(photo).status_code, 200)
        data = dict(nama='Produk Portal Terpisah', kategori='apparel', brand='Anredseller', deskripsi='Foto dan data produk dari domain admin.',
                    harga=299000, hargaAsli=349000, stok=4, gambarList=[photo], ukuran=['S'], warna=['Hitam'], published=False)
        response = self.client.post('/api/admin/products', json=data, headers=headers)
        self.assertEqual(response.status_code, 201, response.json)
        product = response.json['product']
        self.assertFalse(any(p['id']==product['id'] for p in self.public.get('/api/products').json['products']))
        data.update(published=True, version=product['version'])
        response = self.client.put('/api/admin/products/'+str(product['id']), json=data, headers=headers)
        self.assertEqual(response.status_code, 200, response.json)
        self.assertTrue(any(p['id']==product['id'] for p in self.public.get('/api/products').json['products']))
        self.assertEqual(self.client.delete('/api/admin/products/'+str(product['id']), headers=headers).status_code, 200)

    def test_public_buyer_order_enters_portal_and_status_returns_to_buyer(self):
        csrf = self.public.get('/api/customer/session').json['csrf']
        buyer = self.public.post('/api/customer/register', json={'nama':'Pembeli Uji', 'nohp':'081234567890',
                    'email':'buyer@example.test', 'password':secrets.token_urlsafe(24)}, headers={'X-CSRF-Token':csrf})
        product = self.public.get('/api/products').json['products'][0]
        response = self.public.post('/api/orders', json={
            'customer':{'nama_penerima':'Penerima Uji','nohp':'081234567890','alamat':'Jl. Uji 1','kota':'Jakarta','provinsi':'DKI Jakarta','kodepos':'12345'},
            'items':[{'id':product['id'],'jumlah':1,'harga':product['harga']}]},
            headers={'X-CSRF-Token':buyer.json['csrf'], 'Idempotency-Key':secrets.token_hex(16)})
        self.assertEqual(response.status_code, 201, response.json)
        number = response.json['order']['nomor']
        headers = self.login()
        self.assertEqual(self.client.get('/api/admin/orders').json['orders'][0]['nomor'], number)
        advance(self.client,headers,number,'diproses')
        self.assertEqual(self.public.get('/api/customer/orders/'+number).json['order']['status'], 'diproses')

    def test_missing_configuration_invalid_origins_and_secure_cookie(self):
        unconfigured = portal_module.create_app({'BACKEND_URL':'', 'SHOP_URL':'', 'ADMIN_GATEWAY_KEY':''}).test_client()
        self.assertEqual(unconfigured.get('/api/health').status_code, 503)
        self.assertEqual(unconfigured.get('/api/session').status_code, 503)
        for url in ['https://example.test/path', 'http://example.test', 'https://user:password@example.test', 'https://example.test?url=x']:
            with self.assertRaises(ValueError):portal_module.create_app({'BACKEND_URL':url})
        with self.assertRaises(ValueError):create_app({'DATA_DIR':self.directory.name, 'ADMIN_PORTAL_URL':'https://admin.example.test', 'ADMIN_GATEWAY_KEY':''})
        secure = portal_module.create_app({**self.portal.config, 'SECURE_COOKIES':True}).test_client()
        response = secure.get('/api/session')
        self.assertIn('Secure;', response.headers['Set-Cookie'])
        self.assertIn('HttpOnly;', response.headers['Set-Cookie'])

    def test_upstream_redirects_are_not_followed(self):
        other = Flask('redirect_test')
        visited = []
        other.add_url_rule('/api/session', endpoint='session', view_func=lambda:redirect('/capture'))
        other.add_url_rule('/capture', endpoint='capture', view_func=lambda:visited.append(True) or 'unexpected')
        http = make_server('127.0.0.1',0,other,threaded=True,request_handler=QuietHandler)
        thread = threading.Thread(target=http.serve_forever,daemon=True)
        thread.start()
        try:
            portal = portal_module.create_app({**self.portal.config, 'BACKEND_URL':f'http://127.0.0.1:{http.server_port}'})
            self.assertEqual(portal.test_client().get('/api/session').status_code, 502)
            self.assertEqual(visited, [])
        finally:
            http.shutdown();thread.join(timeout=5);http.server_close()
