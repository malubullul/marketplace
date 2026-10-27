from order_workflow import advance
"""Verified commerce metrics and adversarial password-recovery contracts."""
import hashlib
import json
import secrets
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import Mock, patch

from server import create_app, create_owner


class ReviewRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.config = {'TESTING': True, 'DATA_DIR': self.directory.name,
                       'RESEND_API_KEY': 're_' + secrets.token_urlsafe(24),
                       'EMAIL_FROM': 'akun@example.test', 'PUBLIC_URL': 'https://shop.example.test'}
        self.app = create_app(self.config)
        self.password = secrets.token_urlsafe(24)
        self.buyer, self.bh = self.register('alice@example.test', 'Alice Pribadi')
        self.owner = self.app.test_client()
        create_owner(self.app, 'owner@example.test', self.password)
        csrf = self.owner.get('/api/session').json['csrf']
        login = self.owner.post('/api/login', json={'email': 'owner@example.test', 'password': self.password}, headers={'X-CSRF-Token': csrf})
        self.oh = {'X-CSRF-Token': login.json['csrf']}
        self.guest = self.app.test_client()
        self.gh = {'X-CSRF-Token': self.guest.get('/api/customer/session').json['csrf']}
        self.sender = patch.object(self.app.extensions['recovery_mailer'], 'send').start()
        self.addCleanup(patch.stopall)
        self.addCleanup(self.directory.cleanup)
        self.product = self.buyer.get('/api/products').json['products'][0]
        self.pid = self.product['id']

    def register(self, email, name='Pembeli'):
        client = self.app.test_client()
        csrf = client.get('/api/customer/session').json['csrf']
        result = client.post('/api/customer/register', json={'email':email, 'nama':name, 'nohp':'081234567890', 'password':self.password}, headers={'X-CSRF-Token':csrf})
        self.assertEqual(result.status_code, 201, result.json)
        return client, {'X-CSRF-Token': result.json['csrf']}

    def login(self, email='alice@example.test', password=None):
        client = self.app.test_client()
        headers = {'X-CSRF-Token':client.get('/api/customer/session').json['csrf']}
        result = client.post('/api/customer/login', json={'email':email, 'password':password or self.password}, headers=headers)
        self.assertEqual(result.status_code, 200, result.json)
        return client, {'X-CSRF-Token': result.json['csrf']}

    def order(self, quantities=(1,), client=None, headers=None):
        result = (client or self.buyer).post('/api/orders', json={
            'customer':{'nama_penerima':'Penerima', 'nohp':'081234567890', 'alamat':'Jl. Uji 1', 'kota':'Jakarta', 'provinsi':'DKI Jakarta', 'kodepos':'12345'},
            'items':[{'id':self.pid, 'harga':self.product['harga'], 'jumlah':qty} for qty in quantities]},
            headers={**(headers or self.bh), 'Idempotency-Key':secrets.token_hex(16)})
        self.assertEqual(result.status_code, 201, result.json)
        return result.json['order']['nomor']

    def status(self, number, status):
        advance(self.owner,self.oh,number,status)

    def metrics(self):
        return next(p for p in self.guest.get('/api/products').json['products'] if p['id']==self.pid)

    def review(self, **changes):
        return self.buyer.put(f'/api/customer/products/{self.pid}/review', json={'rating':5, 'comment':'Bagus', **changes}, headers=self.bh)

    def forgot(self, email='alice@example.test'):
        return self.guest.post('/api/customer/forgot-password', json={'email':email}, headers=self.gh)

    def token(self):
        self.assertEqual(self.forgot().status_code, 202)
        return self.sender.call_args.args[1]

    def reset(self, token, password=None, client=None, headers=None):
        return (client or self.guest).post('/api/customer/reset-password', json={'token':token,'password':password or secrets.token_urlsafe(24)}, headers=headers or self.gh)

    def test_sold_counts_completed_quantities_once_and_preserves_old_orders(self):
        self.assertEqual((self.metrics()['rating'],self.metrics()['ulasan'],self.metrics()['terjual']), (0,0,0))
        number = self.order((1,2))
        for state in ['baru','diproses','dikirim']:
            self.status(number,state)
            self.assertEqual(self.metrics()['terjual'],0)
        self.status(number,'selesai');self.status(number,'selesai')
        self.assertEqual(self.metrics()['terjual'],3)
        cancelled = self.order();self.status(cancelled,'dibatalkan')
        self.assertEqual(self.metrics()['terjual'],3)
        # Simulate an existing database before order_items existed, then rerun migration twice.
        with self.app.app_context():
            db = self.app.get_db()
            db.execute('DELETE FROM order_items');db.commit()
            if hasattr(db,'initialize'):
                db.initialize();db.initialize()
        restarted = create_app(self.config)
        self.assertEqual(next(p for p in restarted.test_client().get('/api/products').json['products'] if p['id']==self.pid)['terjual'],3)

    def test_review_requires_buyer_completed_purchase_and_csrf(self):
        self.assertEqual(self.guest.put(f'/api/customer/products/{self.pid}/review',json={}).status_code,401)
        self.assertEqual(self.owner.put(f'/api/customer/products/{self.pid}/review',json={'rating':5},headers=self.oh).status_code,401)
        self.assertEqual(self.buyer.put(f'/api/customer/products/{self.pid}/review',json={'rating':5}).status_code,403)
        self.assertEqual(self.review().status_code,403)
        number=self.order()
        for state in ['baru','diproses','dikirim']:
            self.status(number,state);self.assertEqual(self.review().status_code,403)
        self.status(self.order(),'dibatalkan');self.assertEqual(self.review().status_code,403)
        self.status(self.order(),'selesai')
        self.assertEqual(self.review().status_code,200)
        bob,bh=self.register('bob@example.test')
        self.assertFalse(bob.get(f'/api/customer/products/{self.pid}/review').json['eligible'])
        self.assertEqual(bob.put(f'/api/customer/products/{self.pid}/review',json={'rating':5,'customer_id':1},headers=bh).status_code,403)

    def test_reviews_update_in_place_average_and_private_identity(self):
        self.status(self.order(),'selesai')
        comment='<img src=x onerror=alert(1)>\nNyaman'
        self.assertEqual(self.review(comment=comment,customer_id=99,name='Palsu').status_code,200)
        self.assertEqual(self.review(rating=3).json['metrics']['ulasan'],1)
        bob,bh=self.register('bob@example.test','Bob Pribadi')
        self.status(self.order(client=bob,headers=bh),'selesai')
        self.assertEqual(bob.put(f'/api/customer/products/{self.pid}/review',json={'rating':4,'comment':comment},headers=bh).status_code,200)
        self.assertEqual((self.metrics()['rating'],self.metrics()['ulasan'],self.metrics()['terjual']),(3.5,2,2))
        response=self.guest.get(f'/api/products/{self.pid}/reviews')
        self.assertEqual(response.json['total'],2)
        self.assertIsNone(response.json['next_offset'])
        for entry in response.json['reviews']:
            self.assertEqual(set(entry),{'rating','comment','name','created_at','updated_at','verified'})
            self.assertTrue(entry['verified'])
            self.assertNotIn('Pribadi', entry['name'])
        own=self.buyer.get(f'/api/customer/products/{self.pid}/review').json
        self.assertTrue(own['eligible']);self.assertEqual(own['review']['rating'],3)
        self.assertEqual(self.guest.get(f'/api/products/{self.pid}/reviews?offset=-1').status_code,400)
        self.assertEqual(self.guest.get('/api/products/'+('9'*80)+'/reviews').status_code,404)
        # Owner edits cannot replace the actual aggregate metrics with submitted counters.
        product=self.metrics()
        product.update(rating=5,ulasan=999,terjual=999)
        edited=self.owner.put(f'/api/admin/products/{self.pid}',json=product,headers=self.oh)
        self.assertEqual(edited.status_code,200,edited.json)
        self.assertEqual((edited.json['product']['rating'],edited.json['product']['ulasan'],edited.json['product']['terjual']),(3.5,2,2))

    def test_invalid_review_values_and_unpublished_product(self):
        self.status(self.order(),'selesai')
        for value in [True,None,0,6,2.5,'5',{},[]]:
            self.assertEqual(self.review(rating=value).status_code,400)
        self.assertEqual(self.review(comment='a'*1001).status_code,400)
        self.assertEqual(self.review(comment=[]).status_code,400)
        with self.app.app_context():
            self.app.get_db().execute('UPDATE products SET published=0 WHERE id=?',(self.pid,));self.app.get_db().commit()
        self.assertEqual(self.review().status_code,404)
        self.assertEqual(self.guest.get(f'/api/products/{self.pid}/reviews').status_code,404)
        self.assertEqual(self.buyer.get(f'/api/customer/products/{self.pid}/review').status_code,404)

    def test_simultaneous_review_writes_keep_one_rating(self):
        self.status(self.order(),'selesai')
        cookie=self.buyer.get_cookie('session').value
        def submit(rating):
            client=self.app.test_client();client.set_cookie('session',cookie)
            return client.put(f'/api/customer/products/{self.pid}/review',json={'rating':rating},headers=self.bh)
        with ThreadPoolExecutor(max_workers=2) as pool:
            results=list(pool.map(submit,[3,5]))
        self.assertEqual([r.status_code for r in results],[200,200])
        self.assertEqual(self.metrics()['ulasan'],1)
        self.assertIn(self.metrics()['rating'],{3,5})

    def test_recovery_delivery_uniform_no_token_disclosure_and_host_poisoning(self):
        known=self.forgot();unknown=self.forgot('unknown@example.test')
        self.assertEqual((known.status_code,known.json),(unknown.status_code,unknown.json))
        self.assertEqual(self.sender.call_count,2)
        token=self.sender.call_args.args[1]
        self.assertNotIn(token,unknown.get_data(as_text=True))
        with self.app.app_context():
            row=self.app.get_db().execute('SELECT * FROM password_resets WHERE token_hash=?',(hashlib.sha256(token.encode()).hexdigest(),)).fetchone()
            self.assertIsNone(row['customer_id'])
            self.assertNotEqual(row['token_hash'],token)
        self.assertEqual(self.reset(token).status_code,400)
        # A later registration cannot make a previously issued dummy token valid.
        self.register('unknown@example.test')
        self.assertEqual(self.reset(token).status_code,400)
        poisoned=self.guest.post('/api/customer/forgot-password',json={'email':'alice@example.test'},headers={**self.gh,'Host':'evil.example.test','X-Forwarded-Host':'evil.example.test'})
        self.assertIn(poisoned.status_code,{202,403})
        self.assertEqual(self.app.extensions['recovery_mailer'].origin,'https://shop.example.test')

    def test_reset_is_single_use_revokes_sessions_and_does_not_log_in(self):
        second,_=self.login()
        bob,bh=self.register('bob@example.test')
        token=self.token();new=secrets.token_urlsafe(24)
        with self.guest.get('/akun.html') as page:
            self.assertIn('no-store',page.headers['Cache-Control'])
        response=self.reset(token,new)
        self.assertEqual(response.status_code,200,response.json)
        self.assertEqual(self.buyer.get('/api/customer/profile').status_code,401)
        self.assertEqual(second.get('/api/customer/profile').status_code,401)
        self.assertEqual(self.guest.get('/api/customer/profile').status_code,401)
        self.assertEqual(bob.get('/api/customer/profile').status_code,200)
        self.assertEqual(self.owner.get('/api/admin/products').status_code,200)
        self.gh={'X-CSRF-Token':response.json['csrf']}
        self.assertEqual(self.reset(token).status_code,400)
        self.login(password=new)
        client=self.app.test_client();csrf=client.get('/api/customer/session').json['csrf']
        self.assertEqual(client.post('/api/customer/login',json={'email':'alice@example.test','password':self.password},headers={'X-CSRF-Token':csrf}).status_code,401)

    def test_expired_invalid_tokens_and_password_boundaries(self):
        token=self.token()
        for value in ['',None,False,{},token+'x']:
            self.assertEqual(self.reset(value).status_code,400)
        for password in ['short','a'*129,None,True]:
            self.assertEqual(self.guest.post('/api/customer/reset-password',json={'token':token,'password':password},headers=self.gh).status_code,400)
        with self.app.app_context():
            self.app.get_db().execute('UPDATE password_resets SET expires_at=0');self.app.get_db().commit()
        self.assertEqual(self.reset(token).status_code,400)
        self.assertEqual(self.buyer.get('/api/customer/profile').status_code,200)

    def test_reset_race_only_one_request_succeeds(self):
        token=self.token();cookie=self.guest.get_cookie('session').value
        def submit(password):
            client=self.app.test_client();client.set_cookie('session',cookie)
            return self.reset(token,password,client,self.gh).status_code
        with ThreadPoolExecutor(max_workers=2) as pool:
            results=list(pool.map(submit,[secrets.token_urlsafe(24),secrets.token_urlsafe(24)]))
        self.assertEqual(sorted(results),[200,400])

    def test_password_change_invalidates_pending_recovery_and_other_reset_links(self):
        token=self.token()
        changed=self.buyer.post('/api/customer/password',json={'current_password':self.password,'password':secrets.token_urlsafe(24)},headers=self.bh)
        self.assertEqual(changed.status_code,200)
        self.assertEqual(self.reset(token).status_code,400)
        one=self.token();two=self.token()
        self.assertEqual(self.reset(one).status_code,200)
        self.gh={'X-CSRF-Token':self.guest.get('/api/customer/session').json['csrf']}
        self.assertEqual(self.reset(two).status_code,400)

    def test_recovery_csrf_limits_and_unconfigured_service(self):
        self.assertEqual(self.guest.post('/api/customer/forgot-password',json={'email':'alice@example.test'}).status_code,403)
        self.assertEqual(self.guest.post('/api/customer/reset-password',json={}).status_code,403)
        for email in [None,[], 'alice@example.test\r\nBcc:x@test.example','a'*151]:
            self.assertEqual(self.forgot(email).status_code,400)
        for _ in range(4):self.assertEqual(self.forgot().status_code,202)
        self.assertEqual(self.sender.call_count,3)
        for _ in range(6):self.forgot('different@example.test')
        self.assertEqual(self.forgot().status_code,429)
        self.assertEqual(self.sender.call_count,6)
        # A disabled provider is visible to the UI and never fabricates an email delivery.
        self.app.extensions['recovery_mailer'].enabled=False
        self.assertFalse(self.guest.get('/api/customer/session').json['password_recovery'])
        self.assertEqual(self.forgot().status_code,503)

    def test_store_remains_available_before_cloud_migration_then_backfills(self):
        from contextlib import ExitStack
        with self.app.app_context():
            db=self.app.get_db()
            postgres=hasattr(db,'initialize')
            for table in ['product_reviews','order_items','password_resets']:
                db.execute('DROP TABLE '+table)
            db.commit()
        with ExitStack() as stack:
            if not postgres:
                # SQLite creates its schema on startup; simulate the cloud readiness branch.
                stack.enter_context(patch.object(self.app.extensions['product_reviews'],'ready',return_value=False))
                stack.enter_context(patch.object(self.app.extensions['password_recovery'],'ready',return_value=False))
            self.assertEqual(self.metrics()['terjual'],0)
            self.assertFalse(self.metrics()['metrics_ready'])
            self.assertFalse(self.guest.get('/api/customer/session').json['password_recovery'])
            self.assertEqual(self.guest.get(f'/api/products/{self.pid}/reviews').status_code,503)
            self.assertEqual(self.review().status_code,503)
            self.assertEqual(self.forgot().status_code,503)
            number=self.order((2,))
            changed=self.buyer.post('/api/customer/password',json={'current_password':self.password,'password':secrets.token_urlsafe(24)},headers=self.bh)
            self.assertEqual(changed.status_code,200,changed.json)
        if postgres:
            with self.app.app_context():self.app.get_db().initialize()
        else:
            self.app=create_app(self.config)
        self.status(number,'selesai')
        self.assertEqual(self.metrics()['terjual'],2)

    def test_recovering_one_account_preserves_other_browser_identity(self):
        bob,bh=self.register('bob@example.test','Bob')
        token=self.token()
        self.assertEqual(self.reset(token,client=bob,headers=bh).status_code,200)
        self.assertEqual(bob.get('/api/customer/profile').json['customer']['nama'],'Bob')
        self.assertEqual(self.buyer.get('/api/customer/profile').status_code,401)

    def test_provider_failure_invalidates_failed_token_without_disclosing_account(self):
        self.sender.side_effect=RuntimeError('provider failed')
        known=self.forgot();unknown=self.forgot('missing@example.test')
        self.assertEqual((known.status_code,known.json),(unknown.status_code,unknown.json))
        self.assertEqual(known.status_code,503)
        with self.app.app_context():
            self.assertEqual(self.app.get_db().execute('SELECT COUNT(*) FROM password_resets').fetchone()[0],0)


