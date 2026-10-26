"""Owner-managed promotions; eligibility and money are always checked server-side.

Definitions use existing private metadata. Immutable order snapshots are the usage
ledger, so cancellations release quota and retries cannot consume it twice. Both
database adapters serialize order writes. No additional production migration.
"""
import json
import re
import time
from time import time as now_seconds

from flask import g, jsonify


def normalize_code(value, optional=False):
    if not isinstance(value, str) or len(value) > 64:
        raise ValueError('Kode promo tidak valid.')
    code = value.strip().upper()
    if optional and not code:
        return ''
    if not re.fullmatch(r'[A-Z0-9][A-Z0-9_-]{2,31}', code, re.ASCII):
        raise ValueError('Kode promo harus 3–32 huruf, angka, tanda - atau _.')
    return code


def validate_promo(data):
    fields = {'code','partner','kind','value','min_subtotal','max_discount',
              'starts_at','expires_at','usage_limit','per_customer_limit','active','version'}
    if set(data) != fields:
        raise ValueError('Lengkapi semua pengaturan kode promo.')
    promo = {key: data[key] for key in fields}
    promo['code'] = normalize_code(data['code'])
    partner = data['partner']
    if not isinstance(partner, str) or len(partner) > 100 or any(ord(c)<32 for c in partner):
        raise ValueError('Nama partner maksimal 100 karakter.')
    promo['partner'] = partner.strip()
    if data['kind'] not in ('percent','fixed'):
        raise ValueError('Pilih diskon persen atau rupiah.')
    if type(data['active']) is not bool:
        raise ValueError('Status promo tidak valid.')
    ranges = {'value': (1,100 if data['kind']=='percent' else 10_000_000),
              'min_subtotal': (0,100_000_000), 'max_discount': (1,10_000_000),
              'usage_limit': (1,1_000_000), 'per_customer_limit': (1,1000),
              'starts_at': (0,4_102_444_799), 'expires_at': (0,4_102_444_799)}
    optional = {'max_discount','usage_limit','starts_at','expires_at'}
    for key, (low, high) in ranges.items():
        value = data[key]
        if key in optional and value is None:
            continue
        if type(value) is not int or not low <= value <= high:
            raise ValueError('Nilai '+key.replace('_',' ')+' tidak valid; gunakan angka bulat dalam batas kolom.')
    if data['kind']=='fixed' and data['max_discount'] is not None:
        raise ValueError('Batas diskon hanya untuk promo persen.')
    if data['starts_at'] is not None and data['expires_at'] is not None and data['expires_at'] <= data['starts_at']:
        raise ValueError('Tanggal akhir harus sesudah tanggal mulai.')
    if not isinstance(data['version'], str) or not re.fullmatch(r'0|[1-9][0-9]{0,19}',data['version']):
        raise ValueError('Versi promo tidak valid. Muat ulang daftar.')
    return promo


