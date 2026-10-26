"""Owner-controlled public imagery and social links, stored in existing metadata."""
from copy import deepcopy
import json
from pathlib import Path
import re
import time
from urllib.parse import urlsplit

from flask import jsonify

CAMPAIGNS = [
    dict(id='campaign_archive', name='The Archive', heading=['Gaya pilihan.', 'Untuk harimu.'], description='Belanja sneakers, pakaian, dan aksesori pilihan. Temukan yang sesuai dengan gayamu.', href='produk.html?kategori=apparel'),
    dict(id='campaign_after_hours', name='After Hours', heading=['Gaya santai.', 'Tetap rapi.'], description='Jelajahi pilihan pakaian untuk aktivitas santai dan gaya sehari-hari.', href='produk.html?kategori=apparel'),
    dict(id='campaign_city', name='City Uniform', heading=['Pilihan sneakers.', 'Untuk gayamu.'], description='Lihat pilihan sneakers dan padukan dengan pakaian favoritmu.', href='produk.html?kategori=sneakers'),
    dict(id='campaign_soft_form', name='Soft Form', heading=['Tampil simpel.', 'Tetap menarik.'], description='Temukan model pakaian yang cocok untuk beragam gaya dan kesempatan.', href='produk.html?kategori=apparel'),
    dict(id='campaign_objects', name='Everyday Objects', heading=['Lengkapi gaya.', 'Sesukamu.'], description='Jelajahi tas, aksesori, dan pilihan pelengkap kebutuhan harian.', href='produk.html?kategori=essentials'),
]
IMAGE_SLOTS = {
    'campaign_archive': ('Slider 1 · The Archive', 'assets/archive-campaign.webp', 'Dua model mengenakan jaket suede cokelat di lounge bernuansa kayu gelap.', 90),
    'campaign_after_hours': ('Slider 2 · After Hours', 'assets/campaign-after-hours.webp', 'Dua model dengan tailoring warna pasir dan cokelat di koridor hotel berpanel walnut.', 86),
    'campaign_city': ('Slider 3 · City Uniform', 'assets/campaign-city-uniform.webp', 'Model memakai overshirt charcoal, celana hitam, dan sneakers putih di halaman beton modern.', 84),
    'campaign_soft_form': ('Slider 4 · Soft Form', 'assets/campaign-soft-form.webp', 'Model memakai cardigan oatmeal, celana espresso, dan tas kulit di studio bernuansa olive.', 84),
    'campaign_objects': ('Slider 5 · Everyday Objects', 'assets/campaign-everyday-objects.webp', 'Sneakers suede putih, kemeja oatmeal terlipat, dan tas kulit cokelat pada plinth walnut.', 84),
    'category_sneakers': ('Kategori · Sneakers', 'assets/shoe-3.png', 'Sneaker biru dan hitam', 50),
    'category_apparel': ('Kategori · Apparel', 'assets/shirt.png', 'Kaos hitam essential', 50),
    'reseller_banner': ('Banner · Cara belanja Anredseller', 'assets/archive-campaign.webp', 'Detail layer suede dari kampanye Archive', 80),
    'account_editorial': ('Halaman · Akun pembeli', 'assets/archive-campaign.webp', 'Kampanye fashion Anredseller', 69),
}
SOCIALS = {
    'instagram': ('Instagram', {'instagram.com','www.instagram.com'}),
    'tiktok': ('TikTok', {'tiktok.com','www.tiktok.com','vm.tiktok.com','vt.tiktok.com'}),
    'facebook': ('Facebook', {'facebook.com','www.facebook.com','m.facebook.com','fb.com','www.fb.com'}),
    'youtube': ('YouTube', {'youtube.com','www.youtube.com','m.youtube.com','youtu.be'}),
    'x': ('X', {'x.com','www.x.com','twitter.com','www.twitter.com'}),
    'threads': ('Threads', {'threads.com','www.threads.com','threads.net','www.threads.net'}),
}


def default_content():
    return dict(images={key:dict(src=entry[1],alt=entry[2],position=entry[3]) for key,entry in IMAGE_SLOTS.items()},
                socials={**{key:'' for key in SOCIALS},'other_label':'','other_url':''}, version='0')


def public_content(saved):
    # Only curated presentation data is published, never unrelated metadata/accounts.
    result = dict(images=deepcopy(saved['images']),socials=deepcopy(saved['socials']))
    result['campaigns'] = []
    for slide in CAMPAIGNS:
        image = saved['images'][slide['id']]
        if not image['src']:
            continue
        # The original Archive framing is responsive: center/top on desktop,
        # 90%/top on smaller screens. Let its existing CSS apply to the preset.
        original_archive = (slide['id'] == 'campaign_archive'
                            and image['src'] == IMAGE_SLOTS['campaign_archive'][1])
        crop = str(image['position'])+('% top' if original_archive else '% center')
        if original_archive and image['position'] == IMAGE_SLOTS['campaign_archive'][3]:
            crop = ''
        result['campaigns'].append(dict(slide, image=image['src'], alt=image['alt'],
                                        crop=crop))
    return result


