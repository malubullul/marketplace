"""Editable WhatsApp destinations stay owner-only and do not mutate payments."""
import secrets
import tempfile
import unittest

from server import DEFAULT_STORE_CONTACTS, create_app, create_owner


class ContactTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.settings = {'TESTING': True, 'DATA_DIR': self.directory.name}
        self.app = create_app(self.settings)
        self.password = secrets.token_urlsafe(24)
        create_owner(self.app, 'owner@example.test', self.password)
        self.owner = self.app.test_client()
        self.guest = self.app.test_client()
        csrf = self.owner.get('/api/session').json['csrf']
        login = self.owner.post('/api/login', json={'email':'owner@example.test', 'password':self.password},
                                headers={'X-CSRF-Token':csrf})
        self.headers = {'X-CSRF-Token':login.json['csrf']}

    def test_defaults_and_public_response_only_contain_two_phone_numbers(self):
        response = self.guest.get('/api/store/contacts')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json, {'contacts':DEFAULT_STORE_CONTACTS})
        self.assertEqual(response.headers['Cache-Control'], 'no-store')

    def test_only_owner_with_csrf_can_change_or_read_admin_contacts(self):
        payload = dict(payment_whatsapp='081234567890', support_whatsapp='+62 823-4567-8901')
        self.assertEqual(self.guest.get('/api/admin/contacts').status_code, 401)
        self.assertEqual(self.guest.put('/api/admin/contacts', json=payload).status_code, 401)
        self.assertEqual(self.owner.put('/api/admin/contacts', json=payload).status_code, 403)
        csrf = self.guest.get('/api/customer/session').json['csrf']
        buyer = self.guest.post('/api/customer/register', json={
            'email':'buyer@example.test', 'password':self.password, 'nama':'Buyer', 'nohp':'081234567890'},
            headers={'X-CSRF-Token':csrf})
        self.assertEqual(buyer.status_code, 201)
        self.assertEqual(self.guest.put('/api/admin/contacts', json=payload,
                                       headers={'X-CSRF-Token':buyer.json['csrf']}).status_code, 401)
        self.assertEqual(self.guest.get('/api/store/contacts').json['contacts'], DEFAULT_STORE_CONTACTS)

    def test_saved_contacts_are_normalized_and_survive_application_restart(self):
        response = self.owner.put('/api/admin/contacts', json={
            'payment_whatsapp':'0877 1234-5678', 'support_whatsapp':'+62 (823) 4567-8901'}, headers=self.headers)
        expected = {'payment_whatsapp':'6287712345678', 'support_whatsapp':'6282345678901'}
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json['contacts'], expected)
        restarted = create_app(self.settings).test_client()
        self.assertEqual(restarted.get('/api/store/contacts').json['contacts'], expected)

    def test_clearing_payment_keeps_cs_and_does_not_restore_default(self):
        expected = {'payment_whatsapp':'', 'support_whatsapp':'6282345678901'}
        self.assertEqual(self.owner.put('/api/admin/contacts', json=expected, headers=self.headers).status_code, 200)
        self.assertEqual(self.guest.get('/api/store/contacts').json['contacts'], expected)
        self.assertEqual(create_app(self.settings).test_client().get('/api/store/contacts').json['contacts'], expected)

    def test_invalid_destinations_cannot_replace_existing_configuration(self):
        for value in ['https://wa.me/6287712345678', 'javascript:alert(1)', '6287712345678?text=spoof',
                      '<script>', '123', '1'*16, True, 6287712345678, None, ['6287712345678'], '+(62)8234567890', '+62\n8234567890']:
            with self.subTest(value=value):
                response = self.owner.put('/api/admin/contacts', json={
                    'payment_whatsapp':value, 'support_whatsapp':'6282345678901'}, headers=self.headers)
                self.assertEqual(response.status_code, 400)
        self.assertEqual(self.owner.put('/api/admin/contacts', json={
            **DEFAULT_STORE_CONTACTS, 'redirect_url':'https://example.test'}, headers=self.headers).status_code, 400)
        self.assertEqual(self.guest.get('/api/store/contacts').json['contacts'], DEFAULT_STORE_CONTACTS)

