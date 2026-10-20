import io
from pathlib import Path
import secrets
import subprocess
import os
import tempfile
import threading
import unittest
from flask import Flask, Response, request, redirect
from PIL import Image
from werkzeug.serving import make_server, WSGIRequestHandler
from server import create_app, create_owner
from storage import SupabaseStorage


class Quiet(WSGIRequestHandler):
    def log_request(self,*args):pass


class SupabaseStorageTests(unittest.TestCase):
    def setUp(self):
        self.directory=tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.key=secrets.token_urlsafe(40)
        self.objects={};self.mode='normal';self.leaked=[]
        fake=Flask('storage_test')
        @fake.route('/storage/v1/object/product-photos/<name>',methods=['GET','HEAD','POST'])
        def storage(name):
            bearer = None if self.key.startswith('sb_secret_') else 'Bearer '+self.key
            if request.headers.get('apikey')!=self.key or request.headers.get('Authorization')!=bearer:
                return {},403
            if self.mode=='redirect':return redirect('/capture')
            if self.mode=='forbidden':return {},403
            if request.method=='POST':
                self.assertEqual(request.content_type,'image/webp')
                self.objects[name]=request.get_data()
                return {'Key':name}
            if name not in self.objects:return {},404
            return Response(self.objects[name],mimetype='image/webp')
        @fake.get('/capture')
        def capture():self.leaked.append(True);return ''
        self.http=make_server('127.0.0.1',0,fake,threaded=True,request_handler=Quiet)
        self.thread=threading.Thread(target=self.http.serve_forever,daemon=True);self.thread.start()
        self.addCleanup(self.stop)
        self.url=f'http://127.0.0.1:{self.http.server_port}'
        self.app=create_app({'TESTING':True,'DATA_DIR':self.directory.name,'SUPABASE_URL':self.url,'SUPABASE_KEY':self.key})
        password=secrets.token_urlsafe(24);create_owner(self.app,'owner@example.test',password)
        self.client=self.app.test_client();csrf=self.client.get('/api/session').json['csrf']
        response=self.client.post('/api/login',json={'email':'owner@example.test','password':password},headers={'X-CSRF-Token':csrf})
        self.headers={'X-CSRF-Token':response.json['csrf']}

    def stop(self):
        self.http.shutdown();self.thread.join(timeout=5);self.http.server_close()

    def upload(self):
        photo=io.BytesIO();Image.new('RGB',(60,80),'brown').save(photo,'PNG');photo.seek(0)
        return self.client.post('/api/admin/uploads',data={'photo':(photo,'photo.png')},headers=self.headers)

    def test_upload_conversion_readback_and_product_validation_use_remote_bucket(self):
        response=self.upload();self.assertEqual(response.status_code,201,response.json)
        path=response.json['url'];name=path.rsplit('/',1)[1]
        self.assertIn(name,self.objects)
        self.assertEqual(Image.open(io.BytesIO(self.objects[name])).format,'WEBP')
        self.assertFalse((Path(self.directory.name)/'uploads'/name).exists())
        result=self.client.get(path);self.assertEqual(result.status_code,200);self.assertEqual(result.data,self.objects[name])
        self.assertNotIn(self.key.encode(),result.data)
        payload=dict(nama='Produk Foto Supabase',kategori='apparel',brand='Anredseller',deskripsi='Foto dari penyimpanan bersama.',harga=100000,hargaAsli=100000,stok=2,gambarList=[path],published=True)
        product=self.client.post('/api/admin/products',json=payload,headers=self.headers)
        self.assertEqual(product.status_code,201,product.json)
        self.assertEqual(self.app.test_client().get('/api/products').json['products'][0]['gambar'],path)
        self.assertEqual(self.client.get('/uploads/'+'0'*32+'.webp').status_code,404)

    def test_invalid_images_denied_and_storage_redirects_never_receive_key(self):
        response=self.client.post('/api/admin/uploads',data={'photo':(io.BytesIO(b'not an image'),'bad.png')},headers=self.headers)
        self.assertEqual(response.status_code,400);self.assertEqual(self.objects,{})
        for mode in ['redirect','forbidden']:
            self.mode=mode;response=self.upload()
            self.assertEqual(response.status_code,503,response.json)
            self.assertNotIn(self.key,response.get_data(as_text=True))
        self.assertEqual(self.leaked,[])

    def test_new_supabase_secret_key_uses_apikey_without_bearer_jwt(self):
        self.key = 'sb_secret_' + secrets.token_urlsafe(32)
        storage = SupabaseStorage(self.url,self.key,testing=True)
        storage.put('a'*32+'.webp',b'test image')
        self.assertEqual(storage.get('a'*32+'.webp'),b'test image')

    def test_serverless_requires_remote_database_and_stable_secret(self):
        with self.assertRaises(ValueError):create_app({'SERVERLESS':True,'DATABASE_URL':''})
        with self.assertRaises(ValueError):create_app({'DATABASE_URL':'postgresql://unused','SESSION_SECRET':''})
        missing=Path(self.directory.name)/'must-not-be-created'
        app=create_app({'TESTING':True,'SERVERLESS':True,'DATABASE_URL':'postgresql://unused',
                        'SESSION_SECRET':secrets.token_urlsafe(40),'DATA_DIR':str(missing),
                        'SUPABASE_URL':self.url,'SUPABASE_KEY':self.key})
        self.assertFalse(missing.exists())
        self.assertEqual(app.get_db.__name__,'db')

    def test_unconfigured_vercel_keeps_public_pages_but_cannot_accept_orders(self):
        missing=Path(self.directory.name)/'no-sqlite-fallback'
        source="from server import app; c=app.test_client(); assert c.get('/').status_code==200; assert c.get('/api/health').status_code==503; assert c.get('/api/customer/session').status_code==503; assert c.post('/api/orders',json={}).status_code==503"
        environment={**os.environ,'VERCEL':'1','DATABASE_URL':'','ANREDSELLER_SESSION_SECRET':'',
                     'SUPABASE_URL':'','ANREDSELLER_DATA_DIR':str(missing)}
        subprocess.run([str(Path(__file__).resolve().parents[1]/'.venv/bin/python'),'-c',source],env=environment,check=True,capture_output=True)
        self.assertFalse(missing.exists())
