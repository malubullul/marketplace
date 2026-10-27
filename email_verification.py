"""Email-first signup and safe verification of legacy unverified accounts."""
import hashlib
import re
import secrets
import time
from flask import g, jsonify, request, session
from werkzeug.security import generate_password_hash


class EmailVerification:
    def __init__(self, app, db, customers, fail, body):
        self.app, self.db, self.customers, self.fail = app, db, customers, fail
        self.required = app.config['EMAIL_VERIFICATION_REQUIRED']
        self.mailer = app.extensions['recovery_mailer']
        self.postgres = bool(app.config['DATABASE_URL'])
        app.extensions['email_verification'] = self
        if not self.postgres:
            with app.app_context():
                db().executescript('''
                  CREATE TABLE IF NOT EXISTS verified_customer_emails (
                    customer_id INTEGER PRIMARY KEY REFERENCES customers(id) ON DELETE CASCADE,
                    verified_at INTEGER NOT NULL);
                  CREATE TABLE IF NOT EXISTS email_verification_tokens (
                    token_hash TEXT PRIMARY KEY, email TEXT NOT NULL,
                    customer_id INTEGER REFERENCES customers(id) ON DELETE CASCADE,
                    expires_at INTEGER NOT NULL);
                  CREATE INDEX IF NOT EXISTS verification_email ON email_verification_tokens(email);
                  CREATE INDEX IF NOT EXISTS verification_expiry ON email_verification_tokens(expires_at);
                ''')
                db().commit()

        @app.post('/api/customer/email-verification')
        def request_link():
            if not customers.require_csrf(): return fail('Muat ulang formulir verifikasi.', 403)
            customer = customers.current()
            return self.request_link(customer['email'] if customer else body().get('email'))

        @app.post('/api/customer/verify-email')
        def consume():
            if not customers.require_csrf(): return fail('Muat ulang formulir verifikasi.', 403)
            if not self.ready(): return fail('Verifikasi email sedang disiapkan. Hubungi CS.', 503)
            if not customers.throttle('verify-email'): return fail('Terlalu banyak percobaan. Coba lagi dalam 15 menit.', 429)
            data = body(); token = data.get('token'); password = data.get('password')
            if not isinstance(token, str) or not re.fullmatch(r'[A-Za-z0-9_-]{43}', token): return fail('Tautan verifikasi tidak valid atau sudah kedaluwarsa.')
            if not isinstance(password, str) or not 12 <= len(password) <= 128: return fail('Kata sandi harus 12–128 karakter.')
            hashed = generate_password_hash(password)
            db().execute('BEGIN IMMEDIATE')
            row = db().execute('SELECT * FROM email_verification_tokens WHERE token_hash=? AND expires_at>?', (hashlib.sha256(token.encode()).hexdigest(), int(time.time()))).fetchone()
            if not row:
                db().rollback(); return fail('Tautan verifikasi tidak valid atau sudah kedaluwarsa.')
            existing = db().execute('SELECT * FROM customers WHERE email=?', (row['email'],)).fetchone()
            # A token issued before an account existed can NEVER take over that account.
            if (existing and row['customer_id'] != existing['id']) or (not existing and row['customer_id'] is not None) or (existing and self.verified(existing)):
                db().rollback(); return fail('Tautan tidak dapat digunakan. Masuk atau minta tautan verifikasi baru.')
            if existing:
                customer_id = existing['id']
                db().execute('UPDATE customers SET password_hash=? WHERE id=?', (hashed, customer_id))
            else:
                try:
                    name = customers.text(data, 'nama'); phone = customers.text(data, 'nohp', 30)
                    if not re.fullmatch(r'[+()\d\s-]{7,30}', phone): raise ValueError('Nomor HP tidak valid.')
                except ValueError as error:
                    db().rollback(); return fail(str(error))
                customer_id = db().execute('INSERT INTO customers(email,password_hash,nama,nohp,created_at) VALUES(?,?,?,?,?)', (row['email'], hashed, name, phone, int(time.time()))).lastrowid
            self.mark_verified(customer_id)
            db().execute('DELETE FROM customer_sessions WHERE customer_id=?', (customer_id,))
            if app.extensions['password_recovery'].ready():
                db().execute('DELETE FROM password_resets WHERE customer_id=?', (customer_id,))
            db().execute('DELETE FROM email_verification_tokens WHERE email=?', (row['email'],))
            db().commit()
            if not customers.current():
                session.pop('customer_sid', None); session.pop('customer_csrf', None)
            return jsonify(ok=True, csrf=customers.csrf(), message='Email terverifikasi. Semua sesi lama telah keluar. Silakan masuk dengan kata sandi barumu.')

    def ready(self):
        if not self.postgres: return True
        if not hasattr(g, 'verification_ready'):
            row = self.db().execute("SELECT to_regclass('verified_customer_emails') verified, to_regclass('email_verification_tokens') tokens").fetchone()
            g.verification_ready = bool(row['verified'] and row['tokens'])
        return g.verification_ready

    def availability(self):
        return {'required': self.required, 'available': self.ready() and self.mailer.enabled}

    def verified(self, customer):
        return bool(customer and self.ready() and self.db().execute('SELECT 1 FROM verified_customer_emails WHERE customer_id=?', (customer['id'],)).fetchone())

    def mark_verified(self, customer_id):
        if self.ready():
            self.db().execute('INSERT INTO verified_customer_emails(customer_id,verified_at) VALUES(?,?) ON CONFLICT(customer_id) DO NOTHING', (customer_id, int(time.time())))
            self.db().execute('DELETE FROM email_verification_tokens WHERE customer_id=?', (customer_id,))

    def checkout_error(self, customer):
        if not self.required: return None
        if not self.availability()['available']: return self.fail('Verifikasi email sedang disiapkan. Hubungi CS sebelum membuat pesanan.', 503)
        if not self.verified(customer): return self.fail('Verifikasi email terlebih dahulu melalui halaman Akun sebelum membuat pesanan.', 403)
        return None

    def request_link(self, email):
        if not self.availability()['available']: return self.fail('Verifikasi email belum tersedia. Hubungi CS untuk bantuan.', 503)
        if not isinstance(email, str) or len(email) > 150 or not re.fullmatch(r'[^\s@\x00-\x1f]+@[^\s@\x00-\x1f]+\.[^\s@\x00-\x1f]+', email.strip()): return self.fail('Masukkan alamat email yang valid.')
        email = email.strip().lower(); now = int(time.time())
        message = 'Jika alamat ini dapat digunakan, tautan verifikasi dikirim ke kotak masuk. Periksa juga spam. Tautan berlaku 30 menit.'
        response = lambda: (jsonify(verification_required=True, message=message), 202)
        self.db().execute('BEGIN IMMEDIATE')
        ip = 'verify-ip:' + (request.remote_addr or 'unknown')
        recipient = 'verify-email:' + hashlib.sha256(email.encode()).hexdigest()
        self.db().execute('DELETE FROM login_attempts WHERE attempted_at<?', (now-900,))
        for key, limit in [(ip, 10), (recipient, 3)]:
            if self.db().execute('SELECT COUNT(*) FROM login_attempts WHERE address=? AND attempted_at>?', (key, now-900)).fetchone()[0] >= limit:
                self.db().rollback()
                return response() if key == recipient else self.fail('Terlalu banyak permintaan. Coba lagi dalam 15 menit.', 429)
        for key in (ip, recipient): self.db().execute('INSERT INTO login_attempts VALUES(?,?)', (key, now))
        self.db().execute('DELETE FROM email_verification_tokens WHERE expires_at<=?', (now,))
        customer = self.db().execute('SELECT id FROM customers WHERE email=?', (email,)).fetchone()
        token = secrets.token_urlsafe(32); digest = hashlib.sha256(token.encode()).hexdigest()
        self.db().execute('INSERT INTO email_verification_tokens VALUES(?,?,?,?)', (digest, email, customer['id'] if customer else None, now+1800))
        self.db().commit()
        try: self.mailer.send_verification(email, token)
        except RuntimeError:
            self.db().execute('DELETE FROM email_verification_tokens WHERE token_hash=?', (digest,)); self.db().commit()
            return self.fail('Email belum dapat dikirim. Coba lagi nanti atau hubungi CS.', 503)
        return response()
