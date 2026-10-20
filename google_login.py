"""Server-only Google OIDC: one-use state, browser binding and PKCE.

The Google SDK verifies signatures, audience, issuer and token times. Provider
credentials, PKCE verifiers and provider tokens are never returned to JavaScript.
"""
import base64
import hashlib
import json
import re
import secrets
import time
from urllib.parse import urlencode, urlsplit

import requests
from flask import jsonify, redirect, request, session
from google.auth import exceptions as google_errors, jwt
from google.auth.transport.requests import Request
from google.oauth2.id_token import verify_oauth2_token

from database import INTEGRITY_ERRORS

AUTHORIZE_URL = 'https://accounts.google.com/o/oauth2/v2/auth'
TOKEN_URL = 'https://oauth2.googleapis.com/token'
FLOW_LIFETIME = 300
CALLBACK_PATH = '/api/customer/google/callback'
GOOGLE_ONLY = ''  # No local password; the password route explicitly refuses it.


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


def safe_next(value):
    """Only known storefront paths; never a URL or a protocol-relative path."""
    if not isinstance(value, str) or len(value) > 1500 or any(ord(c) < 32 for c in value) or '\\' in value:
        return '/akun.html'
    try:
        parsed = urlsplit(value)
    except ValueError:
        return '/akun.html'
    if parsed.scheme or parsed.netloc or not re.fullmatch(r'/?(?:index|produk|detail|keranjang|checkout|konfirmasi|akun)\.html', parsed.path):
        return '/akun.html'
    return '/' + value.lstrip('/')


class GoogleHTTP(requests.Session):
    """TLS and finite timeouts cannot be disabled by call sites."""
    def request(self, method, url, **kwargs):
        kwargs.update(timeout=(3.05, 8), allow_redirects=False, verify=True)
        return super().request(method, url, **kwargs)


