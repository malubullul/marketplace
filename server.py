"""Anredseller: persistent catalog, owner dashboard and manual order intake."""
import argparse
import functools
import getpass
import hashlib
import io
import json
import os
from pathlib import Path
import re
import secrets
import sqlite3
import time
import uuid
from collections import Counter
from urllib.parse import urlsplit

from flask import Flask, abort, g, jsonify, redirect, request, send_from_directory, session
from PIL import Image, ImageOps, UnidentifiedImageError
from werkzeug.exceptions import HTTPException
from werkzeug.security import check_password_hash, generate_password_hash
from customer_api import CustomerAPI
from product_reviews import ProductReviews
from password_recovery import PasswordRecovery
from database import PostgresDatabase, PostgresError
from storage import LocalStorage, SupabaseStorage, StorageError

ROOT = Path(__file__).resolve().parent
ADMIN_ROOT = ROOT / 'admin-portal'
CATEGORIES = {"apparel", "sneakers", "essentials"}
ORDER_STATES = {"baru", "diproses", "dikirim", "selesai", "dibatalkan"}
COUPONS = {"HEMAT10": 10, "ANRED15": 15, "SALE20": 20}
DEFAULT_STORE_CONTACTS = {'payment_whatsapp': '6287729766809', 'support_whatsapp': '6282335963140'}
Image.MAX_IMAGE_PIXELS = 25_000_000


