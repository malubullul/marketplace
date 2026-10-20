# Anredseller Admin

Portal khusus pemilik toko pada domain sendiri, memakai **repository `marketplace` dan branch `main` yang sama** dengan toko publik. Halaman utama langsung membuka login admin; tidak berisi katalog pembeli, pendaftaran pembeli, atau checkout.

Fitur: login/keluar pemilik, tambah/edit/hapus produk, unggah dan urutkan foto, stok, ukuran/warna, simpan draf/terbitkan produk, rincian pesanan dan pembaruan status. Tampilannya mengikuti dashboard Anredseller, termasuk ukuran HP.

## Cara kerjanya

```text
Pembeli → domain toko → server toko + database + foto
Pemilik → domain admin → portal ini → server toko yang sama
```

Portal ini menjalankan Python/Flask dan meneruskan API admin yang diizinkan ke server toko. Browser hanya menghubungi domain admin untuk login dan pengelolaan, sehingga cookie tidak bergantung pada izin cookie pihak ketiga. Kunci koneksi berada di server, tidak ditaruh di JavaScript. Tidak perlu membuat database produk atau akun pemilik kedua.

Domain admin boleh memakai subdomain seperti `seller.tokomu.com` atau domain terpisah. GitHub menyimpan kode; **GitHub Pages saja tidak dapat menjalankan portal ini**.

## Sumber kode dan hosting

Gunakan satu repository dan dua layanan hosting:

| Layanan | Folder dalam repository | Branch | Modul startup |
| --- | --- | --- | --- |
| Toko publik | Root | `main` | `server:app` |
| Admin | `admin-portal` | `main` | `app:app` |

Untuk **Vercel + Supabase**, ikuti [panduan utama](../docs/VERCEL_SUPABASE.md): buat dua project Vercel dari repository/branch yang sama, pilih Root Directory `admin-portal` untuk project admin, dan gunakan `vercel.json` di folder ini. Project admin tidak memerlukan koneksi database atau secret Supabase, hanya URL backend dan kunci gateway. Database/foto cloud dikelola backend toko.

Sebagai alternatif, Blueprint [render.yaml di root](../render.yaml) mengatur dua layanan Render dan pembaruan otomatis dari `main`. Tidak perlu membuat repository/branch admin baru atau mengunggah ZIP. File `render.yaml` di folder admin ini hanya untuk opsi ekspor mandiri.

## Menghubungkan dua layanan

Server toko memakai kode backend pada repository yang sama. Blueprint root membuat satu kunci acak lewat environment group dan memasangkannya ke kedua layanan. Isi URL layanan melalui pengaturan hosting, bukan dalam file yang diunggah ke GitHub. Tabel ini juga berlaku bila mengatur hosting secara manual.

| Tempat | Variabel | Isi |
| --- | --- | --- |
| Hosting admin | `ANREDSELLER_BACKEND_URL` | Origin HTTPS server toko, misalnya `https://tokomu.com` |
| Hosting admin | `ANREDSELLER_SHOP_URL` | Opsional; default mengikuti backend. Isi hanya jika alamat toko publik berbeda |
| Kedua hosting | `ANREDSELLER_ADMIN_GATEWAY_KEY` | Otomatis dari environment group Blueprint; bila manual, pakai rahasia sama minimal 32 karakter |
| Hosting toko | `ANREDSELLER_ADMIN_PORTAL_URL` | Origin HTTPS admin, misalnya `https://seller.tokomu.com` |
| Kedua hosting | `ANREDSELLER_SECURE_COOKIES` | `1` untuk HTTPS |

Origin berarti alamat tanpa path, query, username, atau password. URL HTTP hanya diterima untuk loopback saat pengembangan lokal. `.env.example` merupakan daftar pengaturan; aplikasi tidak memuat file `.env` secara otomatis.

Pada Blueprint, pertahankan kunci yang dihasilkan environment group yang sama. Pada hosting manual, buat rahasia acak di terminal pribadi atau secret manager dan simpan langsung ke pengaturan hosting. Jangan memasukkan nilainya ke Git, chat, atau JavaScript. Ini adalah kunci antarlayanan, bukan kata sandi pemilik. Rahasia yang berbeda pada kedua layanan menyebabkan koneksi ditolak.

Setelah kedua pengaturan aktif, `/admin` dan `/admin.html` di domain toko mengarahkan pemilik ke domain admin. UI admin lama tidak disajikan di domain toko dan API pemilik memerlukan koneksi dari portal. URL publik dan akun pembeli tetap berjalan di server toko. Tanpa pengaturan tersebut, marketplace mempertahankan mode satu domain untuk pengembangan.

