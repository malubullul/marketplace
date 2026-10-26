"""Verify the homepage's progressive parallax without changing campaign framing."""
import os
from pathlib import Path
import subprocess
import tempfile

from playwright.sync_api import sync_playwright

from browser_campaign_smoke import wait_slide
from responsive_smoke import assert_hero


ROOT = Path(__file__).resolve().parents[1]
SOURCE = '''from server import create_app, public_html
from store_content import CAMPAIGNS, default_content, public_content
from werkzeug.serving import make_server
app = create_app({'TESTING': True, 'DATABASE_URL': ''})
@app.get('/__parallax_no_photo')
def no_photo():
    content = default_content()
    for slide in CAMPAIGNS:
        content['images'][slide['id']]['src'] = ''
    return public_html('index.html', public_content(content))
http = make_server('127.0.0.1', 0, app, threaded=True)
print(http.server_port, flush=True)
http.serve_forever()
'''


def geometry(page):
    return page.evaluate('''() => {
      const read = selector => {
        const element = document.querySelector(selector);
        const style = getComputedStyle(element);
        const rect = element.getBoundingClientRect();
        const matrix = new DOMMatrixReadOnly(style.transform);
        return {x: rect.x, y: rect.y + scrollY, width: rect.width,
          height: rect.height, shift: matrix.m42, scaleX: matrix.m11,
          scaleY: matrix.m22, position: style.objectPosition};
      };
      return {image: read('#campaign-image'),
        outgoing: read('.campaign-image-outgoing'), copy: read('.campaign-copy'),
        previous: read('.campaign-previous'), next: read('.campaign-next'),
        pagination: read('.campaign-pagination'), hero: read('#campaign-carousel'),
        scroll: scrollY, overflow: document.documentElement.scrollWidth > innerWidth + 1};
    }''')


def scroll_to(page, top):
    page.evaluate('top => scrollTo({top, behavior: "instant"})', top)
    page.wait_for_function('top => Math.abs(scrollY - top) < 1', arg=top)


def settled_screenshot(page, path):
    page.wait_for_function('''() => document.getAnimations().every(animation =>
      animation.playState !== 'running' || animation.effect.getTiming().iterations === Infinity)''')
    page.screenshot(path=str(path))


def wait_static(page):
    page.wait_for_function('''() => ['#campaign-image', '.campaign-image-outgoing', '.campaign-copy']
      .every(selector => Math.abs(new DOMMatrixReadOnly(getComputedStyle(
        document.querySelector(selector)).transform).m42) < .1)''')


def assert_static(page):
    wait_static(page)
    state = geometry(page)
    assert not state['overflow'], state
    for key in ['image', 'outgoing', 'copy']:
        assert abs(state[key]['shift']) < .1, (key, state)
        assert state[key]['scaleX'] == state[key]['scaleY'] == 1, (key, state)


def assert_moving(page):
    page.wait_for_function('''() => {
      const shift = selector => new DOMMatrixReadOnly(getComputedStyle(
        document.querySelector(selector)).transform).m42;
      return shift('#campaign-image') > shift('.campaign-copy') && shift('.campaign-copy') > 0;
    }''')
    state = geometry(page)
    assert abs(state['image']['shift'] - state['outgoing']['shift']) < .1, state
    assert state['copy']['shift'] <= 32.1, state
    assert not state['overflow'], state
    assert state['image']['scaleX'] == state['image']['scaleY'] == 1, state
    return state


