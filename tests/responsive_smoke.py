"""Check populated storefront layouts with Playwright and disposable data.

Run: python3 tests/responsive_smoke.py
Screenshots: ANREDSELLER_SCREENSHOT_DIR=/path/to/output
"""
import json
import os
from pathlib import Path
import secrets
import subprocess
import tempfile

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
VIEWPORTS = [(320, 568), (360, 640), (375, 667), (390, 844), (414, 896),
             (430, 932), (600, 960), (760, 1024), (768, 1024), (820, 1180),
             (1024, 768), (1440, 1000), (667, 375), (844, 390)]


def assert_layout(page, label, checks):
    result = page.evaluate("""() => {
      const visible = e => !!(e.getClientRects().length && e.getBoundingClientRect().width);
      const outside = e => {
        const r = e.getBoundingClientRect();
        return r.left < -1 || r.right > innerWidth + 1;
      };
      const fields = [...document.querySelectorAll('input:not([type=hidden]),select,textarea')]
        .filter(visible).filter(outside).map(e => e.id || e.name);
      const header = [...document.querySelectorAll('.store-header-inner > .wordmark,.store-actions .icon-button,.mobile-menu')]
        .filter(visible).map(e => ({name:e.getAttribute('aria-label'),r:e.getBoundingClientRect()}));
      const overlaps=[];
      header.forEach((a,i)=>header.slice(i+1).forEach(b=>{
        if(Math.min(a.r.right,b.r.right)-Math.max(a.r.left,b.r.left)>1 &&
           Math.min(a.r.bottom,b.r.bottom)-Math.max(a.r.top,b.r.top)>1)
          overlaps.push([a.name,b.name]);
      }));
      const dialogs=[...document.querySelectorAll('dialog[open]')].map(e=>({
        id:e.id||e.className, clipped:outside(e), overflow:e.scrollWidth>e.clientWidth+1,
        tall:e.getBoundingClientRect().height>innerHeight+1
      })).filter(e=>e.clipped||e.overflow||e.tall);
      return {width:innerWidth, doc:document.documentElement.scrollWidth, fields, overlaps, dialogs};
    }""")
    assert result['doc'] <= result['width'] + 1, (label, result)
    assert not any(result[key] for key in ['fields', 'overlaps', 'dialogs']), (label, result)
    checks.append(label)


def assert_hero(page):
    # The known subjects occupy x=54–92% of this campaign asset. Both must fit
    # inside the mobile crop, and campaign text must follow the image frame.
    frame = page.locator('.campaign-photo').bounding_box()
    copy = page.locator('.campaign-copy').bounding_box()
    image = page.locator('.campaign-photo img')
    size = image.evaluate('(e) => [e.naturalWidth,e.naturalHeight]')
    scale = max(frame['width'] / size[0], frame['height'] / size[1])
    crop_left = (size[0] * scale - frame['width']) * .90
    assert .54 * size[0] * scale >= crop_left, 'Left model is cropped'
    assert .92 * size[0] * scale <= crop_left + frame['width'], 'Right model is cropped'
    assert copy['y'] >= frame['y'] + frame['height'] - 33, 'Copy covers the models'
    assert frame['y'] >= page.locator('.store-header-inner').bounding_box()['height'], 'Photo under masthead'


