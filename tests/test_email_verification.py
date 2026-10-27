import hashlib
import secrets
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch
from server import create_app


class EmailVerificationTests(unittest.TestCase):
    def setUp(self):
        self.directory=tempfile.TemporaryDirectory();self.addCleanup(self.directory.cleanup)
        self.config=dict(TESTING=True,DATA_DIR=self.directory.name,EMAIL_VERIFICATION_REQUIRED=True,
                         RESEND_API_KEY='re_'+secrets.token_urlsafe(24),EMAIL_FROM='akun@example.test',PUBLIC_URL='https://shop.example.test')
        self.app=create_app(self.config)
        self.client=self.app.test_client();self.headers={'X-CSRF-Token':self.client.get('/api/customer/session').json['csrf']}
        self.sender=patch.object(self.app.extensions['recovery_mailer'],'send_verification').start();self.addCleanup(patch.stopall)
        self.password=secrets.token_urlsafe(24)

    def issue(self,email='buyer@example.test'):
        response=self.client.post('/api/customer/register',json={'email':email},headers=self.headers)
        self.assertEqual(response.status_code,202,response.json)
        return self.sender.call_args.args[1]

    def verify(self,token,client=None,headers=None,**changes):
        return (client or self.client).post('/api/customer/verify-email',json={'token':token,'password':self.password,'nama':'Buyer','nohp':'081234567890',**changes},headers=headers or self.headers)

    def test_signup_requires_proof_and_token_is_hash_only_one_use(self):
        token=self.issue()
        with self.app.app_context():
            db=self.app.get_db();self.assertEqual(db.execute('SELECT COUNT(*) FROM customers').fetchone()[0],0)
            row=db.execute('SELECT token_hash FROM email_verification_tokens').fetchone()
            self.assertEqual(row['token_hash'],hashlib.sha256(token.encode()).hexdigest())
        result=self.verify(token);self.assertEqual(result.status_code,200,result.json)
        self.headers={'X-CSRF-Token':result.json['csrf']}
        self.assertFalse(self.client.get('/api/customer/session').json['authenticated'])
        self.assertEqual(self.verify(token).status_code,400)
        login=self.client.post('/api/customer/login',json={'email':'buyer@example.test','password':self.password},headers=self.headers)
        self.assertTrue(login.json['customer']['email_verified'])

    def test_legacy_verification_changes_password_and_revokes_all_sessions(self):
        self.app.extensions['email_verification'].required=False
        old=self.client.post('/api/customer/register',json={'email':'legacy@example.test','password':'old-password-1234','nama':'Legacy','nohp':'081234567890'},headers=self.headers)
        self.headers={'X-CSRF-Token':old.json['csrf']}
        replay=self.app.test_client();replay.set_cookie('session',self.client.get_cookie('session').value)
        self.app.extensions['email_verification'].required=True
        response=self.client.post('/api/customer/email-verification',json={},headers=self.headers)
        self.assertEqual(response.status_code,202)
        token=self.sender.call_args.args[1]
        result=self.verify(token);self.assertEqual(result.status_code,200,result.json)
        self.assertEqual(replay.get('/api/customer/profile').status_code,401)
        self.headers={'X-CSRF-Token':result.json['csrf']}
        self.assertEqual(self.client.post('/api/customer/login',json={'email':'legacy@example.test','password':'old-password-1234'},headers=self.headers).status_code,401)
        result=self.client.post('/api/customer/login',json={'email':'legacy@example.test','password':self.password},headers=self.headers)
        self.assertEqual(result.json['customer']['nama'],'Legacy')
        self.assertTrue(result.json['customer']['email_verified'])

    def test_pending_new_token_cannot_take_over_account_created_later(self):
        token=self.issue()
        self.app.extensions['email_verification'].required=False
        other=self.app.test_client();csrf=other.get('/api/customer/session').json['csrf']
        account=other.post('/api/customer/register',json={'email':'buyer@example.test','nama':'Other','nohp':'081234567890','password':'someone-else-password'},headers={'X-CSRF-Token':csrf})
        self.assertEqual(account.status_code,201)
        self.assertEqual(self.verify(token).status_code,400)
        self.assertFalse(other.get('/api/customer/session').json['customer']['email_verified'])

    def test_expiry_csrf_wrong_purpose_and_bad_values(self):
        token=self.issue()
        self.assertEqual(self.client.post('/api/customer/verify-email',json={'token':token}).status_code,403)
        for value in [None,[],{},'bad-token']:
            self.assertEqual(self.verify(value).status_code,400)
        with self.app.app_context():
            db=self.app.get_db();db.execute('UPDATE email_verification_tokens SET expires_at=0');db.commit()
        self.assertEqual(self.verify(token).status_code,400)
        reset=self.client.post('/api/customer/reset-password',json={'token':token,'password':self.password},headers=self.headers)
        self.assertEqual(reset.status_code,400)

    def test_concurrent_consume_creates_one_customer(self):
        token=self.issue(); cookie=self.client.get_cookie('session').value
        def submit(_):
            client=self.app.test_client();client.set_cookie('session',cookie)
            return self.verify(token,client=client).status_code
        with ThreadPoolExecutor(max_workers=2) as pool: codes=list(pool.map(submit,range(2)))
        self.assertEqual(sorted(codes),[200,400])
        with self.app.app_context(): self.assertEqual(self.app.get_db().execute('SELECT COUNT(*) FROM customers').fetchone()[0],1)

    def test_limits_provider_failure_and_required_unavailable_fail_closed(self):
        for _ in range(4): self.issue()
        self.assertEqual(self.sender.call_count,3)
        self.sender.side_effect=RuntimeError('private provider data')
        result=self.client.post('/api/customer/email-verification',json={'email':'another@example.test'},headers=self.headers)
        self.assertEqual(result.status_code,503);self.assertNotIn('private',result.text)
        with self.app.app_context(): self.assertEqual(self.app.get_db().execute('SELECT COUNT(*) FROM email_verification_tokens WHERE email=?',('another@example.test',)).fetchone()[0],0)
        self.app.extensions['recovery_mailer'].enabled=False
        self.assertEqual(self.client.post('/api/customer/register',json={'email':'a@example.test'},headers=self.headers).status_code,503)
        with self.app.test_request_context():
            self.assertEqual(self.app.extensions['email_verification'].checkout_error({'id':1}).status_code,503)

    def test_required_unverified_checkout_block_and_validated_policy(self):
        self.app.extensions['email_verification'].required=False
        created=self.client.post('/api/customer/register',json={'email':'buyer@example.test','password':self.password,'nama':'Buyer','nohp':'081234567890'},headers=self.headers)
        self.headers={'X-CSRF-Token':created.json['csrf']}
        self.app.extensions['email_verification'].required=True
        result=self.client.post('/api/orders',json={},headers={**self.headers,'Idempotency-Key':secrets.token_hex(16)})
        self.assertEqual(result.status_code,403)
        self.assertEqual(self.client.get('/api/customer/orders').status_code,200)
        for value in ['false','yes',0,None]:
            with self.assertRaises(ValueError):create_app({**self.config,'EMAIL_VERIFICATION_REQUIRED':value})

    def test_missing_migration_reports_unavailable_and_never_bypasses_requirement(self):
        service=self.app.extensions['email_verification']
        # Readiness is cached only per request; emulate an installation before 005.
        if self.app.config['DATABASE_URL']:
            with self.app.app_context():
                db=self.app.get_db();db.execute('DROP TABLE email_verification_tokens');db.commit()
            self.assertFalse(self.client.get('/api/customer/session').json['email_verification']['available'])
            self.assertEqual(self.client.post('/api/customer/register',json={'email':'buyer@example.test'},headers=self.headers).status_code,503)
        else:
            with patch.object(service,'ready',return_value=False):
                self.assertFalse(self.client.get('/api/customer/session').json['email_verification']['available'])
                self.assertEqual(self.client.post('/api/customer/register',json={'email':'buyer@example.test'},headers=self.headers).status_code,503)