class PromoCodes:
    def __init__(self, app, db, customers, owner_required, fail, body):
        self.db = db
        self.postgres = bool(app.config['DATABASE_URL'])
        app.extensions['promo_codes'] = self

        @app.get('/api/admin/promos')
        @owner_required
        def list_promos():
            rows = db().execute('SELECT value FROM metadata WHERE key LIKE ? ORDER BY key', ('promo:%',)).fetchall()
            stats = self.all_usage()
            promos = [json.loads(row['value']) for row in rows]
            return jsonify(promos=[dict(promo, **stats.get(promo['code'],self.empty_usage())) for promo in promos])

        @app.post('/api/admin/promos')
        @app.put('/api/admin/promos/<code>')
        @owner_required
        def save_promo(code=None):
            try:
                promo = validate_promo(body())
                if code is not None and code != promo['code']:
                    raise ValueError('Kode yang sudah dibuat tidak dapat diganti; buat kode baru.')
            except ValueError as error:
                return fail(str(error))
            db().execute('BEGIN IMMEDIATE')
            key = 'promo:'+promo['code']
            row = db().execute('SELECT value FROM metadata WHERE key=?', (key,)).fetchone()
            if code is None and row:
                db().rollback()
                return fail('Kode promo sudah ada. Edit kode yang tersedia.',409)
            if code is not None and not row:
                db().rollback()
                return fail('Kode promo tidak ditemukan.',404)
            previous = json.loads(row['value']) if row else None
            if promo['version'] != (previous['version'] if previous else '0'):
                db().rollback()
                return fail('Promo telah diubah di tempat lain. Muat ulang daftar sebelum menyimpan.',409)
            promo['version'] = str(time.time_ns())
            db().execute('INSERT INTO metadata(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value', (key,json.dumps(promo)))
            db().commit()
            return jsonify(promo=promo), 200 if previous else 201

        @app.post('/api/customer/promo')
        @customers.required
        def preview_promo():
            # Separate, persisted budget: normal cart edits must not exhaust login limits.
            now = int(now_seconds())
            key = 'promo-preview:'+str(g.customer['id'])
            db().execute('DELETE FROM login_attempts WHERE attempted_at<?',(now-900,))
            attempts = db().execute('SELECT COUNT(*) FROM login_attempts WHERE address=?',(key,)).fetchone()[0]
            if attempts >= 60:
                db().rollback()
                return fail('Terlalu banyak pemeriksaan promo. Coba lagi dalam 15 menit.',429)
            db().execute('INSERT INTO login_attempts VALUES(?,?)',(key,now))
            db().commit()
            try:
                code = normalize_code(body().get('code'))
                state = customers.resolved_state(g.customer['id'])
                cart = state['cart']
                if not cart or any(not item['available'] for item in cart):
                    raise ValueError('Perbarui keranjang sebelum memakai promo.')
                quantities = {}
                for item in cart:
                    quantities[item['id']] = quantities.get(item['id'],0)+item['jumlah']
                if any(quantities[item['id']]>item['stok'] for item in cart):
                    raise ValueError('Stok tidak mencukupi. Perbarui keranjang.')
                subtotal = sum(item['harga']*item['jumlah'] for item in cart)
                promo = self.evaluate(code,g.customer['id'],subtotal)
                shipping = 0 if subtotal>=200000 else 15000
                return jsonify(quote=dict(code=code,subtotal=subtotal,discount=promo['discount'],
                                          shipping=shipping,total=subtotal-promo['discount']+shipping,
                                          revision=state['revision']))
            except ValueError as error:
                return fail(str(error),409)

    @staticmethod
    def empty_usage():
        return dict(used=0,completed=0,completed_sales=0,completed_discount=0)

    def code_sql(self):
        return "(document::jsonb->'promo'->>'code')" if self.postgres else "json_extract(document,'$.promo.code')"

    def all_usage(self):
        money = "(document::jsonb->>'total')::bigint" if self.postgres else "json_extract(document,'$.total')"
        discount = "(document::jsonb->>'diskon')::bigint" if self.postgres else "json_extract(document,'$.diskon')"
        code = self.code_sql()
        rows = self.db().execute(f"SELECT {code} AS code,COUNT(*) AS used, SUM(CASE WHEN status='selesai' THEN 1 ELSE 0 END) AS completed, SUM(CASE WHEN status='selesai' THEN {money} ELSE 0 END) AS completed_sales, SUM(CASE WHEN status='selesai' THEN {discount} ELSE 0 END) AS completed_discount FROM orders WHERE status<>'dibatalkan' AND {code} IS NOT NULL GROUP BY {code}").fetchall()
        return {row['code']: {key:int(row[key]) for key in self.empty_usage()} for row in rows}

    def evaluate(self, code, customer_id, subtotal):
        """Call again INSIDE the checkout write transaction; previews reserve nothing."""
        if not code:
            return None
        row = self.db().execute('SELECT value FROM metadata WHERE key=?',('promo:'+code,)).fetchone()
        if not row:
            raise ValueError('Kode promo tidak tersedia atau sudah nonaktif.')
        promo = json.loads(row['value'])
        now = int(now_seconds())
        if not promo['active']:
            raise ValueError('Kode promo tidak tersedia atau sudah nonaktif.')
        if promo['starts_at'] is not None and now < promo['starts_at']:
            raise ValueError('Kode promo belum mulai berlaku.')
        if promo['expires_at'] is not None and now >= promo['expires_at']:
            raise ValueError('Kode promo sudah kedaluwarsa.')
        if subtotal < promo['min_subtotal']:
            raise ValueError('Minimal belanja promo ini Rp '+format(promo['min_subtotal'],',').replace(',','.')+'.')
        counts = self.db().execute(f"SELECT COUNT(*) AS total,COALESCE(SUM(CASE WHEN customer_id=? THEN 1 ELSE 0 END),0) AS own FROM orders WHERE status<>'dibatalkan' AND {self.code_sql()}=?",(customer_id,code)).fetchone()
        if promo['usage_limit'] is not None and counts['total'] >= promo['usage_limit']:
            raise ValueError('Kuota kode promo sudah habis.')
        if counts['own'] >= promo['per_customer_limit']:
            raise ValueError('Batas penggunaan kode promo untuk akunmu sudah tercapai.')
        discount = subtotal*promo['value']//100 if promo['kind']=='percent' else promo['value']
        discount = min(subtotal,discount,promo['max_discount'] if promo['max_discount'] is not None else subtotal)
        if discount <= 0:
            raise ValueError('Promo tidak memberikan diskon untuk keranjang ini.')
        return dict(code=code,partner=promo['partner'],kind=promo['kind'],value=promo['value'],discount=discount)
