from order_workflow import advance
import json
import secrets
import tempfile
import time
import unittest
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch

from server import create_app, create_owner
import test_server


class PromoTests(unittest.TestCase):
    product = test_server.StoreTests.product
    order = test_server.StoreTests.order
    current_product = test_server.StoreTests.current_product

    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.app = create_app({'TESTING':True,'DATA_DIR':self.directory.name})
        password = secrets.token_urlsafe(24)
        create_owner(self.app,'owner@example.test',password)
        self.client = self.app.test_client()
        csrf = self.client.get('/api/session').json['csrf']
        result = self.client.post('/api/login',json=dict(email='owner@example.test',password=password),headers={'X-CSRF-Token':csrf})
        self.headers = {'X-CSRF-Token':result.json['csrf']}
        self.public,self.buyer_headers = self.buyer('first')

    def tearDown(self):
        self.directory.cleanup()

    def buyer(self,name):
        client = self.app.test_client()
        csrf = client.get('/api/customer/session').json['csrf']
        result = client.post('/api/customer/register',json=dict(nama=name,nohp='081234567890',email=name+'@example.test',password=secrets.token_urlsafe(24)),headers={'X-CSRF-Token':csrf})
        self.assertEqual(result.status_code,201,result.json)
        return client,{'X-CSRF-Token':result.json['csrf']}

    def promo(self, **changes):
        payload = dict(code='PARTNER10',partner='Partner Uji',kind='percent',value=10,
                       min_subtotal=0,max_discount=None,starts_at=None,expires_at=None,
                       usage_limit=None,per_customer_limit=1,active=True,version='0')
        payload.update(changes)
        result = self.client.post('/api/admin/promos',json=payload,headers=self.headers)
        self.assertEqual(result.status_code,201,result.json)
        return result.json['promo']

    def state(self):
        return self.client.get('/api/admin/promos').json['promos']

    def preview(self,code='PARTNER10',**data):
        return self.public.post('/api/customer/promo',json=dict(code=code,**data),headers=self.buyer_headers)

    def add_cart(self, product, quantity=1):
        result = self.public.post('/api/customer/cart',json=dict(action='add',id=product['id'],jumlah=quantity,ukuran='S',warna='Hitam'),headers=self.buyer_headers)
        self.assertEqual(result.status_code,200,result.json)

    def test_private_owner_api_csrf_and_no_automatic_discounts(self):
        self.assertEqual(self.state(),[])
        self.assertEqual(self.public.get('/api/admin/promos').status_code,401)
        self.assertEqual(self.public.post('/api/admin/promos',json={},headers=self.buyer_headers).status_code,401)
        self.assertEqual(self.client.post('/api/admin/promos',json={}).status_code,403)
        self.assertEqual(self.app.test_client().post('/api/customer/promo',json={'code':'PARTNER10'}).status_code,401)
        self.assertEqual(self.public.post('/api/customer/promo',json={'code':'PARTNER10'}).status_code,403)
        product = self.product()
        self.assertEqual(self.order(product,coupon='HEMAT10').status_code,409)
        self.assertEqual(self.order(product).json['order']['diskon'],0)
        self.assertEqual(self.public.get('/api/store/content').headers['Cache-Control'],'no-store')
        self.promo(partner='Private partner')
        self.assertNotIn('Private partner',self.public.get('/api/store/content').text)

    def test_checkout_without_promo_needs_no_configured_or_available_code(self):
        product=self.product(stok=6)
        for changes in [{},{'coupon':'','expected_discount':0},{'coupon':'   ','expected_discount':0}]:
            result=self.order(product,**changes)
            self.assertEqual(result.status_code,201,result.json)
            self.assertEqual(result.json['order']['diskon'],0)
            self.assertNotIn('promo',result.json['order'])
        self.promo(active=False)
        self.assertEqual(self.order(product,coupon='',expected_discount=0).status_code,201)

    def test_withdrawn_promo_allows_same_checkout_key_retry_without_promo(self):
        self.promo(active=False)
        product=self.product();key=secrets.token_hex(16)
        rejected=self.order(product,key=key,coupon='PARTNER10',expected_discount=29900)
        self.assertEqual(rejected.status_code,409)
        self.assertEqual(rejected.json['code'],'promo_unavailable')
        self.assertEqual(self.current_product(product['id'])['stok'],4)
        retry=self.order(product,key=key,coupon='',expected_discount=0)
        self.assertEqual(retry.status_code,201,retry.json)
        self.assertEqual(retry.json['order']['diskon'],0)
        self.assertEqual(self.order(product,key=key,coupon='',expected_discount=0).status_code,200)
        self.assertEqual(self.current_product(product['id'])['stok'],3)
    def test_normalization_duplicate_codes_and_stale_edits(self):
        promo = self.promo(code='  partner10  ')
        self.assertEqual(promo['code'],'PARTNER10')
        duplicate = self.client.post('/api/admin/promos',json=dict(promo,version='0'),headers=self.headers)
        self.assertEqual(duplicate.status_code,409)
        updated = self.client.put('/api/admin/promos/PARTNER10',json=dict(promo,active=False),headers=self.headers)
        self.assertEqual(updated.status_code,200)
        self.assertEqual(self.client.put('/api/admin/promos/PARTNER10',json=promo,headers=self.headers).status_code,409)
        self.assertEqual(self.client.put('/api/admin/promos/PARTNER10',json=dict(promo,code='OTHER10'),headers=self.headers).status_code,400)
        self.assertEqual(self.client.delete('/api/admin/promos/PARTNER10',headers=self.headers).status_code,405)

    def test_invalid_settings_rejected_without_writes(self):
        valid = self.promo()
        bad = [{'code':'💸SALE'}, {'code':'ＡＢＣ'}, {'code':'AA'}, {'code':'a'*33},
               {'code':None}, {'partner':[]}, {'kind':[]}, {'active':1}, {'value':True},
               {'value':0}, {'value':101}, {'value':10.5}, {'min_subtotal':-1},
               {'max_discount':0}, {'usage_limit':0}, {'per_customer_limit':None},
               {'per_customer_limit':0}, {'starts_at':True}, {'expires_at':-1},
               {'starts_at':100,'expires_at':100}, {'version':1}, {'injected':True},
               {'kind':'fixed','max_discount':10}]
        for change in bad:
            response = self.client.put('/api/admin/promos/PARTNER10',json=dict(valid,**change),headers=self.headers)
            self.assertEqual(response.status_code,400,(change,response.json))
        self.assertEqual(self.state()[0]['version'],valid['version'])

    def test_server_quote_uses_real_cart_and_does_not_reserve_quota(self):
        self.promo(usage_limit=1,max_discount=20000,min_subtotal=200000)
        product = self.product(harga=299999,hargaAsli=299999)
        self.assertEqual(self.preview().status_code,409)
        self.add_cart(product)
        for _ in range(2):
            result = self.preview(' partner10 ',subtotal=1,discount=99999999,total=0)
            self.assertEqual(result.status_code,200,result.json)
            quote = result.json['quote']
            self.assertEqual((quote['subtotal'],quote['discount'],quote['total']),(299999,20000,279999))
            self.assertNotIn('partner',quote)
        self.assertEqual(self.state()[0]['used'],0)
        order = self.order(product,coupon='partner10',total=1,diskon=9999999).json['order']
        self.assertEqual(order['total'],279999)
        self.assertEqual(order['promo']['partner'],'Partner Uji')
        self.assertEqual(self.state()[0]['used'],1)

    def test_percent_rounding_fixed_clamp_and_shipping_basis(self):
        self.promo()
        product = self.product(harga=199999,hargaAsli=199999)
        order = self.order(product,coupon='PARTNER10').json['order']
        self.assertEqual((order['diskon'],order['ongkir'],order['total']),(19999,15000,195000))
        self.promo(code='FIXED',kind='fixed',value=500000)
        order = self.order(product,coupon='FIXED').json['order']
        self.assertEqual((order['diskon'],order['ongkir'],order['total']),(199999,15000,15000))
        self.promo(code='FREE',kind='percent',value=100)
        big = self.product(harga=200000,hargaAsli=200000)
        order = self.order(big,coupon='FREE').json['order']
        self.assertEqual((order['diskon'],order['ongkir'],order['total']),(200000,0,0))

    def test_dates_minimum_inactive_and_invalid_code_rollback(self):
        now = int(time.time())
        self.promo(active=False)
        self.promo(code='FUTURE',starts_at=now+300)
        self.promo(code='EXPIRED',expires_at=now-1)
        self.promo(code='MINIMUM',min_subtotal=500000)
        product = self.product()
        for code in ['PARTNER10','FUTURE','EXPIRED','MINIMUM','MISSING',[],True,123]:
            result = self.order(product,coupon=code)
            self.assertIn(result.status_code,(400,409),(code,result.json))
            self.assertEqual(self.current_product(product['id'])['stok'],4)
        self.assertEqual(self.client.get('/api/admin/orders').json['orders'],[])

    def test_exact_schedule_boundary(self):
        now = int(time.time())
        self.promo(starts_at=now,expires_at=now+60)
        product=self.product()
        self.add_cart(product)
        with patch('promo_codes.now_seconds',return_value=now-1):
            self.assertEqual(self.preview().status_code,409)
        with patch('promo_codes.now_seconds',return_value=now):
            self.assertEqual(self.preview().status_code,200)
        with patch('promo_codes.now_seconds',return_value=now+60):
            self.assertEqual(self.preview().status_code,409)

    def test_account_limit_cancellation_idempotency_and_history(self):
        promo = self.promo(usage_limit=1)
        product = self.product()
        key = secrets.token_hex(16)
        order = self.order(product,coupon='PARTNER10',key=key).json['order']
        self.assertEqual(self.order(product,coupon='PARTNER10').status_code,409)
        self.assertEqual(self.state()[0]['used'],1)
        self.assertEqual(self.state()[0]['completed'],0)
        # An edit cannot change the discount/partner on an existing receipt.
        updated = self.client.put('/api/admin/promos/PARTNER10',json=dict(promo,value=20,partner='New partner',active=False),headers=self.headers)
        self.assertEqual(updated.status_code,200)
        retried = self.order(product,coupon='PARTNER10',key=key)
        self.assertEqual(retried.status_code,200)
        self.assertEqual(retried.json['order'],order)
        self.assertEqual(self.state()[0]['used'],1)
        for _ in range(2):
            advance(self.client,self.headers,order['nomor'],'dibatalkan')
        self.assertEqual(self.state()[0]['used'],0)
        active=dict(updated.json['promo'],active=True)
        self.assertEqual(self.client.put('/api/admin/promos/PARTNER10',json=active,headers=self.headers).status_code,200)
        new_order=self.order(product,coupon='PARTNER10').json['order']
        self.assertEqual(new_order['promo']['partner'],'New partner')
        advance(self.client,self.headers,new_order['nomor'],'selesai')
        stat=self.state()[0]
        self.assertEqual((stat['used'],stat['completed'],stat['completed_sales'],stat['completed_discount']),(1,1,new_order['total'],new_order['diskon']))
        self.assertEqual(self.order(product,coupon='PARTNER10').status_code,409)

    def test_per_customer_limit_isolated_between_accounts(self):
        self.promo()
        product=self.product()
        self.assertEqual(self.order(product,coupon='PARTNER10').status_code,201)
        result=self.order(product,coupon='PARTNER10')
        self.assertEqual(result.status_code,409)
        self.assertIn('akunmu',result.json['error'])
        self.public,self.buyer_headers=self.buyer('second')
        self.assertEqual(self.order(product,coupon='PARTNER10').status_code,201)
        self.assertEqual(self.state()[0]['used'],2)

    def concurrent(self, same_key=False):
        self.promo(usage_limit=1,per_customer_limit=3)
        product=self.product(stok=10)
        customer=dict(nama_penerima='Penerima',nohp='081234567890',alamat='Jalan Uji',kota='Jakarta',provinsi='DKI Jakarta',kodepos='12345')
        payload=dict(customer=customer,coupon='PARTNER10',items=[dict(id=product['id'],harga=product['harga'],jumlah=1,ukuran='S',warna='Hitam')])
        cookie=self.public.get_cookie('session').value
        keys=[secrets.token_hex(16),secrets.token_hex(16)]
        if same_key:keys[1]=keys[0]
        def submit(key):
            client=self.app.test_client();client.set_cookie('session',cookie)
            return client.post('/api/orders',json=payload,headers={**self.buyer_headers,'Idempotency-Key':key})
        with ThreadPoolExecutor(max_workers=2) as pool:
            responses=list(pool.map(submit,keys))
        self.assertEqual(sorted(r.status_code for r in responses),[200,201] if same_key else [201,409])
        self.assertEqual(self.current_product(product['id'])['stok'],9)
        self.assertEqual(self.state()[0]['used'],1)
        self.assertEqual(len(self.client.get('/api/admin/orders').json['orders']),1)

    def test_simultaneous_checkout_cannot_exceed_quota(self):
        self.concurrent()

    def test_simultaneous_retries_consume_once(self):
        self.concurrent(same_key=True)

    def test_preview_invalidated_by_owner_and_stock_changes(self):
        promo=self.promo()
        product=self.product()
        self.add_cart(product)
        self.assertEqual(self.preview().status_code,200)
        self.client.put('/api/admin/promos/PARTNER10',json=dict(promo,active=False),headers=self.headers)
        self.assertEqual(self.order(product,coupon='PARTNER10').status_code,409)
        self.assertEqual(self.preview().status_code,409)
        self.assertEqual(self.current_product(product['id'])['stok'],4)

    def test_checkout_rejects_changed_quote_and_preserves_stock(self):
        promo=self.promo()
        product=self.product()
        self.add_cart(product)
        quote=self.preview().json['quote']
        self.client.put('/api/admin/promos/PARTNER10',json=dict(promo,value=5),headers=self.headers)
        result=self.order(product,coupon='PARTNER10',expected_discount=quote['discount'])
        self.assertEqual(result.status_code,409)
        self.assertIn('Diskon promo berubah',result.json['error'])
        self.assertEqual(result.json['code'],'promo_changed')
        self.assertEqual(self.current_product(product['id'])['stok'],4)
        self.assertEqual(self.state()[0]['used'],0)
        latest=self.preview().json['quote']
        self.assertEqual(self.order(product,coupon='PARTNER10',expected_discount=latest['discount']).status_code,201)

    def test_preview_rate_limit_persisted_and_login_not_affected(self):
        self.promo()
        self.add_cart(self.product())
        with self.app.app_context():
            customer_id=self.public.get('/api/customer/session').json['customer']['id']
            db=self.app.get_db()
            for _ in range(60):db.execute('INSERT INTO login_attempts VALUES(?,?)',('promo-preview:'+str(customer_id),int(time.time())))
            db.commit()
        self.assertEqual(self.preview().status_code,429)
        self.assertEqual(self.public.get('/api/customer/session').status_code,200)


if __name__=='__main__':unittest.main()
