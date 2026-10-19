"""Run with Python + Playwright installed; starts an isolated disposable store."""
import json
import os
from pathlib import Path
import secrets
import subprocess
import tempfile
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1]
with tempfile.TemporaryDirectory(prefix='anredseller-browser-') as directory:
    password=secrets.token_urlsafe(24)
    source='''import json,sys
from server import app,create_owner
from werkzeug.serving import make_server
credentials=json.loads(sys.stdin.readline())
create_owner(app,credentials["email"],credentials["password"])
http=make_server("127.0.0.1",0,app,threaded=True)
print(http.server_port,flush=True)
http.serve_forever()
'''
    with open(Path(directory)/'server.log','w') as log:
        process=subprocess.Popen([str(ROOT/'.venv/bin/python'),'-c',source],cwd=ROOT,env={**os.environ,'ANREDSELLER_DATA_DIR':directory},stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=log,text=True)
        process.stdin.write(json.dumps({'email':'owner@example.test','password':password})+'\n');process.stdin.flush()
        port=process.stdout.readline().strip()
        if not port.isdigit():raise RuntimeError('Test server did not start')
        base='http://127.0.0.1:'+port+'/'
        try:
            with sync_playwright() as p:
                browser=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True)
                admin_context=browser.new_context(viewport={'width':1440,'height':1000},reduced_motion='reduce')
                public_context=browser.new_context(viewport={'width':390,'height':844},reduced_motion='reduce')
                owner=admin_context.new_page();shopper=public_context.new_page();errors=[]
                owner.on('pageerror',lambda e:errors.append(str(e)));shopper.on('pageerror',lambda e:errors.append(str(e)))
                owner.goto(base+'admin.html',wait_until='networkidle')
                owner.locator('#login-email').fill('owner@example.test');owner.locator('#login-password').fill(password);owner.locator('#login-button').click();owner.locator('#dashboard').wait_for(state='visible')
                owner.locator('#add-product').click()
                for field,value in {'product-name':'Jaket Suede Uji','product-description':'Jaket nyaman <b>suede</b> dengan detail premium.','product-brand':'Anredseller','product-price':'299000','product-stock':'4','product-sizes':'S, M','product-colors':'Hitam, Cokelat','product-material':'Suede sintetis'}.items():owner.locator('#'+field).fill(value)
                owner.locator('#product-photos').set_input_files(str(ROOT/'assets/shirt.png'))
                owner.get_by_text('Foto berhasil diunggah.',exact=True).wait_for()
                owner.get_by_role('button',name='Simpan draf',exact=True).click();owner.locator('#product-dialog').wait_for(state='hidden')
                assert not any(product['nama']=='Jaket Suede Uji' for product in public_context.request.get(base+'api/products').json()['products'])
                owner.get_by_role('button',name='Edit Jaket Suede Uji',exact=True).click();owner.get_by_role('button',name='Terbitkan produk →',exact=True).click();owner.locator('#product-dialog').wait_for(state='hidden')
                shopper.goto(base+'produk.html?q=Jaket+Suede+Uji',wait_until='networkidle')
                shopper.locator('#grid-produk-list .kartu-produk-nama').wait_for();assert shopper.locator('#grid-produk-list article').count()==1
                assert shopper.locator('#grid-produk-list img').evaluate('(e)=>e.complete&&e.naturalWidth>0')
                shopper.locator('#grid-produk-list .kartu-produk-nama').click();shopper.wait_for_url('**/detail.html?id=*');shopper.locator('#pilihan-ukuran').wait_for()
                assert '<b>suede</b>' in shopper.locator('#tab-deskripsi').inner_text();assert shopper.locator('#tab-deskripsi b').count()==0
                shopper.locator('#btn-tambah').click();assert shopper.evaluate('getKeranjang().length')==0
                shopper.locator('#pilihan-ukuran').select_option('S');shopper.locator('#pilihan-warna').select_option('Hitam');shopper.locator('#btn-tambah').click()
                shopper.locator('#pilihan-ukuran').select_option('M');shopper.locator('#pilihan-warna').select_option('Cokelat');shopper.locator('#btn-tambah').click();assert shopper.evaluate('getKeranjang().length')==2
                shopper.goto(base+'keranjang.html',wait_until='networkidle');assert shopper.locator('.keranjang-item').count()==2
                shopper.locator('.keranjang-qty').first.locator('button').nth(1).click();assert shopper.evaluate('hitungJumlahItem()')==3
                shopper.locator('.keranjang-qty').first.locator('button').first.click();assert shopper.evaluate('hitungJumlahItem()')==2
                shopper.locator('#btn-checkout').click();shopper.wait_for_url('**/checkout.html')
                shopper.locator('#btn-pesan').click();assert shopper.locator('#err-email').inner_text()
                for field,value in {'nama-depan':'Pembeli','nama-belakang':'Uji','email':'buyer@example.test','nohp':'081234567890','nama-penerima':'Penerima Uji','alamat':'Jl. Pengujian 1','kota':'Jakarta','kodepos':'12345'}.items():shopper.locator('#'+field).fill(value)
                shopper.locator('#provinsi').select_option(label='DKI Jakarta');shopper.locator('#btn-pesan').click();shopper.wait_for_url('**/konfirmasi.html');shopper.locator('#nomor-pesanan').filter(has_text='ANR-').wait_for()
                order_number=shopper.locator('#nomor-pesanan').inner_text();assert shopper.evaluate('getKeranjang().length')==0
                assert 'Pembeli Uji' in shopper.locator('#konfirmasi-sub').inner_text()
                owner.locator('[data-page="orders"]').click();owner.locator('#refresh-orders').click();owner.get_by_role('button',name='Lihat pesanan',exact=True).wait_for();owner.get_by_role('button',name='Lihat pesanan',exact=True).click()
                assert order_number in owner.locator('#order-details').inner_text();assert 'Penerima Uji' in owner.locator('#order-details').inner_text();assert 'Cokelat' in owner.locator('#order-details').inner_text();owner.locator('#close-order').click()
                product=next(product for product in public_context.request.get(base+'api/products').json()['products'] if product['nama']=='Jaket Suede Uji');assert product['stok']==2
                owner.locator('[data-page="products"]').click();owner.get_by_role('button',name='Edit Jaket Suede Uji',exact=True).click();owner.get_by_role('button',name='Simpan draf',exact=True).click();owner.locator('#product-dialog').wait_for(state='hidden')
                assert not any(product['nama']=='Jaket Suede Uji' for product in public_context.request.get(base+'api/products').json()['products'])
                for width in [375,768,1440]:
                    owner.set_viewport_size({'width':width,'height':900});assert owner.evaluate('document.documentElement.scrollWidth<=innerWidth'),width
                screenshots=Path(os.environ.get('ANREDSELLER_SCREENSHOT_DIR','/tmp/anredseller-browser'));screenshots.mkdir(exist_ok=True)
                owner.screenshot(path=str(screenshots/'admin-desktop.png'),full_page=True)
                owner.set_viewport_size({'width':390,'height':844});owner.screenshot(path=str(screenshots/'admin-mobile.png'),full_page=True)
                owner.locator('#logout-button').click();owner.locator('#login-view').wait_for(state='visible');assert admin_context.request.get(base+'api/admin/products').status==401
                assert not errors,errors
                browser.close()
                print('PASS: owner login, image upload, draft isolation, publication to a separate public browser, photo/details, variants, cart quantities, real order persistence, owner order view, stock deduction, unpublishing, responsive dashboard and logout')
        finally:
            process.terminate();process.wait(timeout=10)
