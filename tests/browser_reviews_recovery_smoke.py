"""Exercise review and recovery UI against a disposable store; never sends real mail."""
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
SOURCE='''import json,sys,os,signal
from pathlib import Path
from server import create_owner
from werkzeug.serving import make_server
sys.path.insert(0,'tests')
from browser_backend_support import configure_backend
credentials=json.loads(sys.stdin.readline())
app,cleanup=configure_backend({'RESEND_API_KEY':'re_'+credentials['key'], 'EMAIL_FROM':'akun@example.test', 'PUBLIC_URL':'https://shop.example.test'})
create_owner(app,'owner@example.test',credentials['password'])
def send(email,token):
    directory=Path(os.environ['ANREDSELLER_DATA_DIR'])
    if (directory/'fail-mail').exists():raise RuntimeError('test failure')
    (directory/'outbox.json').write_text(json.dumps({'email':email,'token':token}))
app.extensions['recovery_mailer'].send=send
http=make_server('127.0.0.1',0,app,threaded=True)
print(http.server_port,flush=True)
signal.signal(signal.SIGTERM,lambda *_:sys.exit(0))
try:http.serve_forever()
finally:cleanup()
'''

def run():
    shots=Path(os.environ.get('ANREDSELLER_SCREENSHOT_DIR','/tmp/anredseller-reviews-recovery'))
    shots.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='anredseller-reviews-browser-') as directory:
        password=secrets.token_urlsafe(24);new_password=secrets.token_urlsafe(24)
        with open(Path(directory)/'server.log','w') as log:
            process=subprocess.Popen([str(ROOT/'.venv/bin/python'),'-c',SOURCE],cwd=ROOT,
                env={**os.environ,'ANREDSELLER_DATA_DIR':directory},stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=log,text=True)
            process.stdin.write(json.dumps({'key':secrets.token_urlsafe(24),'password':password})+'\n');process.stdin.flush()
            port=process.stdout.readline().strip()
            assert port.isdigit(), 'Test server failed to start'
            base='http://127.0.0.1:'+port
            try:
                with sync_playwright() as p:
                    browser=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True)
                    buyer=browser.new_context(viewport={'width':390,'height':844},is_mobile=True,has_touch=True,reduced_motion='reduce')
                    guest=browser.new_context(viewport={'width':390,'height':844},reduced_motion='reduce')
                    owner=browser.new_context()
                    page=buyer.new_page();public=guest.new_page();errors=[];checks=[]
                    for tab in [page,public]:tab.on('pageerror',lambda error:errors.append(str(error)))
                    product=guest.request.get(base+'/api/products').json()['products'][0];pid=product['id']
                    detail=base+f'/detail.html?id={pid}#ulasan'
                    public.goto(detail,wait_until='networkidle')
                    assert 'Belum ada rating' in public.locator('#product-review-metrics').inner_text()
                    assert '0 terjual' in public.locator('#product-review-metrics').inner_text()
                    assert public.locator('#product-review-form').count()==0
                    assert 'Masuk untuk memberi rating' in public.locator('#review-editor').inner_text()
                    page.goto(base+'/akun.html',wait_until='networkidle');page.locator('#show-register').click()
                    for field,value in {'name':'Alice Pembeli','phone':'081234567890','email':'alice@example.test','password':password,'confirm':password}.items():
                        page.locator('#buyer-register-'+field).fill(value)
                    page.get_by_role('button',name='Buat akun pembeli',exact=True).click();page.locator('#customer-dashboard').wait_for(state='visible')
                    page.goto(detail,wait_until='networkidle')
                    assert 'setelah pesanan produk ini selesai' in page.locator('#review-editor').inner_text()
                    csrf=buyer.request.get(base+'/api/customer/session').json()['csrf']
                    result=buyer.request.post(base+'/api/orders',data={'customer':{'nama_penerima':'Alice Pembeli','nohp':'081234567890','alamat':'Jl. Uji 1','kota':'Jakarta','provinsi':'DKI Jakarta','kodepos':'12345'},'items':[{'id':pid,'harga':product['harga'],'jumlah':2}]},headers={'X-CSRF-Token':csrf,'Idempotency-Key':secrets.token_hex(16)})
                    assert result.status==201,result.text()
                    number=result.json()['order']['nomor']
                    csrf=owner.request.get(base+'/api/session').json()['csrf']
                    auth=owner.request.post(base+'/api/login',data={'email':'owner@example.test','password':password},headers={'X-CSRF-Token':csrf})
                    owner_headers={'X-CSRF-Token':auth.json()['csrf']}
                    assert owner.request.patch(base+'/api/admin/orders/'+number,data={'status':'selesai'},headers=owner_headers).status==200
                    page.goto(base+'/akun.html#orders',wait_until='networkidle')
                    page.get_by_role('button',name='Lihat rincian',exact=True).click()
                    page.locator('.order-review-links a').wait_for(state='visible')
                    assert page.locator('.order-review-links a').count()==1
                    page.locator('.order-review-links a').click();page.wait_for_url('**/detail.html?id=*#ulasan')
                    page.locator('#product-review-form').wait_for(state='visible')
                    assert '2 terjual' in page.locator('#product-review-metrics').inner_text()
                    page.get_by_role('radio',name='3 bintang',exact=True).check()
                    text='<img src=x onerror=alert(1)> Bahan nyaman.\nUkuran pas.'
                    page.locator('#review-comment').fill(text);page.get_by_role('button',name='Kirim rating',exact=True).click()
                    page.get_by_text('Ratingmu tersimpan. Terima kasih sudah berbagi.',exact=True).wait_for()
                    assert page.locator('#review-list .buyer-review').count()==1
                    assert '<img src=x onerror=alert(1)>' in page.locator('#review-list').inner_text()
                    assert page.locator('#review-list img').count()==0
                    page.get_by_role('radio',name='4 bintang',exact=True).check()
                    page.get_by_role('button',name='Simpan perubahan rating',exact=True).click()
                    page.wait_for_function('() => document.getElementById("review-summary-text").textContent.includes("4.0 / 5")')
                    assert '1 ulasan' in page.locator('#review-summary-text').inner_text()
                    page.reload(wait_until='networkidle')
                    assert page.get_by_role('radio',name='4 bintang',exact=True).is_checked()
                    for width,height in VIEWS:
                        page.set_viewport_size({'width':width,'height':height})
                        assert_layout(page,f'rating {width}x{height}',checks)
                        assert page.locator('.rating-option').first.bounding_box()['width']>=44
                        page.screenshot(path=str(shots/f'reviews-{width}.png'),full_page=True)
                    public.reload(wait_until='networkidle')
                    assert '4.0' in public.locator('#product-review-metrics').inner_text()
                    assert 'A***' in public.locator('#review-list').inner_text()
                    assert 'Alice Pembeli' not in public.locator('#review-list').inner_text()
                    public.goto(base+'/produk.html',wait_until='networkidle')
                    card=public.locator(f'[data-produk-id="{pid}"]')
                    assert '2 terjual' in card.locator('.product-rating-line').inner_text()
                    # Recovery sends only to the local test outbox; no external API/email.
                    public.goto(base+'/akun.html',wait_until='networkidle')
                    public.locator('#buyer-login-email').fill('alice@example.test')
                    public.locator('#show-forgot-password').click()
                    assert public.locator('#buyer-forgot-email').input_value()=='alice@example.test'
                    for width,height in VIEWS:
                        public.set_viewport_size({'width':width,'height':height})
                        assert_layout(public,f'forgot {width}x{height}',checks)
                        public.screenshot(path=str(shots/f'forgot-{width}.png'),full_page=True)
                    public.get_by_role('button',name='Kirim tautan pemulihan',exact=True).click()
                    public.locator('#buyer-forgot-success').wait_for(state='visible')
                    token=json.loads((Path(directory)/'outbox.json').read_text())['token']
                    assert token not in public.content()
                    assert buyer.request.get(base+'/api/customer/profile').status==200
                    reset=browser.new_context(viewport={'width':390,'height':844},reduced_motion='reduce')
                    recovery=reset.new_page();recovery.on('pageerror',lambda error:errors.append(str(error)))
                    recovery.goto(base+'/akun.html#reset='+token,wait_until='networkidle')
                    recovery.locator('#buyer-reset-form').wait_for(state='visible')
                    assert token not in recovery.url
                    assert not recovery.evaluate('(token) => [...Object.values(localStorage),...Object.values(sessionStorage)].some(value=>value.includes(token))',token)
                    for width,height in VIEWS:
                        recovery.set_viewport_size({'width':width,'height':height})
                        assert_layout(recovery,f'reset {width}x{height}',checks)
                        recovery.screenshot(path=str(shots/f'reset-{width}.png'),full_page=True)
                    recovery.locator('#buyer-reset-password').fill(new_password)
                    recovery.locator('#buyer-reset-confirm').fill(password)
                    recovery.get_by_role('button',name='Simpan kata sandi baru',exact=True).click()
                    assert 'Kedua kata sandi harus sama' in recovery.locator('#buyer-reset-error').inner_text()
                    recovery.locator('#buyer-reset-confirm').fill(new_password)
                    recovery.get_by_role('button',name='Simpan kata sandi baru',exact=True).click()
                    recovery.locator('#buyer-reset-success').wait_for(state='visible')
                    assert buyer.request.get(base+'/api/customer/profile').status==401
                    assert reset.request.get(base+'/api/customer/profile').status==401
                    recovery.locator('#buyer-reset-form [data-auth-login]').click()
                    recovery.locator('#buyer-login-email').fill('alice@example.test')
                    recovery.locator('#buyer-login-password').fill(new_password)
                    recovery.get_by_role('button',name='Masuk ke akun',exact=True).click()
                    recovery.locator('#customer-dashboard').wait_for(state='visible')
                    assert reset.request.get(base+'/api/customer/profile').json()['customer']['nama']=='Alice Pembeli'
                    # Reusing the old link fails, and provider failure is shown honestly.
                    public.goto(base+'/akun.html#reset='+token,wait_until='networkidle')
                    public.locator('#buyer-reset-password').fill(secrets.token_urlsafe(24))
                    public.locator('#buyer-reset-confirm').fill(public.locator('#buyer-reset-password').input_value())
                    public.get_by_role('button',name='Simpan kata sandi baru',exact=True).click()
                    public.get_by_text('Tautan tidak valid atau kedaluwarsa. Minta tautan baru.',exact=True).wait_for()
                    public.locator('[data-auth-forgot]').click();public.locator('#buyer-forgot-email').fill('alice@example.test')
                    (Path(directory)/'fail-mail').touch()
                    public.get_by_role('button',name='Kirim tautan pemulihan',exact=True).click()
                    public.get_by_text('Email belum dapat dikirim. Coba lagi nanti atau hubungi CS.',exact=True).wait_for()
                    assert not errors,errors
                    print(f'PASS: verified review creation/edit/persistence, honest sold counts, masked identity/XSS escaping, order review links, recovery email UI, single-use reset/session revocation/relogin/provider errors; {len(checks)} responsive checks. No external emails sent.')
                    browser.close()
            finally:
                process.terminate();process.wait(timeout=10)

if __name__=='__main__':run()
