"""Two WhatsApp channels and editable contacts; never contacts WhatsApp servers."""
import json
import os
from pathlib import Path
import secrets
import subprocess
import tempfile
from urllib.parse import parse_qs, urlsplit

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
VIEWPORTS = [(1440, 1000), (768, 1024), (390, 844), (320, 568), (844, 390)]


def check_layout(page):
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth + 1')
    assert page.evaluate('''() => [...document.querySelectorAll('dialog[open]')].every(e => {
      const r = e.getBoundingClientRect();
      return r.left >= -1 && r.right <= innerWidth + 1 && r.top >= -1 && r.bottom <= innerHeight + 1 && e.scrollWidth <= e.clientWidth + 1;
    })''')


def main():
    output = Path(os.environ.get('ANREDSELLER_SCREENSHOT_DIR', '/tmp/anredseller-whatsapp'))
    output.mkdir(parents=True, exist_ok=True)
    password = secrets.token_urlsafe(24)
    source = '''import json,sys,secrets,threading,signal
from server import create_owner
from werkzeug.serving import make_server
password=sys.stdin.readline().strip()
sys.path.insert(0,'tests')
from browser_backend_support import configure_backend
key=secrets.token_urlsafe(40)
app,cleanup=configure_backend({'TESTING':True,'ADMIN_GATEWAY_KEY':key,'ADMIN_PORTAL_URL':'https://owner.example.test'})
create_owner(app,'owner@example.test',password)
store=make_server('127.0.0.1',0,app,threaded=True)
sys.path.insert(0,'admin-portal')
from app import create_app as create_portal
portal=create_portal({'BACKEND_URL':f'http://127.0.0.1:{store.server_port}', 'SHOP_URL':f'http://127.0.0.1:{store.server_port}', 'ADMIN_GATEWAY_KEY':key,'SECURE_COOKIES':False})
owner=make_server('127.0.0.1',0,portal,threaded=True)
threading.Thread(target=owner.serve_forever,daemon=True).start()
print(json.dumps({'store':store.server_port,'admin':owner.server_port}),flush=True)
signal.signal(signal.SIGTERM,lambda *_:sys.exit(0))
try:store.serve_forever()
finally:cleanup()
'''
    with tempfile.TemporaryDirectory(prefix='anredseller-whatsapp-') as directory, open(output / 'server.log', 'w') as log:
        process = subprocess.Popen([str(ROOT / '.venv/bin/python'), '-c', source], cwd=ROOT,
            env={**os.environ, 'ANREDSELLER_DATA_DIR':directory}, stdin=subprocess.PIPE,
            stdout=subprocess.PIPE, stderr=log, text=True)
        try:
            process.stdin.write(password + '\n'); process.stdin.flush()
            ports = json.loads(process.stdout.readline())
            base = 'http://127.0.0.1:' + str(ports['store'])
            admin_base = 'http://localhost:' + str(ports['admin'])
            with sync_playwright() as p:
                browser = p.chromium.launch(executable_path='/usr/bin/chromium', headless=True)
                owner_context, buyer_context, guest_context = [browser.new_context(viewport={'width':390,'height':844}, reduced_motion='reduce') for _ in range(3)]
                owner, buyer, guest = [c.new_page() for c in [owner_context,buyer_context,guest_context]]
                errors = []
                for page in [owner,buyer,guest]: page.on('pageerror',lambda error:errors.append(str(error)))
                owner.goto(admin_base, wait_until='networkidle')
                owner.locator('#login-email').fill('owner@example.test'); owner.locator('#login-password').fill(password)
                owner.locator('#login-button').click(); owner.locator('#dashboard').wait_for(state='visible')
                owner.locator('[data-page=settings]').click()
                owner.wait_for_function("() => document.querySelector('#payment-whatsapp').value !== ''")
                assert owner.locator('#payment-whatsapp').input_value() == '6287729766809'
                assert owner.locator('#support-whatsapp').input_value() == '6282335963140'
                for width,height in VIEWPORTS:
                    owner.set_viewport_size({'width':width,'height':height}); check_layout(owner)
                    owner.screenshot(path=str(output/f'contacts-{width}.png'), full_page=True)

                def save_contacts(payment, support):
                    owner.locator('#payment-whatsapp').fill(payment); owner.locator('#support-whatsapp').fill(support)
                    with owner.expect_response(lambda response: response.url.endswith('/api/admin/contacts') and response.request.method == 'PUT') as pending:
                        owner.locator('#save-contacts').click()
                    assert pending.value.status == 200
                    owner.locator('#contacts-result').get_by_text('Kontak tersimpan.', exact=False).wait_for()

                save_contacts('0812 3456-7890', '+62 823 4567 8901')
                owner.reload(wait_until='networkidle'); owner.locator('[data-page=settings]').click()
                assert owner.locator('#payment-whatsapp').input_value() == '6281234567890'
                assert owner.locator('#support-whatsapp').input_value() == '6282345678901'
                guest.goto(base+'/produk.html', wait_until='networkidle'); guest.locator('.support-launcher').click()
                cs = guest.locator('#support-whatsapp-link')
                cs.wait_for(); guest.wait_for_function("() => document.querySelector('#support-whatsapp-link').hasAttribute('href')")
                assert urlsplit(cs.get_attribute('href')).path == '/6282345678901'
                for width,height in VIEWPORTS:
                    guest.set_viewport_size({'width':width,'height':height}); check_layout(guest)
                    guest.screenshot(path=str(output/f'customer-service-{width}.png'))
                guest.keyboard.press('Escape'); assert not guest.locator('#support-dialog').is_visible()

                csrf = buyer_context.request.get(base+'/api/customer/session').json()['csrf']
                registered = buyer_context.request.post(base+'/api/customer/register', data={'nama':'Pembeli Uji', 'email':'buyer@example.test', 'nohp':'081234567890', 'password':password}, headers={'X-CSRF-Token':csrf})
                assert registered.status == 201
                headers = {'X-CSRF-Token':registered.json()['csrf']}
                product = buyer_context.request.get(base+'/api/products').json()['products'][0]
                created = buyer_context.request.post(base+'/api/orders', data={
                    'customer':{'nama_penerima':'Penerima Uji','nohp':'081234567890','alamat':'Jl. Alamat Privat 123','kota':'Jakarta','provinsi':'DKI Jakarta','kodepos':'12345'},
                    'items':[{'id':product['id'],'jumlah':1,'harga':product['harga'],'ukuran':'','warna':''}]},
                    headers={**headers,'Idempotency-Key':secrets.token_hex(16)})
                assert created.status == 201, created.text()
                order = created.json()['order']; assert order['status'] == 'baru'
                confirmation = base+'/konfirmasi.html?order='+order['nomor']
                buyer.goto(confirmation, wait_until='networkidle')
                payment = buyer.locator('#payment-whatsapp-link')
                buyer.wait_for_function("() => document.querySelector('#payment-whatsapp-link').hasAttribute('href')")
                url = urlsplit(payment.get_attribute('href')); text = parse_qs(url.query)['text'][0]
                assert url.scheme == 'https' and url.netloc == 'wa.me' and url.path == '/6281234567890'
                assert order['nomor'] in text and product['nama'] in text and 'Total pesanan:' in text
                assert ('Rp ' + f"{order['total']:,}".replace(',', '.')) in text
                assert 'buyer@example.test' not in text and 'Alamat Privat' not in text and '081234567890' not in text
                for width,height in VIEWPORTS:
                    buyer.set_viewport_size({'width':width,'height':height}); check_layout(buyer)
                    buyer.screenshot(path=str(output/f'payment-{width}.png'), full_page=True)
                buyer_context.route('https://wa.me/**', lambda route:route.fulfill(status=200,content_type='text/html',body='<p>WhatsApp intercepted by local test.</p>'))
                with buyer.expect_popup() as opened: payment.click()
                opened.value.wait_for_load_state(); opened.value.close()
                assert buyer_context.request.get(base+'/api/customer/orders/'+order['nomor']).json()['order']['status'] == 'baru'
                buyer.goto(base+'/akun.html#orders',wait_until='networkidle'); buyer.get_by_role('button',name='Lihat rincian',exact=True).click()
                buyer.locator('#customer-order-dialog .whatsapp-action').click(); buyer.wait_for_url('**/konfirmasi.html?order=*')

                # Removing one number has an honest unavailable state, without falling back to the other channel.
                save_contacts('', '+62 823 4567 8901')
                buyer.reload(wait_until='networkidle')
                assert payment.get_attribute('href') is None and payment.get_attribute('aria-disabled') == 'true'
                assert 'belum tersedia' in payment.inner_text()
                buyer.locator('.confirmation-help [data-support-open]').click(); buyer.wait_for_function("() => document.querySelector('#support-whatsapp-link').hasAttribute('href')")
                assert urlsplit(buyer.locator('#support-whatsapp-link').get_attribute('href')).path == '/6282345678901'
                buyer.keyboard.press('Escape')

                # Admin explicitly confirms payment; dismissing the prompt leaves the order pending.
                owner.locator('[data-page=orders]').click(); owner.locator('#refresh-orders').click()
                status = owner.locator('[data-order-status="'+order['nomor']+'"]')
                status.wait_for()
                owner.once('dialog', lambda dialog:dialog.dismiss()); status.select_option('diproses')
                assert buyer_context.request.get(base+'/api/customer/orders/'+order['nomor']).json()['order']['status'] == 'baru'
                owner.once('dialog', lambda dialog:dialog.accept()); status.select_option('diproses')
                owner.wait_for_function("() => [...document.querySelectorAll('[data-order-status]')].some(e => e.value === 'diproses' && !e.disabled)")
                buyer.reload(wait_until='networkidle')
                assert not buyer.locator('#payment-next-step').is_visible()
                assert buyer.locator('#confirmation-status').inner_text() == 'Diproses'
                assert not errors, errors
                browser.close()
        finally:
            process.terminate(); process.wait(timeout=10)
    print('PASS: separate editable WhatsApp numbers across admin/public domains; settings persist, order messages and privacy, pending status after opening WhatsApp, payment history, disabled contacts and processed orders; 5 responsive viewports; no WhatsApp servers contacted')


if __name__ == '__main__': main()
