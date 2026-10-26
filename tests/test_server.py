import io
import json
import secrets
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from PIL import Image
from server import create_app, create_owner


class StoreTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.app = create_app({'TESTING': True, 'DATA_DIR': self.directory.name})
        self.password = secrets.token_urlsafe(24)
        create_owner(self.app, 'owner@example.test', self.password)
        self.client = self.app.test_client()
        csrf = self.client.get('/api/session').json['csrf']
        result = self.client.post('/api/login',json={'email':'owner@example.test','password':self.password},headers={'X-CSRF-Token':csrf})
        self.assertEqual(result.status_code,200)
        self.headers = {'X-CSRF-Token':result.json['csrf']}
        self.public = self.app.test_client()
        buyer_csrf=self.public.get('/api/customer/session').json['csrf']
        buyer=self.public.post('/api/customer/register',json={'nama':'Pembeli Uji','nohp':'081234567890','email':'customer@example.test','password':secrets.token_urlsafe(24)},headers={'X-CSRF-Token':buyer_csrf})
        self.assertEqual(buyer.status_code,201,buyer.json)
        self.buyer_headers={'X-CSRF-Token':buyer.json['csrf']}

    def tearDown(self):
        self.directory.cleanup()

    def product(self, **changes):
        payload = dict(nama='Jaket Suede', kategori='apparel', brand='Anredseller',deskripsi='Deskripsi jaket lengkap.',harga=299000,hargaAsli=349000,stok=4,gambarList=['assets/shirt.png'],ukuran=['S','M'],warna=['Hitam'],published=True)
        payload.update(changes)
        response = self.client.post('/api/admin/products',json=payload,headers=self.headers)
        self.assertEqual(response.status_code,201,response.json)
        return response.json['product']

    def order(self, product, quantity=1, key=None, **changes):
        data = dict(customer=dict(nama='Pembeli Uji',nama_penerima='Penerima Uji',email='customer@example.test',nohp='081234567890',alamat='Jl. Pengujian 1',kota='Jakarta',provinsi='DKI Jakarta',kodepos='12345'),items=[dict(id=product['id'],harga=product['harga'],jumlah=quantity,ukuran='S',warna='Hitam')])
        data.update(changes)
        return self.public.post('/api/orders',json=data,headers={**self.buyer_headers,'Idempotency-Key':key or secrets.token_hex(16)})

    def current_product(self, product_id):
        return next(p for p in self.client.get('/api/admin/products').json['products'] if p['id']==product_id)

    def simultaneous_orders(self, product, keys):
        cookie = self.public.get_cookie('session').value
        payload = dict(customer=dict(nama_penerima='Penerima Uji',nohp='081234567890',alamat='Jl. Uji 1',kota='Jakarta',provinsi='DKI Jakarta',kodepos='12345'),items=[dict(id=product['id'],harga=product['harga'],jumlah=1,ukuran='S',warna='Hitam')])
        def submit(key):
            client = self.app.test_client()
            client.set_cookie('session',cookie)
            return client.post('/api/orders',json=payload,headers={**self.buyer_headers,'Idempotency-Key':key})
        with ThreadPoolExecutor(max_workers=2) as executor:
            return list(executor.map(submit,keys))

    def test_concurrent_checkout_cannot_oversell_last_item(self):
        product = self.product(stok=1)
        responses = self.simultaneous_orders(product,[secrets.token_hex(16),secrets.token_hex(16)])
        self.assertEqual(sorted(response.status_code for response in responses),[201,409])
        self.assertEqual(self.current_product(product['id'])['stok'],0)
        self.assertEqual(len(self.client.get('/api/admin/orders').json['orders']),1)

    def test_concurrent_duplicate_checkout_reserves_stock_once(self):
        product = self.product(stok=2)
        key = secrets.token_hex(16)
        responses = self.simultaneous_orders(product,[key,key])
        self.assertEqual(sorted(response.status_code for response in responses),[200,201])
        self.assertEqual(responses[0].json['order']['nomor'],responses[1].json['order']['nomor'])
        self.assertEqual(self.current_product(product['id'])['stok'],1)

    def test_admin_auth_csrf_and_private_files(self):
        self.assertEqual(self.public.get('/api/admin/products').status_code,401)
        self.assertEqual(self.public.get('/api/admin/orders').status_code,401)
        self.assertEqual(self.client.post('/api/admin/products',json={}).status_code,403)
        for path in ['/server.py','/instance/store.sqlite3','/.git/config','/requirements.txt','/data/products.seed.json']:
            self.assertEqual(self.public.get(path).status_code,404,path)
        for path in ['/', '/admin']:
            with self.public.get(path) as response:
                self.assertEqual(response.status_code,200)

    def test_logout_revokes_copied_session(self):
        cookie = self.client.get_cookie('session').value
        replay = self.app.test_client()
        replay.set_cookie('session',cookie)
        self.assertEqual(replay.get('/api/admin/products').status_code,200)
        self.assertEqual(self.client.post('/api/logout',headers=self.headers).status_code,200)
        self.assertEqual(replay.get('/api/admin/products').status_code,401)

    def test_draft_publish_edit_delete_and_restart_persistence(self):
        product = self.product(published=False)
        self.assertNotIn(product['id'],[p['id'] for p in self.public.get('/api/products').json['products']])
        product['published'] = True
        changed = self.client.put('/api/admin/products/'+str(product['id']),json=product,headers=self.headers)
        self.assertEqual(changed.status_code,200,changed.json)
        self.assertIn(product['id'],[p['id'] for p in self.public.get('/api/products').json['products']])
        restarted = create_app({'TESTING':True,'DATA_DIR':self.directory.name}).test_client()
        self.assertIn(product['id'],[p['id'] for p in restarted.get('/api/products').json['products']])
        self.assertEqual(self.client.delete('/api/admin/products/'+str(product['id']),headers=self.headers).status_code,200)
        self.assertNotIn(product['id'],[p['id'] for p in restarted.get('/api/products').json['products']])

    def test_uploaded_photo_validated_and_persisted(self):
        image = io.BytesIO();Image.new('RGB',(20,30),'white').save(image,'PNG');image.seek(0)
        uploaded = self.client.post('/api/admin/uploads',data={'photo':(image,'../../picture.png')},headers=self.headers)
        self.assertEqual(uploaded.status_code,201,uploaded.json)
        self.assertTrue(uploaded.json['url'].endswith('.webp'))
        with self.public.get(uploaded.json['url']) as response:
            self.assertEqual(response.mimetype,'image/webp')
        self.product(gambarList=[uploaded.json['url']])
        rejected = self.client.post('/api/admin/uploads',data={'photo':(io.BytesIO(b'<svg onload="alert(1)"/>'),'photo.svg')},headers=self.headers)
        self.assertEqual(rejected.status_code,400)
        self.assertEqual(self.public.post('/api/admin/uploads',data={}).status_code,401)

    def test_product_validation_and_bad_request_shapes(self):
        self.assertEqual(self.client.post('/api/admin/products',json=[],headers=self.headers).status_code,400)
        product = self.product()
        for change in [{'harga':-1},{'stok':-1},{'gambarList':['https://untrusted.invalid/photo.png']},{'ukuran':'M'},{'hargaAsli':1}]:
            payload=dict(product,**change)
            self.assertEqual(self.client.put('/api/admin/products/'+str(product['id']),json=payload,headers=self.headers).status_code,400,change)
        self.assertEqual(self.public.post('/api/orders',json=[],headers=self.buyer_headers).status_code,400)

    def test_order_authoritative_price_variants_stock_and_idempotency(self):
        product = self.product()
        self.assertEqual(self.order(product,items=[dict(id=product['id'],jumlah=1,harga=1,ukuran='S',warna='Hitam')]).status_code,409)
        self.assertEqual(self.order(product,items=[dict(id=product['id'],jumlah=1,harga=product['harga'],ukuran='XL',warna='Hitam')]).status_code,409)
        self.assertEqual(self.order(product,quantity=0).status_code,409)
        key = secrets.token_hex(16)
        result = self.order(product,quantity=2,key=key,total=1)
        self.assertEqual(result.status_code,201,result.json)
        self.assertEqual(result.json['order']['total'],598000)
        self.assertEqual(self.current_product(product['id'])['stok'],2)
        again = self.order(product,quantity=2,key=key)
        self.assertEqual(again.json['order']['nomor'],result.json['order']['nomor'])
        self.assertEqual(self.current_product(product['id'])['stok'],2)
        self.assertEqual(self.order(product,quantity=3).status_code,409)
        self.assertEqual(len(self.client.get('/api/admin/orders').json['orders']),1)
        self.assertEqual(self.public.get('/api/admin/orders').status_code,401)

    def test_stale_admin_edit_rejected_after_order(self):
        product = self.product()
        self.assertEqual(self.order(product).status_code,201)
        changed = self.client.put('/api/admin/products/'+str(product['id']),json=product,headers=self.headers)
        self.assertEqual(changed.status_code,409)
        self.assertEqual(self.current_product(product['id'])['stok'],3)

    def test_order_cancellation_restores_stock_once(self):
        product = self.product()
        order = self.order(product,quantity=2).json['order']
        for _ in range(2):
            result = self.client.patch('/api/admin/orders/'+order['nomor'],json={'status':'dibatalkan'},headers=self.headers)
            self.assertEqual(result.status_code,200)
        self.assertEqual(self.current_product(product['id'])['stok'],4)
        self.assertEqual(self.client.patch('/api/admin/orders/'+order['nomor'],json={'status':'baru'},headers=self.headers).status_code,409)

    def test_discount_shipping_and_drafts_not_orderable(self):
        product = self.product(harga=10000,hargaAsli=10000)
        promo = dict(code='HEMAT10',partner='',kind='percent',value=10,min_subtotal=0,max_discount=None,starts_at=None,expires_at=None,usage_limit=None,per_customer_limit=1,active=True,version='0')
        self.assertEqual(self.client.post('/api/admin/promos',json=promo,headers=self.headers).status_code,201)
        result = self.order(product,coupon='HEMAT10')
        self.assertEqual(result.status_code,201)
        order = result.json['order']
        self.assertEqual((order['subtotal'],order['diskon'],order['ongkir'],order['total']),(10000,1000,15000,24000))
        draft = self.product(published=False)
        self.assertEqual(self.order(draft).status_code,409)

    def test_multiple_variant_lines_share_product_stock(self):
        product = self.product(stok=2)
        lines=[dict(id=product['id'],harga=product['harga'],jumlah=2,ukuran=size,warna='Hitam') for size in ['S','M']]
        self.assertEqual(self.order(product,items=lines).status_code,409)
        self.assertEqual(self.current_product(product['id'])['stok'],2)
        for line in lines:line['jumlah']=1
        self.assertEqual(self.order(product,items=lines).status_code,201)
        self.assertEqual(self.current_product(product['id'])['stok'],0)


if __name__=='__main__': unittest.main()