class RecoveryMailerTests(unittest.TestCase):
    def mailer(self, **changes):
        from flask import Flask
        from password_recovery import RecoveryMailer
        app=Flask('mailer')
        app.config.update({'RESEND_API_KEY':'re_'+secrets.token_urlsafe(24),'EMAIL_FROM':'akun@example.test','PUBLIC_URL':'https://shop.example.test',**changes})
        return RecoveryMailer(app)

    def test_fixed_provider_origin_and_fragment_link(self):
        mailer=self.mailer()
        response=Mock();response.__enter__=Mock(return_value=response);response.__exit__=Mock(return_value=False)
        response.status=200;response.read.return_value=b'{"id":"delivered-test"}'
        with patch('password_recovery.build_opener') as opener:
            opener.return_value.open.return_value=response
            mailer.send('buyer@example.test','x'*43)
            request_=opener.return_value.open.call_args.args[0]
            self.assertEqual(request_.full_url,'https://api.resend.com/emails')
            payload=json.loads(request_.data)
            self.assertIn('https://shop.example.test/akun.html#reset='+'x'*43,payload['text'])
            self.assertEqual(payload['to'],['buyer@example.test'])

    def test_unsafe_or_partial_configuration_rejected(self):
        for changes in [{'EMAIL_FROM':''},{'RESEND_API_KEY':'invalid'},{'PUBLIC_URL':'http://shop.example.test'}, {'PUBLIC_URL':'https://shop.example.test/path'}, {'PUBLIC_URL':'https://user:pass@shop.example.test'}, {'EMAIL_FROM':'akun@example.test\r\nBcc:other@example.test'}]:
            with self.assertRaises(ValueError):self.mailer(**changes)

    def test_provider_response_errors_and_redirects_fail_closed(self):
        from password_recovery import NoRedirect
        mailer=self.mailer()
        for body in [b'[]',b'{}',b'not json',b'{"id":""}']:
            response=Mock();response.__enter__=Mock(return_value=response);response.__exit__=Mock(return_value=False)
            response.status=200;response.read.return_value=body
            with patch('password_recovery.build_opener') as opener:
                opener.return_value.open.return_value=response
                with self.assertRaisesRegex(RuntimeError,'Pengiriman email belum tersedia'):
                    mailer.send('buyer@example.test','x'*43)
        self.assertIsNone(NoRedirect().redirect_request(None,None,302,'',{},'https://evil.example.test'))
