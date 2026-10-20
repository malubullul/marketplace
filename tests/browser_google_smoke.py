"""Google UI workflow using a local RSA-signed provider fixture; no live Google account."""
import json
import os
from pathlib import Path
import secrets
import subprocess
import tempfile
from urllib.parse import parse_qs, urlsplit, urlencode
import base64

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
SOURCE = '''import sys,json,time,base64,threading
from unittest.mock import patch
from flask import Flask
from werkzeug.serving import make_server,WSGIRequestHandler
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from google.auth import crypt,jwt
import requests
from server import create_app
class Quiet(WSGIRequestHandler):
 def log_request(self,*args):pass
http=make_server('127.0.0.1',0,Flask('placeholder'),threaded=True,request_handler=Quiet)
origin=f'http://127.0.0.1:{http.server_port}'
app=create_app({'TESTING':True,'GOOGLE_CLIENT_ID':'browser-tests.apps.googleusercontent.com','GOOGLE_CLIENT_SECRET':'disposable-browser-test-secret','PUBLIC_ORIGIN':origin,'SESSION_COOKIE_SECURE':False})
http.app=app
key=rsa.generate_private_key(public_exponent=65537,key_size=2048)
signer=crypt.RSASigner.from_string(key.private_bytes(serialization.Encoding.PEM,serialization.PrivateFormat.PKCS8,serialization.NoEncryption()))
public=key.public_key().public_bytes(serialization.Encoding.PEM,serialization.PublicFormat.SubjectPublicKeyInfo).decode()
def network(http_session,method,url,**kwargs):
 response=requests.Response();response.status_code=200
 if url=='https://oauth2.googleapis.com/token':
  fixture=json.loads(base64.urlsafe_b64decode(kwargs['data']['code']+'==='));now=int(time.time())
  claims={'iss':'https://accounts.google.com','aud':app.config['GOOGLE_CLIENT_ID'],'iat':now,'exp':now+300,'sub':fixture['subject'],'email':fixture['email'],'name':'Google buyer','email_verified':True,'nonce':fixture['nonce']}
  payload={'id_token':jwt.encode(signer,claims,key_id='fixture-key').decode()}
 elif url=='https://www.googleapis.com/oauth2/v1/certs':payload={'fixture-key':public}
 else:raise AssertionError('Unexpected external request')
 response._content=json.dumps(payload).encode();return response
print(json.dumps({'origin':origin}),flush=True)
with patch('requests.Session.request',autospec=True,side_effect=network):http.serve_forever()
'''


def layout(page):
    return page.evaluate("""()=>({overflow:document.documentElement.scrollWidth>innerWidth,fields:[...document.querySelectorAll('input,button,dialog[open]')].filter(e=>{const r=e.getBoundingClientRect();return r.width>0&&(r.left<0||r.right>innerWidth+1)}).map(e=>e.id)})""")


