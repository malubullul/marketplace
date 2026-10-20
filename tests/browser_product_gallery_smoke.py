"""Upload four real fixture files in admin, then browse the persisted buyer gallery."""
import json
import os
from pathlib import Path
import secrets
import subprocess
import tempfile

from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1]
VIEWPORTS=[(320,568),(390,844),(768,1024),(1440,1000),(844,390)]


def wait_photo(gallery, index):
    gallery.page.wait_for_function('''({name,index}) => {
      const gallery=[...document.querySelectorAll('[data-product-gallery]')].find(e=>e.dataset.productName===name);
      const image=gallery?.querySelector('.product-gallery-image');
      return gallery?.dataset.photoIndex===String(index) && image?.complete && image.naturalWidth>0 && !gallery.querySelector('[aria-busy=true]');
    }''',arg={'name':gallery.get_attribute('data-product-name'),'index':index})


def swipe(page,x,y,dx,dy):
    session=page.context.new_cdp_session(page)
    session.send('Input.dispatchTouchEvent',{'type':'touchStart','touchPoints':[{'x':x,'y':y}]})
    for i in range(1,7):session.send('Input.dispatchTouchEvent',{'type':'touchMove','touchPoints':[{'x':x+dx*i/6,'y':y+dy*i/6}]})
    session.send('Input.dispatchTouchEvent',{'type':'touchEnd','touchPoints':[]});session.detach()


