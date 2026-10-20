"""Disposable PostgreSQL + Storage HTTP fixture for the full browser workflow."""
import json
import os
from pathlib import Path
import secrets
import threading
import time
from flask import Flask, Response, request
from werkzeug.serving import make_server
from server import create_app


def configure_backend(settings):
    url=os.environ.get('ANREDSELLER_TEST_DATABASE_URL')
    if not url:
        return create_app(settings), lambda:None
    key=secrets.token_urlsafe(40)
    objects={}
    storage=Flask('browser_storage')
    @storage.route('/storage/v1/object/product-photos/<name>',methods=['GET','HEAD','POST'])
    def object_api(name):
        if request.headers.get('apikey')!=key or request.headers.get('Authorization')!='Bearer '+key:return {},403
        if request.method=='POST':objects[name]=request.get_data();return {'Key':name}
        if name not in objects:return {},404
        return Response(objects[name],mimetype='image/webp')
    http=make_server('127.0.0.1',0,storage,threaded=True)
    threading.Thread(target=http.serve_forever,daemon=True).start()
    schema='browser_'+secrets.token_hex(12)
    app=create_app({**settings,'TESTING':True,'DATABASE_URL':url,'DATABASE_SCHEMA':schema,
                    'SESSION_SECRET':secrets.token_urlsafe(40),'SUPABASE_URL':f'http://127.0.0.1:{http.server_port}',
                    'SUPABASE_KEY':key})
    with app.app_context():
        db=app.get_db();db.initialize()
        products=json.loads((Path(__file__).resolve().parents[1]/'data/products.seed.json').read_text())
        for product in products:
            product.update(ukuran=[],warna=[],published=True,demo=True)
            db.execute('INSERT INTO products(id,document,published,updated_at) VALUES(?,?,1,?)',(product['id'],json.dumps(product),time.time_ns()))
        db.execute("SELECT setval(pg_get_serial_sequence('products','id'), (SELECT MAX(id) FROM products))")
        db.execute("INSERT INTO metadata VALUES('seeded','1')");db.commit()
    def cleanup():
        import psycopg
        from psycopg import sql
        http.shutdown();http.server_close()
        with psycopg.connect(url,autocommit=True) as connection:
            connection.execute(sql.SQL('DROP SCHEMA {} CASCADE').format(sql.Identifier(schema)))
    return app,cleanup
