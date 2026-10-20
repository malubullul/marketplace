"""Owner-only content management, persisted removals, safe links and first-paint HTML."""
import io
import json
import secrets
import tempfile
import unittest
from copy import deepcopy
from concurrent.futures import ThreadPoolExecutor
from html.parser import HTMLParser
from PIL import Image
import test_contacts
from server import create_app, create_owner
from store_content import IMAGE_SLOTS, default_content

class HTMLSnapshot(HTMLParser):
    def __init__(self, html):
        super().__init__();self.images={};self.snapshot='';self.inside=False;self.feed(html)
    def handle_starttag(self,tag,attrs):
        attrs=dict(attrs)
        if tag=='img' and attrs.get('id'):self.images[attrs['id']]=attrs
        if tag=='script' and attrs.get('id')=='store-content':self.inside=True
    def handle_endtag(self,tag):
        if tag=='script':self.inside=False
    def handle_data(self,data):
        if self.inside:self.snapshot+=data

class StoreContentTests(unittest.TestCase):
    def setUp(self):
        self.directory=tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.settings={'TESTING':True,'DATA_DIR':self.directory.name}
        self.app=create_app(self.settings)
        self.password=secrets.token_urlsafe(24)
        create_owner(self.app,'owner@example.test',self.password)
        self.owner=self.app.test_client();self.guest=self.app.test_client()
        csrf=self.owner.get('/api/session').json['csrf']
        login=self.owner.post('/api/login',json={'email':'owner@example.test','password':self.password},headers={'X-CSRF-Token':csrf})
        self.headers={'X-CSRF-Token':login.json['csrf']}
    def admin(self):return self.owner.get('/api/admin/content').json['content']
    def save(self,section,value=None,version=None):
        state=self.admin()
        return self.owner.put('/api/admin/content',json={'section':section,section:state[section] if value is None else value,'version':version if version is not None else state['version']},headers=self.headers)

    def test_defaults_are_empty_socials_and_only_curated_public_data(self):
        data=self.guest.get('/api/store/content')
        self.assertEqual(data.status_code,200)
        self.assertEqual(set(data.json['content']),{'images','socials','campaigns'})
        self.assertFalse(any(data.json['content']['socials'].values()))
        self.assertEqual(len(data.json['content']['images']),9)
        self.assertEqual(len(data.json['content']['campaigns']),5)
        self.assertEqual(data.json['content']['campaigns'][0]['crop'],'')
        self.assertEqual(data.headers['Cache-Control'],'no-store')
        for path in ['/','/index.html','/akun','/akun.html','/produk.html','/detail.html']:
            page=self.guest.get(path)
            self.assertEqual(page.status_code,200,path)
            self.assertEqual(page.headers['Cache-Control'],'no-store')
            parsed=HTMLSnapshot(page.data.decode())
            self.assertEqual(json.loads(parsed.snapshot),data.json['content'])
            self.assertNotIn('{{',page.data.decode())

        # An already-saved preset must regain the same framing without a data migration.
        self.assertEqual(self.save('images',self.admin()['images']).status_code,200)
        first=self.guest.get('/api/store/content').json['content']['campaigns'][0]
        self.assertEqual(first['crop'],'')
        self.assertNotIn('style',HTMLSnapshot(self.guest.get('/').data.decode()).images['campaign-image'])
        images=self.admin()['images'];images['campaign_archive']['position']=30
        self.assertEqual(self.save('images',images).status_code,200)
        self.assertEqual(self.guest.get('/api/store/content').json['content']['campaigns'][0]['crop'],'30% top')

    def test_only_owner_with_csrf_can_edit_content(self):
        payload={'section':'socials','socials':default_content()['socials'],'version':'0'}
        self.assertEqual(self.guest.get('/api/admin/content').status_code,401)
        self.assertEqual(self.guest.put('/api/admin/content',json=payload).status_code,401)
        self.assertEqual(self.owner.put('/api/admin/content',json=payload).status_code,403)
        csrf=self.guest.get('/api/customer/session').json['csrf']
        buyer=self.guest.post('/api/customer/register',json={'email':'buyer@example.test','password':secrets.token_urlsafe(24),'nama':'Buyer','nohp':'081234567890'},headers={'X-CSRF-Token':csrf})
        self.assertEqual(self.guest.put('/api/admin/content',json=payload,headers={'X-CSRF-Token':buyer.json['csrf']}).status_code,401)

    def test_image_removal_persists_and_server_skips_deleted_first_slide(self):
        state=self.admin();state['images']['campaign_archive']['src']=''
        self.assertEqual(self.save('images',state['images']).status_code,200)
        for client in [self.guest,create_app(self.settings).test_client()]:
            data=client.get('/api/store/content').json['content']
            self.assertEqual(data['images']['campaign_archive']['src'],'')
            self.assertEqual(len(data['campaigns']),4)
            html=client.get('/').data.decode();parsed=HTMLSnapshot(html)
            self.assertEqual(parsed.images['campaign-image']['src'],'assets/campaign-after-hours.webp')
            self.assertIn('After hours.',html)

    def test_all_images_can_be_removed_without_broken_image_sources(self):
        state=self.admin()
        for image in state['images'].values():image['src']=''
        self.assertEqual(self.save('images',state['images']).status_code,200)
        self.assertEqual(self.guest.get('/api/store/content').json['content']['campaigns'],[])
        html=self.guest.get('/').data.decode();image=HTMLSnapshot(html).images['campaign-image']
        self.assertIn('hidden',image);self.assertNotIn('src',image)
        self.assertIn('campaign-no-photo',html)
        self.assertNotIn('class="account-editorial-photo"',self.guest.get('/akun.html').data.decode())
        # Explicitly restoring a slot works; blank never means use the default.
        state=self.admin();state['images']['campaign_archive']=default_content()['images']['campaign_archive']
        self.assertEqual(self.save('images',state['images']).status_code,200)
        self.assertEqual(len(self.guest.get('/api/store/content').json['content']['campaigns']),1)

    def test_upload_can_be_reused_without_removing_other_placements_and_alt_is_safe(self):
        stream=io.BytesIO();Image.new('RGB',(320,180),'#654a38').save(stream,'PNG');stream.seek(0)
        uploaded=self.owner.post('/api/admin/uploads',data={'photo':(stream,'campaign.png')},headers=self.headers)
        self.assertEqual(uploaded.status_code,201)
        state=self.admin();url=uploaded.json['url']
        text='</script><script>alert("owner")</script> {{7*7}}'
        state['images']['campaign_archive']=dict(src=url,alt=text,position=35)
        state['images']['reseller_banner']['src']=url
        self.assertEqual(self.save('images',state['images']).status_code,200)
        html=self.guest.get('/').data.decode();snapshot=HTMLSnapshot(html)
        self.assertEqual(snapshot.images['campaign-image']['src'],url)
        self.assertEqual(json.loads(snapshot.snapshot)['images']['campaign_archive']['alt'],text)
        self.assertEqual(snapshot.images['campaign-image']['alt'],text)
        self.assertEqual(json.loads(snapshot.snapshot)['campaigns'][0]['crop'],'35% center')
        self.assertNotIn(text,html)
        self.assertEqual(self.guest.get(url).status_code,200)
        state=self.admin();state['images']['campaign_archive']['src']=''
        self.assertEqual(self.save('images',state['images']).status_code,200)
        self.assertEqual(self.guest.get(url).status_code,200)
        self.assertEqual(self.guest.get('/api/store/content').json['content']['images']['reseller_banner']['src'],url)

    def test_rejects_untrusted_image_sources_and_bad_shapes_without_partial_save(self):
        original=self.admin()
        for src in ['https://evil.example/image.webp','//evil.example/a.png','assets/../server.py','/uploads/'+('a'*32)+'.webp','data:image/png;base64,x','javascript:alert(1)',None,True]:
            state=deepcopy(original);state['images']['campaign_archive']['src']=src
            self.assertEqual(self.save('images',state['images']).status_code,400,src)
        for field,value in [('position',True),('position',-1),('position',101),('position',1.5),('alt','a'*241),('alt',''),('alt','\ud800')]:
            state=deepcopy(original);state['images']['campaign_archive'][field]=value
            self.assertEqual(self.save('images',state['images']).status_code,400)
        self.assertEqual(self.save('images',{}).status_code,400)
        for section in [{},[],None,True,1]:
            self.assertEqual(self.owner.put('/api/admin/content',json={'section':section,'version':'0'},headers=self.headers).status_code,400)
        self.assertEqual(self.admin(),original)

    def test_socials_persist_and_clear_without_losing_images_or_whatsapp(self):
        socials=default_content()['socials'];socials.update(instagram='https://www.instagram.com/anredseller/',tiktok='https://www.tiktok.com/@anredseller',other_label='Pinterest',other_url='https://www.pinterest.com/anredseller/')
        self.assertEqual(self.save('socials',socials).status_code,200)
        restarted=create_app(self.settings).test_client()
        self.assertEqual(restarted.get('/api/store/content').json['content']['socials'],socials)
        self.assertEqual(self.admin()['images'],default_content()['images'])
        self.assertEqual(self.guest.get('/api/store/contacts').json['contacts'],test_contacts.DEFAULT_STORE_CONTACTS)
        self.assertEqual(self.save('socials',default_content()['socials']).status_code,200)
        self.assertFalse(any(self.guest.get('/api/store/content').json['content']['socials'].values()))

    def test_unsafe_social_urls_and_unknown_fields_cannot_be_saved(self):
        for url in ['javascript:alert(1)','http://instagram.com/name','//instagram.com/name','https://instagram.com.evil.example/name','https://instagram.com@evil.example/name','https://www.instagram.com:444/name','https://www.instagram.com/\nx','https://www.instagram.com\\@evil.example/name','https://127.0.0.1/account',True,None,123]:
            socials=default_content()['socials'];socials['instagram']=url
            self.assertEqual(self.save('socials',socials).status_code,400,url)
        socials=default_content()['socials'];socials['other_url']='https://linktr.ee/owner'
        self.assertEqual(self.save('socials',socials).status_code,400)
        socials['other_label']='x'*41
        self.assertEqual(self.save('socials',socials).status_code,400)
        self.assertEqual(self.save('socials',{'instagram':''}).status_code,400)
        self.assertEqual(self.owner.put('/api/admin/content',json={'section':'images','version':'0','images':default_content()['images'],'role':'owner'},headers=self.headers).status_code,400)

    def test_stale_or_concurrent_writes_do_not_overwrite_saved_content(self):
        original=self.admin();socials=deepcopy(original['socials']);socials['instagram']='https://instagram.com/store'
        self.assertEqual(self.save('socials',socials,original['version']).status_code,200)
        self.assertEqual(self.save('images',original['images'],original['version']).status_code,409)
        version=self.admin()['version'];cookie=self.owner.get_cookie('session').value
        def save(index):
            client=self.app.test_client();client.set_cookie('session',cookie)
            changed=deepcopy(socials);changed['tiktok']='https://www.tiktok.com/@store'+str(index)
            return client.put('/api/admin/content',json={'section':'socials','version':version,'socials':changed},headers=self.headers).status_code
        with ThreadPoolExecutor(max_workers=2) as pool:statuses=list(pool.map(save,[1,2]))
        self.assertEqual(sorted(statuses),[200,409])
