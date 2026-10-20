"""Real owner/public origins; content publishing, removals and footer links. No external navigation."""
import json
import os
from pathlib import Path
import secrets
import subprocess
import tempfile
from playwright.sync_api import sync_playwright
from responsive_smoke import assert_layout

ROOT=Path(__file__).resolve().parents[1]
VIEWS=[(320,568),(390,844),(768,1024),(1440,1000),(844,390)]
SOURCE='''import sys,json,secrets,signal,threading
from server import create_owner
from werkzeug.serving import make_server
sys.path.insert(0,'tests')
from browser_backend_support import configure_backend
credentials=json.loads(sys.stdin.readline());key=secrets.token_urlsafe(40)
app,cleanup=configure_backend({'ADMIN_GATEWAY_KEY':key,'ADMIN_PORTAL_URL':'https://owner.example.test'})
create_owner(app,'owner@example.test',credentials['password'])
http=make_server('127.0.0.1',0,app,threaded=True)
sys.path.insert(0,'admin-portal')
from app import create_app
portal=create_app({'BACKEND_URL':f'http://127.0.0.1:{http.server_port}','SHOP_URL':f'http://127.0.0.1:{http.server_port}','ADMIN_GATEWAY_KEY':key,'SECURE_COOKIES':False})
admin=make_server('127.0.0.1',0,portal,threaded=True)
app.config['ADMIN_PORTAL_URL']=f'http://localhost:{admin.server_port}'
threading.Thread(target=admin.serve_forever,daemon=True).start()
print(json.dumps({'store':http.server_port,'admin':admin.server_port}),flush=True)
signal.signal(signal.SIGTERM,lambda *_:sys.exit(0))
try:http.serve_forever()
finally:cleanup()
'''

