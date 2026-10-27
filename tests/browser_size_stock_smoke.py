"""Owner size allocation/restock and real multi-size buyer orders on separate origins."""
import json
import os
from pathlib import Path
import secrets
import subprocess
import tempfile
from playwright.sync_api import sync_playwright
from browser_store_content_smoke import SOURCE, VIEWS
from responsive_smoke import assert_layout

ROOT=Path(__file__).resolve().parents[1]


def run():
    shots=Path(os.environ.get('ANREDSELLER_SCREENSHOT_DIR','/tmp/anredseller-size-stock'));shots.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='anredseller-size-browser-') as directory, open(shots/'server.log','w') as log:
        password=secrets.token_urlsafe(24)
        process=subprocess.Popen([str(ROOT/'.venv/bin/python'),'-c',SOURCE],cwd=ROOT,env={**os.environ,'ANREDSELLER_DATA_DIR':directory},stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=log,text=True)
        process.stdin.write(json.dumps({'password':password})+'\n');process.stdin.flush()
        try:
            ports=json.loads(process.stdout.readline());base=f"http://127.0.0.1:{ports['store']}";admin=f"http://localhost:{ports['admin']}"
            with sync_playwright() as p:
                browser=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True)
                owner=browser.new_context(viewport={'width':1440,'height':1000},reduced_motion='reduce').new_page()
                buyer=browser.new_context(viewport={'width':390,'height':844},reduced_motion='reduce').new_page()
                errors=[];checks=[]
                for page in [owner,buyer]:page.on('pageerror',lambda error:errors.append(str(error)))
                owner.goto(admin,wait_until='networkidle');owner.locator('#login-email').fill('owner@example.test');owner.locator('#login-password').fill(password)
                owner.locator('#login-button').click();owner.locator('#dashboard').wait_for(state='visible')
                owner.locator('#add-product').click()
                for field,value in {'product-name':'Jaket Ukuran Uji','product-description':'Ukuran dan stok terpisah untuk pengujian.','product-brand':'Anredseller','product-price':'300000'}.items():owner.locator('#'+field).fill(value)
                owner.locator('#size-stock-enabled').check()
                for size,stock in [('S',2),('M',4),('L',0),('XL',1)]:
                    owner.locator('#new-stock-size').select_option(size);owner.locator('#add-stock-size').click()
                    owner.get_by_label('Stok '+size,exact=True).fill(str(stock))
                assert owner.locator('#product-stock').input_value()=='7'
                for width,height in VIEWS:
                    owner.set_viewport_size({'width':width,'height':height});assert_layout(owner,'size editor '+str(width),checks)
                    owner.locator('#size-stock-rows').scroll_into_view_if_needed();owner.screenshot(path=str(shots/f'editor-{width}.png'))
                owner.locator('#product-photos').set_input_files(str(ROOT/'assets/shirt.png'));owner.get_by_text('Foto berhasil diunggah.',exact=True).wait_for()
                owner.get_by_role('button',name='Terbitkan produk →',exact=True).click();owner.locator('#product-dialog').wait_for(state='hidden')
                owner.get_by_role('button',name='Edit Jaket Ukuran Uji',exact=True).click()
                owner.get_by_label('Tambah stok M',exact=True).fill('3');owner.locator('[data-size-restock="1"]').click()
                assert owner.get_by_label('Stok M',exact=True).input_value()=='7'
                owner.get_by_role('button',name='Terbitkan produk →',exact=True).click();owner.locator('#product-dialog').wait_for(state='hidden')
                buyer.goto(base+'/akun.html',wait_until='networkidle');buyer.locator('#show-register').click()
                for field,value in {'buyer-register-name':'Buyer','buyer-register-phone':'081234567890','buyer-register-email':'sizes@example.test','buyer-register-password':password,'buyer-register-confirm':password}.items():buyer.locator('#'+field).fill(value)
                buyer.get_by_role('button',name='Buat akun pembeli',exact=True).click();buyer.locator('#customer-dashboard').wait_for(state='visible')
                product=next(product for product in buyer.request.get(base+'/api/products').json()['products'] if product['nama']=='Jaket Ukuran Uji')
                buyer.goto(base+'/detail.html?id='+str(product['id']),wait_until='networkidle')
                assert buyer.locator('#pilihan-ukuran option[value=L]').evaluate('(option)=>option.disabled')
                assert buyer.locator('#btn-tambah').is_disabled()
                buyer.locator('#pilihan-ukuran').select_option('S')
                assert buyer.locator('#qty-input').get_attribute('max')=='2'
                buyer.locator('#qty-input').fill('99');buyer.locator('#qty-input').dispatch_event('change')
                assert buyer.locator('#qty-input').input_value()=='2'
                for width,height in VIEWS:
                    buyer.set_viewport_size({'width':width,'height':height});assert_layout(buyer,'size detail '+str(width),checks)
                    buyer.locator('#pilihan-ukuran').scroll_into_view_if_needed();buyer.screenshot(path=str(shots/f'detail-{width}.png'))
                buyer.locator('#btn-tambah').click();buyer.wait_for_function('()=>getKeranjang().length===1')
                buyer.locator('#pilihan-ukuran').select_option('M');buyer.locator('#qty-input').fill('1');buyer.locator('#qty-input').dispatch_event('change')
                buyer.locator('#btn-tambah').click();buyer.wait_for_function('()=>getKeranjang().length===2')
                buyer.goto(base+'/keranjang.html',wait_until='networkidle');assert buyer.locator('#btn-checkout').is_enabled()
                buyer.locator('#btn-checkout').click();buyer.wait_for_url('**/checkout.html')
                for field,value in {'nama-penerima':'Buyer','nohp':'081234567890','alamat':'Jalan Uji 1','kota':'Jakarta','provinsi':'DKI Jakarta','kodepos':'12345'}.items():buyer.locator('#'+field).fill(value)
                buyer.locator('#btn-pesan').click();buyer.wait_for_url('**/konfirmasi.html?order=*');buyer.locator('#nomor-pesanan').filter(has_text='ANR-').wait_for()
                number=buyer.locator('#nomor-pesanan').inner_text()
                def stocks():return next(item for item in buyer.request.get(base+'/api/products').json()['products'] if item['id']==product['id'])
                assert stocks()['stokUkuran']==[{'ukuran':'S','stok':0},{'ukuran':'M','stok':6},{'ukuran':'L','stok':0},{'ukuran':'XL','stok':1}]
                owner.set_viewport_size({'width':1440,'height':1000});owner.locator('[data-page=orders]').click();owner.locator('#refresh-orders').click();owner.locator('[data-order="'+number+'"]').click()
                owner.get_by_role('button',name='Tandai sudah dibayar',exact=True).click();owner.get_by_role('button',name='Konfirmasi',exact=True).click();owner.get_by_role('heading',name='Sudah dibayar',exact=True).wait_for();owner.locator('#close-order').click()
                for state in ['diproses','dikirim','selesai']:
                    owner.locator('[data-order-status="'+number+'"]').select_option(state);owner.wait_for_function('(state)=>orders.some(order=>order.status===state)',arg=state)
                assert stocks()['stok']==7
                owner.locator('[data-page=products]').click();owner.get_by_role('button',name='Edit Jaket Ukuran Uji',exact=True).click()
                owner.locator('#new-stock-size').select_option('XXL');owner.locator('#add-stock-size').click();owner.get_by_label('Stok XXL',exact=True).fill('4')
                owner.get_by_role('button',name='Terbitkan produk →',exact=True).click();owner.locator('#product-dialog').wait_for(state='hidden')
                assert stocks()['stok']==11 and stocks()['stokUkuran'][-1]=={'ukuran':'XXL','stok':4}
                buyer.goto(base+'/detail.html?id='+str(product['id']),wait_until='networkidle');assert buyer.locator('#pilihan-ukuran option[value=S]').evaluate('(option)=>option.disabled')
                buyer.locator('#pilihan-ukuran').select_option('XXL');assert '4 pcs' in buyer.locator('#size-stock-availability').inner_text()
                assert not errors,errors
                browser.close()
                print(f'PASS: individual S/M/L/XL stock, size-specific restock, adding XXL on the same product, sold-out choices, quantity limits, multi-size cart/checkout, manual payment and completion without double deduction; {len(checks)} responsive checks; isolated data only.')
        finally:process.terminate();process.wait(timeout=10)


if __name__=='__main__':run()
