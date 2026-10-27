"""Real checkout stays available without a valid promo; never change a paid total silently."""
import json
import os
from pathlib import Path
import secrets
import subprocess
import tempfile

from playwright.sync_api import sync_playwright
from browser_store_content_smoke import SOURCE
from responsive_smoke import assert_layout

ROOT = Path(__file__).resolve().parents[1]


def run():
    shots = Path(os.environ.get('ANREDSELLER_SCREENSHOT_DIR', '/tmp/anredseller-optional-promo'))
    shots.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='anredseller-optional-promo-') as directory, open(shots/'server.log', 'w') as log:
        password = secrets.token_urlsafe(24)
        process = subprocess.Popen([str(ROOT/'.venv/bin/python'), '-c', SOURCE], cwd=ROOT,
                                   env={**os.environ, 'ANREDSELLER_DATA_DIR':directory},
                                   stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=log, text=True)
        process.stdin.write(json.dumps({'password':password})+'\n'); process.stdin.flush()
        try:
            ports = json.loads(process.stdout.readline())
            base = f"http://127.0.0.1:{ports['store']}"; admin = f"http://localhost:{ports['admin']}"
            with sync_playwright() as p:
                browser = p.chromium.launch(executable_path='/usr/bin/chromium', headless=True)
                context = browser.new_context(viewport={'width':390,'height':844}, reduced_motion='reduce')
                shop = context.new_page(); errors = []; submissions = []; checks = []
                shop.on('pageerror', lambda error:errors.append(str(error)))
                shop.on('request', lambda request:submissions.append(request.post_data_json) if request.url==base+'/api/orders' and request.method=='POST' else None)
                owner = browser.new_context().request
                csrf = owner.get(admin+'/api/session').json()['csrf']
                headers = {'X-CSRF-Token':owner.post(admin+'/api/login', data={'email':'owner@example.test','password':password}, headers={'X-CSRF-Token':csrf}).json()['csrf']}
                product = owner.post(admin+'/api/admin/products', data=dict(nama='Jaket Uji',kategori='apparel',brand='Anredseller',deskripsi='Produk uji checkout opsional.',harga=300000,hargaAsli=300000,stok=30,gambarList=['assets/shirt.png'],ukuran=[],warna=[],published=True), headers=headers).json()['product']
                csrf = context.request.get(base+'/api/customer/session').json()['csrf']
                buyer = context.request.post(base+'/api/customer/register', data={'email':'optional@example.test','nama':'Buyer','nohp':'081234567890','password':password}, headers={'X-CSRF-Token':csrf})
                assert buyer.status==201, buyer.text()
                shop.goto(base+'/akun.html', wait_until='networkidle')

                def checkout(saved=None):
                    shop.evaluate("id=>customerRequest('/cart',{method:'POST',body:{action:'add',id,jumlah:1}})", product['id'])
                    shop.evaluate("code=>{sessionStorage.removeItem('checkout_kupon');if(code)sessionStorage.setItem('checkout_kupon',code)}", saved)
                    shop.goto(base+'/checkout.html', wait_until='networkidle')
                    for field,value in {'nama-penerima':'Buyer','nohp':'081234567890','alamat':'Jalan Uji 1','kota':'Jakarta','provinsi':'DKI Jakarta','kodepos':'12345'}.items(): shop.locator('#'+field).fill(value)

                def submit(discount=0):
                    before = len(submissions)
                    shop.locator('#btn-pesan').click()
                    shop.wait_for_url('**/konfirmasi.html?order=*', timeout=10000)
                    shop.locator('#nomor-pesanan').filter(has_text='ANR-').wait_for()
                    assert len(submissions)==before+1
                    payload = submissions[-1]
                    assert payload['expected_discount']==discount
                    assert payload['coupon']==('PARTNER50' if discount else '')
                    number = shop.locator('#nomor-pesanan').inner_text()
                    order = context.request.get(base+'/api/customer/orders/'+number).json()['order']
                    assert order['diskon']==discount and order['total']==300000-discount, order

                # Reproduce the original blocker with no promo configured in the store.
                checkout()
                shop.locator('#promo-input').fill('TIDAKADA'); shop.locator('#promo-apply').click()
                shop.locator('#promo-message.promo-error').wait_for()
                submit()

                # Empty and un-applied text never require a promo request.
                checkout(); shop.locator('#promo-apply').click(); submit()
                checkout(); shop.locator('#promo-input').fill('BELUMDIPAKAI'); submit()
                checkout(saved='KODELAMA'); shop.locator('#promo-message.promo-error').wait_for(); submit()

                promo = dict(code='PARTNER50',partner='',kind='fixed',value=50000,min_subtotal=0,max_discount=None,starts_at=None,expires_at=None,usage_limit=None,per_customer_limit=99,active=True,version='0')
                promo = owner.post(admin+'/api/admin/promos', data=promo, headers=headers).json()['promo']
                checkout(); shop.locator('#promo-input').fill('PARTNER50'); shop.locator('#promo-apply').click()
                shop.wait_for_function('() => promoDiscount() === 50000')
                shop.locator('#promo-input').fill('')
                assert shop.locator('#co-diskon-row').is_hidden()
                submit()

                # Network failure or a still-pending optional request cannot hold an order.
                checkout(); shop.route('**/api/customer/promo', lambda route:route.abort())
                shop.locator('#promo-input').fill('PARTNER50'); shop.locator('#promo-apply').click()
                shop.locator('#promo-message.promo-error').wait_for(); submit(); shop.unroute('**/api/customer/promo')
                checkout(); pending = []; shop.route('**/api/customer/promo', lambda route:pending.append(route))
                shop.locator('#promo-input').fill('PARTNER50'); shop.locator('#promo-apply').click()
                shop.wait_for_function('() => promoChecking'); assert pending
                submit()
                for route in pending: route.abort()
                shop.unroute('**/api/customer/promo')

                # A valid code still applies its server-calculated discount.
                checkout(); shop.locator('#promo-input').fill('PARTNER50'); shop.locator('#promo-apply').click()
                shop.wait_for_function('() => promoDiscount() === 50000'); submit(discount=50000)

                # A promo withdrawn after preview updates the total and permits a deliberate retry.
                checkout(); shop.locator('#promo-input').fill('PARTNER50'); shop.locator('#promo-apply').click()
                shop.wait_for_function('() => promoDiscount() === 50000')
                owner.put(admin+'/api/admin/promos/PARTNER50', data={**promo,'active':False}, headers=headers)
                with shop.expect_response(lambda response:response.url==base+'/api/orders' and response.request.method=='POST') as response:
                    shop.locator('#btn-pesan').click()
                assert response.value.status==409
                shop.get_by_text('Periksa total', exact=False).wait_for()
                assert shop.locator('#co-total').inner_text()=='Rp 300.000'
                for width,height in [(320,568),(390,844),(768,1024),(844,390),(1440,1000)]:
                    shop.set_viewport_size({'width':width,'height':height}); assert_layout(shop, 'optional promo '+str(width), checks)
                    shop.screenshot(path=str(shots/f'checkout-{width}.png'), full_page=True)
                submit()
                assert not errors, errors
                browser.close()
                print(f'PASS: 9 real orders across invalid, empty, draft, saved, cleared, failed/pending preview, valid discount and withdrawn-promo retry; {len(checks)} responsive checks. No external messages sent.')
        finally:
            process.terminate(); process.wait(timeout=10)


if __name__=='__main__': run()
