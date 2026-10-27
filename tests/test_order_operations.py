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


class OrderOperationTests(unittest.TestCase):
    product = test_server.StoreTests.product
    order = test_server.StoreTests.order
    current_product = test_server.StoreTests.current_product

    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(); self.addCleanup(self.directory.cleanup)
        self.app = create_app({'TESTING':True,'DATA_DIR':self.directory.name})
        password = secrets.token_urlsafe(24); create_owner(self.app,'owner@example.test',password)
        self.client = self.app.test_client()
        csrf = self.client.get('/api/session').json['csrf']
        self.headers = {'X-CSRF-Token':self.client.post('/api/login',json={'email':'owner@example.test','password':password},headers={'X-CSRF-Token':csrf}).json['csrf']}
        self.public = self.app.test_client(); csrf = self.public.get('/api/customer/session').json['csrf']
        result = self.public.post('/api/customer/register',json=dict(email='buyer@example.test',nama='Buyer',nohp='081234567890',password=password),headers={'X-CSRF-Token':csrf})
        self.buyer_headers = {'X-CSRF-Token':result.json['csrf']}

    def settings(self, **changes):
        previous = self.client.get('/api/admin/transaction-settings').json['settings']
        result = self.client.put('/api/admin/transaction-settings', json={**previous,**changes}, headers=self.headers)
        self.assertEqual(result.status_code,200,result.json)
        return result.json['settings']

    def current(self, order):
        return self.public.get('/api/customer/orders/'+order['nomor']).json['order']

    def payment(self, order, **changes):
        return self.client.post('/api/admin/orders/'+order['nomor']+'/payment',json={'version':order['version'],'action':'verify','reference':'PRIVATE-REFERENCE',**changes},headers=self.headers)

    def test_strict_transitions_payment_and_private_history(self):
        product = self.product(); order = self.order(product).json['order']; path = '/api/admin/orders/'+order['nomor']
        for status in ['selesai','dikirim','diproses',[],{},None]:
            result = self.client.patch(path,json={'status':status,'version':order['version']},headers=self.headers)
            self.assertEqual(result.status_code,409,result.json)
        verified = self.payment(order).json['order']
        self.assertEqual(verified['payment']['status'],'verified')
        self.assertNotIn('PRIVATE-REFERENCE',json.dumps(self.current(order)))
        self.assertNotIn('verified_by',json.dumps(self.current(order)))
        self.assertEqual(self.client.get(path+'/history').json['payment_record']['reference'],'PRIVATE-REFERENCE')
        self.assertEqual(self.public.get(path+'/history').status_code,401)
        advance(self.client,self.headers,order['nomor'],'dikirim')
        shipped = self.current(order)
        self.assertEqual(self.client.patch(path,json={'status':'dibatalkan','version':shipped['version']},headers=self.headers).status_code,409)
        self.assertEqual(self.current_product(product['id'])['stok'],3)
        advance(self.client,self.headers,order['nomor'],'selesai')

    def test_paid_without_reference_automatically_records_owner_and_time_once(self):
        order=self.order(self.product()).json['order'];path='/api/admin/orders/'+order['nomor']
        started=int(time.time())
        result=self.client.post(path+'/payment',json={'action':'verify','version':order['version'],
                               'verified_by':-999,'verified_at':0},headers=self.headers)
        self.assertEqual(result.status_code,200,result.json)
        paid=result.json['order']
        self.assertEqual(paid['payment']['status'],'verified')
        self.assertEqual(paid['status'],'baru')
        history=self.client.get(path+'/history').json
        record=history['payment_record'];event=next(e for e in history['events'] if e['action']=='payment.verify')
        self.assertEqual(record['reference'],'')
        self.assertEqual(record['verified_by'],event['actor']['id'])
        self.assertNotEqual(record['verified_by'],-999)
        self.assertGreaterEqual(record['verified_at'],started)
        self.assertEqual(self.client.post(path+'/payment',json={'action':'verify','version':paid['version']},headers=self.headers).status_code,200)
        self.assertEqual(sum(e['action']=='payment.verify' for e in self.client.get(path+'/history').json['events']),1)
        self.assertEqual(self.client.get(path+'/history').json['payment_record'],record)
        self.assertNotIn('verified_by',json.dumps(self.current(order)))
        self.assertEqual(self.client.patch(path,json={'status':'diproses','version':paid['version']},headers=self.headers).status_code,200)

    def test_optional_payment_note_accepts_blank_and_short_text_but_rejects_bad_values(self):
        order=self.order(self.product()).json['order']
        for reference in [None,True,4,[],{},'x'*161,'bad\nline','\t']:
            response=self.payment(order,reference=reference)
            self.assertEqual(response.status_code,409,response.json)
            self.assertEqual(self.current(order)['payment']['status'],'pending')
        for reference in ['','   ','1']:
            if reference: order=self.order(self.product()).json['order']
            result=self.payment(order,reference=reference)
            self.assertEqual(result.status_code,200,result.json)
            record=self.client.get('/api/admin/orders/'+order['nomor']+'/history').json['payment_record']
            self.assertEqual(record['reference'],reference.strip())

    def test_cancel_is_owned_csrf_protected_once_and_stale_safe(self):
        product = self.product(); order = self.order(product).json['order']; path = '/api/customer/orders/'+order['nomor']+'/cancel'
        self.assertEqual(self.app.test_client().post(path,json={}).status_code,401)
        self.assertEqual(self.public.post(path,json={'version':order['version']}).status_code,403)
        done = self.public.post(path,json={'version':order['version']},headers=self.buyer_headers)
        self.assertEqual(done.status_code,200,done.json)
        self.assertEqual(self.public.post(path,json={'version':order['version']},headers=self.buyer_headers).status_code,409)
        self.assertEqual(self.public.post(path,json={'version':done.json['order']['version']},headers=self.buyer_headers).status_code,200)
        self.assertEqual(self.current_product(product['id'])['stok'],4)
        self.assertEqual(len(self.client.get('/api/admin/orders/'+order['nomor']+'/history').json['events']),2)

    def test_deadline_snapshot_legacy_and_report_or_hold(self):
        product = self.product(stok=10); legacy = self.order(product).json['order']
        settings = self.settings(deadline_enabled=True,payment_hours=1)
        terms = {k:settings[k] for k in ('deadline_enabled','payment_hours')}
        self.assertEqual(self.order(product).status_code,409)
        expired = self.order(product,payment_terms=terms).json['order']
        reported = self.order(product,payment_terms=terms).json['order']
        held = self.order(product,payment_terms=terms).json['order']
        self.assertEqual(self.public.post('/api/customer/orders/'+reported['nomor']+'/payment',json={'version':reported['version']},headers=self.buyer_headers).status_code,200)
        self.assertEqual(self.payment(held,action='hold').status_code,200)
        with patch('order_operations.time.time',return_value=expired['payment_deadline']+1):
            self.assertEqual(self.current(expired)['cancellation_reason'],'kedaluwarsa')
            self.assertEqual(self.current(reported)['status'],'baru')
            self.assertEqual(self.current(held)['status'],'baru')
            self.assertEqual(self.current(legacy)['status'],'baru')
            self.assertEqual(self.current(expired)['status'],'dibatalkan')
        self.assertEqual(self.current_product(product['id'])['stok'],7)
        self.assertEqual(len([e for e in self.client.get('/api/admin/orders/'+expired['nomor']+'/history').json['events'] if e['action']=='order.expired']),1)

    def test_payment_cancel_race_changes_stock_at_most_once(self):
        product=self.product(); order=self.order(product).json['order']; cookie=self.client.get_cookie('session').value
        def submit(action):
            client=self.app.test_client();client.set_cookie('session',cookie)
            if action=='verify': return client.post('/api/admin/orders/'+order['nomor']+'/payment',json={'version':order['version'],'action':'verify','reference':'Real fixture'},headers=self.headers).status_code
            return client.patch('/api/admin/orders/'+order['nomor'],json={'version':order['version'],'status':'dibatalkan'},headers=self.headers).status_code
        with ThreadPoolExecutor(max_workers=2) as pool: statuses=list(pool.map(submit,['verify','cancel']))
        self.assertEqual(sorted(statuses),[200,409])
        current=self.current(order)
        self.assertEqual(self.current_product(product['id'])['stok'],4 if current['status']=='dibatalkan' else 3)

    def test_concurrent_expiry_releases_stock_and_last_promo_quota_once(self):
        product=self.product(stok=1)
        settings=self.settings(deadline_enabled=True,payment_hours=1)
        terms={k:settings[k] for k in ('deadline_enabled','payment_hours')}
        promo=dict(code='LASTONE',partner='',kind='fixed',value=1000,min_subtotal=0,max_discount=None,
                   starts_at=None,expires_at=None,usage_limit=1,per_customer_limit=1,active=True,version='0')
        self.assertEqual(self.client.post('/api/admin/promos',json=promo,headers=self.headers).status_code,201)
        order=self.order(product,payment_terms=terms,coupon='LASTONE',expected_discount=1000).json['order']
        with self.app.app_context():
            order['payment_deadline']=int(time.time())-1
            db=self.app.get_db();db.execute('UPDATE orders SET document=? WHERE id=?',(json.dumps(order),order['nomor']));db.commit()
        def sweep(_):
            return self.app.test_client().get('/api/products').status_code
        with ThreadPoolExecutor(max_workers=2) as pool:self.assertEqual(list(pool.map(sweep,range(2))),[200,200])
        self.assertEqual(self.current_product(product['id'])['stok'],1)
        events=self.client.get('/api/admin/orders/'+order['nomor']+'/history').json['events']
        self.assertEqual(sum(e['action']=='order.expired' for e in events),1)
        self.assertEqual(self.order(product,payment_terms=terms,coupon='LASTONE',expected_discount=1000).status_code,201)

    def test_other_buyer_cannot_report_or_cancel_and_owner_requires_csrf(self):
        order=self.order(self.product()).json['order']
        stranger=self.app.test_client();csrf=stranger.get('/api/customer/session').json['csrf']
        signup=stranger.post('/api/customer/register',json=dict(email='other@example.test',nama='Other',nohp='081234567890',password=secrets.token_urlsafe(24)),headers={'X-CSRF-Token':csrf})
        for action in ['payment','cancel']:
            response=stranger.post('/api/customer/orders/'+order['nomor']+'/'+action,json={'version':order['version']},headers={'X-CSRF-Token':signup.json['csrf']})
            self.assertEqual(response.status_code,404)
        self.assertEqual(self.client.post('/api/admin/orders/'+order['nomor']+'/payment',json={'action':'verify','version':order['version'],'reference':'test'}).status_code,403)

    def test_report_rejection_and_hold_release_grant_a_fresh_payment_window(self):
        settings=self.settings(deadline_enabled=True,payment_hours=1)
        order=self.order(self.product(),payment_terms={k:settings[k] for k in ('deadline_enabled','payment_hours')}).json['order']
        order=self.public.post('/api/customer/orders/'+order['nomor']+'/payment',json={'version':order['version']},headers=self.buyer_headers).json['order']
        # An expired reported order is protected until the owner finishes checking it.
        now=order['payment_deadline']+60
        with patch('order_operations.time.time',return_value=now):
            rejected=self.payment(order,action='reject')
            self.assertEqual(rejected.status_code,200,rejected.json)
            order=rejected.json['order']
            self.assertEqual(order['payment']['status'],'pending')
            self.assertEqual(order['payment_deadline'],now+3600)
            order=self.payment(order,action='hold').json['order']
        with patch('order_operations.time.time',return_value=now+7200):
            released=self.payment(order,action='release')
            self.assertEqual(released.status_code,200,released.json)
            self.assertFalse(released.json['order']['payment_hold'])
            self.assertEqual(released.json['order']['payment_deadline'],now+10800)

    def test_settings_types_audit_pagination_and_cron_auth(self):
        initial=self.client.get('/api/admin/transaction-settings').json['settings']
        for value in [0,-1,169,True,None,'24']:
            self.assertEqual(self.client.put('/api/admin/transaction-settings',json={**initial,'payment_hours':value},headers=self.headers).status_code,400)
        self.settings(deadline_enabled=True)
        self.assertEqual(self.client.put('/api/admin/transaction-settings',json=initial,headers=self.headers).status_code,409)
        self.assertEqual(self.public.get('/api/admin/activity').status_code,401)
        first=self.client.get('/api/admin/activity?limit=1').json
        second=self.client.get('/api/admin/activity?limit=1&cursor='+first['next_cursor']).json
        self.assertNotEqual(first['events'][0]['id'],second['events'][0]['id'])
        for query in ['limit=0','limit=101','cursor=invalid']:
            self.assertEqual(self.client.get('/api/admin/activity?'+query).status_code,400)
        self.assertEqual(self.public.get('/api/internal/expire-orders').status_code,401)
        self.app.config['CRON_SECRET']=secrets.token_urlsafe(32)
        self.assertEqual(self.public.get('/api/internal/expire-orders',headers={'Authorization':'Bearer '+self.app.config['CRON_SECRET']}).status_code,200)

    def test_product_with_active_order_cannot_be_deleted_and_invalid_empty_options(self):
        product=self.product();order=self.order(product).json['order']
        self.assertEqual(self.client.delete('/api/admin/products/'+str(product['id']),headers=self.headers).status_code,409)
        advance(self.client,self.headers,order['nomor'],'dibatalkan')
        self.assertEqual(self.client.delete('/api/admin/products/'+str(product['id']),headers=self.headers).status_code,200)
        plain=self.product(ukuran=[],warna=[])
        self.assertEqual(self.order(plain).status_code,409)

    def test_legacy_orders_keep_history_without_fabricated_verification(self):
        order=self.order(self.product()).json['order']
        with self.app.app_context():
            db=self.app.get_db()
            for field in ['payment','version','payment_hold','payment_deadline']:order.pop(field,None)
            order['status']='dikirim'
            db.execute("UPDATE orders SET status='dikirim',document=? WHERE id=?",(json.dumps(order),order['nomor']));db.commit()
        current=self.current(order)
        self.assertEqual(current['payment']['status'],'unrecorded');self.assertIsNone(current['payment_deadline'])
        self.assertEqual(self.client.patch('/api/admin/orders/'+order['nomor'],json={'version':'0','status':'selesai'},headers=self.headers).status_code,409)
        self.assertEqual(self.payment(current).status_code,200)
        advance(self.client,self.headers,order['nomor'],'selesai')