def main():
    output = Path(os.environ.get('ANREDSELLER_SCREENSHOT_DIR', '/tmp/anredseller-parallax'))
    output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='anredseller-parallax-') as directory, open(output / 'server.log', 'w') as log:
        process = subprocess.Popen(
            [str(ROOT / '.venv/bin/python'), '-c', SOURCE], cwd=ROOT,
            env={**os.environ, 'ANREDSELLER_DATA_DIR': directory, 'DATABASE_URL': '', 'VERCEL': ''},
            stdout=subprocess.PIPE, stderr=log, text=True,
        )
        try:
            port = process.stdout.readline().strip()
            assert port.isdigit(), 'Isolated parallax test server did not start'
            base = 'http://127.0.0.1:' + port
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(executable_path='/usr/bin/chromium', headless=True)
                context = browser.new_context(viewport={'width':1440, 'height':1000}, reduced_motion='no-preference')
                page = context.new_page()
                errors = []
                page.on('pageerror', lambda error: errors.append(str(error)))
                page.goto(base, wait_until='networkidle')
                wait_slide(page, 0)
                page.wait_for_selector('.campaign-parallax')
                page.wait_for_function('''() => document.querySelector('#campaign-carousel').getAnimations({subtree: true})
                  .every(animation => animation.playState !== 'running')''')
                assert_static(page)
                original = geometry(page)
                assert original['image']['position'] == '50% 0%'
                assert page.locator('#campaign-image').get_attribute('src') == 'assets/archive-campaign.webp'
                image_identity = page.locator('#campaign-image').element_handle()
                settled_screenshot(page, output / 'desktop-top.png')

                # A real wheel gesture remains native and moves photo/text at different speeds.
                page.mouse.move(700, 400)
                page.mouse.wheel(0, 240)
                page.wait_for_function('() => scrollY > 200')
                scrolled = assert_moving(page)
                assert abs(scrolled['hero']['height'] - original['hero']['height']) < 1
                for key in ['previous', 'next', 'pagination']:
                    assert abs(scrolled[key]['y'] - original[key]['y']) < 1, (key, original, scrolled)
                    assert scrolled[key]['shift'] == original[key]['shift'], (key, original, scrolled)
                assert image_identity.evaluate('element => element === document.querySelector("#campaign-image")')
                settled_screenshot(page, output / 'desktop-scrolled.png')

                # Keyboard users can focus the CTA without its text layer drifting.
                page.locator('#campaign-shop-link').evaluate('element => element.focus({preventScroll:true})')
                focused = geometry(page)
                assert focused['copy']['shift'] == 0, focused
                assert focused['image']['shift'] > 0, focused
                page.locator('#campaign-shop-link').evaluate('element => element.blur()')
                assert_moving(page)

                # Keyboard navigation still works while scrolled. The outgoing layer aligns midfade.
                page.locator('#campaign-carousel').evaluate('element => element.focus({preventScroll:true})')
                page.keyboard.press('ArrowRight')
                wait_slide(page, 1)
                assert page.locator('.campaign-image-outgoing').evaluate(
                    'element => getComputedStyle(element).backgroundImage !== "none"'
                )
                assert_moving(page)
                assert image_identity.evaluate('element => element === document.querySelector("#campaign-image")')
                page.keyboard.press('ArrowLeft')
                wait_slide(page, 0)
                assert_moving(page)
                assert geometry(page)['image']['position'] == '50% 0%'

                scroll_to(page, 0)
                assert_static(page)
                restored = geometry(page)
                for dimension in ['x', 'y', 'width', 'height', 'position']:
                    assert restored['image'][dimension] == original['image'][dimension], (dimension, original, restored)

                # Reduced-motion updates are honored immediately without reloading.
                scroll_to(page, 240)
                assert_moving(page)
                page.emulate_media(reduced_motion='reduce')
                assert_static(page)
                page.emulate_media(reduced_motion='no-preference')
                assert_moving(page)

                page.set_viewport_size({'width':768, 'height':1024})
                scroll_to(page, 240)
                assert_moving(page)
                scroll_to(page, 0)
                assert_static(page)
                assert geometry(page)['image']['position'] == '90% 0%'

                # Phone and short landscape layouts stay still, including after live resizing.
                for width, height in [(390,844), (320,568), (760,1024), (844,390), (1440,599)]:
                    page.set_viewport_size({'width':width, 'height':height})
                    scroll_to(page, 180)
                    assert_static(page)
                    scroll_to(page, 0)
                    assert_static(page)
                    if width <= 760:
                        assert_hero(page)
                    if width == 390:
                        settled_screenshot(page, output / 'mobile-top.png')
                page.set_viewport_size({'width':1440, 'height':1000})
                scroll_to(page, 240)
                assert_moving(page)

                # The zero-image CMS state must remain usable and inert.
                page.goto(base + '/__parallax_no_photo', wait_until='networkidle')
                page.wait_for_selector('.campaign-no-photo')
                assert page.locator('#campaign-image').is_hidden()
                assert not page.locator('#campaign-carousel').evaluate('element => element.classList.contains("campaign-parallax")')
                scroll_to(page, 160)
                assert_static(page)
                assert page.locator('#campaign-title').is_visible()
                assert page.locator('#campaign-shop-link').is_visible()

                # Failed optional enhancement and disabled JS both leave the SSR campaign usable.
                failed_context = browser.new_context(viewport={'width':1440, 'height':1000}, reduced_motion='no-preference')
                failed_context.route('**/js/parallax-scrolling.js', lambda route: route.abort())
                failed = failed_context.new_page()
                failed.on('pageerror', lambda error: errors.append(str(error)))
                failed.goto(base, wait_until='networkidle')
                wait_slide(failed, 0)
                scroll_to(failed, 240)
                assert_static(failed)
                failed.locator('#campaign-carousel').evaluate('element => element.focus({preventScroll:true})')
                failed.keyboard.press('ArrowRight')
                wait_slide(failed, 1)
                assert failed.locator('#campaign-shop-link').is_visible()

                plain = browser.new_context(java_script_enabled=False, viewport={'width':390, 'height':844}).new_page()
                plain.goto(base, wait_until='networkidle')
                assert plain.locator('#campaign-image').is_visible()
                assert plain.locator('#campaign-shop-link').is_visible()
                assert plain.locator('.campaign-arrows').is_hidden()
                assert plain.locator('.campaign-pagination').is_hidden()
                assert plain.locator('#campaign-image').get_attribute('src') == 'assets/archive-campaign.webp'
                assert_static(plain)
                assert geometry(plain)['image']['position'] == '90% 0%'
                assert not errors, errors
                browser.close()
        finally:
            process.terminate()
            process.wait(timeout=10)
    print('PASS: native scrolling, layered depth and aligned crossfade, fixed controls, unchanged Archive framing, keyboard carousel, return-to-top reset, live reduced motion, mobile/landscape resizing, no-photo CMS and no-JS/failed-enhancement fallbacks; no horizontal overflow or uncaught JavaScript errors')


if __name__ == '__main__':
    main()
