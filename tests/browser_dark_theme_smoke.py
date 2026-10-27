"""Check dark surfaces, contrast and real store/admin states using disposable data."""
import json
import os
from pathlib import Path
import secrets
import subprocess
import tempfile
from playwright.sync_api import sync_playwright
from browser_store_content_smoke import SOURCE
from responsive_smoke import assert_layout

ROOT=Path(__file__).resolve().parents[1]
VIEWS=[(320,568),(390,844),(768,1024),(1440,1000)]
CONTRAST=r'''() => {
 const rgba=s=>{const n=s.match(/[\d.]+/g)?.map(Number);return n?[n[0],n[1],n[2],n[3]??1]:[0,0,0,0]};
 const luminance=c=>c.slice(0,3).map(v=>{v/=255;return v<=.04045?v/12.92:((v+.055)/1.055)**2.4}).reduce((s,v,i)=>s+v*[.2126,.7152,.0722][i],0);
 const ratio=(a,b)=>{a=luminance(a);b=luminance(b);return (Math.max(a,b)+.05)/(Math.min(a,b)+.05)};
 const findings=[];let checked=0;
 function inspect(el,text,foreground) {
   if(!el.getClientRects().length||!text.trim()||el.closest('script,style,option,:disabled,[aria-disabled=true]'))return;
   const style=getComputedStyle(el);if(style.visibility!=='visible'||Number(style.opacity)===0)return;
   let layers=[],node=el;
   while(node){const s=getComputedStyle(node),bg=rgba(s.backgroundColor);layers.push(bg);if(bg[3]===1)break;
     if(s.backgroundImage!=='none'||node.matches('.campaign,.account-editorial,.login-editorial')&&node.querySelector('img'))return;node=node.parentElement;}
   let bg=[16,18,16];for(const c of layers.reverse())bg=bg.map((v,i)=>c[i]*c[3]+v*(1-c[3]));
   const fg=rgba(foreground||style.color),large=parseFloat(style.fontSize)>=24||(parseFloat(style.fontSize)>=18.66&&Number(style.fontWeight)>=700);
   const score=ratio(fg,bg);checked++;
   if(score<(large?3:4.5)-.02)findings.push({selector:el.tagName.toLowerCase()+(el.id?'#'+el.id:'.'+[...el.classList].join('.')),text:text.trim().slice(0,65),fg:style.color,bg:bg.map(Math.round),ratio:Number(score.toFixed(2))});
 }
 const walk=document.createTreeWalker(document.body,NodeFilter.SHOW_TEXT);
 while(walk.nextNode())inspect(walk.currentNode.parentElement,walk.currentNode.textContent);
 for(const el of document.querySelectorAll('input:not([type=hidden]):not([type=checkbox]):not([type=radio]),textarea')) {
   inspect(el,el.value||el.placeholder,el.value?getComputedStyle(el).color:getComputedStyle(el,'::placeholder').color);
 }
 return {checked,findings,scheme:getComputedStyle(document.documentElement).colorScheme,background:getComputedStyle(document.body).backgroundColor};
}'''


