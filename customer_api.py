"""Customer accounts and private, server-backed shopping data."""
import functools
import hashlib
import json
import re
import secrets
from database import INTEGRITY_ERRORS
import time
from urllib.parse import quote

from flask import g, jsonify, request, session
from werkzeug.security import check_password_hash, generate_password_hash


def cart_key(product_id, size='', color=''):
    return f"{product_id}:{quote(size, safe='!()*-._~')}:{quote(color, safe='!()*-._~')}"


class CustomerAPI:
    def __init__(self, app, db, fail, body):
        self.app, self.db, self.fail, self.body = app, db, fail, body
        if not app.config['DATABASE_URL']:
            with app.app_context():
                db().executescript('''
                    CREATE TABLE IF NOT EXISTS customers (id INTEGER PRIMARY KEY AUTOINCREMENT, email TEXT UNIQUE NOT NULL COLLATE NOCASE, password_hash TEXT NOT NULL, nama TEXT NOT NULL, nohp TEXT NOT NULL, created_at INTEGER NOT NULL);
                    CREATE TABLE IF NOT EXISTS customer_sessions (token TEXT PRIMARY KEY, customer_id INTEGER NOT NULL REFERENCES customers(id) ON DELETE CASCADE, expires_at INTEGER NOT NULL);
                    CREATE TABLE IF NOT EXISTS customer_addresses (id INTEGER PRIMARY KEY AUTOINCREMENT, customer_id INTEGER NOT NULL REFERENCES customers(id) ON DELETE CASCADE, document TEXT NOT NULL, is_default INTEGER NOT NULL DEFAULT 0);
                    CREATE UNIQUE INDEX IF NOT EXISTS customer_default_address ON customer_addresses(customer_id) WHERE is_default=1;
                    CREATE TABLE IF NOT EXISTS customer_state (customer_id INTEGER PRIMARY KEY REFERENCES customers(id) ON DELETE CASCADE, document TEXT NOT NULL, revision INTEGER NOT NULL DEFAULT 0);
                ''')
                columns = {row['name'] for row in db().execute('PRAGMA table_info(orders)')}
                if 'customer_id' not in columns:
                    db().execute('ALTER TABLE orders ADD COLUMN customer_id INTEGER REFERENCES customers(id)')
                db().execute('CREATE INDEX IF NOT EXISTS customer_order_history ON orders(customer_id,created_at)')
                db().commit()
        self.register_routes()

    def csrf(self):
        if 'customer_csrf' not in session:
            session['customer_csrf'] = secrets.token_urlsafe(32)
        return session['customer_csrf']

    def current(self):
        sid = session.get('customer_sid','')
        return self.db().execute('SELECT customers.* FROM customer_sessions JOIN customers ON customers.id=customer_sessions.customer_id WHERE customer_sessions.token=? AND expires_at>?', (hashlib.sha256(sid.encode()).hexdigest(),int(time.time()))).fetchone()

    def require_csrf(self):
        return secrets.compare_digest(request.headers.get('X-CSRF-Token',''),self.csrf())

    def required(self, function):
        @functools.wraps(function)
        def wrapped(*args,**kwargs):
            customer = self.current()
            if not customer:
                return self.fail('Silakan masuk ke akun pembeli terlebih dahulu.',401)
            if request.method not in {'GET','HEAD'} and not self.require_csrf():
                return self.fail('Sesi formulir berubah. Muat ulang halaman dan coba lagi.',403)
            g.customer = customer
            return function(*args,**kwargs)
        return wrapped

    @staticmethod
    def profile(customer):
        return {key:customer[key] for key in ['id','email','nama','nohp']}

    def start_session(self,customer_id):
        old = session.get('customer_sid','')
        self.db().execute('DELETE FROM customer_sessions WHERE token=? OR expires_at<?', (hashlib.sha256(old.encode()).hexdigest(),int(time.time())))
        sid = secrets.token_urlsafe(32)
        self.db().execute('INSERT INTO customer_sessions VALUES(?,?,?)',(hashlib.sha256(sid.encode()).hexdigest(),customer_id,int(time.time())+30*86400))
        session['customer_sid']=sid
        session['customer_csrf']=secrets.token_urlsafe(32)
        session.permanent=True

    def throttle(self,scope):
        key='customer:'+scope+':'+(request.remote_addr or 'unknown')
        now=int(time.time())
        self.db().execute('DELETE FROM login_attempts WHERE attempted_at<?',(now-900,))
        count=self.db().execute('SELECT COUNT(*) FROM login_attempts WHERE address=?',(key,)).fetchone()[0]
        if count>=10:
            return None
        self.db().execute('INSERT INTO login_attempts VALUES(?,?)',(key,now))
        self.db().commit()
        return key

    @staticmethod
    def text(data,key,maximum=150,required=True):
        value=data.get(key,'')
        if not isinstance(value,str) or len(value.strip())>maximum or (required and not value.strip()):
            raise ValueError(f'Isian {key.replace("_"," ")} tidak valid.')
        return value.strip()

    def validated_address(self,data):
        address={key:self.text(data,key,limit) for key,limit in {'nama_penerima':150,'nohp':30,'alamat':1000,'kota':100,'provinsi':100,'kodepos':5}.items()}
        address['label']=self.text(data,'label',40,False) or 'Alamat pengiriman'
        if not re.fullmatch(r'\d{5}',address['kodepos']):
            raise ValueError('Kode pos harus terdiri dari 5 angka.')
        if not re.fullmatch(r'[+()\d\s-]{7,30}',address['nohp']):
            raise ValueError('Nomor HP tidak valid.')
        return address

    def save_address(self,customer_id,data,address_id=None):
        address=self.validated_address(data)
        if address_id is not None:
            existing=self.db().execute('SELECT id,is_default FROM customer_addresses WHERE id=? AND customer_id=?',(address_id,customer_id)).fetchone()
            if not existing:
                raise ValueError('Alamat tidak ditemukan.')
        else:
            count=self.db().execute('SELECT COUNT(*) FROM customer_addresses WHERE customer_id=?',(customer_id,)).fetchone()[0]
            if count>=10:
                raise ValueError('Maksimal 10 alamat tersimpan. Hapus salah satu alamat lebih dahulu.')
            existing=None
        has_default=self.db().execute('SELECT 1 FROM customer_addresses WHERE customer_id=? AND is_default=1',(customer_id,)).fetchone()
        default=data.get('is_default') is True or not has_default or bool(existing and existing['is_default'])
        if default:
            self.db().execute('UPDATE customer_addresses SET is_default=0 WHERE customer_id=?',(customer_id,))
        if existing:
            self.db().execute('UPDATE customer_addresses SET document=?,is_default=? WHERE id=? AND customer_id=?',(json.dumps(address),default,address_id,customer_id))
        else:
            cursor=self.db().execute('INSERT INTO customer_addresses(customer_id,document,is_default) VALUES(?,?,?)',(customer_id,json.dumps(address),default))
            address_id=cursor.lastrowid
        return dict(address,id=address_id,is_default=default)

    def raw_state(self,customer_id):
        row=self.db().execute('SELECT * FROM customer_state WHERE customer_id=?',(customer_id,)).fetchone()
        return (json.loads(row['document']),row['revision']) if row else ({'cart':[],'wishlist':[]},0)

    def write_state(self,customer_id,data):
        self.db().execute('INSERT INTO customer_state(customer_id,document,revision) VALUES(?,?,1) ON CONFLICT(customer_id) DO UPDATE SET document=excluded.document,revision=customer_state.revision+1',(customer_id,json.dumps(data)))

    def resolved_state(self,customer_id):
        state,revision=self.raw_state(customer_id)
        lines=[]
        for stored in state['cart']:
            row=self.db().execute('SELECT document FROM products WHERE id=? AND published=1',(stored['id'],)).fetchone()
            product=json.loads(row['document']) if row else None
            valid=bool(product and product['stok']>0 and stored['ukuran'] in (product.get('ukuran') or ['']) and stored['warna'] in (product.get('warna') or ['']))
            lines.append(dict(stored,nama=product['nama'] if product else 'Produk tidak tersedia',harga=product['harga'] if product else stored['harga'],gambar=product['gambar'] if product else stored['gambar'],stok=product['stok'] if valid else 0,available=valid))
        return {'cart':lines,'wishlist':state['wishlist'],'revision':revision,'customer_id':customer_id}

    def consume_cart(self,customer_id,items):
        state,_=self.raw_state(customer_id)
        quantities={}
        for item in items:
            key=cart_key(item['id'],item['ukuran'],item['warna'])
            quantities[key]=quantities.get(key,0)+item['jumlah']
        state['cart']=[dict(line,jumlah=line['jumlah']-quantities.get(line['key'],0)) for line in state['cart'] if line['jumlah']>quantities.get(line['key'],0)]
        self.write_state(customer_id,state)

    def register_routes(self):
        app,db,fail,body=self.app,self.db,self.fail,self.body

        @app.get('/api/customer/session')
        def customer_session():
            customer=self.current()
            return jsonify(authenticated=bool(customer),customer=self.profile(customer) if customer else None,csrf=self.csrf())

        @app.post('/api/customer/register')
        def customer_register():
            if not self.require_csrf():return fail('Muat ulang halaman pendaftaran.',403)
            if not self.throttle('register'):return fail('Terlalu banyak percobaan pendaftaran. Coba lagi dalam 15 menit.',429)
            data=body()
            try:
                email=self.text(data,'email').lower()
                name=self.text(data,'nama')
                phone=self.text(data,'nohp',30)
                password=data.get('password','')
                if not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+',email):raise ValueError('Email tidak valid.')
                if not isinstance(password,str) or not 12<=len(password)<=128:raise ValueError('Kata sandi harus 12–128 karakter.')
                if not re.fullmatch(r'[+()\d\s-]{7,30}',phone):raise ValueError('Nomor HP tidak valid.')
                hashed=generate_password_hash(password)
                cursor=db().execute('INSERT INTO customers(email,password_hash,nama,nohp,created_at) VALUES(?,?,?,?,?)',(email,hashed,name,phone,int(time.time())))
                self.start_session(cursor.lastrowid)
                db().commit()
            except ValueError as error:
                db().rollback();return fail(str(error))
            except INTEGRITY_ERRORS:
                db().rollback();return fail('Email sudah terdaftar. Gunakan halaman masuk.',409)
            return jsonify(authenticated=True,customer=self.profile(self.current()),csrf=self.csrf()),201

        @app.post('/api/customer/login')
        def customer_login():
            if not self.require_csrf():return fail('Muat ulang halaman masuk.',403)
            limit=self.throttle('login')
            if not limit:return fail('Terlalu banyak percobaan masuk. Coba lagi dalam 15 menit.',429)
            data=body()
            email=str(data.get('email','')).strip().lower()
            password=data.get('password','')
            customer=db().execute('SELECT * FROM customers WHERE email=?',(email,)).fetchone()
            if not isinstance(password,str) or len(password)>128 or not customer or not check_password_hash(customer['password_hash'],password):return fail('Email atau kata sandi salah.',401)
            db().execute('DELETE FROM login_attempts WHERE address=?',(limit,))
            self.start_session(customer['id']);db().commit()
            return jsonify(authenticated=True,customer=self.profile(customer),csrf=self.csrf())

        @app.post('/api/customer/logout')
        @self.required
        def customer_logout():
            db().execute('DELETE FROM customer_sessions WHERE token=?',(hashlib.sha256(session.get('customer_sid','').encode()).hexdigest(),));db().commit()
            session.pop('customer_sid',None);session.pop('customer_csrf',None)
            return jsonify(ok=True)

        @app.get('/api/customer/profile')
        @self.required
        def customer_profile():return jsonify(customer=self.profile(g.customer))

        @app.put('/api/customer/profile')
        @self.required
        def update_profile():
            data=body()
            try:
                name=self.text(data,'nama');phone=self.text(data,'nohp',30)
                if not re.fullmatch(r'[+()\d\s-]{7,30}',phone):raise ValueError('Nomor HP tidak valid.')
            except ValueError as error:return fail(str(error))
            db().execute('UPDATE customers SET nama=?,nohp=? WHERE id=?',(name,phone,g.customer['id']));db().commit()
            return jsonify(customer=self.profile(self.current()))

        @app.post('/api/customer/password')
        @self.required
        def change_password():
            data=body();password=data.get('password','');current=data.get('current_password','')
            if not isinstance(current,str) or len(current)>128 or not check_password_hash(g.customer['password_hash'],current):return fail('Kata sandi saat ini salah.',400)
            if not isinstance(password,str) or not 12<=len(password)<=128:return fail('Kata sandi baru harus 12–128 karakter.')
            db().execute('UPDATE customers SET password_hash=? WHERE id=?',(generate_password_hash(password),g.customer['id']))
            db().execute('DELETE FROM customer_sessions WHERE customer_id=?',(g.customer['id'],))
            self.start_session(g.customer['id']);db().commit()
            return jsonify(ok=True,csrf=self.csrf())

        @app.get('/api/customer/addresses')
        @self.required
        def customer_addresses():
            rows=db().execute('SELECT * FROM customer_addresses WHERE customer_id=? ORDER BY is_default DESC,id DESC',(g.customer['id'],)).fetchall()
            return jsonify(addresses=[dict(json.loads(row['document']),id=row['id'],is_default=bool(row['is_default'])) for row in rows])

        @app.post('/api/customer/addresses')
        @self.required
        def add_address():
            db().execute('BEGIN IMMEDIATE')
            try:address=self.save_address(g.customer['id'],body());db().commit()
            except ValueError as error:db().rollback();return fail(str(error))
            return jsonify(address=address),201

        @app.put('/api/customer/addresses/<int:address_id>')
        @self.required
        def edit_address(address_id):
            db().execute('BEGIN IMMEDIATE')
            try:address=self.save_address(g.customer['id'],body(),address_id);db().commit()
            except ValueError as error:db().rollback();return fail(str(error),404 if str(error)=='Alamat tidak ditemukan.' else 400)
            return jsonify(address=address)

        @app.delete('/api/customer/addresses/<int:address_id>')
        @self.required
        def delete_address(address_id):
            db().execute('BEGIN IMMEDIATE')
            deleted=db().execute('DELETE FROM customer_addresses WHERE id=? AND customer_id=?',(address_id,g.customer['id'])).rowcount
            if not deleted:db().rollback();return fail('Alamat tidak ditemukan.',404)
            if not db().execute('SELECT 1 FROM customer_addresses WHERE customer_id=? AND is_default=1',(g.customer['id'],)).fetchone():
                db().execute('UPDATE customer_addresses SET is_default=1 WHERE id=(SELECT id FROM customer_addresses WHERE customer_id=? ORDER BY id DESC LIMIT 1)',(g.customer['id'],))
            db().commit();return jsonify(ok=True)

        @app.get('/api/customer/state')
        @self.required
        def shopping_state():return jsonify(state=self.resolved_state(g.customer['id']))

        @app.post('/api/customer/cart')
        @self.required
        def shopping_cart():
            data=body();action=data.get('action');customer_id=g.customer['id']
            if not isinstance(action,str) or action not in {'add','update','remove','clear'}:return fail('Perubahan keranjang tidak valid.')
            db().execute('BEGIN IMMEDIATE');state,_=self.raw_state(customer_id)
            try:
                if action=='clear':state['cart']=[]
                elif action in {'remove','update'}:
                    key=data.get('key');line=next((line for line in state['cart'] if line['key']==key),None)
                    if not line:raise ValueError('Item keranjang tidak ditemukan. Muat ulang halaman.')
                    quantity=data.get('jumlah') if action=='update' else 0
                    if isinstance(quantity,bool) or not isinstance(quantity,int) or not 0<=quantity<=1000:raise ValueError('Jumlah produk tidak valid.')
                    if quantity==0:state['cart'].remove(line)
                    else:
                        row=db().execute('SELECT document FROM products WHERE id=? AND published=1',(line['id'],)).fetchone()
                        product=json.loads(row['document']) if row else None
                        other=sum(item['jumlah'] for item in state['cart'] if item['id']==line['id'] and item['key']!=key)
                        if not product or other+quantity>product['stok']:raise ValueError('Stok tidak mencukupi. Kurangi jumlah atau hapus item.')
                        line['jumlah']=quantity
                elif action=='add':
                    product_id=data.get('id');quantity=data.get('jumlah',1);size=data.get('ukuran','');color=data.get('warna','')
                    if isinstance(product_id,bool) or not isinstance(product_id,int) or isinstance(quantity,bool) or not isinstance(quantity,int) or not 1<=quantity<=1000:raise ValueError('Produk atau jumlah tidak valid.')
                    row=db().execute('SELECT document FROM products WHERE id=? AND published=1',(product_id,)).fetchone();product=json.loads(row['document']) if row else None
                    if not product:raise ValueError('Produk tidak tersedia.')
                    if not isinstance(size,str) or not isinstance(color,str) or size not in (product.get('ukuran') or ['']) or color not in (product.get('warna') or ['']):raise ValueError('Pilih ukuran dan warna yang tersedia.')
                    total=sum(line['jumlah'] for line in state['cart'] if line['id']==product_id)
                    if total+quantity>product['stok']:raise ValueError('Stok produk tidak mencukupi.')
                    key=cart_key(product_id,size,color);line=next((line for line in state['cart'] if line['key']==key),None)
                    if line:line['jumlah']+=quantity
                    else:
                        if len(state['cart'])>=50:raise ValueError('Keranjang maksimal 50 pilihan produk.')
                        state['cart'].append(dict(key=key,id=product_id,jumlah=quantity,ukuran=size,warna=color,nama=product['nama'],gambar=product['gambar'],harga=product['harga']))
                else:raise ValueError('Perubahan keranjang tidak valid.')
                self.write_state(customer_id,state);db().commit()
            except ValueError as error:db().rollback();return fail(str(error),409)
            return jsonify(state=self.resolved_state(customer_id))

        @app.post('/api/customer/wishlist')
        @self.required
        def shopping_wishlist():
            data=body();product_id=data.get('id')
            if isinstance(product_id,bool) or not isinstance(product_id,int):return fail('Produk tidak valid.')
            db().execute('BEGIN IMMEDIATE');state,_=self.raw_state(g.customer['id'])
            if product_id in state['wishlist']:state['wishlist'].remove(product_id)
            else:
                if not db().execute('SELECT 1 FROM products WHERE id=? AND published=1',(product_id,)).fetchone():db().rollback();return fail('Produk tidak tersedia.',404)
                if len(state['wishlist'])>=200:db().rollback();return fail('Wishlist maksimal 200 produk.')
                state['wishlist'].append(product_id)
            self.write_state(g.customer['id'],state);db().commit()
            return jsonify(state=self.resolved_state(g.customer['id']))

        @app.get('/api/customer/orders')
        @self.required
        def customer_orders():
            rows=db().execute('SELECT document,status FROM orders WHERE customer_id=? ORDER BY created_at DESC,id DESC',(g.customer['id'],)).fetchall()
            return jsonify(orders=[dict(json.loads(row['document']),status=row['status']) for row in rows])

        @app.get('/api/customer/orders/<order_id>')
        @self.required
        def customer_order(order_id):
            row=db().execute('SELECT document,status FROM orders WHERE id=? AND customer_id=?',(order_id,g.customer['id'])).fetchone()
            if not row:return fail('Pesanan tidak ditemukan.',404)
            return jsonify(order=dict(json.loads(row['document']),status=row['status']))
