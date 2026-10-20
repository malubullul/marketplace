"""Exercise the real campaign slider, responsive photos, touch and failure states."""
import os
from pathlib import Path
import subprocess
import tempfile

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
VIEWPORTS = [(320,568), (360,640), (375,667), (390,844), (414,896), (430,932),
             (600,960), (760,1024), (768,1024), (820,1180), (1024,768), (1440,1000), (667,375), (844,390)]
NAMES = ['archive-campaign', 'campaign-after-hours', 'campaign-city-uniform', 'campaign-soft-form', 'campaign-everyday-objects']


def wait_slide(page, index):
    page.wait_for_function('''index => document.querySelector('#campaign-carousel').dataset.campaignIndex === String(index)
        && document.querySelector('#campaign-image').complete && document.querySelector('#campaign-image').naturalWidth > 0
        && !document.querySelector('.campaign-photo').hasAttribute('aria-busy')''', arg=index)


def select_slide(page, index):
    if page.locator('[data-campaign="0"]').is_visible():
        page.locator(f'[data-campaign="{index}"]').click()
        wait_slide(page,index)
    else:
        while int(page.locator('#campaign-carousel').get_attribute('data-campaign-index')) != index:
            next_index=(int(page.locator('#campaign-carousel').get_attribute('data-campaign-index'))+1)%5
            page.locator('.campaign-next').click();wait_slide(page,next_index)


def swipe(page, x, y, dx, dy):
    session = page.context.new_cdp_session(page)
    session.send('Input.dispatchTouchEvent', {'type':'touchStart','touchPoints':[{'x':x,'y':y}]})
    for step in range(1,7):
        session.send('Input.dispatchTouchEvent', {'type':'touchMove','touchPoints':[{'x':x+dx*step/6,'y':y+dy*step/6}]})
    session.send('Input.dispatchTouchEvent', {'type':'touchEnd','touchPoints':[]})
    session.detach()


