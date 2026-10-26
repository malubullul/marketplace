"""Promo setup on a separate owner origin, real customer checkout and receipts."""
import json
import os
from pathlib import Path
import secrets
import subprocess
import tempfile
from urllib.parse import parse_qs, urlparse
from playwright.sync_api import sync_playwright
from browser_store_content_smoke import SOURCE, VIEWS
from responsive_smoke import assert_layout

ROOT=Path(__file__).resolve().parents[1]

def run():
    shots=Path(os.environ.get('ANREDSELLER_SCREENSHOT_DIR','/tmp/anredseller-promos'));shots.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='anredseller-promos-') as directory, open(Path(directory)/'server.log','w') as log:
        password=secrets.token_urlsafe(24)
        process=subprocess.Popen([str(ROOT/'.venv/bin/python'),'-c',SOURCE],cwd=ROOT,env={**os.environ,'ANREDSELLER_DATA_DIR':directory},stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=log,text=True)
        process.stdin.write(json.dumps({'password':password})+'\n');process.stdin.flush()
        ports=json.loads(process.stdout.readline());base=f"http://127.0.0.1:{ports['store']}";admin=f"http://localhost:{ports['admin']}"
        try:
            with sync_playwright() as p:
                browser=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True)
                owner_context=browser.new_context(viewport={'width':1440,'height':1000},reduced_motion='reduce')
                buyer_context=browser.new_context(viewport={'width':390,'height':844},reduced_motion='reduce',is_mobile=True,has_touch=True)
                owner=owner_context.new_page();shop=buyer_context.new_page();errors=[];checks=[]
                for page in [owner,shop]:page.on('pageerror',lambda error:errors.append(str(error)))
                owner.goto(admin,wait_until='networkidle');owner.locator('#login-email').fill('owner@example.test');owner.locator('#login-password').fill(password)
                owner.locator('#login-button').click();owner.locator('#dashboard').wait_for(state='visible')
                owner.locator('[data-page=promos]').click();owner.locator('#promos-empty').wait_for(state='visible')
                owner.locator('#add-promo').click()
                for width,height in VIEWS:
                    owner.set_viewport_size({'width':width,'height':height});assert_layout(owner,f'promo editor {width}',checks)
                    owner.screenshot(path=str(shots/f'admin-editor-{width}.png'))
                owner.set_viewport_size({'width':1440,'height':1000})
                for field,value in {'promo-code':'PARTNER15','promo-partner':'Partner <b>Uji</b>','promo-value':'15','promo-min':'200000','promo-cap':'40000','promo-limit':'2'}.items():owner.locator('#'+field).fill(value)
                owner.locator('#promo-active').check();owner.locator('#save-promo').click();owner.locator('#promo-dialog').wait_for(state='hidden');owner.locator('[data-edit-promo=PARTNER15]').wait_for()
                assert owner.locator('#promo-rows b').count()==0
                csrf=owner_context.request.get(admin+'/api/session').json()['csrf']
                product=owner_context.request.post(admin+'/api/admin/products',data=dict(nama='Jaket Kolaborasi Uji',kategori='apparel',brand='Anredseller',deskripsi='Jaket untuk pengujian promo.',harga=299999,hargaAsli=299999,stok=10,gambarList=['assets/shirt.png'],ukuran=[],warna=[],published=True),headers={'X-CSRF-Token':csrf}).json()['product']
                owner.reload(wait_until='networkidle');owner.locator('[data-edit-promo=PARTNER15]').wait_for()
                for width,height in VIEWS:
                    owner.set_viewport_size({'width':width,'height':height});assert_layout(owner,f'promo list {width}',checks)
                    owner.screenshot(path=str(shots/f'admin-promos-{width}.png'),full_page=True)
                # No customer, promo enumeration or shared cookie on the owner domain.
                assert owner_context.request.post(admin+'/api/customer/promo',data={'code':'PARTNER15'}).status==404
                assert buyer_context.request.get(base+'/api/admin/promos').status==401
                shop.goto(base+'/akun.html',wait_until='networkidle');shop.locator('#show-register').click()
                for field,value in {'buyer-register-name':'Pembeli Promo','buyer-register-phone':'081234567890','buyer-register-email':'promo@example.test','buyer-register-password':password,'buyer-register-confirm':password}.items():shop.locator('#'+field).fill(value)
                shop.get_by_role('button',name='Buat akun pembeli',exact=True).click();shop.locator('#customer-dashboard').wait_for(state='visible')
                shop.goto(base+'/detail.html?id='+str(product['id']),wait_until='networkidle');shop.locator('#btn-tambah').click();shop.wait_for_function('() => getKeranjang().length === 1')
                shop.goto(base+'/keranjang.html',wait_until='networkidle')
                shop.locator('#promo-input').fill('partner15');shop.locator('#promo-apply').click();shop.get_by_text('Kode PARTNER15 dipakai. Hemat Rp 40.000.',exact=True).wait_for()
                assert shop.locator('#total-ringkasan').inner_text()=='Rp 259.999'
                # Quantities cause a fresh server quote; never multiply a client-side percentage.
                shop.locator('.keranjang-qty button').last.click();shop.wait_for_function('() => hitungJumlahItem() === 2 && !promoChecking && promoDiscount() === 40000')
                assert shop.locator('#total-ringkasan').inner_text()=='Rp 559.998'
                shop.locator('.keranjang-qty button').first.click();shop.wait_for_function('() => hitungJumlahItem() === 1 && !promoChecking && promoDiscount() === 40000')
                for width,height in VIEWS:
                    shop.set_viewport_size({'width':width,'height':height});assert_layout(shop,f'promo cart {width}',checks)
                    if width == 768:
                        shop.locator('.mobile-menu').click()
                        shop.locator('.desktop-nav.mobile-open').wait_for(state='visible')
                        assert_layout(shop,'promo cart tablet menu',checks)
                        shop.locator('.mobile-menu').click()
                    shop.screenshot(path=str(shots/f'cart-{width}.png'),full_page=True)
                shop.set_viewport_size({'width':390,'height':844});shop.locator('#btn-checkout').click();shop.wait_for_url('**/checkout.html')
                shop.wait_for_function('() => !promoChecking && promoDiscount() === 40000')
                for field,value in {'nama-penerima':'Penerima Promo','nohp':'081234567890','alamat':'Jalan Pengujian 1','kota':'Jakarta','provinsi':'DKI Jakarta','kodepos':'12345'}.items():shop.locator('#'+field).fill(value)
                for width,height in VIEWS:
                    shop.set_viewport_size({'width':width,'height':height});assert_layout(shop,f'promo checkout {width}',checks)
                    shop.screenshot(path=str(shots/f'checkout-{width}.png'),full_page=True)
                # Invalid/replaced codes never silently submit a higher undiscounted total.
                shop.locator('#promo-input').fill('MISSING');shop.locator('#promo-apply').click();shop.locator('#promo-message.promo-error').wait_for()
                shop.locator('#btn-pesan').click();assert 'Kode promo belum valid' in shop.locator('#checkout-error').inner_text()
                shop.locator('#promo-remove').click();assert shop.locator('#co-diskon-row').is_hidden();assert shop.locator('#co-total').inner_text()=='Rp 299.999'
                shop.locator('#promo-input').fill('PARTNER15');shop.locator('#promo-apply').click();shop.wait_for_function('() => !promoChecking && promoDiscount() === 40000')
                shop.locator('#btn-pesan').click();shop.wait_for_url('**/konfirmasi.html?order=*');shop.locator('#payment-whatsapp-link[href]').wait_for()
                number=shop.locator('#nomor-pesanan').inner_text()
                assert 'PARTNER15' in shop.locator('#detail-pesanan').inner_text()
                message=parse_qs(urlparse(shop.locator('#payment-whatsapp-link').get_attribute('href')).query)['text'][0]
                assert 'Kode promo: PARTNER15' in message and '40.000' in message and '259.999' in message
                assert buyer_context.request.get(base+'/api/customer/orders/'+number).json()['order']['diskon']==40000
                # History and owner detail retain the exact code and original partner.
                shop.goto(base+'/akun.html#orders',wait_until='networkidle');shop.get_by_role('button',name='Lihat rincian',exact=True).click();shop.locator('#customer-order-dialog').wait_for(state='visible')
                assert 'PARTNER15' in shop.locator('#customer-order-details').inner_text();shop.locator('#close-customer-order').click()
                owner.set_viewport_size({'width':1440,'height':1000});owner.locator('[data-page=orders]').click();owner.locator('#refresh-orders').click();owner.locator('[data-order]').first.click();owner.locator('#order-dialog').wait_for(state='visible')
                assert 'PARTNER15 / Partner <b>Uji</b>' in owner.locator('#order-details').inner_text();assert owner.locator('#order-details b').count()==0
                owner.locator('#close-order').click()
                owner.locator('[data-page=promos]').click();owner.locator('[data-edit-promo=PARTNER15]').click();owner.locator('#promo-active').uncheck();owner.locator('#save-promo').click();owner.locator('#promo-dialog').wait_for(state='hidden')
                owner.locator('#promo-rows').get_by_text('Nonaktif',exact=True).wait_for()
                # Editing and then cancelling a fixed promo must not create it.
                owner.locator('#add-promo').click();owner.locator('#promo-kind').select_option('fixed');assert owner.locator('#promo-cap-label').is_hidden()
                owner.locator('#cancel-promo').click();assert len(owner_context.request.get(admin+'/api/admin/promos').json()['promos'])==1
                assert not errors,errors
                print(f'PASS: promo CRUD on separate owner origin, reload persistence, literal partner text, server quote, quantity revalidation, invalid/remove/reapply, checkout receipt/history, WhatsApp discount and owner details, deactivation; {len(checks)} layout checks at 5 viewport sizes; no external links opened or uncaught JS errors.')
                browser.close()
        finally:
            process.terminate();process.wait(timeout=10)

if __name__=='__main__':run()
