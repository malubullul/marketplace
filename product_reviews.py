"""Verified buyer reviews and order-backed catalogue metrics."""
import json
import time
from collections import Counter

from flask import g, jsonify, request


class ProductReviews:
    def __init__(self, app, db, customers, fail, body):
        self.db = db
        self.postgres = bool(app.config['DATABASE_URL'])
        app.extensions['product_reviews'] = self
        if not app.config['DATABASE_URL']:
            with app.app_context():
                db().executescript('''
                    CREATE TABLE IF NOT EXISTS order_items (
                        order_id TEXT NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
                        product_id INTEGER NOT NULL, quantity INTEGER NOT NULL CHECK(quantity>0),
                        PRIMARY KEY(order_id,product_id));
                    CREATE INDEX IF NOT EXISTS order_items_product ON order_items(product_id,order_id);
                    CREATE TABLE IF NOT EXISTS product_reviews (
                        customer_id INTEGER NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
                        product_id INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
                        rating INTEGER NOT NULL CHECK(rating BETWEEN 1 AND 5),
                        comment TEXT NOT NULL, created_at INTEGER NOT NULL, updated_at INTEGER NOT NULL,
                        PRIMARY KEY(customer_id,product_id));
                    CREATE INDEX IF NOT EXISTS product_reviews_latest ON product_reviews(product_id,created_at,customer_id);
                ''')
                # Existing orders retain their original quantities, including multiple variants.
                for row in db().execute('SELECT id,document FROM orders').fetchall():
                    quantities = Counter()
                    for item in json.loads(row['document']).get('items', []):
                        quantities[item['id']] += item['jumlah']
                    for product_id, quantity in quantities.items():
                        db().execute('INSERT INTO order_items VALUES(?,?,?) ON CONFLICT(order_id,product_id) DO NOTHING', (row['id'], product_id, quantity))
                db().commit()

        def published(product_id):
            if not 0 < product_id <= 9223372036854775807:
                return False
            return db().execute('SELECT 1 FROM products WHERE id=? AND published=1', (product_id,)).fetchone()

        def eligible(customer_id, product_id):
            return bool(db().execute("SELECT 1 FROM order_items i JOIN orders o ON o.id=i.order_id WHERE i.product_id=? AND o.customer_id=? AND o.status='selesai' LIMIT 1", (product_id, customer_id)).fetchone())

        @app.get('/api/products/<int:product_id>/reviews')
        def public_reviews(product_id):
            if not self.ready():
                return fail('Ulasan sedang disiapkan. Silakan coba lagi nanti.', 503)
            if not published(product_id):
                return fail('Produk tidak ditemukan.', 404)
            try:
                offset = int(request.args.get('offset', '0'))
                if not 0 <= offset <= 1000000:
                    raise ValueError()
            except ValueError:
                return fail('Halaman ulasan tidak valid.')
            total = db().execute('SELECT COUNT(*) FROM product_reviews WHERE product_id=?', (product_id,)).fetchone()[0]
            rows = db().execute('SELECT r.*,c.nama FROM product_reviews r JOIN customers c ON c.id=r.customer_id WHERE r.product_id=? ORDER BY r.created_at DESC,r.customer_id DESC LIMIT 10 OFFSET ?', (product_id, offset)).fetchall()
            # Never publish account IDs, emails, addresses, or full customer names.
            reviews = [dict(rating=row['rating'], comment=row['comment'], name=(row['nama'].strip()[:1] or 'P') + '***', created_at=row['created_at'], updated_at=row['updated_at'], verified=True) for row in rows]
            return jsonify(reviews=reviews, total=total, next_offset=offset+len(rows) if offset+len(rows)<total else None)

        @app.get('/api/customer/products/<int:product_id>/review')
        @customers.required
        def own_review(product_id):
            if not self.ready():
                return fail('Ulasan sedang disiapkan. Silakan coba lagi nanti.', 503)
            if not published(product_id):
                return fail('Produk tidak ditemukan.', 404)
            row = db().execute('SELECT rating,comment FROM product_reviews WHERE customer_id=? AND product_id=?', (g.customer['id'], product_id)).fetchone()
            return jsonify(eligible=eligible(g.customer['id'], product_id), review=dict(row) if row else None)

        @app.put('/api/customer/products/<int:product_id>/review')
        @customers.required
        def save_review(product_id):
            if not self.ready():
                return fail('Ulasan sedang disiapkan. Silakan coba lagi nanti.', 503)
            data = body()
            rating, comment = data.get('rating'), data.get('comment', '')
            if type(rating) is not int or not 1 <= rating <= 5:
                return fail('Pilih rating 1 sampai 5 bintang.')
            if not isinstance(comment, str) or len(comment) > 1000:
                return fail('Ulasan maksimal 1.000 karakter.')
            if not customers.throttle('review'):
                return fail('Terlalu banyak perubahan ulasan. Coba lagi dalam 15 menit.', 429)
            db().execute('BEGIN IMMEDIATE')
            customer = customers.current()
            if not customer:
                db().rollback();return fail('Silakan masuk kembali.', 401)
            if not published(product_id):
                db().rollback();return fail('Produk tidak ditemukan.', 404)
            if not eligible(customer['id'], product_id):
                db().rollback();return fail('Rating dapat diberikan setelah pesanan produk ini selesai.', 403)
            now = int(time.time())
            db().execute('INSERT INTO product_reviews(customer_id,product_id,rating,comment,created_at,updated_at) VALUES(?,?,?,?,?,?) ON CONFLICT(customer_id,product_id) DO UPDATE SET rating=excluded.rating,comment=excluded.comment,updated_at=excluded.updated_at', (customer['id'], product_id, rating, comment.strip(), now, now))
            db().commit()
            return jsonify(ok=True, metrics=self.metrics()[product_id])

    def ready(self):
        if not self.postgres:
            return True
        if not hasattr(g, 'reviews_ready'):
            row = self.db().execute("SELECT to_regclass('order_items') items,to_regclass('product_reviews') reviews").fetchone()
            g.reviews_ready = bool(row['items'] and row['reviews'])
        return g.reviews_ready

    def metrics(self):
        if not self.ready():
            return {}
        result = {}
        for row in self.db().execute('SELECT product_id,AVG(rating) rating,COUNT(*) count FROM product_reviews GROUP BY product_id').fetchall():
            result[row['product_id']] = dict(rating=round(float(row['rating']), 1), ulasan=row['count'], terjual=0)
        for row in self.db().execute("SELECT i.product_id,SUM(i.quantity) sold FROM order_items i JOIN orders o ON o.id=i.order_id WHERE o.status='selesai' GROUP BY i.product_id").fetchall():
            result.setdefault(row['product_id'], dict(rating=0, ulasan=0, terjual=0))['terjual'] = int(row['sold'])
        return result