def main():
    output = Path(os.environ.get('ANREDSELLER_SCREENSHOT_DIR','/tmp/anredseller-campaign'))
    output.mkdir(parents=True, exist_ok=True)
    source = "from server import create_app; from werkzeug.serving import make_server; app=create_app({'TESTING':True}); http=make_server('127.0.0.1',0,app,threaded=True); print(http.server_port,flush=True); http.serve_forever()"
    with tempfile.TemporaryDirectory(prefix='anredseller-campaign-') as directory, open(output/'server.log','w') as log:
        process = subprocess.Popen([str(ROOT/'.venv/bin/python'),'-c',source],cwd=ROOT,
            env={**os.environ,'ANREDSELLER_DATA_DIR':directory},stdout=subprocess.PIPE,stderr=log,text=True)
        try:
            port = process.stdout.readline().strip(); assert port.isdigit()
            base = 'http://127.0.0.1:'+port+'/'
            with sync_playwright() as p:
                browser = p.chromium.launch(executable_path='/usr/bin/chromium',headless=True)
                context = browser.new_context(viewport={'width':390,'height':844},has_touch=True,reduced_motion='reduce')
                page = context.new_page(); errors=[]
                page.on('pageerror',lambda error:errors.append(str(error)))
                page.goto(base,wait_until='networkidle'); wait_slide(page,0)
                assert page.locator('h1:visible').count()==1
                assert page.locator('.archive-announcement').count()==0
                for width,height in VIEWPORTS:
                    page.set_viewport_size({'width':width,'height':height}); page.evaluate('scrollTo(0,0)')
                    original_height = None
                    for index,name in enumerate(NAMES):
                        select_slide(page,index)
                        assert page.locator('#campaign-image').get_attribute('src') == 'assets/'+name+'.webp'
                        assert page.locator('#campaign-current').inner_text()==f'{index+1:02}'
                        assert page.locator('[data-campaign][aria-current=true]').count()==1
                        assert page.locator('#campaign-image').get_attribute('alt')
                        assert page.locator('#campaign-shop-link').get_attribute('href').startswith('produk.html?kategori=')
                        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth + 1'), (width,index)
                        controls = page.locator('.campaign-pagination').bounding_box()
                        assert controls['x'] >= 0 and controls['x']+controls['width'] <= width+1, (width,index,controls)
                        photo = page.locator('.campaign-photo').bounding_box()
                        heading = page.locator('#campaign-title').bounding_box()
                        for selector in ['.campaign-previous','.campaign-next']:
                            arrow = page.locator(selector).bounding_box()
                            assert arrow['width']>=44 and arrow['height']>=44
                            assert arrow['x']>=0 and arrow['x']+arrow['width']<=width
                            assert arrow['y']>=photo['y'] and arrow['y']+arrow['height']<=photo['y']+photo['height']
                            overlap = min(heading['x']+heading['width'],arrow['x']+arrow['width'])-max(heading['x'],arrow['x'])>1 and min(heading['y']+heading['height'],arrow['y']+arrow['height'])-max(heading['y'],arrow['y'])>1
                            assert not overlap,(width,index,'arrow covers headline')
                        current_height = page.locator('.campaign').bounding_box()['height']
                        if original_height is None: original_height=current_height
                        assert abs(current_height-original_height)<2,(width,index,'layout jumps',original_height,current_height)
                        if width in [1440,768,390,320,844]:
                            page.locator('.campaign').screenshot(path=str(output/f'slide-{index+1}-{width}.png'))
                # Edges wrap, both directions work, and keyboard navigation stays on the page.
                page.set_viewport_size({'width':390,'height':844});page.evaluate('scrollTo(0,0)')
                page.locator('.campaign-next').click();wait_slide(page,0)
                page.locator('.campaign-previous').click();wait_slide(page,4)
                page.locator('#campaign-carousel').focus();page.keyboard.press('ArrowRight');wait_slide(page,0)
                page.keyboard.press('ArrowLeft');wait_slide(page,4)
                select_slide(page,0)
                photo=page.locator('.campaign-photo').bounding_box();x=photo['x']+photo['width']*.65;y=photo['y']+photo['height']*.45
                swipe(page,x,y,-120,2);wait_slide(page,1)
                swipe(page,x-120,y,120,2);wait_slide(page,0)
                swipe(page,x,y,2,-100)
                assert page.locator('#campaign-carousel').get_attribute('data-campaign-index')=='0'
                assert page.evaluate('scrollY > 0'), 'Vertical touch scrolling was blocked'
                page.evaluate('scrollTo(0,0)')
                page.evaluate("() => { for(let i=0;i<6;i++) document.querySelector('.campaign-next').click(); }")
                wait_slide(page,1)
                page.clock.install();page.clock.fast_forward(120000)
                assert page.locator('#campaign-carousel').get_attribute('data-campaign-index')=='1'
                # Failed photos leave the current image and CTA usable; the next navigation can recover.
                failed_context=browser.new_context(viewport={'width':390,'height':844},reduced_motion='reduce')
                failed_context.route('**/campaign-soft-form.webp',lambda route:route.abort())
                failed=failed_context.new_page();failed.on('pageerror',lambda error:errors.append(str(error)))
                failed.goto(base,wait_until='networkidle');select_slide(failed,2);failed.locator('.campaign-next').click()
                failed.locator('#campaign-status').get_by_text('Foto belum bisa dimuat.',exact=False).wait_for()
                assert failed.locator('#campaign-image').get_attribute('src')=='assets/campaign-city-uniform.webp'
                failed.locator('.campaign-previous').click();wait_slide(failed,1)
                # Real animation uses a crossfade; reduced-motion preference removes it.
                motion_context=browser.new_context(viewport={'width':1440,'height':1000},reduced_motion='no-preference')
                motion=motion_context.new_page();motion.on('pageerror',lambda error:errors.append(str(error)))
                motion.goto(base,wait_until='networkidle');motion.locator('.campaign-next').click();wait_slide(motion,1)
                assert motion.locator('#campaign-image').evaluate('e => getComputedStyle(e).transitionDuration')=='0.5s'
                motion.wait_for_function("() => getComputedStyle(document.querySelector('#campaign-image')).opacity === '1'")
                motion.emulate_media(reduced_motion='reduce')
                assert motion.locator('#campaign-image').evaluate('e => getComputedStyle(e).transitionDuration')=='0s'
                # No-JS fallback keeps the initial campaign and shopping link without dead controls.
                plain=browser.new_context(java_script_enabled=False,viewport={'width':390,'height':844}).new_page()
                plain.goto(base)
                assert plain.locator('#campaign-image').is_visible()
                assert not plain.locator('.campaign-arrows').is_visible()
                assert not plain.locator('.campaign-pagination').is_visible()
                assert plain.locator('#campaign-shop-link').is_visible()
                assert not errors,errors
                browser.close()
        finally:
            process.terminate();process.wait(timeout=10)
    print('PASS: all 5 campaign photos at 14 viewport sizes; stable layout, arrows and indicators, keyboard, real touch swipe/vertical scroll, rapid navigation, reduced motion/manual timing, failed-image recovery and no-JS fallback; no uncaught JavaScript errors')


if __name__=='__main__':main()