def main():
    output=Path(os.environ.get('ANREDSELLER_SCREENSHOT_DIR','/tmp/anredseller-product-gallery'));output.mkdir(parents=True,exist_ok=True)
    password=secrets.token_urlsafe(24)
    source='''import sys,json,secrets,threading,signal
from server import create_owner
from werkzeug.serving import make_server
sys.path.insert(0,'tests')
from browser_backend_support import configure_backend
password=sys.stdin.readline().strip();key=secrets.token_urlsafe(40)
app,cleanup=configure_backend({'TESTING':True,'ADMIN_GATEWAY_KEY':key,'ADMIN_PORTAL_URL':'https://owner.example.test'})
create_owner(app,'owner@example.test',password)
store=make_server('127.0.0.1',0,app,threaded=True)
sys.path.insert(0,'admin-portal')
from app import create_app as create_portal
portal=create_portal({'BACKEND_URL':f'http://127.0.0.1:{store.server_port}','SHOP_URL':f'http://127.0.0.1:{store.server_port}','ADMIN_GATEWAY_KEY':key,'SECURE_COOKIES':False})
admin=make_server('127.0.0.1',0,portal,threaded=True)
threading.Thread(target=admin.serve_forever,daemon=True).start()
print(json.dumps({'store':store.server_port,'admin':admin.server_port}),flush=True)
signal.signal(signal.SIGTERM,lambda *_:sys.exit(0))
try:store.serve_forever()
finally:cleanup()
'''
    with tempfile.TemporaryDirectory(prefix='anredseller-product-gallery-') as directory,open(output/'server.log','w') as log:
        process=subprocess.Popen([str(ROOT/'.venv/bin/python'),'-c',source],cwd=ROOT,env={**os.environ,'ANREDSELLER_DATA_DIR':directory},stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=log,text=True)
        try:
            process.stdin.write(password+'\n');process.stdin.flush();ports=json.loads(process.stdout.readline())
            base='http://127.0.0.1:'+str(ports['store'])+'/'
            admin_base='http://localhost:'+str(ports['admin'])+'/'
            with sync_playwright() as p:
                browser=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True)
                owner_context=browser.new_context(viewport={'width':1440,'height':1000},reduced_motion='reduce')
                buyer_context=browser.new_context(viewport={'width':390,'height':844},has_touch=True,reduced_motion='reduce')
                owner,buyer=owner_context.new_page(),buyer_context.new_page();errors=[]
                for page in [owner,buyer]:page.on('pageerror',lambda error:errors.append(str(error)))
                owner.goto(admin_base,wait_until='networkidle');owner.locator('#login-email').fill('owner@example.test');owner.locator('#login-password').fill(password)
                owner.locator('#login-button').click();owner.locator('#dashboard').wait_for(state='visible');owner.locator('#add-product').click()
                name='Koleksi Empat Foto Uji'
                for field,value in {'product-name':name,'product-description':'Produk sementara untuk pengujian galeri empat foto.','product-brand':'Anredseller','product-price':'299000','product-stock':'8'}.items():owner.locator('#'+field).fill(value)
                # Existing fixture assets only; no production merchandise or customer data is changed.
                files=[str(ROOT/'assets'/name) for name in ['shirt.png','polo.png','jeans.png','check-shirt.png']]
                owner.locator('#product-photos').set_input_files(files)
                owner.get_by_text('Foto berhasil diunggah.',exact=True).wait_for()
                assert owner.locator('#photo-grid img').count()==4
                assert '4 dari 8 foto' in owner.locator('#photo-count').inner_text()
                owner.locator('#photo-grid [data-cover="2"]').click()
                expected=owner.locator('#photo-grid img').evaluate_all('(images)=>images.map(e=>e.getAttribute("src"))')
                owner.locator('.editor-photos').scroll_into_view_if_needed();owner.screenshot(path=str(output/'admin-four-photos-1440.png'))
                owner.get_by_role('button',name='Terbitkan produk →',exact=True).click();owner.locator('#product-dialog').wait_for(state='hidden')
                product=next(item for item in buyer_context.request.get(base+'api/products').json()['products'] if item['nama']==name)
                assert product['gambarList']==expected and product['gambar']==expected[0]
                pid=product['id']
                # A second gallery must maintain its own position.
                owner_csrf=owner_context.request.get(admin_base+'api/session').json()['csrf']
                second=owner_context.request.post(admin_base+'api/admin/products',data={**product,'nama':'Koleksi Empat Foto Kedua'},headers={'X-CSRF-Token':owner_csrf})
                assert second.status==201;second_id=second.json()['product']['id']
                for file in expected:assert buyer_context.request.get(base+file.lstrip('/')).status==200
                owner.get_by_role('button',name='Edit '+name,exact=True).click()
                assert owner.locator('#photo-grid img').evaluate_all('(images)=>images.map(e=>e.getAttribute("src"))')==expected
                owner.locator('#close-editor').click()
                for width,height in VIEWPORTS:
                    buyer.set_viewport_size({'width':width,'height':height});buyer.goto(base+'produk.html?q=Koleksi+Empat+Foto+Uji',wait_until='networkidle')
                    gallery=buyer.locator('#grid-produk-list [data-product-gallery]');gallery.wait_for()
                    for index in range(4):
                        wait_photo(gallery,index)
                        assert gallery.locator('.product-gallery-image').get_attribute('src')==expected[index]
                        assert gallery.locator('[data-product-photo-current]').inner_text()==str(index+1)
                        assert buyer.evaluate('document.documentElement.scrollWidth <= innerWidth+1')
                        assert gallery.locator('.product-photo-next').bounding_box()['width']>=44
                        if index<3:gallery.locator('.product-photo-next').click()
                    buyer.screenshot(path=str(output/f'catalog-four-photos-{width}.png'),full_page=True)
                    gallery.locator('.product-photo-next').click();wait_photo(gallery,0)
                    gallery.locator('.product-photo-previous').click();wait_photo(gallery,3)
                    gallery.locator('.product-photo-previous').focus();buyer.keyboard.press('Home');wait_photo(gallery,0)
                    # Normal image clicks still open the product, independent of gallery controls.
                    gallery.locator('.product-photo-link').click();buyer.wait_for_url('**/detail.html?id='+str(pid))
                    detail=buyer.locator('.product-gallery-detail');detail.wait_for();assert detail.locator('.galeri-thumb-item').count()==4
                    detail.locator('[data-product-photo-index="2"]').click();wait_photo(detail,2)
                    assert detail.locator('[data-product-photo-index="2"]').get_attribute('aria-pressed')=='true'
                    detail.locator('.product-photo-next').click();wait_photo(detail,3)
                    buyer.screenshot(path=str(output/f'detail-four-photos-{width}.png'),full_page=True)
                buyer.set_viewport_size({'width':390,'height':844});buyer.goto(base+'produk.html?q=Koleksi+Empat+Foto+Uji',wait_until='networkidle')
                gallery=buyer.locator('#grid-produk-list [data-product-gallery]');gallery.scroll_into_view_if_needed()
                rect=gallery.locator('[data-product-photo-stage]').bounding_box();x=rect['x']+rect['width']*.65;y=rect['y']+rect['height']*.28
                swipe(buyer,x,y,-60,1);wait_photo(gallery,1);assert '/produk.html' in buyer.url
                swipe(buyer,x-60,y,60,1);wait_photo(gallery,0);assert '/produk.html' in buyer.url
                swipe(buyer,x,y,1,-90);assert gallery.get_attribute('data-photo-index')=='0'
                buyer.goto(base+'produk.html?q=Koleksi+Empat+Foto+Uji',wait_until='networkidle')
                gallery=buyer.locator('#grid-produk-list [data-product-gallery]');gallery.scroll_into_view_if_needed()
                rect=gallery.locator('.product-photo-link').bounding_box()
                buyer.touchscreen.tap(rect['x']+rect['width']*.5,rect['y']+rect['height']*.25)
                buyer.wait_for_url('**/detail.html?id='+str(pid))
                buyer.goto(base,wait_until='networkidle');buyer.locator('[data-collection=apparel]').click()
                home=buyer.locator(f'#grid-trending [data-produk-id="{pid}"] [data-product-gallery]')
                home.locator('.product-photo-next').click();wait_photo(home,1)
                independent=buyer.locator(f'#grid-trending [data-produk-id="{second_id}"] [data-product-gallery]')
                assert independent.get_attribute('data-photo-index')=='0'
                buyer.locator('[data-collection=all]').click();home.locator('.product-photo-next').click();wait_photo(home,1)
                csrf=buyer_context.request.get(base+'api/customer/session').json()['csrf']
                registered=buyer_context.request.post(base+'api/customer/register',data={'nama':'Pembeli Galeri','email':'gallery@example.test','nohp':'081234567890','password':password},headers={'X-CSRF-Token':csrf})
                assert registered.status==201
                assert buyer_context.request.post(base+'api/customer/wishlist',data={'id':pid},headers={'X-CSRF-Token':registered.json()['csrf']}).status==200
                buyer.goto(base+'akun.html#wishlist',wait_until='networkidle')
                saved=buyer.locator(f'#customer-wishlist [data-produk-id="{pid}"] [data-product-gallery]')
                saved.locator('.product-photo-next').click();wait_photo(saved,1)
                # Failure leaves the previous photo and product link intact.
                failed_context=browser.new_context(viewport={'width':390,'height':844},reduced_motion='reduce')
                failed_context.route('**'+expected[1],lambda route:route.abort())
                failed=failed_context.new_page();failed.on('pageerror',lambda error:errors.append(str(error)))
                failed.goto(base+'produk.html?q=Koleksi+Empat+Foto+Uji',wait_until='networkidle')
                failed_gallery=failed.locator('#grid-produk-list [data-product-gallery]');failed_gallery.locator('.product-photo-next').click()
                failed_gallery.locator('.product-gallery-status').get_by_text('Foto belum dapat dimuat.',exact=False).wait_for()
                assert failed_gallery.locator('.product-gallery-image').get_attribute('src')==expected[0]
                failed_gallery.locator('.product-photo-previous').click();wait_photo(failed_gallery,3)
                # A product with one image keeps an ordinary image link and no redundant controls.
                buyer.goto(base+'produk.html',wait_until='networkidle')
                single=buyer.locator('[data-product-gallery]').filter(has_not=buyer.locator('.product-photo-next')).first
                assert single.locator('.product-photo-arrow').count()==0
                assert not errors,errors
                browser.close()
        finally:process.terminate();process.wait(timeout=10)
    print('PASS: admin uploads four files through separate gateway, cover order persists, four real public photos, card/detail arrows and thumbnails, keyboard, real touch swipe without accidental navigation, dynamic homepage filters, single-photo fallback and five viewport sizes; no JavaScript errors')


if __name__=='__main__':main()