class StoreContent:
    def __init__(self, app, db, owner_required, fail, body, storage):
        self.db = db
        root=Path(__file__).resolve().parent

        @app.get('/api/store/content')
        def published_content():
            return jsonify(content=public_content(self.read()))

        @app.get('/api/admin/content')
        @owner_required
        def admin_content():
            return jsonify(content=self.read(), slots=[dict(id=key,label=entry[0],default_src=entry[1],default_image=default_content()['images'][key]) for key,entry in IMAGE_SLOTS.items()],
                           platforms=[dict(id=key,label=entry[0]) for key,entry in SOCIALS.items()])

        @app.put('/api/admin/content')
        @owner_required
        def update_content():
            data=body()
            section=data.get('section')
            if not isinstance(section,str) or section not in {'images','socials'} or set(data) != {'section','version',section}:
                return fail('Pilih pengaturan gambar atau media sosial yang akan disimpan.')
            previous=self.read()
            db().commit()  # Release the read transaction before checking uploaded Storage objects.
            if data.get('version')!=previous['version']:
                return fail('Pengaturan berubah di perangkat lain. Muat ulang pengaturan sebelum menyimpan.',409)
            try:
                if section=='images':
                    incoming=data['images']
                    if not isinstance(incoming,dict) or set(incoming)!=set(IMAGE_SLOTS):
                        raise ValueError('Daftar gambar toko tidak lengkap.')
                    validated={}
                    checked={image['src'] for image in previous['images'].values() if image['src']}
                    for key,entry in incoming.items():
                        if not isinstance(entry,dict) or set(entry)!={'src','alt','position'}:
                            raise ValueError('Data gambar tidak valid.')
                        src,alt,position=entry['src'],entry['alt'],entry['position']
                        if not isinstance(src,str) or not isinstance(alt,str) or len(alt)>240 or (src and not alt.strip()):
                            raise ValueError('Isi deskripsi gambar, maksimal 240 karakter.')
                        try:
                            alt.encode('utf-8')
                        except UnicodeEncodeError:
                            raise ValueError('Gunakan teks deskripsi gambar yang valid.') from None
                        if type(position) is not int or not 0<=position<=100:
                            raise ValueError('Fokus gambar harus antara 0 dan 100.')
                        if src and src not in checked:
                            if src in {slot[1] for slot in IMAGE_SLOTS.values()}:
                                exists=(root/src).is_file()
                            elif re.fullmatch(r'/uploads/[a-f0-9]{32}\.webp',src):
                                exists=storage.exists(src.rsplit('/',1)[1])
                            else:
                                exists=False
                            if not exists:
                                raise ValueError('Gunakan foto yang diunggah melalui admin atau gambar bawaan toko.')
                            checked.add(src)
                        validated[key]=dict(src=src,alt=alt.strip(),position=position)
                else:
                    incoming=data['socials']
                    if not isinstance(incoming,dict) or set(incoming)!=set(default_content()['socials']):
                        raise ValueError('Daftar media sosial tidak lengkap.')
                    validated={}
                    for key,value in incoming.items():
                        if not isinstance(value,str):
                            raise ValueError('Tautan media sosial harus berupa teks.')
                        value=value.strip()
                        if key=='other_label':
                            if len(value)>40:raise ValueError('Nama tautan lainnya maksimal 40 karakter.')
                        elif value:
                            if len(value)>2048 or re.search(r'[\s\x00-\x1f\x7f\\]',value):
                                raise ValueError('Tautan media sosial tidak valid.')
                            parsed=urlsplit(value)
                            host=parsed.hostname or ''
                            if (parsed.scheme!='https' or parsed.username or parsed.password or parsed.port not in {None,443}
                                    or not re.fullmatch(r'(?:[a-z0-9](?:[a-z0-9-]*[a-z0-9])?\.)+[a-z]{2,63}',host)):
                                raise ValueError('Gunakan tautan HTTPS lengkap, misalnya https://www.instagram.com/namatoko/.')
                            if key in SOCIALS and host not in SOCIALS[key][1]:
                                raise ValueError('Domain tautan '+SOCIALS[key][0]+' tidak sesuai.')
                        validated[key]=value
                    if validated['other_url'] and not validated['other_label']:
                        raise ValueError('Isi nama untuk tautan lainnya.')
            except ValueError as error:
                return fail(str(error))
            db().execute('BEGIN IMMEDIATE')
            current=self.read()
            if data.get('version')!=current['version']:
                db().rollback()
                return fail('Pengaturan berubah di perangkat lain. Muat ulang pengaturan sebelum menyimpan.',409)
            current[section]=validated
            current['version']=str(time.time_ns())
            db().execute("INSERT INTO metadata(key,value) VALUES('store_content',?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",(json.dumps(current),))
            db().commit()
            return jsonify(content=current)

    def read(self):
        row=self.db().execute("SELECT value FROM metadata WHERE key='store_content'").fetchone()
        return json.loads(row['value']) if row else default_content()
