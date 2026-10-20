# Anredseller Admin

Portal khusus pemilik toko yang siap dipasang di repository dan domain sendiri. Halaman utama langsung membuka login admin; tidak berisi katalog pembeli, pendaftaran pembeli, atau checkout.

Fitur: login/keluar pemilik, tambah/edit/hapus produk, unggah dan urutkan foto, stok, ukuran/warna, simpan draf/terbitkan produk, rincian pesanan dan pembaruan status. Tampilannya mengikuti dashboard Anredseller, termasuk ukuran HP.

## Cara kerjanya

```text
Pembeli → domain toko → server toko + database + foto
Pemilik → domain admin → portal ini → server toko yang sama
```

Portal ini menjalankan Python/Flask dan meneruskan API admin yang diizinkan ke server toko. Browser hanya menghubungi domain admin untuk login dan pengelolaan, sehingga cookie tidak bergantung pada izin cookie pihak ketiga. Kunci koneksi berada di server, tidak ditaruh di JavaScript. Tidak perlu membuat database produk atau akun pemilik kedua.

Domain admin boleh memakai subdomain seperti `seller.tokomu.com` atau domain terpisah. GitHub menyimpan kode; **GitHub Pages saja tidak dapat menjalankan portal ini**.

## Isi repository admin baru

Unggah **isi** folder `Anredseller-Admin` dari ZIP ke root repository baru. File `app.py`, `requirements.txt`, dan `render.yaml` harus berada langsung di root, bersama folder `static/` dan `templates/`.

Jika memakai checkout marketplace, proyek ini berada di `admin-portal/`. Buat ulang ZIP dari root marketplace dengan:

```sh
python3 scripts/export_admin.py /tmp/Anredseller-Admin.zip
```

Tidak ada kata sandi bawaan, database, foto pelanggan, `.env` asli, atau kunci rahasia dalam paket.

## Menghubungkan dua layanan

Server toko perlu memakai versi marketplace yang mendukung portal admin terpisah. Isi variabel berikut melalui pengaturan hosting, bukan dalam file yang diunggah ke GitHub.

| Tempat | Variabel | Isi |
| --- | --- | --- |
| Hosting admin | `ANREDSELLER_BACKEND_URL` | Origin HTTPS server toko, misalnya `https://tokomu.com` |
| Hosting admin | `ANREDSELLER_SHOP_URL` | Origin HTTPS toko publik untuk tombol **Lihat toko** |
| Kedua hosting | `ANREDSELLER_ADMIN_GATEWAY_KEY` | Rahasia acak yang sama, minimal 32 karakter |
| Hosting toko | `ANREDSELLER_ADMIN_PORTAL_URL` | Origin HTTPS admin, misalnya `https://seller.tokomu.com` |
| Kedua hosting | `ANREDSELLER_SECURE_COOKIES` | `1` untuk HTTPS |

Origin berarti alamat tanpa path, query, username, atau password. URL HTTP hanya diterima untuk loopback saat pengembangan lokal. `.env.example` merupakan daftar pengaturan; aplikasi tidak memuat file `.env` secara otomatis.

Buat rahasia acak di terminal pribadi atau secret manager dan simpan langsung ke pengaturan hosting. Jangan memasukkan nilainya ke Git, chat, atau JavaScript. Ini adalah kunci antarlayanan, bukan kata sandi pemilik. Rahasia yang berbeda pada kedua layanan menyebabkan koneksi ditolak.

Setelah kedua pengaturan aktif, `/admin` dan `/admin.html` di domain toko mengarahkan pemilik ke domain admin. UI admin lama tidak disajikan di domain toko dan API pemilik memerlukan koneksi dari portal. URL publik dan akun pembeli tetap berjalan di server toko. Tanpa pengaturan tersebut, marketplace mempertahankan mode satu domain untuk pengembangan.

## Pemasangan hosting

1. Buat repository GitHub admin dan unggah isi paket seperti struktur di atas.
2. Hubungkan repository itu ke web service Python di hosting. `render.yaml` menyediakan contoh Render Starter berbayar; tinjau biaya sebelum membuat layanan. Jika memakai folder dalam repository marketplace, tetapkan root directory `admin-portal`.
3. Isi pengaturan admin dan toko dari tabel, lalu deploy kedua versi. Gunakan satu instance backend toko dengan persistent disk untuk SQLite/foto. Portal admin tidak memerlukan disk database.
4. Tambahkan domain admin dan aktifkan HTTPS melalui hosting. Sebelum domain sendiri siap, alamat HTTPS bawaan hosting dapat dipakai pada konfigurasi.
5. Buat akun pemilik **di terminal server toko** dengan `python server.py create-admin`, jika belum ada. Gunakan akun pemilik yang sudah ada bila sebelumnya dibuat. Tidak ada pendaftaran admin publik.
6. Buka domain admin dan login. Terbitkan produk lalu periksa di toko publik. Buat pesanan melalui akun pembeli dan pastikan muncul pada **Pesanan masuk**.

Perintah hosting dari root repository admin:

```sh
pip install -r requirements.txt
gunicorn --no-control-socket --workers 1 --threads 4 --timeout 60 --bind 0.0.0.0:$PORT app:app
```

Health check: `/api/health`. Respons sehat membutuhkan koneksi ke backend yang tersedia. Pengaturan kosong menghasilkan 503, bukan sukses semu. Jika kunci tidak cocok atau server toko belum diperbarui, login tidak akan bekerja.

## Menjalankan secara lokal

Gunakan Python 3.12+, buat virtualenv lalu pasang dependensi. Muat variabel melalui shell/IDE; atur backend ke loopback server toko dan `ANREDSELLER_SECURE_COOKIES=0` hanya untuk uji HTTP lokal. Kedua server harus memakai kunci yang sama. Jalankan `python app.py` dari folder ini; portal mendengarkan port 8001. Akun pemilik tetap dibuat pada backend toko.

Di repository marketplace, pengujian terisolasi tidak memerlukan kredensial nyata:

```sh
.venv/bin/python -m unittest discover -s tests -v
ANREDSELLER_TEST_ADMIN_PORTAL=1 python3 tests/browser_smoke.py
```

Pengujian browser membuka toko dan portal pada origin berbeda, menjalankan unggah → draf → terbit → pesanan → pembaruan dashboard, serta memeriksa bahwa API pembeli tidak tersedia pada portal admin. Data uji disimpan sementara dan dihapus setelah pengujian.
