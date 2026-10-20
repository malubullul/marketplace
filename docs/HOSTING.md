# Menjalankan Anredseller untuk pemilik dan pengunjung

**Untuk Vercel dan project Supabase yang sudah dibuat, gunakan [panduan Vercel + Supabase](VERCEL_SUPABASE.md).** Kedua project Vercel memakai repository/branch yang sama, dengan PostgreSQL dan Storage di Supabase. Panduan Render di bawah tetap tersedia sebagai alternatif.

Anredseller sekarang memiliki dua sisi yang memakai database server yang sama:

- `/` atau `/index.html`: toko publik. Pengunjung melihat produk terbit tanpa login.
- `/admin` atau `/admin.html`: dashboard pemilik. Pengelolaan produk dan pesanan membutuhkan login.
- `/akun` atau `/akun.html`: akun pembeli untuk daftar/masuk, profil, alamat, wishlist, keranjang lintas perangkat, serta riwayat pesanan.

GitHub menyimpan kode. GitHub Pages dan membuka file HTML langsung tidak menjalankan database atau API; keduanya hanya memberikan pratinjau statis. Gunakan hosting Python dengan PostgreSQL/Storage eksternal untuk Vercel, atau persistent disk untuk mode SQLite.

## Satu repository, dua layanan dan domain

Toko dan [admin-portal](../admin-portal/README.md) memakai repository `malubullul/marketplace` dan branch `main` yang sama. Tidak perlu repository admin baru, branch terpisah, atau unggah ZIP. Satu push ke `main` dapat memperbarui kedua layanan hosting.

| Layanan | Folder sumber | Branch | Contoh domain |
| --- | --- | --- | --- |
| Toko publik | Root repository | `main` | `anredseller.com` |
| Portal admin | `admin-portal` | `main` | `admin.anredseller.com` |

Alamat di tabel hanya contoh, belum merupakan domain yang dipasang. Domain toko melayani pembeli, sedangkan domain admin membuka login pemilik di halaman utama. Database, akun pemilik, foto dan pesanan tetap berada pada satu backend toko. Portal admin tidak membuat salinan database.

Blueprint root membuat environment group `anredseller-admin-connection` yang menghasilkan satu `ANREDSELLER_ADMIN_GATEWAY_KEY` acak dan memasangkannya ke kedua layanan. Nilai rahasia tidak ditulis ke repository. Isi dua URL ketika menghubungkan hosting: `ANREDSELLER_ADMIN_PORTAL_URL` pada toko untuk alamat HTTPS admin, dan `ANREDSELLER_BACKEND_URL` pada admin untuk alamat HTTPS toko. Tombol **Lihat toko** mengikuti alamat backend ini; `ANREDSELLER_SHOP_URL` hanya perlu diisi bila alamat publiknya berbeda. Bila memakai hosting selain Render, buat satu rahasia acak minimal 32 karakter dan pasang nilai yang sama pada kedua layanan.

Jika mode ini diaktifkan, `/admin` serta `/admin.html` pada domain toko menjadi pengalihan menuju portal. File UI admin tidak disajikan dari toko dan API pemilik menolak permintaan tanpa kunci antarlayanan. Portal tetap memerlukan login pemilik dan CSRF; mengetahui domain admin tidak memberi akses pengelolaan. Akun pembeli dan checkout tidak dilayani portal admin. Mode satu domain tetap tersedia ketika variabel pemisahan belum diisi.

## Menjalankan di komputer/server