def main():
    shots=Path(os.environ.get('ANREDSELLER_SCREENSHOT_DIR','/tmp/anredseller-dark'));shots.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='anredseller-dark-') as directory,open(shots/'server.log','w') as log:
        password=secrets.token_urlsafe(24)
        process=subprocess.Popen([str(ROOT/'.venv/bin/python'),'-c',SOURCE],cwd=ROOT,env={**os.environ,'ANREDSELLER_DATA_DIR':directory},stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=log,text=True)
        process.stdin.write(json.dumps({'password':password})+'\n');process.stdin.flush()
        try:
            ports=json.loads(process.stdout.readline());base=f"http://127.0.0.1:{ports['store']}";admin=f"http://localhost:{ports['admin']}"
            with sync_playwright() as p:
                browser=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True)
                owner=browser.new_context(viewport={'width':1440,'height':1000},reduced_motion='reduce').new_page()
                buyer=browser.new_context(viewport={'width':390,'height':844},reduced_motion='reduce').new_page()
                guest=browser.new_context(viewport={'width':390,'height':844},reduced_motion='reduce').new_page()
                checks=[];reports=[];errors=[]
                for page in [owner,buyer,guest]:page.on('pageerror',lambda error:errors.append(str(error)))
                def capture(page,name,views=VIEWS):
                    for width,height in views:
                        page.set_viewport_size({'width':width,'height':height});assert_layout(page,name+' '+str(width),checks)
                        report=page.evaluate(CONTRAST);reports.append(dict(page=name,width=width,**report))
                        assert report['scheme']=='dark',(name,report['scheme'])
                        assert page.locator('img').evaluate_all('(images)=>images.every(img=>getComputedStyle(img).filter==="none")')
                        page.screenshot(path=str(shots/f'{name}-{width}.png'),full_page=True)

                owner.goto(admin,wait_until='networkidle');capture(owner,'admin-login')
                owner.locator('#login-email').fill('owner@example.test');owner.locator('#login-password').fill(password);owner.locator('#login-button').click();owner.locator('#dashboard').wait_for(state='visible')
                csrf=owner.request.get(admin+'/api/session').json()['csrf'];headers={'X-CSRF-Token':csrf}
                product=owner.request.post(admin+'/api/admin/products',data=dict(nama='Archive Overshirt',kategori='apparel',brand='Anredseller',deskripsi='Kemeja dengan potongan santai untuk pengujian tampilan.',harga=350000,hargaAsli=500000,stok=10,stokUkuran=[{'ukuran':'S','stok':3},{'ukuran':'M','stok':5},{'ukuran':'L','stok':0},{'ukuran':'XL','stok':2}],ukuran=[],warna=['Hitam'],gambarList=['assets/shirt.png'],published=True),headers=headers).json()['product']
                owner.locator('#refresh-products').click();capture(owner,'admin-products')
                owner.get_by_role('button',name='Edit Archive Overshirt',exact=True).click();capture(owner,'admin-editor')
                owner.locator('#product-dialog').evaluate('(dialog)=>dialog.close()')
                for area in ['settings','transactions','appearance','socials','promos']:
                    owner.locator('[data-page='+area+']').click();owner.wait_for_load_state('networkidle');capture(owner,'admin-'+area,[(390,844),(1440,1000)])
                for path,name in [('/','home'),('/produk.html','catalog'),('/detail.html?id='+str(product['id']),'detail'),('/akun.html','login'),('/missing-black-page','404')]:
                    guest.goto(base+path,wait_until='networkidle');capture(guest,name)
                guest.goto(base+'/akun.html',wait_until='networkidle');guest.locator('#show-register').click();capture(guest,'register')
                csrf=buyer.request.get(base+'/api/customer/session').json()['csrf']
                signup=buyer.request.post(base+'/api/customer/register',data=dict(email='dark@example.test',nama='Buyer',nohp='081234567890',password=password),headers={'X-CSRF-Token':csrf}).json()
                buyer_headers={'X-CSRF-Token':signup['csrf']}
                buyer.goto(base+'/detail.html?id='+str(product['id']),wait_until='networkidle');buyer.locator('#pilihan-ukuran').select_option('M');buyer.locator('#pilihan-warna').select_option('Hitam');buyer.locator('#btn-tambah').click();buyer.wait_for_function('()=>getKeranjang().length===1')
                buyer.goto(base+'/keranjang.html',wait_until='networkidle');capture(buyer,'cart')
                buyer.locator('#btn-checkout').click();buyer.wait_for_url('**/checkout.html');capture(buyer,'checkout')
                for field,value in {'nama-penerima':'Buyer','nohp':'081234567890','alamat':'Jalan Uji 1','kota':'Jakarta','provinsi':'DKI Jakarta','kodepos':'12345'}.items():buyer.locator('#'+field).fill(value)
                buyer.locator('#btn-pesan').click();buyer.wait_for_url('**/konfirmasi.html?order=*');buyer.locator('#nomor-pesanan').filter(has_text='ANR-').wait_for();number=buyer.locator('#nomor-pesanan').inner_text();capture(buyer,'receipt')
                buyer.goto(base+'/akun.html',wait_until='networkidle');capture(buyer,'profile')
                buyer.locator('[data-customer-panel=orders]').click();buyer.locator('[data-customer-order="'+number+'"]').click();capture(buyer,'buyer-order')
                owner.set_viewport_size({'width':1440,'height':1000});owner.locator('[data-page=orders]').click();owner.locator('#refresh-orders').click();owner.locator('[data-order="'+number+'"]').click();capture(owner,'owner-order')
                owner.get_by_role('button',name='Tandai sudah dibayar',exact=True).click();capture(owner,'confirm-payment')
                owner.get_by_role('button',name='Konfirmasi',exact=True).click();owner.get_by_role('heading',name='Sudah dibayar',exact=True).wait_for();owner.locator('#close-order').click()
                for state in ['diproses','dikirim','selesai']:
                    owner.locator('[data-order-status="'+number+'"]').select_option(state);owner.wait_for_function('(state)=>orders.some(order=>order.status===state)',arg=state)
                buyer.goto(base+'/detail.html?id='+str(product['id'])+'#ulasan',wait_until='networkidle');buyer.locator('#product-review-form').wait_for();capture(buyer,'review')
                owner.locator('[data-page=activity]').click();owner.locator('#activity-list article').first.wait_for();capture(owner,'activity')
                (shots/'contrast.json').write_text(json.dumps(reports,ensure_ascii=False,indent=2))
                failures=[dict(page=r['page'],width=r['width'],issues=r['findings']) for r in reports if r['findings']]
                print(json.dumps({'layouts':len(checks),'text_samples':sum(r['checked'] for r in reports),'contrast_failure_pairs':len(failures)},ensure_ascii=False))
                assert not errors,errors
                assert not failures,f'{len(failures)} page/viewport pairs have contrast failures; see contrast.json'
                browser.close()
        finally:process.terminate();process.wait(timeout=10)


if __name__=='__main__':main()