def create_app(config=None):
    app = Flask(__name__, static_folder=None)
    app.config.update(
        DATA_DIR=os.environ.get("ANREDSELLER_DATA_DIR", str(ROOT / "instance")),
        DATABASE_URL=os.environ.get('DATABASE_URL', ''),
        DATABASE_SCHEMA='anredseller',
        SESSION_SECRET=os.environ.get('ANREDSELLER_SESSION_SECRET', ''),
        SUPABASE_URL=os.environ.get('SUPABASE_URL', ''),
        SUPABASE_KEY=os.environ.get('SUPABASE_SECRET_KEY') or os.environ.get('SUPABASE_SERVICE_ROLE_KEY', ''),
        SUPABASE_BUCKET=os.environ.get('SUPABASE_STORAGE_BUCKET', 'product-photos'),
        SERVERLESS=bool(os.environ.get('VERCEL')),
        MAX_CONTENT_LENGTH=4 * 1024 * 1024 + 64 * 1024,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=os.environ.get("ANREDSELLER_SECURE_COOKIES", '1' if os.environ.get('VERCEL') else '0') == "1",
        PERMANENT_SESSION_LIFETIME=30 * 86400,
        ADMIN_GATEWAY_KEY=os.environ.get('ANREDSELLER_ADMIN_GATEWAY_KEY', ''),
        ADMIN_PORTAL_URL=os.environ.get('ANREDSELLER_ADMIN_PORTAL_URL', '').rstrip('/'),
        PUBLIC_URL=os.environ.get('ANREDSELLER_PUBLIC_URL', ''),
        RESEND_API_KEY=os.environ.get('RESEND_API_KEY', ''),
        EMAIL_FROM=os.environ.get('ANREDSELLER_EMAIL_FROM', ''),
    )
    app.config.update(config or {})
    if app.config['ADMIN_GATEWAY_KEY'] and len(app.config['ADMIN_GATEWAY_KEY']) < 32:
        raise ValueError('ADMIN_GATEWAY_KEY harus minimal 32 karakter.')
    if app.config['ADMIN_PORTAL_URL']:
        portal = urlsplit(app.config['ADMIN_PORTAL_URL'])
        local = portal.scheme == 'http' and portal.hostname in {'localhost', '127.0.0.1', '::1'}
        if not portal.netloc or (portal.scheme != 'https' and not local) or portal.username or portal.password or portal.path or portal.query or portal.fragment:
            raise ValueError('ADMIN_PORTAL_URL harus berupa origin HTTPS tanpa path.')
        if not app.config['ADMIN_GATEWAY_KEY']:
            raise ValueError('Portal terpisah membutuhkan ADMIN_GATEWAY_KEY di kedua server.')
    postgres = bool(app.config['DATABASE_URL'])
    if app.config['SERVERLESS'] and not postgres:
        raise ValueError('Vercel membutuhkan DATABASE_URL PostgreSQL; SQLite hanya untuk lokal.')
    directory = Path(app.config['DATA_DIR'])
    if postgres:
        if len(app.config['SESSION_SECRET']) < 32:
            raise ValueError('PostgreSQL membutuhkan ANREDSELLER_SESSION_SECRET minimal 32 karakter.')
        app.secret_key = app.config['SESSION_SECRET']
    else:
        directory.mkdir(parents=True, exist_ok=True)
        secret_file = directory / 'session.key'
        if not secret_file.exists():
            try:
                with secret_file.open('x') as out:
                    out.write(secrets.token_hex(32))
                secret_file.chmod(0o600)
            except FileExistsError:
                pass
        app.secret_key = app.config['SESSION_SECRET'] or secret_file.read_text().strip()
    if postgres and not app.config['TESTING'] and not app.config['SUPABASE_URL']:
        raise ValueError('PostgreSQL produksi membutuhkan Supabase Storage untuk foto.')
    if app.config['SUPABASE_URL']:
        photos = SupabaseStorage(app.config['SUPABASE_URL'], app.config['SUPABASE_KEY'],
                                 app.config['SUPABASE_BUCKET'], app.config['TESTING'])
    else:
        photos = LocalStorage(directory)

    def db():
        if "database" not in g:
            if postgres:
                g.database = PostgresDatabase(app.config['DATABASE_URL'], app.config['DATABASE_SCHEMA'])
            else:
                g.database = sqlite3.connect(directory / "store.sqlite3", timeout=15)
                g.database.row_factory = sqlite3.Row
                g.database.execute("PRAGMA foreign_keys=ON")
        return g.database

    @app.teardown_appcontext
    def close_database(error=None):
        connection = g.pop("database", None)
        if connection is not None:
            connection.close()

    app.get_db = db
    if not postgres:
        with app.app_context():
            db().executescript("""
                PRAGMA journal_mode=WAL;
                CREATE TABLE IF NOT EXISTS metadata (key TEXT PRIMARY KEY, value TEXT);
                CREATE TABLE IF NOT EXISTS owners (id INTEGER PRIMARY KEY, email TEXT UNIQUE NOT NULL, password_hash TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS products (id INTEGER PRIMARY KEY AUTOINCREMENT, document TEXT NOT NULL, published INTEGER NOT NULL DEFAULT 0, updated_at INTEGER NOT NULL);
                CREATE TABLE IF NOT EXISTS orders (id TEXT PRIMARY KEY, document TEXT NOT NULL, status TEXT NOT NULL, idempotency_key TEXT UNIQUE NOT NULL, created_at INTEGER NOT NULL);
                CREATE TABLE IF NOT EXISTS login_attempts (address TEXT NOT NULL, attempted_at INTEGER NOT NULL);
                CREATE TABLE IF NOT EXISTS owner_sessions (token TEXT PRIMARY KEY, owner_id INTEGER NOT NULL REFERENCES owners(id), expires_at INTEGER NOT NULL);
            """)
            if not db().execute("SELECT 1 FROM metadata WHERE key='seeded'").fetchone():
                for product in json.loads((ROOT / "data/products.seed.json").read_text()):
                    product.update(ukuran=[], warna=[], published=True, demo=True)
                    db().execute("INSERT INTO products(id, document, published, updated_at) VALUES(?,?,1,?)", (product["id"], json.dumps(product), int(time.time())))
                db().execute("INSERT INTO metadata VALUES('seeded','1')")
                db().commit()

    def fail(message, status=400):
        response = jsonify(error=message)
        response.status_code = status
        return response

    def token():
        if "csrf" not in session:
            session["csrf"] = secrets.token_urlsafe(32)
        return session["csrf"]

    def body():
        data = request.get_json(silent=True)
        if not isinstance(data, dict):
            abort(400)
        return data

    customers = CustomerAPI(app, db, fail, body)
    reviews = ProductReviews(app, db, customers, fail, body)
    PasswordRecovery(app, db, customers, fail, body)

    def authenticated_owner():
        sid = session.get("sid", "")
        return db().execute("SELECT owners.id,owners.email FROM owner_sessions JOIN owners ON owners.id=owner_sessions.owner_id WHERE owner_sessions.token=? AND expires_at>?", (hashlib.sha256(sid.encode()).hexdigest(), int(time.time()))).fetchone()

    def owner_required(func):
        @functools.wraps(func)
        def wrapped(*args, **kwargs):
            owner = authenticated_owner()
            if not owner:
                return fail("Silakan login sebagai pemilik toko.", 401)
            if request.method != "GET" and not secrets.compare_digest(request.headers.get("X-CSRF-Token", ""), token()):
                return fail("Sesi formulir tidak valid. Muat ulang halaman.", 403)
            return func(*args, **kwargs)
        return wrapped

    @app.before_request
    def admin_gateway():
        protected = request.path in {'/api/session', '/api/login', '/api/logout'} or request.path.startswith('/api/admin/')
        key = app.config['ADMIN_GATEWAY_KEY']
        if protected and key and not secrets.compare_digest(request.headers.get('X-Anredseller-Admin-Key', '').encode(), key.encode()):
            return fail('Akses admin harus melalui portal pemilik.', 401)

    @app.after_request
    def headers(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers.setdefault("Referrer-Policy", "same-origin")
        response.headers["Content-Security-Policy"] = "default-src 'self'; img-src 'self' data: blob:; style-src 'self' 'unsafe-inline'; script-src 'self' 'unsafe-inline'; base-uri 'self'; frame-ancestors 'none'; form-action 'self'"
        if request.path.startswith("/api/") or request.path.startswith("/admin") or request.path in {"/akun","/akun.html","/checkout.html","/konfirmasi.html"}:
            response.headers["Cache-Control"] = "no-store"
        return response

    @app.errorhandler(StorageError)
    def storage_error(error):
        return fail(str(error), 503)

    @app.errorhandler(PostgresError)
    def database_error(error):
        if app.testing:
            raise error
        # Classify diagnostics, but NEVER log the exception text or database URL:
        # connection errors can contain sensitive connection details.
        message = str(error).lower()
        sqlstate = getattr(error, 'sqlstate', None)
        if sqlstate == '28P01' or 'password authentication failed' in message:
            category = 'authentication'
        elif 'tenant or user not found' in message or 'database does not exist' in message:
            category = 'pooler_configuration'
        elif 'certificate verify failed' in message or 'certificate validation failed' in message:
            category = 'tls_certificate'
        elif 'could not translate host name' in message or 'name or service not known' in message:
            category = 'dns'
        elif 'timeout' in message or 'connection refused' in message or 'no route to host' in message:
            category = 'network'
        elif sqlstate == '42P01':
            category = 'schema_missing'
        elif sqlstate == '42501':
            category = 'permissions'
        else:
            category = 'unknown'
        app.logger.error('PostgreSQL connection diagnostic: class=%s sqlstate=%s category=%s',
                         type(error).__name__, sqlstate or 'none', category)
        return fail('Database belum dapat diakses. Periksa koneksi dan migrasi Supabase di pengaturan server.', 503)

    @app.errorhandler(HTTPException)
    def http_error(error):
        if request.path.startswith("/api/"):
            messages = {413: "File terlalu besar. Batas unggahan 4 MB.", 404: "Data tidak ditemukan.", 405: "Metode tidak diizinkan."}
            return fail(messages.get(error.code, "Permintaan tidak dapat diproses."), error.code)
        return error

    @app.get("/api/health")
    def health():
        db().execute("SELECT key FROM metadata LIMIT 1").fetchone()
        db().execute("SELECT id FROM products LIMIT 1").fetchone()
        db().execute("SELECT id FROM customers LIMIT 1").fetchone()
        db().execute("SELECT id FROM orders LIMIT 1").fetchone()
        return jsonify(status="ok")

    @app.get("/api/session")
    def current_session():
        owner = authenticated_owner()
        configured = db().execute("SELECT 1 FROM owners LIMIT 1").fetchone() is not None
        return jsonify(authenticated=bool(owner), email=owner["email"] if owner else None, configured=configured, csrf=token())

    @app.post("/api/login")
    def login():
        if not secrets.compare_digest(request.headers.get("X-CSRF-Token", ""), token()):
            return fail("Muat ulang halaman login dan coba lagi.", 403)
        data = body()
        address = request.remote_addr or "unknown"
        now = int(time.time())
        db().execute("DELETE FROM login_attempts WHERE attempted_at<?", (now - 900,))
        attempts = db().execute("SELECT COUNT(*) FROM login_attempts WHERE address=?", (address,)).fetchone()[0]
        if attempts >= 10:
            return fail("Terlalu banyak percobaan. Coba lagi dalam 15 menit.", 429)
        owner = db().execute("SELECT * FROM owners WHERE email=?", (str(data.get("email", "")).strip().lower(),)).fetchone()
        if not owner or not check_password_hash(owner["password_hash"], str(data.get("password", ""))):
            db().execute("INSERT INTO login_attempts VALUES(?,?)", (address, now))
            db().commit()
            return fail("Email atau kata sandi salah.", 401)
        db().execute("DELETE FROM login_attempts WHERE address=?", (address,))
        db().execute("DELETE FROM owner_sessions WHERE token=?", (hashlib.sha256(session.get("sid", "").encode()).hexdigest(),))
        session.pop("csrf", None)
        session["sid"] = secrets.token_urlsafe(32)
        db().execute("DELETE FROM owner_sessions WHERE expires_at<?", (now,))
        db().execute("INSERT INTO owner_sessions VALUES(?,?,?)", (hashlib.sha256(session["sid"].encode()).hexdigest(), owner["id"], now+8*3600))
        db().commit()
        session.permanent = True
        return jsonify(authenticated=True, email=owner["email"], csrf=token())

    @app.post("/api/logout")
    @owner_required
    def logout():
        db().execute("DELETE FROM owner_sessions WHERE token=?", (hashlib.sha256(session.get("sid", "").encode()).hexdigest(),))
        db().commit()
        session.pop("sid", None)
        session.pop("csrf", None)
        return jsonify(ok=True)

    def products(include_drafts=False):
        rows = db().execute("SELECT * FROM products" + ("" if include_drafts else " WHERE published=1") + " ORDER BY id DESC").fetchall()
        metrics = reviews.metrics()
        return [dict(json.loads(row["document"]), id=row["id"], published=bool(row["published"]), version=str(row["updated_at"]), metrics_ready=reviews.ready(), **metrics.get(row['id'], dict(rating=0, ulasan=0, terjual=0))) for row in rows]

    @app.get("/api/products")
    def public_products():
        return jsonify(products=products(), mode="server")

    @app.get("/api/admin/products")
    @owner_required
    def admin_products():
        return jsonify(products=products(True))

    def store_contacts():
        row = db().execute("SELECT value FROM metadata WHERE key='store_contacts'").fetchone()
        saved = json.loads(row['value']) if row else DEFAULT_STORE_CONTACTS
        # Only phone numbers can become public destinations, never arbitrary URLs.
        return {key: saved.get(key, '') if isinstance(saved.get(key), str)
                and re.fullmatch(r'[1-9][0-9]{7,14}', saved[key]) else ''
                for key in ('payment_whatsapp', 'support_whatsapp')}

    @app.get('/api/store/contacts')
    def public_contacts():
        return jsonify(contacts=store_contacts())

    @app.get('/api/admin/contacts')
    @owner_required
    def admin_contacts():
        return jsonify(contacts=store_contacts())

    @app.put('/api/admin/contacts')
    @owner_required
    def update_contacts():
        data = body()
        keys = {'payment_whatsapp', 'support_whatsapp'}
        if set(data) != keys:
            return fail('Isi nomor WhatsApp pembayaran dan customer service.')
        normalized = {}
        for key in keys:
            value = data[key]
            if not isinstance(value, str) or len(value) > 40:
                return fail('Nomor WhatsApp tidak valid.')
            value = value.strip()
            if value and not re.fullmatch(r'\+?[0-9][0-9 ()-]*', value):
                return fail('Gunakan nomor telepon, misalnya 08… atau +62…. Jangan masukkan tautan.')
            number = re.sub(r'[^0-9]', '', value)
            if number.startswith('0'):
                number = '62' + number[1:]
            if number and not re.fullmatch(r'[1-9][0-9]{7,14}', number):
                return fail('Nomor WhatsApp harus memiliki 8–15 digit termasuk kode negara.')
            normalized[key] = number
        db().execute("INSERT INTO metadata(key,value) VALUES('store_contacts',?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (json.dumps(normalized),))
        db().commit()
        return jsonify(contacts=normalized)

    def validated_product(data, previous=None):
        def text(key, maximum=150, required=False):
            value = data.get(key, "")
            if not isinstance(value, str) or len(value.strip()) > maximum or (required and not value.strip()):
                raise ValueError(f"Isian {key} tidak valid (maksimal {maximum} karakter).")
            return value.strip()
        def number(key, minimum, maximum):
            value = data.get(key)
            if isinstance(value, bool) or not isinstance(value, int) or not minimum <= value <= maximum:
                raise ValueError(f"Isian {key} harus bilangan bulat antara {minimum}–{maximum}.")
            return value
        category = text("kategori", required=True)
        if category not in CATEGORIES:
            raise ValueError("Pilih kategori yang tersedia.")
        price = number("harga", 1000, 1_000_000_000)
        old_price = data.get("hargaAsli") or price
        if isinstance(old_price, bool) or not isinstance(old_price, int) or not price <= old_price <= 1_000_000_000:
            raise ValueError("Harga awal harus sama atau lebih besar dari harga jual.")
        photo_list = data.get("gambarList", [])
        if not isinstance(photo_list, list) or not 1 <= len(photo_list) <= 8:
            raise ValueError("Unggah 1–8 foto produk.")
        for photo in photo_list:
            if not isinstance(photo, str):
                raise ValueError("Foto tidak valid.")
            if re.fullmatch(r"/uploads/[a-f0-9]{32}\.webp", photo):
                exists = photos.exists(photo.rsplit("/", 1)[1])
            elif re.fullmatch(r"assets/[a-zA-Z0-9_-]+\.(png|jpg|jpeg|webp|svg)", photo):
                exists = (ROOT / photo).is_file()
            else:
                exists = False
            if not exists:
                raise ValueError("Foto belum diunggah atau tidak ditemukan.")
        def options(key):
            value = data.get(key, [])
            if not isinstance(value, list) or len(value) > 20 or any(not isinstance(v, str) or not v.strip() or len(v.strip()) > 30 for v in value):
                raise ValueError(f"Pilihan {key} tidak valid.")
            return list(dict.fromkeys(v.strip() for v in value))
        return dict(
            nama=text("nama", required=True), kategori=category, harga=price, hargaAsli=old_price,
            stok=number("stok", 0, 1_000_000), deskripsi=text("deskripsi", 10000, True), brand=text("brand", 80),
            label=text("label", 40), ukuran=options("ukuran"), warna=options("warna"),
            gambarList=photo_list, gambar=photo_list[0], published=data.get("published") is True,
            trending=data.get("trending") is True, rekomendasi=data.get("rekomendasi") is True,
            rating=0, ulasan=0, terjual=0,
            demo=(previous or {}).get("demo", False),
            spesifikasi={"Bahan": text("bahan", 120), "Perawatan": text("perawatan", 500)},
            bahan=text("bahan", 120), perawatan=text("perawatan", 500),
        )

    @app.post("/api/admin/products")
    @owner_required
    def create_product():
        try:
            product = validated_product(body())
        except ValueError as error:
            return fail(str(error))
        version = time.time_ns()
        cursor = db().execute("INSERT INTO products(document,published,updated_at) VALUES(?,?,?)", (json.dumps(product), product["published"], version))
        db().commit()
        return jsonify(product=dict(product, id=cursor.lastrowid, version=str(version))), 201

    @app.put("/api/admin/products/<int:product_id>")
    @owner_required
    def edit_product(product_id):
        db().execute("BEGIN IMMEDIATE")
        row = db().execute("SELECT document,updated_at FROM products WHERE id=?", (product_id,)).fetchone()
        if not row:
            db().rollback()
            return fail("Produk tidak ditemukan.", 404)
        data = body()
        if data.get("version") != str(row["updated_at"]):
            db().rollback()
            return fail("Produk atau stok telah berubah. Muat ulang daftar produk sebelum menyimpan.", 409)
        try:
            product = validated_product(data, json.loads(row["document"]))
        except ValueError as error:
            db().rollback()
            return fail(str(error))
        version = time.time_ns()
        db().execute("UPDATE products SET document=?,published=?,updated_at=? WHERE id=?", (json.dumps(product), product["published"], version, product_id))
        db().commit()
        return jsonify(product=dict(product, id=product_id, version=str(version), **reviews.metrics().get(product_id, dict(rating=0, ulasan=0, terjual=0))))

    @app.delete("/api/admin/products/<int:product_id>")
    @owner_required
    def delete_product(product_id):
        deleted = db().execute("DELETE FROM products WHERE id=?", (product_id,)).rowcount
        db().commit()
        if not deleted:
            return fail("Produk tidak ditemukan.", 404)
        return jsonify(ok=True)

    @app.post("/api/admin/uploads")
    @owner_required
    def upload():
        photo = request.files.get("photo")
        if not photo:
            return fail("Pilih foto yang ingin diunggah.")
        data = photo.read(4 * 1024 * 1024 + 1)
        if len(data) > 4 * 1024 * 1024:
            return fail("Foto maksimal 4 MB.", 413)
        try:
            with Image.open(io.BytesIO(data)) as image:
                if image.format not in {"JPEG", "PNG", "WEBP"}:
                    raise ValueError("Gunakan foto JPG, PNG, atau WebP.")
                if image.width * image.height > Image.MAX_IMAGE_PIXELS:
                    raise ValueError("Foto maksimal 25 megapiksel.")
                image.load()
                image = ImageOps.exif_transpose(image).convert("RGB")
                image.thumbnail((2000, 2000))
                name = uuid.uuid4().hex + ".webp"
                output = io.BytesIO()
                image.save(output, 'WEBP', quality=88)
                if output.tell() > 4 * 1024 * 1024:
                    return fail('Foto hasil konversi maksimal 4 MB. Gunakan gambar berukuran lebih kecil.', 413)
                photos.put(name, output.getvalue())
        except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError):
            return fail("Foto tidak valid. Gunakan JPG, PNG, atau WebP maksimal 25 megapiksel.")
        return jsonify(url="/uploads/" + name), 201

    @app.post("/api/orders")
    @customers.required
    def create_order():
        if not request.is_json:
            return fail("Gunakan formulir pemesanan toko.")
        data = body()
        customer_id = g.customer["id"]
        key = request.headers.get("Idempotency-Key", "")
        if not re.fullmatch(r"[a-zA-Z0-9-]{16,80}", key):
            return fail("Identitas permintaan tidak valid. Muat ulang checkout.")
        order_key = hashlib.sha256(f"{customer_id}:{key}".encode()).hexdigest()
        existing = db().execute("SELECT document FROM orders WHERE idempotency_key=? AND customer_id=?", (order_key,customer_id)).fetchone()
        if existing:
            return jsonify(order=json.loads(existing["document"]),state=customers.resolved_state(customer_id))
        customer = data.get("customer", {})
        if not isinstance(customer, dict):
            return fail("Lengkapi data penerima.")
        customer["nama"] = g.customer["nama"]
        customer["email"] = g.customer["email"]
        address_id = data.get("address_id")
        if address_id is not None and (isinstance(address_id,bool) or not isinstance(address_id,int) or address_id<1):
            return fail("Alamat tidak valid.")
        if address_id is not None:
            address = db().execute("SELECT document FROM customer_addresses WHERE id=? AND customer_id=?", (address_id,customer_id)).fetchone()
            if not address: return fail("Alamat tidak ditemukan.",404)
            customer.update(json.loads(address["document"]))
        required = {"nama":150,"nama_penerima":150,"email":150,"nohp":30,"alamat":1000,"kota":100,"provinsi":100,"kodepos":5}
        for field, maximum in required.items():
            value = customer.get(field)
            if not isinstance(value, str) or not value.strip() or len(value.strip()) > maximum:
                return fail(f"Lengkapi {field.replace('_', ' ')} dengan benar.")
            customer[field] = value.strip()
        customer = {field: customer[field] for field in required}
        if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", customer["email"]) or not re.fullmatch(r"\d{5}", customer["kodepos"]):
            return fail("Email atau kode pos tidak valid.")
        lines = data.get("items", [])
        if not isinstance(lines, list) or not 1 <= len(lines) <= 50:
            return fail("Keranjang tidak valid.")
        coupon = str(data.get("coupon", "")).strip().upper()
        if coupon and coupon not in COUPONS:
            return fail("Kupon tidak berlaku.")
        try:
            db().execute("BEGIN IMMEDIATE")
            # Check again inside the write transaction for simultaneous retries.
            existing = db().execute("SELECT document FROM orders WHERE idempotency_key=? AND customer_id=?", (order_key,customer_id)).fetchone()
            if existing:
                db().rollback()
                return jsonify(order=json.loads(existing["document"]),state=customers.resolved_state(customer_id))
            quantities = Counter()
            items = []
            source = {}
            for line in lines:
                if not isinstance(line, dict):
                    raise ValueError("Item keranjang tidak valid.")
                product_id, quantity = line.get("id"), line.get("jumlah")
                if isinstance(product_id, bool) or not isinstance(product_id, int) or isinstance(quantity, bool) or not isinstance(quantity, int) or not 1 <= quantity <= 1000:
                    raise ValueError("Jumlah produk tidak valid.")
                row = db().execute("SELECT document FROM products WHERE id=? AND published=1", (product_id,)).fetchone()
                if not row:
                    raise ValueError("Ada produk yang tidak lagi tersedia. Perbarui keranjang.")
                product = json.loads(row["document"])
                if line.get("harga") != product["harga"]:
                    raise ValueError("Harga produk berubah. Buka keranjang untuk melihat harga terbaru.")
                size, color = line.get("ukuran", ""), line.get("warna", "")
                if (product.get("ukuran") and size not in product["ukuran"]) or (product.get("warna") and color not in product["warna"]):
                    raise ValueError("Pilih ukuran dan warna yang tersedia.")
                if not isinstance(size, str) or not isinstance(color, str) or len(size)>30 or len(color)>30:
                    raise ValueError("Pilihan produk tidak valid.")
                quantities[product_id] += quantity
                source[product_id] = product
                items.append(dict(id=product_id, nama=product["nama"], gambar=product["gambar"], harga=product["harga"], jumlah=quantity, ukuran=size, warna=color))
            for product_id, quantity in quantities.items():
                product = source[product_id]
                if product["stok"] < quantity:
                    raise ValueError(f"Stok {product['nama']} tidak mencukupi. Perbarui keranjang.")
                product["stok"] -= quantity
                db().execute("UPDATE products SET document=?,updated_at=? WHERE id=?", (json.dumps(product), time.time_ns(), product_id))
            subtotal = sum(line["harga"] * line["jumlah"] for line in items)
            discount = subtotal * COUPONS.get(coupon, 0) // 100
            shipping = 0 if subtotal >= 200000 else 15000
            order_id = "ANR-" + secrets.token_hex(6).upper()
            order = dict(customer, nomor=order_id, tanggal=time.strftime("%Y-%m-%d"), created_at=int(time.time()), items=items, subtotal=subtotal, diskon=discount, ongkir=shipping, total=subtotal-discount+shipping, kurir="Dikonfirmasi oleh toko", metode="whatsapp", status="baru", catatan=str(data.get("catatan", ""))[:1000])
            if data.get("save_address") is True and address_id is None:
                customers.save_address(customer_id, dict(customer,label="Alamat checkout"))
            db().execute("INSERT INTO orders(id,document,status,idempotency_key,created_at,customer_id) VALUES(?,?,?,?,?,?)", (order_id, json.dumps(order), "baru", order_key, int(time.time()), customer_id))
            if reviews.ready():
                for product_id, quantity in quantities.items():
                    db().execute('INSERT INTO order_items(order_id,product_id,quantity) VALUES(?,?,?)', (order_id, product_id, quantity))
            customers.consume_cart(customer_id,items)
            db().commit()
            return jsonify(order=order,state=customers.resolved_state(customer_id)), 201
        except ValueError as error:
            db().rollback()
            return fail(str(error), 409)

    @app.get("/api/admin/orders")
    @owner_required
    def orders():
        return jsonify(orders=[dict(json.loads(row["document"]),status=row["status"]) for row in db().execute("SELECT * FROM orders ORDER BY created_at DESC, id DESC").fetchall()])

    @app.patch("/api/admin/orders/<order_id>")
    @owner_required
    def update_order(order_id):
        state = body().get("status")
        if state not in ORDER_STATES:
            return fail("Status pesanan tidak valid.")
        db().execute("BEGIN IMMEDIATE")
        row = db().execute("SELECT * FROM orders WHERE id=?", (order_id,)).fetchone()
        if not row:
            db().rollback()
            return fail("Pesanan tidak ditemukan.", 404)
        if row["status"] in {"dibatalkan", "selesai"} and state != row["status"]:
            db().rollback()
            return fail("Pesanan yang sudah selesai atau dibatalkan tidak dapat diaktifkan kembali.", 409)
        order = json.loads(row["document"])
        if state == "dibatalkan" and row["status"] != "dibatalkan":
            for line in order["items"]:
                product_row = db().execute("SELECT document FROM products WHERE id=?", (line["id"],)).fetchone()
                if product_row:
                    product = json.loads(product_row["document"])
                    product["stok"] += line["jumlah"]
                    db().execute("UPDATE products SET document=?,updated_at=? WHERE id=?", (json.dumps(product), time.time_ns(), line["id"]))
        order["status"] = state
        db().execute("UPDATE orders SET status=?,document=? WHERE id=?", (state,json.dumps(order),order_id))
        db().commit()
        return jsonify(order=order)

    @app.get("/uploads/<filename>")
    def uploaded_file(filename):
        if not re.fullmatch(r"[a-f0-9]{32}\.webp", filename):
            return fail("Foto tidak ditemukan.", 404)
        data = photos.get(filename)
        if data is None:
            return fail('Foto tidak ditemukan.', 404)
        response = app.response_class(data, mimetype='image/webp')
        response.cache_control.public = True
        response.cache_control.max_age = 86400
        return response

    @app.get("/")
    def index():
        return send_from_directory(ROOT, "index.html")

    @app.get("/akun")
    def customer_page():
        return send_from_directory(ROOT,"akun.html")

    @app.get("/admin")
    def admin_page():
        if app.config['ADMIN_PORTAL_URL']:
            return redirect(app.config['ADMIN_PORTAL_URL'] + '/', code=302)
        return send_from_directory(ADMIN_ROOT / 'templates', 'index.html')

    @app.get('/portal-config')
    def local_admin_config():
        if app.config['ADMIN_PORTAL_URL']:
            abort(404)
        return jsonify(shop_url='/')

    @app.get("/<path:filename>")
    def static_file(filename):
        if filename == 'admin.html':
            return admin_page()
        if filename in {'css/admin.css', 'js/admin.js'} or re.fullmatch(r'fonts/switzer-latin-(?:400|500|600)-normal\.woff2', filename):
            if app.config['ADMIN_PORTAL_URL']:
                abort(404)
            return send_from_directory(ADMIN_ROOT / 'static', filename)
        pages = {"index.html","produk.html","detail.html","keranjang.html","checkout.html","konfirmasi.html","akun.html"}
        parts = Path(filename).parts
        if filename in pages or (parts and parts[0] in {"css","js","assets"} and not any(part.startswith(".") for part in parts)):
            return send_from_directory(ROOT, filename)
        return fail("Halaman tidak ditemukan.", 404)

    return app


def create_owner(app, email, password):
    email = email.strip().lower()
    if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", email) or len(password) < 12:
        raise ValueError("Gunakan email valid dan kata sandi minimal 12 karakter.")
    with app.app_context():
        connection = app.get_db()
        if connection.execute("SELECT 1 FROM owners WHERE email=?", (email,)).fetchone():
            raise ValueError("Email pemilik sudah terdaftar. Gunakan perintah reset-password untuk mengganti kata sandi.")
        connection.execute("INSERT INTO owners(email,password_hash) VALUES(?,?)", (email,generate_password_hash(password)))
        connection.commit()


def configuration_app():
    """Keep public pages accessible while Vercel secrets are being configured.

    No database is opened and every API fails closed with 503. This is not a
    fallback SQLite store and cannot accept registrations or orders.
    """
    pending = Flask(__name__, static_folder=None)

    @pending.route('/api/<path:path>', methods=['GET','POST','PUT','PATCH','DELETE'])
    def unavailable_api(path):
        return jsonify(error='Konfigurasi server belum lengkap. Lengkapi Environment Variables Vercel dan migrasi Supabase, lalu redeploy.'), 503

    @pending.get('/', defaults={'filename':'index.html'})
    @pending.get('/<path:filename>')
    def public_page(filename):
        pages = {'index.html','produk.html','detail.html','keranjang.html','checkout.html','konfirmasi.html','akun.html'}
        parts = Path(filename).parts
        if filename in pages or (parts and parts[0] in {'css','js','assets'} and not any(part.startswith('.') for part in parts)):
            return send_from_directory(ROOT, filename)
        abort(404)

    @pending.after_request
    def pending_headers(response):
        response.headers['Cache-Control'] = 'no-store'
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        return response

    return pending


def initialize_app():
    """Expose a top-level Flask application for Vercel's Python entrypoint detection."""
    try:
        return create_app()
    except ValueError:
        if not os.environ.get('VERCEL'):
            raise
        return configuration_app()


# Vercel's entrypoint discovery expects a top-level app assignment.
app = initialize_app()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["run","create-admin","reset-password","init-db"], nargs="?", default="run")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--host", default="127.0.0.1")
    args = parser.parse_args()
    if args.command == 'init-db':
        if not app.config['DATABASE_URL']:
            parser.error('Atur DATABASE_URL PostgreSQL terlebih dahulu.')
        with app.app_context():
            app.get_db().initialize()
        print('Schema PostgreSQL berhasil disiapkan tanpa menghapus data.')
    elif args.command in {"create-admin", "reset-password"}:
        email = input("Email pemilik: ").strip().lower()
        password = getpass.getpass("Kata sandi (minimal 12 karakter): ")
        if password != getpass.getpass("Ulangi kata sandi: "):
            parser.error("Kata sandi tidak sama.")
        try:
            if args.command == "create-admin":
                create_owner(app,email,password)
            else:
                if len(password) < 12:
                    raise ValueError("Kata sandi minimal 12 karakter.")
                with app.app_context():
                    cursor = app.get_db().execute("UPDATE owners SET password_hash=? WHERE email=?", (generate_password_hash(password),email))
                    if not cursor.rowcount:
                        raise ValueError("Akun pemilik tidak ditemukan.")
                    app.get_db().execute("DELETE FROM owner_sessions WHERE owner_id=(SELECT id FROM owners WHERE email=?)", (email,))
                    app.get_db().commit()
            print("Akun pemilik berhasil disimpan.")
        except ValueError as error:
            parser.error(str(error))
    else:
        app.run(host=args.host,port=args.port,debug=False)
