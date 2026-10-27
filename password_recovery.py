"""Single-use password recovery, delivered by a fixed HTTPS email provider."""
import hashlib
import json
import re
import secrets
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

from flask import g, jsonify, session
from werkzeug.security import generate_password_hash


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        # Never forward the email API credential to a redirected host.
        return None


class RecoveryMailer:
    def __init__(self, app):
        self.key = app.config['RESEND_API_KEY']
        self.sender = app.config['EMAIL_FROM']
        self.origin = app.config['PUBLIC_URL'].rstrip('/')
        self.enabled = bool(self.key and self.sender and self.origin)
        if any((self.key, self.sender)):
            origin = urlsplit(self.origin)
            if (not self.enabled or not re.fullmatch(r're_[A-Za-z0-9_-]{10,200}', self.key)
                    or not re.fullmatch(r'[A-Za-z0-9.!#$%&\'*+/=?^_`{|}~-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}', self.sender)
                    or origin.scheme != 'https' or not origin.hostname
                    or origin.username or origin.password or origin.path or origin.query or origin.fragment):
                raise ValueError('Pemulihan email membutuhkan RESEND_API_KEY, ANREDSELLER_EMAIL_FROM valid, dan ANREDSELLER_PUBLIC_URL berupa origin HTTPS.')

    def send(self, email, token):
        # Fragment is not sent in HTTP requests, access logs, or referrer headers.
        link = self.origin + '/akun.html#reset=' + token
        payload = {'from': self.sender, 'to': [email], 'subject': 'Atur ulang kata sandi Anredseller',
                   'text': 'Ada permintaan untuk mengatur ulang kata sandi.\n\n'
                           'Jika email ini terdaftar di Anredseller, gunakan tautan berikut dalam 30 menit:\n'
                           + link + '\n\nTautan hanya dapat dipakai sekali. Setelah berhasil, semua perangkat akan keluar. '
                           'Jika kamu tidak meminta perubahan ini, abaikan email ini. Kata sandimu tetap sama.'}
        self.deliver(payload)

    def send_verification(self, email, token):
        self.deliver({'from': self.sender, 'to': [email], 'subject': 'Verifikasi email Anredseller',
                      'text': 'Untuk mengaktifkan atau memverifikasi akun Anredseller, buka tautan berikut dalam 30 menit dan tentukan kata sandi baru. Semua sesi lama akan keluar.\n\n'
                      + self.origin + '/akun.html#verify=' + token + '\n\nJika kamu tidak meminta ini, abaikan email ini. Tautan hanya berlaku sekali.'})

    def deliver(self, payload):
        request_ = Request('https://api.resend.com/emails', data=json.dumps(payload).encode(),
                           headers={'Authorization': 'Bearer ' + self.key, 'Content-Type': 'application/json',
                                    'User-Agent': 'Anredseller/1.0'}, method='POST')
        try:
            with build_opener(NoRedirect()).open(request_, timeout=10) as response:
                result = json.loads(response.read(4096))
                if response.status != 200 or not isinstance(result, dict) or not isinstance(result.get('id'), str) or not result['id']:
                    raise ValueError('Email provider rejected delivery')
        except (HTTPError, URLError, TimeoutError, OSError, ValueError):
            # Do not propagate provider bodies, credentials, recipient, or reset URL.
            raise RuntimeError('Pengiriman email belum tersedia.') from None