def run():
    screenshots = Path(os.environ.get('ANREDSELLER_SCREENSHOT_DIR', '/tmp/anredseller-responsive'))
    screenshots.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='anredseller-responsive-') as directory:
        password = secrets.token_urlsafe(24)
        source = '''import json,sys
from server import app,create_owner
from werkzeug.serving import make_server
create_owner(app,'owner@example.test',sys.stdin.readline().strip())
with app.app_context():
    db=app.get_db()
    row=db.execute('SELECT id,document FROM products ORDER BY id LIMIT 1').fetchone()
    product=json.loads(row['document'])
    product['nama']='Jaket Suede Koleksi Terbatas ' + 'Anredseller'*9
    product['brand']='Anredseller'*6
    product['deskripsi']='Detail bahan dan perawatan. ' + 'DeskripsiPanjang'*12
    db.execute('UPDATE products SET document=? WHERE id=?',(json.dumps(product),row['id']))
    db.commit()
http=make_server('127.0.0.1',0,app,threaded=True)
print(http.server_port,flush=True)
http.serve_forever()
'''
        with open(Path(directory) / 'server.log', 'w') as log:
            process = subprocess.Popen(
                [str(ROOT / '.venv/bin/python'), '-c', source], cwd=ROOT,
                env={**os.environ, 'ANREDSELLER_DATA_DIR': directory},
                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=log, text=True)
            process.stdin.write(password + '\n')
            process.stdin.flush()
            port = process.stdout.readline().strip()
            if not port.isdigit():
                raise RuntimeError('Responsive test server did not start')
            base = 'http://127.0.0.1:' + port
            try:
                with sync_playwright() as p:
                    browser = p.chromium.launch(executable_path='/usr/bin/chromium', headless=True)
                    mobile = dict(is_mobile=True, has_touch=True, device_scale_factor=2,
                                  viewport={'width':390,'height':844}, reduced_motion='reduce')
                    buyer, owner, guest = [browser.new_context(**mobile) for _ in range(3)]
                    errors, checks = [], []
                    csrf = buyer.request.get(base + '/api/customer/session').json()['csrf']
                    email = 'mobile.' + 'address'*10 + '@example.test'
                    response = buyer.request.post(base + '/api/customer/register', data={
                        'email':email, 'nama':'Pelanggan' + 'NamaPanjang'*10,
                        'nohp':'081234567890', 'password':password}, headers={'X-CSRF-Token':csrf})
                    assert response.status == 201, response.text()
                    headers = {'X-CSRF-Token':response.json()['csrf']}
                    products = buyer.request.get(base + '/api/products').json()['products']
                    product = next(item for item in products if item['nama'].startswith('Jaket Suede Koleksi'))
                    pid = product['id']
                    address = {'label':'Alamat Pengiriman Jakarta Selatan', 'nama_penerima':'Penerima Pesanan Mobile',
                               'nohp':'081234567890', 'alamat':'Jl. Pengujian Nomor 123, Blok A, Kecamatan Kebayoran Baru',
                               'kota':'Jakarta Selatan', 'provinsi':'DKI Jakarta', 'kodepos':'12345'}
                    assert buyer.request.post(base + '/api/customer/addresses', data=address, headers=headers).status == 201
                    item = {'id':pid, 'jumlah':1, 'ukuran':'', 'warna':'', 'harga':product['harga']}
                    response = buyer.request.post(base + '/api/orders', data={
                        'customer':{'nama':'Pembeli', 'email':email, **address}, 'items':[item]},
                        headers={**headers, 'Idempotency-Key':secrets.token_hex(16)})
                    assert response.status == 201, response.text()
                    number = response.json()['order']['nomor']
                    assert buyer.request.post(base + '/api/customer/cart', data={'action':'add', **item}, headers=headers).status == 200
                    assert buyer.request.post(base + '/api/customer/wishlist', data={'id':pid}, headers=headers).status == 200
                    csrf = owner.request.get(base + '/api/session').json()['csrf']
                    assert owner.request.post(base + '/api/login', data={
                        'email':'owner@example.test', 'password':password}, headers={'X-CSRF-Token':csrf}).status == 200
                    cases = [('home',guest,'/'), ('catalog',guest,'/produk.html'),
                             ('detail',guest,f'/detail.html?id={pid}'), ('login',guest,'/akun.html'),
                             ('admin-login',guest,'/admin.html'), ('profile',buyer,'/akun.html'),
                             ('addresses',buyer,'/akun.html#addresses'), ('orders',buyer,'/akun.html#orders'),
                             ('wishlist',buyer,'/akun.html#wishlist'), ('cart',buyer,'/keranjang.html'),
                             ('checkout',buyer,'/checkout.html'), ('confirmation',buyer,'/konfirmasi.html?order='+number),
                             ('admin',owner,'/admin.html')]
                    for name, context, path in cases:
                        page = context.new_page()
                        page.on('pageerror', lambda error: errors.append(str(error)))
                        page.goto(base + path, wait_until='networkidle')
                        for width, height in VIEWPORTS:
                            page.set_viewport_size({'width':width, 'height':height})
                            # Wait for the normal image/card transitions to settle.
                            page.wait_for_timeout(40)
                            assert_layout(page, f'{name} {width}x{height}', checks)
                            if name == 'home' and width <= 760:
                                assert_hero(page)
                            if (width, height) in [(390,844), (1440,1000)]:
                                page.screenshot(path=str(screenshots / f'{name}-{width}.png'), full_page=True)
                                if name == 'home':
                                    page.screenshot(path=str(screenshots / f'landing-{width}.png'))
                        # Test expanded layouts as well as the initial page.
                        for width, height in [(320,568), (390,844), (667,375), (844,390), (1440,1000)]:
                            page.set_viewport_size({'width':width, 'height':height})
                            page.evaluate('window.scrollTo(0,0)')
                            if name in ['home','catalog']:
                                menu = page.get_by_role('button', name='Buka menu', exact=True)
                                if menu.is_visible():
                                    menu.click()
                                    assert_layout(page, f'{name} menu {width}x{height}', checks)
                                    nav = page.locator('.desktop-nav.mobile-open')
                                    assert nav.bounding_box()['y'] + nav.bounding_box()['height'] <= height + 1, (name, width, height, nav.bounding_box())
                                    nav.locator('a,button').last.scroll_into_view_if_needed()
                                    assert nav.locator('a,button').last.is_visible()
                                    page.keyboard.press('Escape')
                                page.get_by_role('button', name='Cari produk', exact=True).click()
                                page.locator('.store-dialog').wait_for(state='visible')
                                assert_layout(page, f'{name} search {width}x{height}', checks)
                                page.locator('.dialog-search input').fill('jaket')
                                page.locator('.dialog-close').click()
                            elif name == 'login':
                                page.locator('#show-register').click()
                                assert_layout(page, f'registration {width}x{height}', checks)
                            elif name == 'detail' and width <= 760:
                                page.evaluate("tampilToast('Produk ' + 'NamaProdukPanjang'.repeat(10) + ' ditambahkan ke keranjang')")
                                page.wait_for_function("() => document.querySelector('.toast').getBoundingClientRect().right <= innerWidth")
                                bounds = page.locator('.toast').last.bounding_box()
                                assert bounds['x'] >= 15 and bounds['x'] + bounds['width'] <= width - 15
                                assert_layout(page, f'notification {width}x{height}', checks)
                                page.locator('#toast-container').evaluate('(e) => e.remove()')
                            elif name == 'addresses':
                                page.locator('#add-address').click()
                                assert_layout(page, f'address editor {width}x{height}', checks)
                                page.locator('#close-address').click()
                            elif name == 'orders':
                                page.get_by_role('button', name='Lihat rincian', exact=True).click()
                                page.locator('#customer-order-dialog').wait_for(state='visible')
                                assert_layout(page, f'customer receipt {width}x{height}', checks)
                                page.locator('#close-customer-order').click()
                            elif name == 'wishlist' and width <= 760:
                                page.get_by_role('button', name='Buka menu', exact=True).click()
                                page.locator('.desktop-nav [data-dialog="wishlist"]').click()
                                page.locator('.store-dialog').wait_for(state='visible')
                                assert_layout(page, f'wishlist dialog {width}x{height}', checks)
                                page.locator('.dialog-close').click()
                            elif name == 'admin':
                                page.locator('#add-product').click()
                                assert_layout(page, f'product editor {width}x{height}', checks)
                                page.locator('#close-editor').click()
                                page.locator('[data-page="orders"]').click()
                                page.get_by_role('button', name='Lihat pesanan', exact=True).click()
                                page.locator('#order-dialog').wait_for(state='visible')
                                assert_layout(page, f'owner receipt {width}x{height}', checks)
                                page.locator('#close-order').click()
                                page.locator('[data-page="products"]').click()
                        page.close()
                    assert not errors, errors
                    print(f'PASS: {len(checks)} responsive checks across {len(cases)} pages/states and {len(VIEWPORTS)} viewport sizes; portrait hero framing, touch menus, search, registration, address/product editors and private receipts; long product names, profile names, email and shipping address.')
                    browser.close()
            finally:
                process.terminate()
                process.wait(timeout=10)


if __name__ == '__main__':
    run()
