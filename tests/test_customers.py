import hashlib
import json
import secrets
import tempfile
import unittest
from server import create_app, create_owner


class CustomerTests(unittest.TestCase):
    def setUp(self):
        self.directory=tempfile.TemporaryDirectory()
        self.app=create_app({'TESTING':True,'DATA_DIR':self.directory.name})
        self.password=secrets.token_urlsafe(24)
        self.a,self.ah=self.register('alice@example.test','Alice')
        self.b,self.bh=self.register('bob@example.test','Bob')

    def tearDown(self):self.directory.cleanup()

    def register(self,email,name='Pembeli'):
        client=self.app.test_client();csrf=client.get('/api/customer/session').json['csrf']
        response=client.post('/api/customer/register',json={'email':email,'nama':name,'nohp':'081234567890','password':self.password,'role':'admin'},headers={'X-CSRF-Token':csrf})
        self.assertEqual(response.status_code,201,response.json)
        return client,{'X-CSRF-Token':response.json['csrf']}

    def test_only_email_authentication_is_exposed(self):
        response = self.a.get('/api/customer/session').json
        self.assertNotIn('providers', response)
        self.assertNotIn('google_linked', response['customer'])
        for path, method in [('/google/start', 'post'), ('/google/callback', 'get'), ('/google/unlink', 'post')]:
            self.assertIn(getattr(self.a, method)('/api/customer' + path).status_code, {404, 405})
        self.assertFalse(any('/google/' in rule.rule for rule in self.app.url_map.iter_rules()))
        with self.a.get('/akun.html') as page:
            html = page.data.decode()
        self.assertNotIn('google-login', html)
        self.assertNotIn('google-connect', html)
        self.assertNotIn('google-security-dialog', html)

    def login(self,email,password=None):
        client=self.app.test_client();csrf=client.get('/api/customer/session').json['csrf']
        response=client.post('/api/customer/login',json={'email':email,'password':password or self.password},headers={'X-CSRF-Token':csrf})
        self.assertEqual(response.status_code,200,response.json)
        return client,{'X-CSRF-Token':response.json['csrf']}

    def product(self):
        # Seed products have no options; clients still receive server prices.
        return self.a.get('/api/products').json['products'][0]

    def address(self,client,headers,**changes):
        data={'label':'Rumah','nama_penerima':'Penerima','nohp':'081234567890','alamat':'Jl. Uji 1','kota':'Jakarta','provinsi':'DKI Jakarta','kodepos':'12345'};data.update(changes)
        response=client.post('/api/customer/addresses',json=data,headers=headers)
        self.assertEqual(response.status_code,201,response.json)
        return response.json['address']

    def order(self,client,headers,key=None,**changes):
        product=self.product()
        data={'customer':{'nama':'Nama palsu','email':'other@example.test','nama_penerima':'Penerima','nohp':'081234567890','alamat':'Jl. Uji 1','kota':'Jakarta','provinsi':'DKI Jakarta','kodepos':'12345'},'items':[{'id':product['id'],'harga':product['harga'],'jumlah':1}]};data.update(changes)
        return client.post('/api/orders',json=data,headers={**headers,'Idempotency-Key':key or secrets.token_hex(16)})

    def test_catalog_public_checkout_requires_customer_not_owner(self):
        guest=self.app.test_client()
        self.assertEqual(guest.get('/api/products').status_code,200)
        self.assertEqual(guest.post('/api/orders',json={}).status_code,401)
        self.assertEqual(guest.get('/api/customer/profile').status_code,401)
        self.assertEqual(self.a.get('/api/admin/products').status_code,401)
        self.assertEqual(self.a.get('/api/admin/orders').status_code,401)
        self.assertEqual(self.a.post('/api/customer/cart',json={}).status_code,403)
        self.assertEqual(self.a.get('/customer_api.py').status_code,404)

    def test_profile_addresses_and_defaults_are_scoped(self):
        self.assertEqual(self.a.put('/api/customer/profile',json={'nama':'Alice Baru','nohp':'089123456789','id':2,'role':'owner'},headers=self.ah).status_code,200)
        self.assertEqual(self.b.get('/api/customer/profile').json['customer']['nama'],'Bob')
        first=self.address(self.a,self.ah);second=self.address(self.a,self.ah,label='Kantor',is_default=True)
        self.assertTrue(first['is_default'])
        rows=self.a.get('/api/customer/addresses').json['addresses'];self.assertEqual(sum(row['is_default'] for row in rows),1);self.assertEqual(rows[0]['id'],second['id'])
        self.assertEqual(self.b.get('/api/customer/addresses').json['addresses'],[])
        self.assertEqual(self.b.put('/api/customer/addresses/'+str(first['id']),json=first,headers=self.bh).status_code,404)
        self.assertEqual(self.b.delete('/api/customer/addresses/'+str(first['id']),headers=self.bh).status_code,404)
        self.assertEqual(self.a.delete('/api/customer/addresses/'+str(second['id']),headers=self.ah).status_code,200)
        self.assertTrue(self.a.get('/api/customer/addresses').json['addresses'][0]['is_default'])

    def test_cart_wishlist_cross_device_and_account_isolation(self):
        product=self.product();line={'action':'add','id':product['id'],'jumlah':1,'harga':1,'customer_id':2}
        response=self.a.post('/api/customer/cart',json=line,headers=self.ah);self.assertEqual(response.status_code,200,response.json)
        self.assertEqual(response.json['state']['cart'][0]['harga'],product['harga'])
        self.a.post('/api/customer/wishlist',json={'id':product['id']},headers=self.ah)
        other,other_headers=self.login('alice@example.test')
        state=other.get('/api/customer/state').json['state'];self.assertEqual(len(state['cart']),1);self.assertEqual(state['wishlist'],[product['id']])
        other.post('/api/customer/cart',json=line,headers=other_headers)
        self.assertEqual(self.a.get('/api/customer/state').json['state']['cart'][0]['jumlah'],2)
        self.assertEqual(self.b.get('/api/customer/state').json['state']['cart'],[])
        self.assertEqual(self.b.get('/api/customer/state').json['state']['wishlist'],[])
        self.assertEqual(self.b.post('/api/customer/cart',json={'action':'remove','key':state['cart'][0]['key']},headers=self.bh).status_code,409)

    def test_orders_scope_email_binding_idempotency_and_saved_address(self):
        product=self.product();self.a.post('/api/customer/cart',json={'action':'add','id':product['id'],'jumlah':2},headers=self.ah)
        key=secrets.token_hex(16)
        created=self.order(self.a,self.ah,key=key,save_address=True);self.assertEqual(created.status_code,201,created.json)
        order=created.json['order'];self.assertEqual(order['nama'],'Alice');self.assertEqual(order['email'],'alice@example.test')
        self.assertEqual(created.json['state']['cart'][0]['jumlah'],1)
        self.assertEqual(len(self.a.get('/api/customer/addresses').json['addresses']),1)
        self.assertEqual(len(self.a.get('/api/customer/orders').json['orders']),1)
        self.assertEqual(self.b.get('/api/customer/orders').json['orders'],[])
        self.assertEqual(self.b.get('/api/customer/orders/'+order['nomor']).status_code,404)
        again=self.order(self.a,self.ah,key=key);self.assertEqual(again.json['order']['nomor'],order['nomor'])
        self.assertEqual(self.a.get('/api/customer/state').json['state']['cart'][0]['jumlah'],1)
        other=self.order(self.b,self.bh,key=key);self.assertEqual(other.status_code,201);self.assertNotEqual(other.json['order']['nomor'],order['nomor'])
        foreign_address=self.a.get('/api/customer/addresses').json['addresses'][0]
        self.assertEqual(self.order(self.b,self.bh,address_id=foreign_address['id']).status_code,404)

    def test_logout_and_password_change_revoke_sessions(self):
        second,headers=self.login('alice@example.test')
        cookie=self.a.get_cookie('session').value;replay=self.app.test_client();replay.set_cookie('session',cookie)
        self.assertEqual(self.a.post('/api/customer/logout',headers=self.ah).status_code,200)
        self.assertEqual(replay.get('/api/customer/profile').status_code,401)
        self.assertEqual(second.get('/api/customer/profile').status_code,200)
        third,third_headers=self.login('alice@example.test');new_password=secrets.token_urlsafe(24)
        changed=second.post('/api/customer/password',json={'current_password':self.password,'password':new_password},headers=headers);self.assertEqual(changed.status_code,200)
        self.assertEqual(third.get('/api/customer/profile').status_code,401)
        self.assertEqual(second.get('/api/customer/profile').status_code,200)
        self.login('alice@example.test',new_password)

    def test_owner_customer_sessions_independent_same_browser(self):
        owner_password=secrets.token_urlsafe(24);create_owner(self.app,'owner@example.test',owner_password)
        csrf=self.a.get('/api/session').json['csrf']
        owner=self.a.post('/api/login',json={'email':'owner@example.test','password':owner_password},headers={'X-CSRF-Token':csrf});self.assertEqual(owner.status_code,200)
        self.assertEqual(self.a.get('/api/customer/profile').status_code,200)
        self.assertEqual(self.a.post('/api/logout',headers={'X-CSRF-Token':owner.json['csrf']}).status_code,200)
        self.assertEqual(self.a.get('/api/customer/profile').status_code,200)
        self.assertEqual(self.a.get('/api/admin/products').status_code,401)

    def test_logout_all_revokes_only_this_customer_and_preserves_owner(self):
        second, _ = self.login('alice@example.test')
        owner_password = secrets.token_urlsafe(24)
        create_owner(self.app, 'owner@example.test', owner_password)
        csrf = self.a.get('/api/session').json['csrf']
        self.assertEqual(self.a.post('/api/login', json={'email':'owner@example.test','password':owner_password}, headers={'X-CSRF-Token':csrf}).status_code, 200)
        self.assertEqual(self.a.post('/api/customer/logout-all').status_code, 403)
        self.assertEqual(self.a.post('/api/customer/logout-all', headers=self.ah).status_code, 200)
        self.assertEqual(self.a.get('/api/customer/profile').status_code, 401)
        self.assertEqual(second.get('/api/customer/profile').status_code, 401)
        self.assertEqual(self.b.get('/api/customer/profile').status_code, 200)
        self.assertEqual(self.a.get('/api/admin/products').status_code, 200)

    def test_legacy_guest_orders_not_claimed_by_matching_email(self):
        with self.app.app_context():
            self.app.get_db().execute('INSERT INTO orders(id,document,status,idempotency_key,created_at) VALUES(?,?,?,?,?)',('LEGACY',json.dumps({'email':'alice@example.test'}),'baru',secrets.token_hex(16),1));self.app.get_db().commit()
        self.assertEqual(self.a.get('/api/customer/orders').json['orders'],[])
        self.assertEqual(self.a.get('/api/customer/orders/LEGACY').status_code,404)
        restarted=create_app({'TESTING':True,'DATA_DIR':self.directory.name})
        with restarted.app_context():self.assertIsNone(restarted.get_db().execute('SELECT customer_id FROM orders WHERE id=?', ('LEGACY',)).fetchone()[0])

    def test_registration_validation_duplicates_csrf_and_password_hash(self):
        client=self.app.test_client();csrf=client.get('/api/customer/session').json['csrf']
        data={'nama':'Uji','nohp':'081234567890','email':'new@example.test','password':'short'}
        self.assertEqual(client.post('/api/customer/register',json=data).status_code,403)
        self.assertEqual(client.post('/api/customer/register',json=data,headers={'X-CSRF-Token':csrf}).status_code,400)
        data.update(email='alice@example.test',password=self.password)
        self.assertEqual(client.post('/api/customer/register',json=data,headers={'X-CSRF-Token':csrf}).status_code,409)
        with self.app.app_context():
            row=self.app.get_db().execute('SELECT password_hash FROM customers WHERE email=?',('alice@example.test',)).fetchone();self.assertNotEqual(row['password_hash'],self.password);self.assertTrue(row['password_hash'].startswith('scrypt:'))