class PasswordRecovery:
    def __init__(self, app, db, customers, fail, body):
        self.db, self.postgres = db, bool(app.config['DATABASE_URL'])
        mailer = RecoveryMailer(app)
        app.extensions['recovery_mailer'] = mailer
        app.extensions['password_recovery'] = self
        if not app.config['DATABASE_URL']:
            with app.app_context():
                db().executescript('''
                    CREATE TABLE IF NOT EXISTS password_resets (
                        token_hash TEXT PRIMARY KEY,
                        customer_id INTEGER REFERENCES customers(id) ON DELETE CASCADE,
                        expires_at INTEGER NOT NULL);
                    CREATE INDEX IF NOT EXISTS password_resets_customer ON password_resets(customer_id);
                    CREATE INDEX IF NOT EXISTS password_resets_expiry ON password_resets(expires_at);
                ''')
                db().commit()

        generic = 'Jika email ini terdaftar, tautan pemulihan dapat digunakan dari kotak masuk. Periksa juga folder spam.'

        @app.post('/api/customer/forgot-password')
        def forgot_password():
            if not customers.require_csrf():
                return fail('Muat ulang formulir pemulihan.', 403)
            if not mailer.enabled or not self.ready():
                return fail('Pemulihan lewat email belum aktif. Hubungi CS untuk bantuan akun.', 503)
            email = body().get('email', '')
            if not isinstance(email, str) or len(email) > 150 or not re.fullmatch(r'[^\s@\x00-\x1f]+@[^\s@\x00-\x1f]+\.[^\s@\x00-\x1f]+', email.strip()):
                return fail('Masukkan alamat email yang valid.')
            email = email.strip().lower()
            if not customers.throttle('forgot-password'):
                return fail('Terlalu banyak permintaan. Coba lagi dalam 15 menit.', 429)
            # Per-recipient limits also hold across IP addresses. Store a digest, not an email.
            scope = 'reset-email:' + hashlib.sha256(email.encode()).hexdigest()
            now = int(time.time())
            db().execute('BEGIN IMMEDIATE')
            count = db().execute('SELECT COUNT(*) FROM login_attempts WHERE address=? AND attempted_at>?', (scope, now-900)).fetchone()[0]
            if count >= 3:
                db().rollback();return jsonify(message=generic), 202
            db().execute('INSERT INTO login_attempts VALUES(?,?)', (scope, now))
            db().execute('DELETE FROM password_resets WHERE expires_at<=?', (now,))
            customer = db().execute('SELECT id FROM customers WHERE email=?', (email,)).fetchone()
            token = secrets.token_urlsafe(32)
            digest = hashlib.sha256(token.encode()).hexdigest()
            # Identical delivery for registered/unregistered addresses prevents enumeration
            # through provider timing/errors. Unregistered tokens cannot change any account.
            db().execute('INSERT INTO password_resets VALUES(?,?,?)', (digest, customer['id'] if customer else None, now+1800))
            db().commit()
            try:
                mailer.send(email, token)
            except RuntimeError:
                db().execute('DELETE FROM password_resets WHERE token_hash=?', (digest,));db().commit()
                app.logger.error('Password recovery email delivery failed; check Resend configuration.')
                return fail('Email belum dapat dikirim. Coba lagi nanti atau hubungi CS.', 503)
            return jsonify(message=generic), 202

        @app.post('/api/customer/reset-password')
        def reset_password():
            if not customers.require_csrf():
                return fail('Muat ulang formulir pemulihan.', 403)
            if not self.ready():
                return fail('Pemulihan akun sedang disiapkan. Coba lagi nanti atau hubungi CS.', 503)
            if not customers.throttle('reset-password'):
                return fail('Terlalu banyak percobaan. Coba lagi dalam 15 menit.', 429)
            data = body()
            token, password = data.get('token'), data.get('password')
            if not isinstance(token, str) or not re.fullmatch(r'[A-Za-z0-9_-]{43}', token):
                return fail('Tautan tidak valid atau kedaluwarsa. Minta tautan baru.')
            if not isinstance(password, str) or not 12 <= len(password) <= 128:
                return fail('Kata sandi baru harus 12–128 karakter.')
            hashed = generate_password_hash(password)
            db().execute('BEGIN IMMEDIATE')
            row = db().execute('SELECT customer_id FROM password_resets WHERE token_hash=? AND expires_at>?', (hashlib.sha256(token.encode()).hexdigest(), int(time.time()))).fetchone()
            if not row or row['customer_id'] is None:
                db().rollback();return fail('Tautan tidak valid atau kedaluwarsa. Minta tautan baru.')
            db().execute('UPDATE customers SET password_hash=? WHERE id=?', (hashed, row['customer_id']))
            app.extensions['email_verification'].mark_verified(row['customer_id'])
            db().execute('DELETE FROM password_resets WHERE customer_id=?', (row['customer_id'],))
            db().execute('DELETE FROM customer_sessions WHERE customer_id=?', (row['customer_id'],))
            db().commit()
            # No automatic login, and never disturb a different buyer's browser session.
            if not customers.current():
                session.pop('customer_sid', None)
                session.pop('customer_csrf', None)
            return jsonify(ok=True, csrf=customers.csrf())

    def ready(self):
        if not self.postgres:
            return True
        if not hasattr(g, 'recovery_ready'):
            g.recovery_ready = bool(self.db().execute("SELECT to_regclass('password_resets') resets").fetchone()['resets'])
        return g.recovery_ready
