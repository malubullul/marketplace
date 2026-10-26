"""Exercise the real React 404, hydration, responsive layout and recovery links."""
import os
from pathlib import Path
import subprocess
import tempfile

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
SOURCE = """from server import create_app
from werkzeug.serving import make_server
app = create_app({'TESTING': True, 'DATABASE_URL': ''})
http = make_server('127.0.0.1', 0, app, threaded=True)
print(http.server_port, flush=True)
http.serve_forever()
"""


def main():
    output = Path(os.environ.get('ANREDSELLER_SCREENSHOT_DIR', '/tmp/anredseller-404'))
    output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='anredseller-404-') as directory, open(output / 'server.log', 'w') as log:
        process = subprocess.Popen([str(ROOT / '.venv/bin/python'), '-c', SOURCE], cwd=ROOT,
            env={**os.environ, 'ANREDSELLER_DATA_DIR': directory, 'DATABASE_URL': '', 'VERCEL': ''},
            stdout=subprocess.PIPE, stderr=log, text=True)
        try:
            port = process.stdout.readline().strip()
            assert port.isdigit()
            base = 'http://127.0.0.1:' + port
            with sync_playwright() as p:
                browser = p.chromium.launch(executable_path='/usr/bin/chromium', headless=True)
                context = browser.new_context(viewport={'width':1440,'height':900})
                page = context.new_page()
                errors = []
                page.on('pageerror', lambda error: errors.append(str(error)))
                page.on('console', lambda message: errors.append(message.text) if message.type == 'error' and 'Minified React error' in message.text else None)
                assert page.goto(base + '/koleksi/halaman-hilang', wait_until='networkidle').status == 404
                assert page.locator('h1').count() == 1
                assert page.get_by_role('heading', level=1).inner_text().startswith('Error 404.')
                assert page.get_by_role('link').count() == 2
                assert page.locator('button a, a button').count() == 0
                assert page.locator('svg:not([aria-hidden="true"])').count() == 0
                assert page.locator('body').evaluate('element => getComputedStyle(element).fontFamily').startswith('Switzer')

                for width, height in [(320,568), (390,844), (640,800), (768,1024), (1440,900), (667,375), (844,390)]:
                    page.set_viewport_size({'width':width,'height':height})
                    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth + 1'), width
                    for link in page.get_by_role('link').all():
                        rect = link.bounding_box()
                        assert rect['height'] >= 44 and rect['width'] >= 44, rect
                        assert 0 <= rect['x'] and rect['x'] + rect['width'] <= width + 1
                    page.screenshot(path=str(output / f'404-{width}.png'), full_page=True)

                page.set_viewport_size({'width':390,'height':844})
                page.keyboard.press('Tab')
                assert page.evaluate('document.activeElement.textContent.trim()') == 'Ke beranda'
                assert page.evaluate('getComputedStyle(document.activeElement).boxShadow !== "none"')
                page.keyboard.press('Tab')
                assert page.evaluate('document.activeElement.textContent.trim()') == 'Kembali'

                # Direct visits have no previous store page: the back action opens the catalogue.
                page.get_by_role('link', name='Kembali', exact=True).click()
                page.wait_for_url(base + '/produk.html')
                assert page.locator('#grid-produk-list').count() == 1

                # With a same-origin referrer, the hydrated handler restores the exact prior URL.
                previous = base + '/produk.html?sort=terbaru&kategori=apparel'
                page.goto(previous, wait_until='networkidle')
                page.evaluate("""() => {
                  const link = document.createElement('a'); link.href = '/hilang-lagi';
                  link.textContent = 'Uji tautan hilang'; document.body.prepend(link);
                }""")
                page.get_by_role('link', name='Uji tautan hilang').click()
                page.wait_for_url(base + '/hilang-lagi')
                page.wait_for_load_state('networkidle')
                assert page.evaluate('document.referrer') == previous
                page.get_by_role('link', name='Kembali', exact=True).click()
                page.wait_for_url(previous)

                # An external referring page does not pull the user away from the store.
                external = context.new_page()
                external.route('http://external.example.test/**', lambda route: route.fulfill(
                    content_type='text/html', body=f'<a href="{base}/missing-external">Visit</a>'))
                external.goto('http://external.example.test/')
                external.get_by_role('link', name='Visit').click()
                external.wait_for_load_state('networkidle')
                assert external.evaluate('document.referrer').startswith('http://external.example.test/')
                external.get_by_role('link', name='Kembali', exact=True).click()
                external.wait_for_url(base + '/produk.html')

                page.goto(base + '/404.html', wait_until='networkidle')
                page.get_by_role('link', name='Ke beranda', exact=True).click()
                page.wait_for_url(base + '/')
                assert page.locator('#campaign-carousel').is_visible()

                # SSR keeps both recovery links useful with JavaScript blocked or disabled.
                for javascript_enabled in [True, False]:
                    fallback = browser.new_context(java_script_enabled=javascript_enabled, viewport={'width':320,'height':568}, reduced_motion='reduce')
                    if javascript_enabled:
                        fallback.route('**/js/generated/error-page.js*', lambda route: route.abort())
                    plain = fallback.new_page()
                    assert plain.goto(base + '/nested/missing-page', wait_until='networkidle').status == 404
                    assert plain.get_by_role('heading', level=1).is_visible()
                    assert plain.evaluate('document.documentElement.scrollWidth <= innerWidth + 1')
                    plain.get_by_role('link', name='Kembali', exact=True).click()
                    plain.wait_for_url(base + '/produk.html')
                    fallback.close()
                assert not errors, errors
                browser.close()
        finally:
            process.terminate()
            process.wait(timeout=10)
    print('PASS: real HTTP 404, React hydration, 7 responsive sizes, keyboard focus, home/back navigation, external/direct visit fallback and no-JS/failed-bundle recovery; no React errors or horizontal overflow.')


if __name__ == '__main__':
    main()