Gunakan Python 3.12 atau lebih baru.

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python server.py create-admin
.venv/bin/python server.py run
```

Perintah `create-admin` meminta email serta kata sandi melalui terminal. Kata sandi minimal 12 karakter dan tidak ditampilkan saat diketik. Tidak ada akun atau kata sandi bawaan. Jangan menaruh kata sandi di GitHub, kode, atau chat. Untuk menggantinya, gunakan `.venv/bin/python server.py reset-password`; sesi admin lama akan dicabut.

Server pengembangan hanya mendengarkan loopback. Untuk produksi, jalankan Gunicorn di belakang HTTPS/reverse proxy:

```sh
.venv/bin/gunicorn --no-control-socket --workers 1 --threads 4 --timeout 60 --bind 0.0.0.0:8000 server:app
```

Atur `ANREDSELLER_SECURE_COOKIES=1` pada deployment HTTPS. Jangan aktifkan opsi ini untuk uji lokal melalui HTTP karena browser tidak akan mengirim cookie login.

## Alternatif pemasangan: Render dengan disk permanen

`render.yaml` di **root repository** mendefinisikan dua web service Python pada branch `main`, satu environment group bersama, dan persistent disk hanya untuk toko. Ini belum membuat atau mempublikasikan layanan. Dua layanan Starter dan disk toko menggunakan layanan berbayar; tinjau total biaya di Render sebelum membuatnya.

1. Hubungkan repository `malubullul/marketplace` ke Blueprint Render milikmu. Pilih branch `main` dan berkas `render.yaml` di root. Jangan membuat Blueprint kedua dari `admin-portal/render.yaml`; berkas itu hanya untuk opsi ekspor lama.
2. Tinjau dua layanan `anredseller` dan `anredseller-admin` beserta biayanya. Folder root dan perintah startup masing-masing sudah diatur dalam Blueprint.
3. Isi `ANREDSELLER_ADMIN_PORTAL_URL` pada layanan toko dan `ANREDSELLER_BACKEND_URL` pada layanan admin dengan origin HTTPS yang benar, tanpa path. Gunakan domain yang akan dipasang atau URL bawaan hosting yang benar dari dashboard. Bila URL bawaan baru diketahui sesudah layanan dibuat, lengkapi pengaturan lalu deploy ulang; layanan admin belum sehat sebelum URL backend terisi dan backend aktif.
4. Gunakan kunci dari environment group yang sama pada kedua layanan. Jangan membuat kunci berbeda per layanan atau menaruh nilainya di Git. Server toko dapat mulai lebih dahulu; portal admin membutuhkan backend yang sudah tersedia.
5. Pada Shell **layanan toko**, jalankan `python server.py create-admin` jika akun pemilik belum ada. Masukkan email dan kata sandi pribadi langsung di terminal layanan. Portal memakai akun tersebut, bukan akun GitHub.
6. Tambahkan domain toko pada layanan publik dan domain/subdomain admin pada layanan admin, lalu ikuti instruksi DNS dan HTTPS hosting. Jika URL berubah, perbarui dua variabel URL pada langkah 3. Buka domain admin langsung untuk login; `/admin` di toko mengarah ke sana.
7. Isi produk asli, foto, kebijakan pembayaran, dan informasi kontak sebelum mulai menerima pelanggan. Uji terbitkan produk dari admin → terlihat di toko → buat pesanan sebagai pembeli → muncul di admin. Push berikutnya ke `main` memicu pembaruan kedua layanan.

Kedua layanan memakai `pip install -r requirements.txt` dari foldernya masing-masing, Gunicorn, serta health check `/api/health`. Toko menjalankan `server:app`; admin menjalankan `app:app` dari `admin-portal`. Portal tidak memerlukan persistent disk. Jalankan hanya satu instance toko dengan disk SQLite ini. Scaling toko ke beberapa mesin membutuhkan database dan penyimpanan objek bersama; jangan menjalankan beberapa instance dengan salinan database masing-masing.

## Menyimpan produk

Login ke dashboard → **Tambah produk** → isi nama, deskripsi, kategori, harga, stok, pilihan ukuran/warna, bahan/perawatan, dan foto → pilih:

- **Simpan draf**: hanya terlihat oleh pemilik.
- **Terbitkan produk**: muncul di katalog publik saat pengunjung memuat halaman.

Foto pertama menjadi sampul. Foto dapat dipilih dari perangkat, diurutkan dengan **Jadikan sampul**, dan dihapus dari formulir. Format unggahan JPG/PNG/WebP, maksimal 4 MB/foto dan 8 foto/produk. Server memvalidasi gambar, menghapus metadata lewat konversi WebP, dan membatasi ukuran hasil. Batas gambar sumber 25 megapiksel.

Stok adalah total persediaan gabungan semua pilihan ukuran dan warna, bukan stok terpisah per varian. Admin mendapat peringatan jika stok/produk sudah berubah sejak editor dibuka.

## Alur pengunjung dan pesanan

Pengunjung membuka katalog → daftar/masuk akun pembeli → memilih produk, ukuran/warna, serta jumlah → keranjang → checkout memakai alamat tersimpan atau alamat baru → **Buat pesanan & lanjut pembayaran** → WhatsApp pembayaran. Nomor pembayaran dan CS dapat diganti lewat **Admin → Kontak WhatsApp → Simpan kontak**; lihat [panduan WhatsApp](WHATSAPP.md).

Katalog tetap dapat dibuka tanpa login. Menyimpan wishlist/keranjang dan checkout membutuhkan akun. Pembeli dapat mendaftar langsung melalui `/akun`; pendaftaran tidak membuat akun admin. Profil, hingga 10 alamat, alamat utama, wishlist, keranjang dan riwayat pesanan disimpan di database yang sama untuk seluruh perangkat. Email dan nama pemesan diambil dari akun yang terautentikasi; alamat pengiriman dapat ditujukan kepada penerima lain.

Pembeli hanya dapat membaca pesanannya sendiri. Pengelola toko dapat membaca seluruh pesanan dari dashboard admin. Pesanan lama yang dibuat sebelum fitur akun tidak otomatis ditautkan hanya karena alamat email sama. Migrasi database menambahkan kepemilikan akun tanpa menghapus data lama.

Keluar akun mencabut sesi perangkat tersebut. Mengganti kata sandi memerlukan kata sandi saat ini dan mencabut sesi di perangkat lain. Password disimpan sebagai hash; tidak ada kata sandi pelanggan bawaan. Verifikasi email, pemulihan kata sandi lewat email, dan SMS OTP belum tersedia. Akun menggunakan email dan kata sandi.

Harga, diskon, ongkir, dan ketersediaan diperiksa kembali di server. Stok dicadangkan ketika pesanan tercatat. Pengiriman ulang permintaan yang sama tidak membuat pesanan ganda. Rincian pesanan dapat dibaca kembali melalui akun pembeli yang bersangkutan dan dashboard pemilik.

Dashboard **Pesanan masuk** menampilkan rincian pesanan dan status Baru/Diproses/Dikirim/Selesai/Dibatalkan. Membatalkan pesanan mengembalikan stok satu kali. Pesanan selesai atau dibatalkan tidak dapat diaktifkan kembali.

Pembayaran masih dikonfirmasi manual dengan pelanggan. Tidak ada pemotongan uang, pengiriman email, integrasi kurir, atau pelacakan otomatis. Mengubah status tidak membuktikan pembayaran berhasil. Belum ada harga reseller bertingkat, stok per varian, atau refund otomatis.

## Data dan pencadangan

- Default lokal: `instance/`.
- Produksi contoh Render: `/var/data/anredseller`, diatur oleh `ANREDSELLER_DATA_DIR`.
- `store.sqlite3`: produk, akun pemilik/pembeli, sesi, alamat, keranjang, wishlist, dan pesanan.
- `uploads/`: foto yang diunggah.
- `session.key`: kunci penandatanganan cookie, dibuat otomatis dan disimpan di disk.

Folder data, `.venv`, serta `.env` diabaikan Git dan tidak disajikan lewat HTTP. Jangan mengarahkan data ke filesystem hosting yang dihapus saat redeploy. Cadangkan database melalui SQLite backup API dan salin folder unggahan. Contoh backup database ketika server berjalan:

```sh
.venv/bin/python - <<'PY'
import os, sqlite3
from pathlib import Path
source = Path(os.environ.get('ANREDSELLER_DATA_DIR', 'instance')) / 'store.sqlite3'
with sqlite3.connect(source) as src, sqlite3.connect('anredseller-backup.sqlite3') as dst:
    src.backup(dst)
PY
```

Simpan backup di lokasi privat, bukan di folder publik atau Git. Jangan menyalin file database aktif sendirian tanpa backup API karena transaksi WAL bisa belum masuk ke file utama. Foto lama tidak langsung dihapus dari disk ketika produk dihapus agar arsip pesanan tidak kehilangan gambarnya.
