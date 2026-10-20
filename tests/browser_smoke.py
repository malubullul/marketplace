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
    buyer_password=secrets.token_urlsafe(24)
    separate=os.environ.get('ANREDSELLER_TEST_ADMIN_PORTAL')=='1'
    source='''import json,sys,secrets,threading,signal
from server import create_app,create_owner
from werkzeug.serving import make_server
credentials=json.loads(sys.stdin.readline())
settings={}
if credentials['separate']:
    settings={'ADMIN_GATEWAY_KEY':secrets.token_urlsafe(40),'ADMIN_PORTAL_URL':'https://owner.example.test'}
sys.path.insert(0,'tests')
from browser_backend_support import configure_backend
app,cleanup=configure_backend(settings)
create_owner(app,credentials["email"],credentials["password"])
http=make_server("127.0.0.1",0,app,threaded=True)
ports={'store':http.server_port}
if credentials['separate']:
    sys.path.insert(0,'admin-portal')
    from app import create_app as create_portal
    portal=create_portal({'BACKEND_URL':f'http://127.0.0.1:{http.server_port}',
                          'SHOP_URL':f'http://127.0.0.1:{http.server_port}',
                          'ADMIN_GATEWAY_KEY':settings['ADMIN_GATEWAY_KEY'],'SECURE_COOKIES':False})
    owner_http=make_server('127.0.0.1',0,portal,threaded=True)
    ports['admin']=owner_http.server_port
    app.config['ADMIN_PORTAL_URL']=f'http://localhost:{owner_http.server_port}'
    threading.Thread(target=owner_http.serve_forever,daemon=True).start()
print(json.dumps(ports),flush=True)
signal.signal(signal.SIGTERM,lambda *_:sys.exit(0))
try:http.serve_forever()
finally:cleanup()
'''
    with open(Path(directory)/'server.log','w') as log:
        process=subprocess.Popen([str(ROOT/'.venv/bin/python'),'-c',source],cwd=ROOT,env={**os.environ,'ANREDSELLER_DATA_DIR':directory},stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=log,text=True)
        process.stdin.write(json.dumps({'email':'owner@example.test','password':password,'separate':separate})+'\n');process.stdin.flush()
        ports=json.loads(process.stdout.readline())
        base='http://127.0.0.1:'+str(ports['store'])+'/'
        admin_base=('http://localhost:'+str(ports['admin'])+'/') if separate else base
        try:
            with sync_playwright() as p:
                browser=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True)
                admin_context=browser.new_context(viewport={'width':1440,'height':1000},reduced_motion='reduce')
                public_context=browser.new_context(viewport={'width':390,'height':844},reduced_motion='reduce')
                owner=admin_context.new_page();shopper=public_context.new_page();errors=[]
                owner.on('pageerror',lambda e:errors.append(str(e)));shopper.on('pageerror',lambda e:errors.append(str(e)))
                owner.goto(admin_base+('' if separate else 'admin.html'),wait_until='networkidle')
                if separate:
                    assert owner.locator('[data-store-link]').first.get_attribute('href')==base.rstrip('/')
                    assert public_context.request.get(base+'api/session').status==401
                    assert admin_context.request.get(admin_base+'api/customer/session').status==404
                    assert admin_context.request.get(admin_base+'produk.html').status==404
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
                shopper.wait_for_url('**/akun.html?next=*');shopper.locator('#show-register').click()
                for field,value in {'buyer-register-name':'Pembeli Uji','buyer-register-phone':'081234567890','buyer-register-email':'buyer@example.test','buyer-register-password':buyer_password,'buyer-register-confirm':buyer_password}.items():shopper.locator('#'+field).fill(value)
                shopper.get_by_role('button',name='Buat akun pembeli',exact=True).click();shopper.wait_for_url('**/detail.html?id=*');shopper.locator('#pilihan-ukuran').wait_for()
                shopper.goto(base+'produk.html?q=Jaket+Suede+Uji',wait_until='networkidle');shopper.locator('.btn-wishlist').first.click();shopper.wait_for_function('() => getWishlist().length===1')
                shopper.locator('#grid-produk-list .kartu-produk-nama').click();shopper.wait_for_url('**/detail.html?id=*');shopper.locator('#pilihan-ukuran').wait_for()
                shopper.locator('#pilihan-ukuran').select_option('S');shopper.locator('#pilihan-warna').select_option('Hitam');shopper.locator('#btn-tambah').click();shopper.wait_for_function('() => getKeranjang().length===1')
                shopper.locator('#pilihan-ukuran').select_option('M');shopper.locator('#pilihan-warna').select_option('Cokelat');shopper.locator('#btn-tambah').click();shopper.wait_for_function('() => getKeranjang().length===2')
                shopper.goto(base+'akun.html#addresses',wait_until='networkidle');shopper.locator('#add-address').click()
                for field,value in {'address-label':'Rumah','address-recipient':'Penerima Uji','address-street':'Jl. Pengujian 1','address-city':'Jakarta','address-province':'DKI Jakarta','address-postcode':'12345'}.items():shopper.locator('#'+field).fill(value)
                shopper.get_by_role('button',name='Simpan alamat',exact=True).click();shopper.locator('#address-dialog').wait_for(state='hidden')
                device_context=browser.new_context(viewport={'width':1440,'height':1000},reduced_motion='reduce');device=device_context.new_page();device.on('pageerror',lambda e:errors.append(str(e)))
                device.goto(base+'akun.html?next=keranjang.html',wait_until='networkidle');device.locator('#buyer-login-email').fill('buyer@example.test');device.locator('#buyer-login-password').fill(buyer_password);device.get_by_role('button',name='Masuk ke akun',exact=True).click();device.wait_for_url('**/keranjang.html');device.wait_for_function('() => getKeranjang().length===2&&getWishlist().length===1')
                assert device_context.request.get(base+'api/customer/addresses').json()['addresses'][0]['label']=='Rumah'
                shopper.goto(base+'keranjang.html',wait_until='networkidle');assert shopper.locator('.keranjang-item').count()==2
                shopper.locator('.keranjang-qty').first.locator('button').nth(1).click();shopper.wait_for_function('() => hitungJumlahItem()===3')
                shopper.locator('.keranjang-qty').first.locator('button').first.click();shopper.wait_for_function('() => hitungJumlahItem()===2')
                shopper.locator('#btn-checkout').click();shopper.wait_for_url('**/checkout.html')
                shopper.wait_for_function('() => document.getElementById("kodepos").value==="12345"')
                assert shopper.locator('#email').input_value()=='buyer@example.test'
                shopper.locator('#kodepos').fill('1');shopper.locator('#btn-pesan').click();assert shopper.locator('#err-kodepos').inner_text()
                shopper.locator('#kodepos').fill('12345');shopper.locator('#checkout-address-select').select_option(index=1)
                shopper.locator('#btn-pesan').click();shopper.wait_for_url('**/konfirmasi.html?order=*');shopper.locator('#nomor-pesanan').filter(has_text='ANR-').wait_for()
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
                owner.locator('#logout-button').click();owner.locator('#login-view').wait_for(state='visible');assert admin_context.request.get(admin_base+'api/admin/products').status==401
                device.goto(base+'akun.html#orders',wait_until='networkidle');device.get_by_role('button',name='Lihat rincian',exact=True).wait_for();device.get_by_role('button',name='Lihat rincian',exact=True).click();device.locator('#customer-order-dialog').wait_for(state='visible');assert order_number in device.locator('#customer-order-details').inner_text();device.locator('#close-customer-order').click()
                assert device_context.request.get(base+'api/admin/orders').status==401
                other_context=browser.new_context(viewport={'width':390,'height':844},reduced_motion='reduce');other=other_context.new_page();other.on('pageerror',lambda e:errors.append(str(e)));other.goto(base+'akun.html',wait_until='networkidle');other.locator('#show-register').click()
                for field,value in {'buyer-register-name':'Pelanggan Lain','buyer-register-phone':'089123456789','buyer-register-email':'other@example.test','buyer-register-password':buyer_password,'buyer-register-confirm':buyer_password}.items():other.locator('#'+field).fill(value)
                other.get_by_role('button',name='Buat akun pembeli',exact=True).click();other.locator('#customer-dashboard').wait_for(state='visible')
                assert other_context.request.get(base+'api/customer/orders').json()['orders']==[]
                assert other_context.request.get(base+'api/customer/addresses').json()['addresses']==[]
                assert other_context.request.get(base+'api/customer/state').json()['state']['wishlist']==[]
                assert other_context.request.get(base+'api/customer/orders/'+order_number).status==404
                for width in [320,390,768,1440]:
                    device.set_viewport_size({'width':width,'height':900});assert device.evaluate('document.documentElement.scrollWidth<=innerWidth'),width
                device.screenshot(path=str(screenshots/'customer-desktop.png'),full_page=True)
                device.set_viewport_size({'width':390,'height':844});device.screenshot(path=str(screenshots/'customer-mobile.png'),full_page=True)
                shopper.goto(base+'akun.html',wait_until='networkidle');shopper.locator('#customer-logout').click();shopper.locator('#customer-auth').wait_for(state='visible');assert public_context.request.get(base+'api/customer/orders').status==401
                assert device_context.request.get(base+'api/customer/orders').status==200
                assert not errors,errors
                if separate:print('PASS: independent admin/public origins, admin-only routes, backend gateway protection, cookie login, photo upload, publishing and shared buyer orders')
                if os.environ.get('ANREDSELLER_TEST_DATABASE_URL'):print('PASS: full browser workflow uses real PostgreSQL and the Supabase Storage HTTP contract')
                browser.close()
                print('PASS: owner product management; customer signup/login, saved address, wishlist, cross-device cart, authenticated checkout, private order history, account isolation, responsive account/dashboard and independent logout')
        finally:
            process.terminate();process.wait(timeout=10)
