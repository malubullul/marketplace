import json
import secrets
import tempfile
import time
import unittest
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch

from server import create_app, create_owner
import test_server
from order_workflow import advance


class SizeStockTests(unittest.TestCase):
    product = test_server.StoreTests.product
    order = test_server.StoreTests.order
    current_product = test_server.StoreTests.current_product

    def setUp(self):
        directory=tempfile.TemporaryDirectory();self.addCleanup(directory.cleanup)
        self.app=create_app({'TESTING':True,'DATA_DIR':directory.name})
        password=secrets.token_urlsafe(24);create_owner(self.app,'owner@example.test',password)
        self.client=self.app.test_client();csrf=self.client.get('/api/session').json['csrf']
        self.headers={'X-CSRF-Token':self.client.post('/api/login',json={'email':'owner@example.test','password':password},headers={'X-CSRF-Token':csrf}).json['csrf']}
        self.public=self.app.test_client();csrf=self.public.get('/api/customer/session').json['csrf']
        buyer=self.public.post('/api/customer/register',json=dict(email='buyer@example.test',nama='Buyer',nohp='081234567890',password=password),headers={'X-CSRF-Token':csrf})
        self.buyer_headers={'X-CSRF-Token':buyer.json['csrf']}

    def sizes(self, **values):
        return self.product(stokUkuran=[dict(ukuran=size,stok=stock) for size,stock in values.items()])

    def edit(self, product, **changes):
        return self.client.put('/api/admin/products/'+str(product['id']),json={**product,**changes},headers=self.headers)

    def test_validation_totals_and_unique_individual_sizes(self):
        product=self.sizes(S=2,M=5,L=0,XL=3)
        self.assertEqual(product['stok'],10);self.assertEqual(product['ukuran'],['S','M','L','XL'])
        for rows in [[],None,[{'ukuran':'S M XL','stok':2}],[{'ukuran':'S','stok':True}],
                     [{'ukuran':'S','stok':-1}],[{'ukuran':'S','stok':1.5}],
                     [{'ukuran':'S','stok':1},{'ukuran':'s','stok':2}]]:
            self.assertEqual(self.edit(product,stokUkuran=rows).status_code,400,rows)
        without_rows={k:v for k,v in product.items() if k!='stokUkuran'}
        self.assertEqual(self.client.put('/api/admin/products/'+str(product['id']),json=without_rows,headers=self.headers).status_code,400)

    def test_checkout_multiple_sizes_completion_and_retry_never_double_deduct(self):
        product=self.sizes(S=2,M=5)
        items=[dict(id=product['id'],harga=product['harga'],jumlah=n,ukuran=size,warna='Hitam') for size,n in [('S',2),('M',1)]]
        key=secrets.token_hex(16);created=self.order(product,items=items,key=key)
        self.assertEqual(created.status_code,201,created.json)
        number=created.json['order']['nomor']
        self.assertEqual(self.order(product,items=items,key=key).status_code,200)
        advance(self.client,self.headers,number,'selesai')
        current=self.current_product(product['id'])
        self.assertEqual(current['stokUkuran'],[dict(ukuran='S',stok=0),dict(ukuran='M',stok=4)])
        self.assertEqual(current['stok'],4);self.assertEqual(current['terjual'],3)

    def test_exact_size_rejected_when_other_sizes_have_stock(self):
        product=self.sizes(S=0,M=10)
        self.assertEqual(self.order(product).status_code,409)
        self.assertEqual(self.current_product(product['id'])['stok'],10)

    def test_concurrent_last_size_is_reserved_once(self):
        product=self.sizes(S=1,M=10);cookie=self.public.get_cookie('session').value
        def submit(_):
            client=self.app.test_client();client.set_cookie('session',cookie)
            payload=dict(customer=dict(nama_penerima='Buyer',nohp='081234567890',alamat='Jalan Uji 1',kota='Jakarta',provinsi='DKI Jakarta',kodepos='12345'),items=[dict(id=product['id'],harga=product['harga'],jumlah=1,ukuran='S',warna='Hitam')])
            return client.post('/api/orders',json=payload,headers={**self.buyer_headers,'Idempotency-Key':secrets.token_hex(16)}).status_code
        with ThreadPoolExecutor(max_workers=2) as pool:codes=list(pool.map(submit,range(2)))
        self.assertEqual(sorted(codes),[201,409])
        self.assertEqual(self.current_product(product['id'])['stokUkuran'],[dict(ukuran='S',stok=0),dict(ukuran='M',stok=10)])

    def test_cart_and_promo_pool_colors_within_size_but_not_across_sizes(self):
        product=self.product(stokUkuran=[dict(ukuran='S',stok=1),dict(ukuran='M',stok=3)],warna=['Hitam','Putih'])
        def add(size,color,n=1):return self.public.post('/api/customer/cart',json=dict(action='add',id=product['id'],jumlah=n,ukuran=size,warna=color),headers=self.buyer_headers)
        self.assertEqual(add('S','Hitam').status_code,200)
        self.assertEqual(add('S','Putih').status_code,409)
        result=add('M','Putih',3);self.assertEqual(result.status_code,200,result.json)
        cart=result.json['state']['cart'];self.assertEqual([r['stok'] for r in cart],[1,3])
        promo=dict(code='SIZE10',partner='',kind='percent',value=10,min_subtotal=0,max_discount=None,starts_at=None,expires_at=None,usage_limit=None,per_customer_limit=1,active=True,version='0')
        self.assertEqual(self.client.post('/api/admin/promos',json=promo,headers=self.headers).status_code,201)
        self.assertEqual(self.public.post('/api/customer/promo',json={'code':'SIZE10'},headers=self.buyer_headers).status_code,200)
        updated=self.public.post('/api/customer/cart',json={'action':'update','key':cart[0]['key'],'jumlah':2},headers=self.buyer_headers)
        self.assertEqual(updated.status_code,409)

    def test_cancel_and_expiry_restore_the_same_size_once_after_restock(self):
        product=self.sizes(S=2,M=4);order=self.order(product).json['order']
        current=self.current_product(product['id'])
        saved=self.edit(current,stokUkuran=[dict(ukuran='S',stok=6),dict(ukuran='M',stok=4)])
        self.assertEqual(saved.status_code,200,saved.json)
        advance(self.client,self.headers,order['nomor'],'dibatalkan')
        self.assertEqual(self.current_product(product['id'])['stokUkuran'][0]['stok'],7)
        current=self.current_product(product['id']);order=self.order(current).json['order']
        with self.app.app_context():
            db=self.app.get_db();order['payment_deadline']=int(time.time())-1
            db.execute('UPDATE orders SET document=? WHERE id=?',(json.dumps(order),order['nomor']));db.commit()
        self.public.get('/api/products');self.public.get('/api/products')
        self.assertEqual(self.current_product(product['id'])['stokUkuran'][0]['stok'],7)

    def test_active_sizes_cannot_disappear_and_stale_edits_cannot_overwrite_checkout(self):
        product=self.sizes(S=2,M=4);order=self.order(product).json['order']
        self.assertEqual(self.edit(product).status_code,409)
        current=self.current_product(product['id'])
        self.assertEqual(self.edit(current,stokUkuran=[dict(ukuran='M',stok=4)]).status_code,400)
        self.assertEqual(self.edit(current,stokUkuran=[dict(ukuran='S',stok=1),dict(ukuran='M',stok=5),dict(ukuran='XL',stok=2)]).status_code,200)
        advance(self.client,self.headers,order['nomor'],'dibatalkan')

    def test_legacy_allocation_preserves_total_and_existing_reservations(self):
        product=self.product(ukuran=['S m xl'])
        rows=[dict(ukuran='S',stok=1),dict(ukuran='M',stok=2),dict(ukuran='XL',stok=1)]
        self.assertEqual(self.edit(product,stokUkuran=rows[:-1]).status_code,400)
        self.assertEqual(self.edit(product,stokUkuran=rows).status_code,200)
        legacy=self.product();order=self.order(legacy).json['order'];current=self.current_product(legacy['id'])
        self.assertEqual(self.edit(current,stokUkuran=[dict(ukuran='S',stok=3)]).status_code,400)
        advance(self.client,self.headers,order['nomor'],'dibatalkan')
        current=self.current_product(legacy['id'])
        self.assertEqual(self.edit(current,stokUkuran=[dict(ukuran='S',stok=4)]).status_code,200)
