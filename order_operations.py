"""Manual WhatsApp payment verification and safe order/reservation transitions."""
import json
import secrets
import time
import inventory
from flask import g, jsonify, request


class OrderOperations:
    def __init__(self, app, db, customers, owner_required, fail, body):
        self.app, self.db, self.customers = app, db, customers
        app.extensions['order_operations'] = self

        @app.get('/api/store/transaction-settings')
        def public_settings():
            settings = self.settings()
            return jsonify(settings={k: settings[k] for k in ('deadline_enabled', 'payment_hours')})

        @app.get('/api/admin/transaction-settings')
        @owner_required
        def settings_read():
            return jsonify(settings=self.settings(), email_verification=app.extensions['email_verification'].availability())

        @app.put('/api/admin/transaction-settings')
        @owner_required
        def settings_write():
            data = body()
            if type(data.get('deadline_enabled')) is not bool or type(data.get('payment_hours')) is not int or not 1 <= data['payment_hours'] <= 168:
                return fail('Batas pembayaran harus 1–168 jam dan pilihan aktif harus benar.')
            db().execute('BEGIN IMMEDIATE')
            if data.get('version') != self.settings()['version']:
                db().rollback(); return fail('Pengaturan berubah. Muat ulang sebelum menyimpan.', 409)
            saved = {k: data[k] for k in ('deadline_enabled', 'payment_hours')}
            saved['version'] = str(time.time_ns())
            self.save_metadata('transaction-settings', saved)
            app.audit_log.record('transaction.settings', 'settings', 'transactions', saved)
            db().commit()
            return jsonify(settings=saved)

        @app.get('/api/admin/orders/<order_id>/history')
        @owner_required
        def history(order_id):
            if not db().execute('SELECT 1 FROM orders WHERE id=?', (order_id,)).fetchone():
                return fail('Pesanan tidak ditemukan.', 404)
            return jsonify(events=app.audit_log.order_events(order_id), payment_record=self.metadata('payment-private:' + order_id, {}))

        def mutate(order_id, operation, customer=False):
            data = body()
            db().execute('BEGIN IMMEDIATE')
            row = db().execute('SELECT * FROM orders WHERE id=?', (order_id,)).fetchone()
            if not row or (customer and row['customer_id'] != g.customer['id']):
                db().rollback(); return fail('Pesanan tidak ditemukan.', 404)
            order = self.decorate(json.loads(row['document']))
            if self.expire_one(order):
                db().commit(); return fail('Batas pembayaran sudah lewat. Pesanan dibatalkan dan stok dikembalikan.', 409)
            if data.get('version') != order['version']:
                db().rollback(); return fail('Pesanan berubah. Muat ulang rincian sebelum melanjutkan.', 409)
            actor = {'type': 'customer', 'id': g.customer['id']} if customer else None
            try:
                changed = operation(order, data)
                if changed:
                    self.write(order)
                    app.audit_log.record(changed, 'order', order_id, {'to': order['status'], 'payment_status': order['payment']['status']}, actor)
                db().commit()
                return jsonify(order=order)
            except ValueError as error:
                db().rollback(); return fail(str(error), 409)

        @app.patch('/api/admin/orders/<order_id>')
        @owner_required
        def transition(order_id):
            def change(order, data):
                state = data.get('status')
                if not isinstance(state, str) or state not in {'baru', 'diproses', 'dikirim', 'selesai', 'dibatalkan'}:
                    raise ValueError('Status pesanan tidak valid.')
                if state == order['status']: return None
                if state == 'dibatalkan':
                    self.cancel(order, 'pemilik')
                elif {'baru': 'diproses', 'diproses': 'dikirim', 'dikirim': 'selesai'}.get(order['status']) != state:
                    raise ValueError('Ikuti urutan baru → diproses → dikirim → selesai. Pesanan final tidak dapat diubah.')
                elif order['payment']['status'] != 'verified':
                    raise ValueError('Tandai pembayaran sebagai sudah dibayar sebelum melanjutkan pesanan.')
                else:
                    order['status'] = state
                return 'order.status'
            return mutate(order_id, change)

        @app.post('/api/admin/orders/<order_id>/payment')
        @owner_required
        def payment(order_id):
            def change(order, data):
                action = data.get('action')
                if not isinstance(action, str) or action not in {'verify', 'reject', 'hold', 'release'}:
                    raise ValueError('Tindakan pembayaran tidak valid.')
                if order['status'] == 'dibatalkan': raise ValueError('Pesanan dibatalkan tidak dapat menerima perubahan pembayaran.')
                if action == 'verify':
                    if order['payment']['status'] == 'verified': return None
                    reference = data.get('reference', '')
                    if not isinstance(reference, str) or len(reference) > 160 or any(ord(c) < 32 for c in reference):
                        raise ValueError('Catatan pembayaran opsional, maksimal 160 karakter tanpa karakter kontrol.')
                    order['payment'].update(status='verified', verified_at=int(time.time()))
                    order['payment_hold'] = False
                    self.save_metadata('payment-private:' + order['nomor'], {'reference': reference.strip(), 'verified_by': g.owner['id'], 'verified_at': order['payment']['verified_at']})
                else:
                    if order['status'] != 'baru' or order['payment']['status'] == 'verified':
                        raise ValueError('Pembayaran terverifikasi atau pesanan yang diproses memerlukan penanganan manual; tidak dapat dibatalkan otomatis.')
                    if action == 'reject':
                        if order['payment']['status'] != 'reported': raise ValueError('Belum ada laporan transfer untuk ditolak.')
                        order['payment']['status'] = 'pending'
                        order['payment_hold'] = False
                        # Give the buyer a new full window after the owner rejects a claim.
                        if order['payment_deadline']:
                            order['payment_deadline'] = int(time.time()) + order.get('payment_hours', 24) * 3600
                    elif action == 'hold':
                        if order['payment_hold']: return None
                        order['payment_hold'] = True
                    else:
                        if not order['payment_hold']: return None
                        order['payment_hold'] = False
                        if order['payment_deadline']:
                            order['payment_deadline'] = int(time.time()) + order.get('payment_hours', 24) * 3600
                return 'payment.' + action
            return mutate(order_id, change)

        @app.post('/api/customer/orders/<order_id>/payment')
        @customers.required
        def report(order_id):
            def change(order, data):
                if order['status'] != 'baru' or order['payment']['status'] not in {'pending', 'reported'}:
                    raise ValueError('Pesanan ini tidak menerima laporan transfer baru.')
                if order['payment']['status'] == 'reported': return None
                order['payment'].update(status='reported', reported_at=int(time.time()))
                return 'payment.reported'
            return mutate(order_id, change, True)

        @app.post('/api/customer/orders/<order_id>/cancel')
        @customers.required
        def cancel(order_id):
            def change(order, data):
                if order['status'] == 'dibatalkan': return None
                if order['status'] != 'baru': raise ValueError('Pesanan sudah diproses. Hubungi CS untuk bantuan.')
                self.cancel(order, 'pembeli')
                return 'order.cancelled'
            return mutate(order_id, change, True)

        @app.route('/api/internal/expire-orders', methods=['GET', 'POST'])
        def expire_orders():
            key = app.config.get('CRON_SECRET', '')
            if not key or not secrets.compare_digest(request.headers.get('Authorization', '').encode(), ('Bearer ' + key).encode()):
                return fail('Akses tidak diizinkan.', 401)
            return jsonify(expired=self.sweep_expired(500))

    def metadata(self, key, default):
        row = self.db().execute('SELECT value FROM metadata WHERE key=?', (key,)).fetchone()
        return json.loads(row['value']) if row else default

    def save_metadata(self, key, value):
        self.db().execute('INSERT INTO metadata(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value', (key, json.dumps(value)))

    def settings(self):
        return self.metadata('transaction-settings', {'deadline_enabled': False, 'payment_hours': 24, 'version': '0'})

    @staticmethod
    def decorate(order):
        order.setdefault('version', '0')
        order.setdefault('payment', {'status': 'pending' if order['status'] == 'baru' else 'unrecorded', 'reported_at': None, 'verified_at': None})
        order.setdefault('payment_deadline', None)
        order.setdefault('payment_hold', False)
        order.setdefault('cancellation_reason', None)
        return order

    def initialize_order(self, order):
        self.decorate(order)
        settings = self.settings()
        order['version'] = str(time.time_ns())
        order['payment_hours'] = settings['payment_hours']
        if settings['deadline_enabled']: order['payment_deadline'] = order['created_at'] + settings['payment_hours'] * 3600
        return order

    def record_created(self, order, customer_id):
        self.app.audit_log.record('order.created', 'order', order['nomor'], actor={'type': 'customer', 'id': customer_id})

    def write(self, order):
        order['version'] = str(time.time_ns())
        self.db().execute('UPDATE orders SET document=?,status=? WHERE id=?', (json.dumps(order), order['status'], order['nomor']))

    def cancel(self, order, reason):
        if order['status'] not in {'baru', 'diproses'} or order['payment']['status'] != 'pending' or order['payment_hold']:
            raise ValueError('Pesanan dikirim, sudah dibayar, dilaporkan transfer, atau ditahan tidak dapat dibatalkan. Hubungi CS untuk pemeriksaan.')
        for line in order['items']:
            row = self.db().execute('SELECT document FROM products WHERE id=?', (line['id'],)).fetchone()
            if not row: continue  # Historical deleted products must never be recreated.
            product = json.loads(row['document']); inventory.adjust(product, line['ukuran'], line['jumlah'])
            self.db().execute('UPDATE products SET document=?,updated_at=? WHERE id=?', (json.dumps(product), time.time_ns(), line['id']))
        order.update(status='dibatalkan', cancellation_reason=reason)

    def expire_one(self, order):
        if (order['status'] == 'baru' and order['payment']['status'] == 'pending' and not order['payment_hold']
                and order['payment_deadline'] and order['payment_deadline'] <= int(time.time())):
            self.cancel(order, 'kedaluwarsa'); self.write(order)
            self.app.audit_log.record('order.expired', 'order', order['nomor'], actor={'type': 'system'})
            return True
        return False

    def sweep_expired(self, limit=100):
        self.db().execute('BEGIN IMMEDIATE')
        field = "(document::jsonb->>'payment_deadline')::bigint" if self.app.config['DATABASE_URL'] else "json_extract(document,'$.payment_deadline')"
        payment = "document::jsonb->'payment'->>'status'" if self.app.config['DATABASE_URL'] else "json_extract(document,'$.payment.status')"
        no_hold = "COALESCE((document::jsonb->>'payment_hold')::boolean,FALSE)=FALSE" if self.app.config['DATABASE_URL'] else "COALESCE(json_extract(document,'$.payment_hold'),0)=0"
        rows = self.db().execute(f"SELECT document FROM orders WHERE status='baru' AND {field}<=? AND {payment}='pending' AND {no_hold} ORDER BY created_at,id LIMIT ?", (int(time.time()), limit)).fetchall()
        count = sum(self.expire_one(self.decorate(json.loads(row['document']))) for row in rows)
        self.db().commit()
        return count