def run():
    output = Path(os.environ.get('ANREDSELLER_SCREENSHOT_DIR', '/tmp/anredseller-google-browser'))
    output.mkdir(exist_ok=True, parents=True)
    with tempfile.TemporaryDirectory(prefix='anredseller-google-browser-') as directory, open(Path(directory)/'server.log','w') as log:
        process = subprocess.Popen([str(ROOT/'.venv/bin/python'), '-c', SOURCE], cwd=ROOT,
                                   env={**os.environ, 'ANREDSELLER_DATA_DIR':directory}, stdout=subprocess.PIPE, stderr=log, text=True)
        try:
            base = json.loads(process.stdout.readline())['origin']
            with sync_playwright() as p:
                browser = p.chromium.launch(executable_path='/usr/bin/chromium', headless=True)
                context = browser.new_context(viewport={'width':1440,'height':1000}, reduced_motion='reduce')
                page = context.new_page(); errors=[]; page.on('pageerror',lambda error:errors.append(str(error)))
                provider = {'email':'google-buyer@example.test', 'subject':'google-browser-buyer'}
                def authorize(route):
                    params = {k:v[0] for k,v in parse_qs(urlsplit(route.request.url).query).items()}
                    code = base64.urlsafe_b64encode(json.dumps({**provider, 'nonce':params['nonce']}).encode()).rstrip(b'=').decode()
                    route.fulfill(status=302, headers={'location':params['redirect_uri']+'?'+urlencode({'code':code,'state':params['state']})})
                page.route('https://accounts.google.com/o/oauth2/v2/auth?**', authorize)
                page.goto(base+'/akun.html',wait_until='networkidle')
                page.locator('#google-login').wait_for();assert page.locator('#google-login').is_enabled()
                for width,height in [(1440,1000),(768,1024),(390,844),(320,568),(844,390)]:
                    page.set_viewport_size({'width':width,'height':height})
                    assert layout(page)=={'overflow':False,'fields':[]}
                    page.locator('#show-register').click()
                    assert page.locator('#google-login').is_enabled()
                    field=page.locator('#buyer-register-password');field.fill('temporary-visible-check')
                    toggle=page.locator('[aria-controls="buyer-register-password"]')
                    toggle.click();assert field.get_attribute('type')=='text'
                    toggle.click();assert field.get_attribute('type')=='password'
                    field.fill('')
                    page.evaluate('scrollTo(0,0)');page.screenshot(path=str(output/f'register-google-{width}.png'),full_page=True)
                    page.locator('#show-login').click()
                    page.evaluate('scrollTo(0,0)');page.screenshot(path=str(output/f'login-google-{width}.png'),full_page=True)
                page.set_viewport_size({'width':390,'height':844})
                page.locator('#google-login').click();page.locator('#customer-dashboard').wait_for(state='visible')
                assert page.locator('#google-method-status').inner_text()=='Terhubung'
                assert not page.locator('#password-settings').is_visible()
                assert not page.locator('#google-connect').is_visible()
                page.evaluate('scrollTo(0,0)');page.screenshot(path=str(output/'google-account-mobile.png'),full_page=True)
                page.locator('#logout-all-devices').click();page.locator('#customer-auth').wait_for(state='visible')
                # Existing email account: reauthenticate, link only its matching Google identity, then unlink.
                password=secrets.token_urlsafe(24)
                page.locator('#show-register').click()
                for field,value in {'buyer-register-name':'Email buyer','buyer-register-phone':'081234567890','buyer-register-email':'email-buyer@example.test','buyer-register-password':password,'buyer-register-confirm':password}.items():page.locator('#'+field).fill(value)
                page.get_by_role('button',name='Buat akun pembeli',exact=True).click();page.locator('#customer-dashboard').wait_for(state='visible')
                page.locator('#google-connect').click();page.locator('#google-security-dialog').wait_for(state='visible')
                assert layout(page)=={'overflow':False,'fields':[]}
                page.locator('#google-current-password').fill('wrong-password');page.locator('#submit-google-security').click()
                page.locator('#google-security-error').get_by_text('Kata sandi saat ini salah.',exact=True).wait_for()
                provider.update(email='email-buyer@example.test',subject='google-browser-linked')
                page.locator('#google-current-password').fill(password);page.locator('#submit-google-security').click()
                page.locator('#google-method-status').get_by_text('Terhubung',exact=True).wait_for()
                page.locator('#google-connect').click();page.locator('#google-current-password').fill(password)
                page.evaluate('scrollTo(0,0)');page.screenshot(path=str(output/'unlink-google-mobile.png'),full_page=True)
                page.locator('#submit-google-security').click();page.locator('#google-security-dialog').wait_for(state='hidden')
                assert page.locator('#google-method-status').inner_text()=='Belum terhubung'
                assert not errors,errors
                browser.close()
        finally:
            process.terminate();process.wait(timeout=10)
    print('PASS: Google signup/signin UI with real local RSA verification, password visibility, safe linking/unlinking, logout-all and 5 responsive viewports; no live provider or account used')


if __name__=='__main__':run()