class GoogleLogin:
    def __init__(self, customers):
        self.customers = customers
        self.app, self.db, self.fail = customers.app, customers.db, customers.fail
        settings = [self.app.config.get(key, '') for key in ('GOOGLE_CLIENT_ID', 'GOOGLE_CLIENT_SECRET', 'PUBLIC_ORIGIN')]
        if not all(isinstance(value, str) for value in settings):
            raise ValueError('Konfigurasi Google harus berupa teks.')
        self.client_id, self.client_secret, origin = [value.strip() for value in settings]
        self.enabled = bool(self.client_id and self.client_secret and origin)
        if (self.client_id or self.client_secret) and not self.enabled:
            raise ValueError('Google membutuhkan Client ID, Client Secret, dan ANREDSELLER_PUBLIC_ORIGIN.')
        self.origin = origin.rstrip('/')
        if self.enabled:
            if not self.app.secret_key or len(self.app.secret_key) < 32:
                raise ValueError('Google membutuhkan kunci penandatangan sesi minimal 32 karakter.')
            parsed = urlsplit(self.origin)
            local = parsed.hostname in {'localhost', '127.0.0.1', '::1'} and parsed.scheme == 'http'
            if (not parsed.netloc or (parsed.scheme != 'https' and not local) or parsed.username or parsed.password
                    or parsed.path or parsed.query or parsed.fragment or any(c.isspace() for c in self.origin)):
                raise ValueError('ANREDSELLER_PUBLIC_ORIGIN harus berupa satu origin HTTPS tanpa path.')
            if not local and not self.app.config['SESSION_COOKIE_SECURE']:
                raise ValueError('Google produksi membutuhkan cookie Secure. Aktifkan ANREDSELLER_SECURE_COOKIES=1.')
            if not re.fullmatch(r'[A-Za-z0-9_-]+\.apps\.googleusercontent\.com', self.client_id) or len(self.client_secret) < 16:
                raise ValueError('Client ID atau Client Secret Google tidak valid.')
        self.callback = self.origin + CALLBACK_PATH
        self.register_routes()

    def error(self, code):
        # Only fixed error codes are echoed; never Google's query, token or message.
        response = redirect('/akun.html?' + urlencode({'auth': code}), code=303)
        response.headers['Referrer-Policy'] = 'no-referrer'
        return response

    def consume(self, state):
        browser = session.get('google_flow_browser', '')
        if not isinstance(state, str) or not re.fullmatch(r'[A-Za-z0-9_-]{43}', state) or not isinstance(browser, str) or not browser:
            return None
        self.db().execute('BEGIN IMMEDIATE')
        row = self.db().execute('SELECT document FROM customer_oauth_flows WHERE state_hash=? AND browser_hash=? AND expires_at>?',
                                (digest(state), digest(browser), int(time.time()))).fetchone()
        if not row:
            self.db().rollback()
            return None
        self.db().execute('DELETE FROM customer_oauth_flows WHERE state_hash=?', (digest(state),))
        self.db().commit()  # Consumed before network calls; works across Vercel workers.
        session.pop('google_flow_browser', None)
        return json.loads(row['document'])

    def verified_identity(self, code, flow):
        with GoogleHTTP() as http:
            response = http.post(TOKEN_URL, data={'code': code, 'client_id': self.client_id,
                'client_secret': self.client_secret, 'redirect_uri': self.callback,
                'grant_type': 'authorization_code', 'code_verifier': flow['verifier']})
            if response.status_code != 200 or len(response.content) > 65536:
                raise ValueError('Google exchange failed')
            payload = response.json()
            if not isinstance(payload, dict):
                raise ValueError('Invalid token response')
            token = payload.get('id_token')
            if not isinstance(token, str) or not 1 <= len(token) <= 16384 or jwt.decode_header(token).get('alg') != 'RS256':
                raise ValueError('Invalid ID token')
            claims = verify_oauth2_token(token, Request(session=http), audience=self.client_id, clock_skew_in_seconds=30)
        nonce = claims.get('nonce')
        if (not isinstance(nonce, str) or len(nonce) > 128 or not secrets.compare_digest(nonce.encode(), flow['nonce'].encode())
                or claims.get('email_verified') is not True or claims.get('aud') != self.client_id
                or claims.get('azp', self.client_id) != self.client_id):
            raise ValueError('Invalid Google identity')
        subject, email = claims.get('sub'), claims.get('email')
        if not isinstance(subject, str) or not 1 <= len(subject) <= 255:
            raise ValueError('Invalid subject')
        if not isinstance(email, str) or len(email) > 150 or not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+', email):
            raise ValueError('Invalid email')
        name = claims.get('name')
        name = name.strip()[:150] if isinstance(name, str) else ''
        return {'subject': subject, 'email': email.strip().lower(), 'name': name or email.split('@')[0]}

    def register_routes(self):
        app, customers, db = self.app, self.customers, self.db

        @app.post('/api/customer/google/start')
        def start_google():
            if not customers.require_csrf():
                return self.fail('Muat ulang halaman masuk.', 403)
            if not self.enabled:
                return self.fail('Google belum tersedia. Silakan masuk dengan email.', 503)
            if not customers.throttle('google'):
                return self.fail('Terlalu banyak percobaan. Coba lagi dalam 15 menit.', 429)
            data = customers.body()
            intent = data.get('intent', 'login')
            current = customers.current()
            if intent not in {'login', 'link'}:
                return self.fail('Pilihan masuk tidak valid.')
            if intent == 'link':
                if not current:
                    return self.fail('Masuk ke akunmu terlebih dahulu.', 401)
                if not customers.confirm_password(current, data.get('current_password')):
                    return self.fail('Kata sandi saat ini salah.', 400)
            elif current:
                return self.fail('Kamu sudah masuk. Hubungkan Google dari halaman akun.', 409)
            state, browser = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
            flow = {'intent': intent, 'customer_id': current['id'] if current else None,
                    'sid_hash': digest(session.get('customer_sid', '')), 'nonce': secrets.token_urlsafe(32),
                    'verifier': secrets.token_urlsafe(32), 'next': safe_next(data.get('next'))}
            old_browser = session.get('google_flow_browser', '')
            db().execute('DELETE FROM customer_oauth_flows WHERE expires_at<? OR browser_hash=?', (int(time.time()), digest(old_browser)))
            db().execute('INSERT INTO customer_oauth_flows VALUES(?,?,?,?)',
                         (digest(state), digest(browser), json.dumps(flow), int(time.time()) + FLOW_LIFETIME))
            db().commit()
            session['google_flow_browser'] = browser
            challenge = base64.urlsafe_b64encode(hashlib.sha256(flow['verifier'].encode()).digest()).rstrip(b'=').decode()
            params = {'client_id': self.client_id, 'redirect_uri': self.callback, 'response_type': 'code',
                      'scope': 'openid email profile', 'state': state, 'nonce': flow['nonce'],
                      'code_challenge': challenge, 'code_challenge_method': 'S256', 'prompt': 'select_account'}
            return jsonify(url=AUTHORIZE_URL + '?' + urlencode(params))

        @app.get(CALLBACK_PATH)
        def finish_google():
            if not self.enabled:
                return self.error('google-unavailable')
            # Query parameter ambiguity must not select a different state/code.
            if any(len(request.args.getlist(key)) > 1 for key in ('state', 'code', 'error')):
                return self.error('google-invalid')
            flow = self.consume(request.args.get('state'))
            if not flow:
                return self.error('google-invalid')
            if request.args.get('error'):
                return self.error('google-cancelled')
            code = request.args.get('code', '')
            if not 1 <= len(code) <= 4096:
                return self.error('google-invalid')
            try:
                identity = self.verified_identity(code, flow)
            except (ValueError, TypeError, KeyError, requests.RequestException, google_errors.GoogleAuthError):
                return self.error('google-failed')
            db().execute('BEGIN IMMEDIATE')
            existing = db().execute('SELECT customer_id FROM customer_google_identities WHERE subject=?', (identity['subject'],)).fetchone()
            current = customers.current()
            try:
                if flow['intent'] == 'link':
                    if (not current or current['id'] != flow['customer_id']
                            or not secrets.compare_digest(flow['sid_hash'], digest(session.get('customer_sid', '')))):
                        db().rollback()
                        return self.error('google-invalid')
                    if current['email'].lower() != identity['email'] or (existing and existing['customer_id'] != current['id']):
                        db().rollback()
                        return self.error('google-link-mismatch')
                    customer_id = current['id']
                    if not existing:
                        db().execute('INSERT INTO customer_google_identities VALUES(?,?,?)', (identity['subject'], customer_id, int(time.time())))
                else:
                    if current:
                        db().rollback()
                        return self.error('google-invalid')
                    if existing:
                        customer_id = existing['customer_id']
                    elif db().execute('SELECT id FROM customers WHERE lower(email)=?', (identity['email'],)).fetchone():
                        db().rollback()
                        return self.error('google-email-exists')
                    else:
                        cursor = db().execute('INSERT INTO customers(email,password_hash,nama,nohp,created_at) VALUES(?,?,?,?,?)',
                                              (identity['email'], GOOGLE_ONLY, identity['name'], '', int(time.time())))
                        customer_id = cursor.lastrowid
                        db().execute('INSERT INTO customer_google_identities VALUES(?,?,?)', (identity['subject'], customer_id, int(time.time())))
                customers.start_session(customer_id)
                db().commit()
            except INTEGRITY_ERRORS:
                db().rollback()
                return self.error('google-email-exists')
            response = redirect('/akun.html?' + urlencode({'auth': 'google-success', 'next': flow['next']}), code=303)
            response.headers['Referrer-Policy'] = 'no-referrer'
            return response

        @app.post('/api/customer/google/unlink')
        @customers.required
        def unlink_google():
            if not self.enabled:
                return self.fail('Google belum tersedia.', 503)
            if not customers.throttle('google-unlink'):
                return self.fail('Terlalu banyak percobaan. Coba lagi dalam 15 menit.', 429)
            db().execute('BEGIN IMMEDIATE')
            current = customers.current()
            if not current:
                db().rollback()
                return self.fail('Masuk ke akunmu terlebih dahulu.', 401)
            if not customers.confirm_password(current, customers.body().get('current_password')):
                db().rollback()
                return self.fail('Kata sandi saat ini salah.', 400)
            db().execute('DELETE FROM customer_google_identities WHERE customer_id=?', (current['id'],))
            db().execute('DELETE FROM customer_sessions WHERE customer_id=?', (current['id'],))
            customers.start_session(current['id'])
            db().commit()
            return jsonify(ok=True, csrf=customers.csrf(), customer=customers.profile(customers.current()))
