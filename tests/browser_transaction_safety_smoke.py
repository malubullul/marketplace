"""Stage 01 on separate owner/store origins with a disposable email outbox."""
import json
import os
from pathlib import Path
import secrets
import subprocess
import tempfile
from playwright.sync_api import sync_playwright
from browser_store_content_smoke import SOURCE as BASE_SOURCE
from responsive_smoke import assert_layout

ROOT=Path(__file__).resolve().parents[1]
SOURCE=BASE_SOURCE.replace("app,cleanup=configure_backend({'ADMIN_GATEWAY_KEY':key,'ADMIN_PORTAL_URL':'https://owner.example.test'})", """app,cleanup=configure_backend({'ADMIN_GATEWAY_KEY':key,'ADMIN_PORTAL_URL':'https://owner.example.test',
    'EMAIL_VERIFICATION_REQUIRED':True,'RESEND_API_KEY':'re_'+secrets.token_urlsafe(24),
    'EMAIL_FROM':'akun@example.test','PUBLIC_URL':'https://shop.example.test'})
outbox=[]
app.extensions['recovery_mailer'].send_verification=lambda email,token:outbox.append({'email':email,'token':token})
@app.get('/__test_outbox')
def test_outbox():return {'messages':outbox}
""")


def main():
    shots=Path(os.environ.get('ANREDSELLER_SCREENSHOT_DIR','/tmp/anredseller-transactions'));shots.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='anredseller-transactions-') as directory, open(shots/'server.log','w') as log:
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
                owner.locator('[data-page=transactions]').click();owner.locator('#save-transaction-settings:enabled').wait_for()
                assert 'ya' in owner.locator('#email-verification-readiness').inner_text()
                owner.locator('#deadline-enabled').check();owner.locator('#payment-hours').fill('1');owner.locator('#save-transaction-settings').click()
                owner.get_by_text('Ketentuan tersimpan dan berlaku untuk pesanan baru.',exact=True).wait_for()
                for width,height in [(320,568),(390,844),(768,1024),(1440,1000),(844,390)]:
                    owner.set_viewport_size({'width':width,'height':height});assert_layout(owner,'transaction settings '+str(width),checks)
                    owner.screenshot(path=str(shots/f'settings-{width}.png'),full_page=True)

                buyer.goto(base+'/akun.html',wait_until='networkidle');buyer.locator('#show-register').click()
                assert buyer.locator('#buyer-register-password').is_hidden()
                buyer.locator('#buyer-register-email').fill('buyer@example.test');buyer.locator('#buyer-register-form [type=submit]').click()
                buyer.locator('#buyer-register-success').get_by_text('Jika alamat ini dapat digunakan',exact=False).wait_for()
                token=buyer.request.get(base+'/__test_outbox').json()['messages'][-1]['token']
                assert not buyer.request.get(base+'/api/customer/session').json()['authenticated']
                buyer.goto(base+'/akun.html#verify='+token,wait_until='networkidle')
                buyer.locator('#buyer-verify-form').wait_for(state='visible')
                assert '#verify' not in buyer.url
                for field,value in {'verify-name':'Buyer Verified','verify-phone':'081234567890','verify-password':password,'verify-confirm':password}.items():buyer.locator('#'+field).fill(value)
                assert_layout(buyer,'verification form',checks);buyer.screenshot(path=str(shots/'verification-mobile.png'),full_page=True)
                buyer.locator('#buyer-verify-form [type=submit]').click();buyer.get_by_text('Email terverifikasi. Semua sesi lama telah keluar.',exact=False).wait_for()
                buyer.locator('#buyer-verify-form [data-auth-login]').click()
                buyer.locator('#buyer-login-email').fill('buyer@example.test');buyer.locator('#buyer-login-password').fill(password);buyer.locator('#buyer-login-form [type=submit]').click()
                buyer.locator('#customer-dashboard').wait_for(state='visible')
                assert buyer.request.get(base+'/api/customer/session').json()['customer']['email_verified']
                product=buyer.request.get(base+'/api/products').json()['products'][0]
                buyer.evaluate("id=>customerRequest('/cart',{method:'POST',body:{action:'add',id,jumlah:1}})",product['id'])
                buyer.goto(base+'/checkout.html',wait_until='networkidle')
                buyer.get_by_text('Bayar dalam 1 jam',exact=False).wait_for()
                for field,value in {'nama-penerima':'Buyer','nohp':'081234567890','alamat':'Jalan Uji 1','kota':'Jakarta','provinsi':'DKI Jakarta','kodepos':'12345'}.items():buyer.locator('#'+field).fill(value)
                buyer.locator('#btn-pesan').click();buyer.wait_for_url('**/konfirmasi.html?order=*')
                buyer.locator('[data-order-action=payment]').wait_for();number=buyer.locator('#nomor-pesanan').inner_text()
                for width,height in [(320,568),(390,844),(768,1024),(1440,1000),(844,390)]:
                    buyer.set_viewport_size({'width':width,'height':height});assert_layout(buyer,'payment report '+str(width),checks)
                    buyer.screenshot(path=str(shots/f'receipt-{width}.png'),full_page=True)
                buyer.locator('[data-order-action=payment]').click();buyer.get_by_text('Transfer dilaporkan · menunggu pemeriksaan',exact=False).first.wait_for()
                assert buyer.locator('[data-order-action=cancel]').count()==0
                owner.set_viewport_size({'width':1440,'height':1000});owner.locator('[data-page=orders]').click();owner.locator('#refresh-orders').click()
                owner.locator('[data-order="'+number+'"]').click()
                owner.get_by_text('Tambah catatan (opsional)',exact=True).click()
                owner.locator('#payment-reference').fill('Fixture PRIVATE bank reference')
                for width,height in [(320,568),(390,844),(768,1024),(1440,1000),(844,390)]:
                    owner.set_viewport_size({'width':width,'height':height});assert_layout(owner,'payment dialog '+str(width),checks)
                    owner.screenshot(path=str(shots/f'payment-{width}.png'))
                owner.get_by_role('button',name='Tandai sudah dibayar',exact=True).click()
                for width,height in [(320,568),(390,844),(768,1024),(1440,1000),(844,390)]:
                    owner.set_viewport_size({'width':width,'height':height});assert_layout(owner,'payment confirmation '+str(width),checks)
                    owner.locator('[data-payment-confirm]').scroll_into_view_if_needed()
                    owner.screenshot(path=str(shots/f'confirmation-{width}.png'))
                owner.get_by_role('button',name='Konfirmasi',exact=True).click()
                owner.get_by_role('heading',name='Sudah dibayar',exact=True).wait_for()
                record=owner.request.get(admin+'/api/admin/orders/'+number+'/history').json()['payment_record']
                assert record['reference']=='Fixture PRIVATE bank reference' and record['verified_by'] and record['verified_at']

                owner.locator('#close-order').click()
                for status in ['diproses','dikirim','selesai']:
                    owner.locator('[data-order-status="'+number+'"]').select_option(status)
                    owner.wait_for_function('(status)=>orders.some(order=>order.status===status)',arg=status)
                receipt=buyer.request.get(base+'/api/customer/orders/'+number).json()['order']
                assert receipt['status']=='selesai' and receipt['payment']['status']=='verified'
                assert 'PRIVATE' not in json.dumps(receipt) and 'verified_by' not in json.dumps(receipt)
                owner.locator('[data-page=activity]').click();owner.locator('#activity-list').get_by_text('Pembayaran ditandai sudah dibayar',exact=True).wait_for()
                assert_layout(owner,'activity',checks);owner.screenshot(path=str(shots/'activity.png'),full_page=True)
                first=owner.request.get(admin+'/api/admin/activity?limit=1').json()
                second=owner.request.get(admin+'/api/admin/activity?limit=1&cursor='+first['next_cursor']).json()
                assert len(first['events'])==1 and first['events'][0]['id']!=second['events'][0]['id']
                buyer.goto(base+'/akun.html#orders',wait_until='networkidle')
                buyer.locator('[data-customer-order="'+number+'"]').click()
                buyer.get_by_text('Sudah dibayar',exact=True).wait_for()
                assert buyer.locator('[data-order-action=cancel]').count()==0
                buyer.locator('#close-customer-order').click()
                buyer.evaluate("id=>customerRequest('/cart',{method:'POST',body:{action:'add',id,jumlah:1}})",product['id'])
                buyer.goto(base+'/checkout.html',wait_until='networkidle')
                for field,value in {'nama-penerima':'Buyer','nohp':'081234567890','alamat':'Jalan Uji 1','kota':'Jakarta','provinsi':'DKI Jakarta','kodepos':'12345'}.items():buyer.locator('#'+field).fill(value)
                buyer.locator('#btn-pesan').click();buyer.wait_for_url('**/konfirmasi.html?order=*')
                buyer.once('dialog',lambda dialog:dialog.accept());buyer.locator('[data-order-action=cancel]').click()
                buyer.get_by_role('heading',name='Pesanan dibatalkan.',exact=True).wait_for()
                assert buyer.locator('#payment-next-step').is_hidden() and buyer.locator('[data-order-action=payment]').count()==0
                assert not errors,errors
                browser.close()
        finally:process.terminate();process.wait(timeout=10)
    print(f'PASS: email-first signup and verification, separate owner/store origins, deadline settings, checkout terms, buyer transfer report, private owner verification, sequential fulfillment and audit log; {len(checks)} responsive checks; no real email or WhatsApp sent.')


if __name__=='__main__':main()
