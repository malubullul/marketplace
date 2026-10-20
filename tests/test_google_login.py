"""Real RSA signature verification with mocked Google HTTP, never live accounts."""
import base64
import hashlib
import json
import secrets
import tempfile
import time
import unittest
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

import requests
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from google.auth import crypt, jwt

from server import create_app
from google_login import safe_next

CLIENT = 'anredseller-tests.apps.googleusercontent.com'
SETTINGS = {'GOOGLE_CLIENT_ID': CLIENT, 'GOOGLE_CLIENT_SECRET': 'only-a-disposable-test-secret',
            'PUBLIC_ORIGIN': 'https://shop.example.test', 'SESSION_COOKIE_SECURE': True}
CERT_URL = 'https://www.googleapis.com/oauth2/v1/certs'


class GoogleLoginTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        private = key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption())
        cls.signer = crypt.RSASigner.from_string(private)
        cls.public_key = key.public_key().public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo).decode()

    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.app = create_app({'TESTING': True, 'DATA_DIR': self.directory.name, **SETTINGS})
        self.client = self.app.test_client()
        self.password = secrets.token_urlsafe(24)
        self.counter = 0

    def tearDown(self):
        self.directory.cleanup()

    def start(self, client=None, **body):
        client = client or self.client
        csrf = client.get('/api/customer/session').json['csrf']
        self.counter += 1
        result = client.post('/api/customer/google/start', json=body, headers={'X-CSRF-Token': csrf},
                             environ_overrides={'REMOTE_ADDR': f'192.0.2.{self.counter}'})
        self.assertEqual(result.status_code, 200, result.json)
        params = {key: value[0] for key, value in parse_qs(urlsplit(result.json['url']).query).items()}
        with self.app.app_context():
            record = self.app.get_db().execute('SELECT document FROM customer_oauth_flows WHERE state_hash=?',
                                               (hashlib.sha256(params['state'].encode()).hexdigest(),)).fetchone()
            flow = json.loads(record['document'])
        self.assertNotIn(flow['verifier'], result.data.decode())
        self.assertEqual(params['code_challenge'], base64.urlsafe_b64encode(hashlib.sha256(flow['verifier'].encode()).digest()).rstrip(b'=').decode())
        self.assertEqual(params['code_challenge_method'], 'S256')
        self.assertEqual(params['redirect_uri'], SETTINGS['PUBLIC_ORIGIN'] + '/api/customer/google/callback')
        return params, flow

    def register(self, email='existing@example.test'):
        csrf = self.client.get('/api/customer/session').json['csrf']
        response = self.client.post('/api/customer/register', json={'email': email, 'nama': 'Existing buyer',
            'nohp': '081234567890', 'password': self.password}, headers={'X-CSRF-Token': csrf})
        self.assertEqual(response.status_code, 201, response.json)
        return response.json['customer']['id']

    def claims(self, params, **changes):
        now = int(time.time())
        claims = {'iss': 'https://accounts.google.com', 'aud': CLIENT, 'sub': 'google-subject-123',
                  'iat': now, 'exp': now + 300, 'email': 'google@example.test', 'email_verified': True,
                  'name': 'Google buyer', 'nonce': params['nonce']}
        claims.update(changes)
        for key in [key for key, value in claims.items() if value is None]:
            claims.pop(key)
        return claims

    def callback(self, params, claims=None, client=None, token=None, http_status=200):
        claims = claims or self.claims(params)
        token = token or jwt.encode(self.signer, claims, key_id='test-key').decode()
        calls = []
        def network(http, method, url, **kwargs):
            calls.append((method, url, kwargs))
            self.assertTrue(kwargs['verify'])
            self.assertFalse(kwargs['allow_redirects'])
            self.assertEqual(kwargs['timeout'], (3.05, 8))
            response = requests.Response()
            response.status_code = http_status if url == 'https://oauth2.googleapis.com/token' else 200
            if url == 'https://oauth2.googleapis.com/token':
                payload = {'id_token': token, 'access_token': 'must-never-reach-browser', 'refresh_token': 'never-stored'}
            elif url == CERT_URL:
                payload = {'test-key': self.public_key}
            else:
                raise AssertionError('Unexpected network destination: ' + url)
            response._content = json.dumps(payload).encode()
            response.headers['Content-Type'] = 'application/json'
            return response
        with patch('requests.Session.request', autospec=True, side_effect=network):
            response = (client or self.client).get('/api/customer/google/callback', query_string={'state': params['state'], 'code': 'one-use-code'})
        for sensitive in ['must-never-reach-browser', 'never-stored', token, SETTINGS['GOOGLE_CLIENT_SECRET']]:
            self.assertNotIn(sensitive, response.data.decode() + response.location)
        return response, calls

    def test_google_signup_is_verified_customer_only_and_no_local_password(self):
        params, flow = self.start(next='checkout.html')
        response, calls = self.callback(params, self.claims(params, role='owner'))
        self.assertIn('auth=google-success', response.location)
        self.assertIn('next=%2Fcheckout.html', response.location)
        profile = self.client.get('/api/customer/profile').json['customer']
        self.assertEqual(profile['email'], 'google@example.test')
        self.assertFalse(profile['has_password']); self.assertTrue(profile['google_linked'])
        self.assertEqual(self.client.get('/api/admin/products').status_code, 401)
        self.assertEqual(calls[0][2]['data']['code_verifier'], flow['verifier'])
        with self.app.app_context():
            db = self.app.get_db()
            row = db.execute('SELECT * FROM customers WHERE id=?', (profile['id'],)).fetchone()
            self.assertEqual(row['password_hash'], '')
            self.assertEqual(db.execute('SELECT COUNT(*) FROM customer_oauth_flows').fetchone()[0], 0)
        second = self.app.test_client(); csrf = second.get('/api/customer/session').json['csrf']
        self.assertEqual(second.post('/api/customer/login', json={'email': 'google@example.test', 'password': ''}, headers={'X-CSRF-Token': csrf}).status_code, 401)
        self.assertEqual(self.client.post('/api/customer/google/unlink', json={'current_password': ''}, headers={'X-CSRF-Token': self.client.get('/api/customer/session').json['csrf']}).status_code, 400)

    def test_invalid_signed_claims_never_create_an_account(self):
        cases = [{'aud': 'somebody-else'}, {'iss': 'https://attacker.example'}, {'exp': 1}, {'iat': int(time.time()) + 600},
                 {'nonce': 'wrong'}, {'nonce': None}, {'email_verified': False}, {'email_verified': 'true'},
                 {'email_verified': None}, {'sub': None}, {'email': None}, {'azp': 'another-client'}]
        for changes in cases:
            with self.subTest(changes=changes):
                params, _ = self.start()
                response, _ = self.callback(params, self.claims(params, **changes))
                self.assertIn('google-failed', response.location)
                self.assertFalse(self.client.get('/api/customer/session').json['authenticated'])
        with self.app.app_context():
            self.assertEqual(self.app.get_db().execute('SELECT COUNT(*) FROM customers').fetchone()[0], 0)

    def test_unsigned_wrong_key_and_algorithm_confusion_tokens_fail(self):
        for mode in ['unsigned', 'wrong-key', 'HS256']:
            params, _ = self.start()
            if mode == 'wrong-key':
                private = rsa.generate_private_key(public_exponent=65537, key_size=2048).private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption())
                token = jwt.encode(crypt.RSASigner.from_string(private), self.claims(params), key_id='test-key').decode()
            else:
                enc = lambda value: base64.urlsafe_b64encode(json.dumps(value).encode()).rstrip(b'=').decode()
                token = enc({'alg': 'none' if mode == 'unsigned' else 'HS256'}) + '.' + enc(self.claims(params)) + '.forged'
            response, _ = self.callback(params, token=token)
            self.assertIn('google-failed', response.location)
            self.assertEqual(self.client.get('/api/customer/profile').status_code, 401)

    def test_browser_binding_expiry_duplicate_parameters_and_single_use(self):
        params, _ = self.start()
        other = self.app.test_client()
        response, calls = self.callback(params, client=other)
        self.assertIn('google-invalid', response.location); self.assertFalse(calls)
        cookie = self.client.get_cookie('session').value
        duplicated = self.client.get('/api/customer/google/callback?state=' + params['state'] + '&state=other&code=x')
        self.assertIn('google-invalid', duplicated.location)
        success, _ = self.callback(params); self.assertIn('google-success', success.location)
        replay = self.app.test_client(); replay.set_cookie('session', cookie)
        response, calls = self.callback(params, client=replay)
        self.assertIn('google-invalid', response.location); self.assertFalse(calls)
        self.assertEqual(replay.get('/api/customer/profile').status_code, 401)
        params, _ = self.start(client=other)
        with self.app.app_context():
            self.app.get_db().execute('UPDATE customer_oauth_flows SET expires_at=?', (int(time.time()) - 1,)); self.app.get_db().commit()
        response, calls = self.callback(params, client=other)
        self.assertIn('google-invalid', response.location); self.assertFalse(calls)

    def test_email_collision_does_not_merge_accounts_and_link_needs_password(self):
        owner_id = self.register('google@example.test')
        csrf = self.client.get('/api/customer/session').json['csrf']
        self.assertEqual(self.client.post('/api/customer/google/start', json={'intent': 'link', 'current_password': 'wrong'}, headers={'X-CSRF-Token': csrf}).status_code, 400)
        new_browser = self.app.test_client(); params, _ = self.start(client=new_browser)
        collision, _ = self.callback(params, client=new_browser)
        self.assertIn('google-email-exists', collision.location)
        self.assertFalse(new_browser.get('/api/customer/session').json['authenticated'])
        params, _ = self.start(intent='link', current_password=self.password)
        linked, _ = self.callback(params)
        self.assertIn('google-success', linked.location)
        self.assertEqual(self.client.get('/api/customer/profile').json['customer']['id'], owner_id)
        params, _ = self.start(client=new_browser)
        self.callback(params, client=new_browser)
        self.assertEqual(new_browser.get('/api/customer/profile').json['customer']['id'], owner_id)
        csrf = self.client.get('/api/customer/session').json['csrf']
        result = self.client.post('/api/customer/google/unlink', json={'current_password': self.password}, headers={'X-CSRF-Token': csrf})
        self.assertEqual(result.status_code, 200, result.json)
        self.assertFalse(result.json['customer']['google_linked'])
        self.assertEqual(new_browser.get('/api/customer/profile').status_code, 401)
        self.assertEqual(self.client.get('/api/customer/profile').status_code, 200)

    def test_link_cannot_cross_email_or_survive_logout(self):
        self.register()
        params, _ = self.start(intent='link', current_password=self.password)
        mismatch, _ = self.callback(params)
        self.assertIn('google-link-mismatch', mismatch.location)
        params, _ = self.start(intent='link', current_password=self.password)
        csrf = self.client.get('/api/customer/session').json['csrf']
        self.client.post('/api/customer/logout', headers={'X-CSRF-Token': csrf})
        rejected, _ = self.callback(params, self.claims(params, email='existing@example.test'))
        self.assertIn('google-invalid', rejected.location)
        self.assertFalse(self.client.get('/api/customer/session').json['authenticated'])

    def test_repeated_subject_is_stable_and_does_not_claim_another_email(self):
        params, _ = self.start(); self.callback(params)
        first_id = self.client.get('/api/customer/profile').json['customer']['id']
        another = self.app.test_client(); params, _ = self.start(client=another)
        self.callback(params, self.claims(params, email='updated@example.test'), client=another)
        profile = another.get('/api/customer/profile').json['customer']
        self.assertEqual(profile['id'], first_id)
        self.assertEqual(profile['email'], 'google@example.test')
        self.assertEqual(another.get('/api/customer/orders').json['orders'], [])

    def test_csrf_throttle_cancel_and_provider_failure(self):
        self.assertEqual(self.client.post('/api/customer/google/start', json={}).status_code, 403)
        self.assertIn(self.client.get('/api/customer/google/start').status_code, {404, 405})
        params, _ = self.start()
        cancelled = self.client.get('/api/customer/google/callback', query_string={'state': params['state'], 'error': 'access_denied', 'error_description': 'untrusted-provider-text'})
        self.assertIn('google-cancelled', cancelled.location)
        self.assertNotIn('untrusted-provider-text', cancelled.location)
        response, calls = self.callback(params); self.assertFalse(calls)
        params, _ = self.start(); failed, _ = self.callback(params, http_status=500)
        self.assertIn('google-failed', failed.location)
        self.assertEqual(failed.headers['Referrer-Policy'], 'no-referrer')
        self.assertIn('no-store', failed.headers['Cache-Control'])
        csrf = self.client.get('/api/customer/session').json['csrf']
        for _ in range(10):
            self.assertEqual(self.client.post('/api/customer/google/start', json={}, headers={'X-CSRF-Token': csrf}).status_code, 200)
        self.assertEqual(self.client.post('/api/customer/google/start', json={}, headers={'X-CSRF-Token': csrf}).status_code, 429)
        self.assertEqual(self.client.get('/google_login.py').status_code, 404)

    def test_configuration_fails_closed(self):
        invalid = [{'GOOGLE_CLIENT_SECRET': ''}, {'PUBLIC_ORIGIN': '//attacker.example'},
                   {'PUBLIC_ORIGIN': 'http://shop.example.test'}, {'PUBLIC_ORIGIN': 'https://shop.example.test/redirect'},
                   {'SESSION_COOKIE_SECURE': False}, {'GOOGLE_CLIENT_ID': 'wrong'}, {'GOOGLE_CLIENT_SECRET': 'short'}, {'SESSION_SECRET':'short'}]
        for changes in invalid:
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                create_app({'TESTING': True, 'DATA_DIR': self.directory.name, **SETTINGS, **changes})
        disabled = create_app({'TESTING': True, 'DATA_DIR': self.directory.name}).test_client()
        session = disabled.get('/api/customer/session').json
        self.assertFalse(session['providers']['google'])
        self.assertEqual(disabled.post('/api/customer/google/start', json={}, headers={'X-CSRF-Token': session['csrf']}).status_code, 503)

    def test_redirect_targets_and_host_headers_cannot_choose_callback(self):
        for value in ['https://attacker.example', '//attacker.example', '//[', 'javascript:alert(1)', '/admin.html', '/api/admin/products', '/%2f%2fattacker.example', '/akun.html\r\nLocation: https://attacker.example', '\\attacker.example', None, {}, 42]:
            with self.subTest(value=value):self.assertEqual(safe_next(value), '/akun.html')
        self.assertEqual(safe_next('detail.html?id=1'), '/detail.html?id=1')
        csrf = self.client.get('/api/customer/session').json['csrf']
        raw = self.app.test_client(use_cookies=False)
        result = raw.post('/api/customer/google/start', json={'next':'//attacker.example'}, headers={
            'Host':'attacker.example', 'X-Forwarded-Host':'other.example',
            'Cookie':'session='+self.client.get_cookie('session').value, 'X-CSRF-Token':csrf})
        self.assertEqual(result.status_code, 200, result.json)
        self.assertEqual(parse_qs(urlsplit(result.json['url']).query)['redirect_uri'], [SETTINGS['PUBLIC_ORIGIN']+'/api/customer/google/callback'])
        self.assertNotIn(SETTINGS['GOOGLE_CLIENT_SECRET'], result.data.decode())