def run():
    shots=Path(os.environ.get('ANREDSELLER_SCREENSHOT_DIR','/tmp/anredseller-store-content'));shots.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='anredseller-content-browser-') as directory, open(Path(directory)/'server.log','w') as log:
        password=secrets.token_urlsafe(24)
        process=subprocess.Popen([str(ROOT/'.venv/bin/python'),'-c',SOURCE],cwd=ROOT,env={**os.environ,'ANREDSELLER_DATA_DIR':directory},stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=log,text=True)
        process.stdin.write(json.dumps({'password':password})+'\n');process.stdin.flush()
        ports=json.loads(process.stdout.readline());base=f"http://127.0.0.1:{ports['store']}";admin_base=f"http://localhost:{ports['admin']}"
        try:
            with sync_playwright() as p:
                browser=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True)
                admin_context=browser.new_context(viewport={'width':1440,'height':1000},reduced_motion='reduce')
                public_context=browser.new_context(viewport={'width':390,'height':844},is_mobile=True,has_touch=True,reduced_motion='reduce')
                owner=admin_context.new_page();shop=public_context.new_page();errors=[];checks=[]
                for page in [owner,shop]:page.on('pageerror',lambda error:errors.append(str(error)))
                shop.goto(base,wait_until='networkidle')
                assert shop.locator('#footer-socials').is_hidden()
                assert shop.locator('[data-campaign]').count()==5
                assert public_context.request.get(base+'/api/admin/content').status==401
                assert admin_context.request.get(admin_base+'/api/store/content').status==404
                owner.goto(admin_base,wait_until='networkidle')
                owner.locator('#login-email').fill('owner@example.test');owner.locator('#login-password').fill(password)
                owner.locator('#login-button').click();owner.locator('#dashboard').wait_for(state='visible')
                owner.locator('[data-page=settings]').click()
                owner.locator('#payment-whatsapp').fill('087729766809');owner.locator('#support-whatsapp').fill('082335963140')
                owner.locator('#save-contacts').click();owner.get_by_text('Kontak tersimpan. Tautan WhatsApp di toko mengikuti nomor ini.',exact=True).wait_for()
                assert public_context.request.get(base+'/api/store/contacts').json()['contacts']=={'payment_whatsapp':'6287729766809','support_whatsapp':'6282335963140'}
                owner.locator('[data-page=appearance]').click()
                owner.locator('[data-site-slot=campaign_archive]').wait_for()
                assert owner.locator('[data-site-slot]').count()==9
                for width,height in VIEWS:
                    owner.set_viewport_size({'width':width,'height':height});assert_layout(owner,f'admin images {width}',checks)
                    owner.screenshot(path=str(shots/f'admin-images-{width}.png'),full_page=True)
                owner.set_viewport_size({'width':1440,'height':1000})
                urls={}
                for key in ['campaign_archive','category_apparel','reseller_banner','account_editorial']:
                    owner.locator('#site-file-'+key).set_input_files(str(ROOT/'assets/shirt.png'))
                    owner.get_by_text('Foto berhasil diunggah. Simpan perubahan gambar untuk menerbitkannya.',exact=True).wait_for()
                    urls[key]=owner.locator(f'[data-site-slot={key}] img').get_attribute('src')
                    assert urls[key].startswith('/uploads/')
                owner.locator('#site-alt-campaign_archive').fill('Koleksi editorial milik toko')
                owner.locator('#site-position-campaign_archive').evaluate('(element)=>{element.value=25;element.dispatchEvent(new Event("input",{bubbles:true}));}')
                assert public_context.request.get(base+'/api/store/content').json()['content']['images']['campaign_archive']['src']=='assets/archive-campaign.webp'
                for key in ['campaign_after_hours','campaign_soft_form','campaign_objects','category_sneakers']:
                    owner.locator(f'[data-site-remove={key}]').click()
                owner.locator('#save-site-images').click()
                owner.get_by_text('Gambar tersimpan. Muat ulang toko publik untuk melihat perubahan.',exact=True).wait_for()
                shop.reload(wait_until='networkidle')
                assert shop.locator('#campaign-image').get_attribute('src')==urls['campaign_archive']
                assert shop.locator('#campaign-image').get_attribute('alt')=='Koleksi editorial milik toko'
                assert shop.locator('#campaign-image').evaluate('(element)=>getComputedStyle(element).objectPosition')=='25% 50%'
                assert shop.locator('[data-campaign]').count()==2
                assert shop.locator('#campaign-total').inner_text()=='02'
                assert shop.locator('.sneakers-edit img').is_hidden()
                assert shop.locator('.apparel-edit img').get_attribute('src')==urls['category_apparel']
                assert shop.locator('.reseller-photo').get_attribute('src')==urls['reseller_banner']
                shop.locator('.campaign-next').click();shop.wait_for_function('() => document.querySelector("#campaign-carousel").dataset.campaignIndex === "1"')
                assert shop.locator('#campaign-image').get_attribute('src')=='assets/campaign-city-uniform.webp'
                # Account photograph and no-JavaScript SSR also respect the owner snapshot.
                shop.goto(base+'/akun.html',wait_until='networkidle')
                assert shop.locator('.account-editorial-photo').get_attribute('src')==urls['account_editorial']
                owner.locator('[data-page=socials]').click();owner.locator('#site-social-instagram').wait_for()
                for key,value in {'instagram':'https://www.instagram.com/anredseller/','tiktok':'https://www.tiktok.com/@anredseller','other_label':'Pinterest','other_url':'https://www.pinterest.com/anredseller/'}.items():owner.locator('#site-social-'+key).fill(value)
                owner.locator('#save-site-socials').click();owner.get_by_text('Media sosial tersimpan. Tautan yang terisi kini tampil di footer toko publik.',exact=True).wait_for()
                for width,height in VIEWS:
                    owner.set_viewport_size({'width':width,'height':height});assert_layout(owner,f'admin socials {width}',checks)
                    owner.screenshot(path=str(shots/f'admin-socials-{width}.png'),full_page=True)
                shop.goto(base,wait_until='networkidle');shop.locator('#footer-socials').wait_for(state='visible')
                assert shop.locator('#footer-social-links a').count()==3
                for link in shop.locator('#footer-social-links a').all():
                    assert link.get_attribute('target')=='_blank';assert 'noopener' in link.get_attribute('rel')
                    assert link.get_attribute('href').startswith('https://')
                assert 'Facebook' not in shop.locator('#footer-social-links').inner_text()
                for width,height in VIEWS:
                    shop.set_viewport_size({'width':width,'height':height});assert_layout(shop,f'public custom images/footer {width}',checks)
                    shop.locator('.footer-wordmark').scroll_into_view_if_needed()
                    shop.wait_for_function('() => document.querySelector(".support-launcher").classList.contains("support-docked")')
                    assert shop.locator('.support-launcher').evaluate('(element)=>getComputedStyle(element).position')=='absolute'
                    shop.screenshot(path=str(shots/f'footer-{width}.png'))
                # Unsafe link errors do not publish, and removing a link hides it after reload.
                owner.locator('#site-social-instagram').fill('http://www.instagram.com/name')
                owner.locator('#save-site-socials').click()
                owner.locator('#site-socials-result.error').wait_for(state='visible')
                assert public_context.request.get(base+'/api/store/content').json()['content']['socials']['instagram']=='https://www.instagram.com/anredseller/'
                owner.locator('#site-social-instagram').fill('');owner.locator('#save-site-socials').click()
                owner.locator('#site-socials-result:not(.error)').wait_for(state='visible')
                shop.reload(wait_until='networkidle');assert shop.locator('#footer-social-links a').count()==2
                owner.locator('[data-page=appearance]').click()
                for key in ['campaign_archive','campaign_city','account_editorial','reseller_banner']:
                    owner.locator(f'[data-site-remove={key}]').click()
                owner.locator('#save-site-images').click()
                owner.get_by_text('Gambar tersimpan. Muat ulang toko publik untuk melihat perubahan.',exact=True).wait_for()
                shop.goto(base,wait_until='networkidle')
                assert shop.locator('#campaign-image').is_hidden()
                assert shop.locator('.campaign-arrows').is_hidden()
                assert shop.locator('.campaign-pagination').is_hidden()
                assert shop.locator('#campaign-title').is_visible()
                assert shop.locator('.reseller-photo').is_hidden()
                for width,height in VIEWS:
                    shop.set_viewport_size({'width':width,'height':height});assert_layout(shop,f'no campaign photos {width}',checks)
                    shop.evaluate('scrollTo(0,0)');shop.screenshot(path=str(shots/f'no-hero-{width}.png'))
                shop.goto(base+'/akun.html',wait_until='networkidle')
                assert shop.locator('.account-editorial-photo').count()==0
                assert 'url(' not in shop.locator('.account-editorial').evaluate('(element)=>getComputedStyle(element).backgroundImage')
                for width,height in VIEWS:
                    shop.set_viewport_size({'width':width,'height':height});assert_layout(shop,f'no account photo {width}',checks)
                owner.locator('[data-site-restore=campaign_archive]').click();owner.locator('#save-site-images').click()
                owner.get_by_text('Gambar tersimpan. Muat ulang toko publik untuk melihat perubahan.',exact=True).wait_for()
                shop.goto(base,wait_until='networkidle')
                assert shop.locator('#campaign-image').get_attribute('src')=='assets/archive-campaign.webp'
                assert shop.locator('.campaign-arrows').is_hidden()
                assert shop.locator('[data-campaign]').count()==1
                nojs=browser.new_context(java_script_enabled=False,viewport={'width':390,'height':844})
                document=nojs.new_page();document.goto(base,wait_until='networkidle')
                assert document.locator('#campaign-image').get_attribute('src')=='assets/archive-campaign.webp'
                assert document.locator('.sneakers-edit img').is_hidden()
                # Login and edited settings survive reloading the separate owner origin.
                owner.reload(wait_until='networkidle');owner.locator('[data-site-slot]').first.wait_for()
                assert owner.locator('[data-site-slot=campaign_archive] img').get_attribute('src')=='assets/archive-campaign.webp'
                assert not errors,errors
                print(f'PASS: separate admin/store origins, editable WhatsApp, 9 managed image slots, actual uploads, draft publication, dynamic 2/1/0-slide carousel, persisted removals/restore, account/category/banner photos, empty/social-link footer, HTTPS validation and no-JS SSR; {len(checks)} layout checks. No external links opened.')
                browser.close()
        finally:
            process.terminate();process.wait(timeout=10)

if __name__=='__main__':run()