## Alternatif pemasangan di Render

1. Hubungkan repository `malubullul/marketplace`, branch `main`, ke Blueprint **root** `render.yaml`. Tidak perlu repository kedua. Tinjau biaya dua layanan Starter dan disk toko sebelum membuat layanan.
2. Blueprint memakai root repository untuk toko dan `admin-portal` untuk admin, serta kunci koneksi bersama. Isi URL admin pada pengaturan toko dan URL backend pada pengaturan admin.
3. Deploy kedua layanan. Gunakan satu instance backend toko dengan persistent disk untuk SQLite/foto. Portal admin tidak memerlukan disk database. Admin baru sehat setelah URL backend terisi dan server toko dapat dihubungi.
4. Pasang domain publik pada layanan toko dan domain/subdomain admin pada layanan admin, lalu aktifkan HTTPS. Sebelum domain sendiri siap, alamat HTTPS bawaan hosting yang benar dapat dipakai. Perbarui variabel URL bila alamat berubah. Push ke `main` memicu pembaruan kedua layanan.
5. Buat akun pemilik **di terminal server toko** dengan `python server.py create-admin`, jika belum ada. Gunakan akun pemilik yang sudah ada bila sebelumnya dibuat. Tidak ada pendaftaran admin publik.
6. Buka domain admin dan login. Terbitkan produk lalu periksa di toko publik. Buat pesanan melalui akun pembeli dan pastikan muncul pada **Pesanan masuk**.

Perintah hosting dijalankan dari folder `admin-portal`:

```sh
pip install -r requirements.txt
gunicorn --no-control-socket --workers 1 --threads 4 --timeout 60 --bind 0.0.0.0:$PORT app:app
```

Health check: `/api/health`. Respons sehat membutuhkan koneksi ke backend yang tersedia. Pengaturan kosong menghasilkan 503, bukan sukses semu. Jika kunci tidak cocok atau server toko belum diperbarui, login tidak akan bekerja.

## Opsi ekspor mandiri

Paket ZIP lama tetap dapat dibuat bila suatu saat ingin memindahkan admin ke repository terpisah. Ini opsional dan tidak digunakan oleh konfigurasi utama satu repository. Jalankan dari root marketplace:

```sh
python3 scripts/export_admin.py /tmp/Anredseller-Admin.zip
```

Jika memakai opsi ini, unggah isi folder hasil ekstrak ke root repository baru, lalu gunakan `render.yaml` di dalam paket dan isi kunci/URL secara manual. Paket tidak berisi kata sandi bawaan, database, data pelanggan, `.env` asli, atau kunci rahasia. Untuk konfigurasi satu repository, ikuti [panduan hosting utama](../docs/HOSTING.md).

## Menjalankan secara lokal

Untuk mengganti nomor pembayaran/CS, masuk lalu buka **Kontak WhatsApp → Simpan kontak**. Pengaturan disimpan oleh backend toko, bukan di browser atau database admin terpisah. Lihat [panduan WhatsApp](../docs/WHATSAPP.md).

Gunakan Python 3.12+, buat virtualenv lalu pasang dependensi. Muat variabel melalui shell/IDE; atur backend ke loopback server toko dan `ANREDSELLER_SECURE_COOKIES=0` hanya untuk uji HTTP lokal. Kedua server harus memakai kunci yang sama. Jalankan `python app.py` dari folder ini; portal mendengarkan port 8001. Akun pemilik tetap dibuat pada backend toko.

Di repository marketplace, pengujian terisolasi tidak memerlukan kredensial nyata:

```sh
.venv/bin/python -m unittest discover -s tests -v
ANREDSELLER_TEST_ADMIN_PORTAL=1 python3 tests/browser_smoke.py
```

Pengujian browser membuka toko dan portal pada origin berbeda, menjalankan unggah → draf → terbit → pesanan → pembaruan dashboard, serta memeriksa bahwa API pembeli tidak tersedia pada portal admin. Data uji disimpan sementara dan dihapus setelah pengujian.

## Tampilan toko dan media sosial

Dashboard menyediakan menu **Tampilan toko** untuk sembilan foto publik (slider, kategori, banner dan halaman akun), **Media sosial** untuk tautan footer yang awalnya kosong, dan **Kontak WhatsApp** untuk dua nomor toko. Foto produk tetap di **Koleksi produk**. Setelah mengubah, simpan lalu muat ulang toko publik. Backend dan portal harus menggunakan commit terbaru; tidak memerlukan database, environment variable atau migrasi baru untuk pengaturan konten.
