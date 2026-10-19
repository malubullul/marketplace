# Menjalankan Anredseller untuk pemilik dan pengunjung

Anredseller sekarang memiliki dua sisi yang memakai database server yang sama:

- `/` atau `/index.html`: toko publik. Pengunjung melihat produk terbit tanpa login.
- `/admin` atau `/admin.html`: dashboard pemilik. Pengelolaan produk dan pesanan membutuhkan login.

GitHub menyimpan kode. GitHub Pages dan membuka file HTML langsung tidak menjalankan database atau API; keduanya hanya memberikan pratinjau statis. Gunakan hosting yang dapat menjalankan Python dan menyediakan penyimpanan permanen.

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

## Opsi pemasangan: Render

`render.yaml` adalah konfigurasi siap ditinjau untuk satu web service Python dan persistent disk. Ini belum membuat atau mempublikasikan layanan. Paket Starter dan persistent disk menggunakan layanan berbayar; tinjau biaya di Render sebelum membuatnya.

1. Hubungkan repositori `malubullul/marketplace` dengan layanan Render milikmu.
2. Buat Blueprint dari `render.yaml`, periksa biaya, kemudian deploy jika sudah sesuai.
3. Sesudah server aktif, buka Shell layanan tersebut dan jalankan `python server.py create-admin` untuk membuat akun pemilik. Masukkan email dan kata sandi pribadi langsung di terminal layanan.
4. Buka alamat layanan dengan akhiran `/admin` untuk login. Alamat utama adalah toko publik.
5. Isi produk asli, foto, kebijakan pembayaran, dan informasi kontak sebelum mulai menerima pelanggan. Contoh produk di database dapat diedit, dijadikan draf, atau dihapus melalui dashboard.
6. Domain sendiri dapat ditambahkan melalui pengaturan hosting. HTTPS harus aktif agar cookie admin bekerja sesuai konfigurasi produksi.

Konfigurasi build memakai `pip install -r requirements.txt`, start memakai Gunicorn, dan health check memakai `/api/health`. Jalankan hanya satu instance dengan disk SQLite ini. Scaling ke beberapa mesin membutuhkan database dan penyimpanan objek bersama; jangan menjalankan beberapa instance dengan salinan database masing-masing.

## Menyimpan produk

Login ke dashboard → **Tambah produk** → isi nama, deskripsi, kategori, harga, stok, pilihan ukuran/warna, bahan/perawatan, dan foto → pilih:

- **Simpan draf**: hanya terlihat oleh pemilik.
- **Terbitkan produk**: muncul di katalog publik saat pengunjung memuat halaman.

Foto pertama menjadi sampul. Foto dapat dipilih dari perangkat, diurutkan dengan **Jadikan sampul**, dan dihapus dari formulir. Format unggahan JPG/PNG/WebP, maksimal 5 MB/foto dan 8 foto/produk. Server memvalidasi gambar, menghapus metadata lewat konversi WebP, dan membatasi ukuran hasil. Batas gambar sumber 25 megapiksel.

Stok adalah total persediaan gabungan semua pilihan ukuran dan warna, bukan stok terpisah per varian. Admin mendapat peringatan jika stok/produk sudah berubah sejak editor dibuka.

## Alur pengunjung dan pesanan

Pengunjung membuka katalog → memilih produk, ukuran/warna, serta jumlah → keranjang → checkout → mengisi penerima → **Kirim pesanan ke toko**.

Harga, diskon, ongkir, dan ketersediaan diperiksa kembali di server. Stok dicadangkan ketika pesanan tercatat. Pengiriman ulang permintaan yang sama tidak membuat pesanan ganda. Rincian pembeli dan alamat hanya dapat dibaca kembali melalui dashboard pemilik yang sudah login.

Dashboard **Pesanan masuk** menampilkan rincian pesanan dan status Baru/Diproses/Dikirim/Selesai/Dibatalkan. Membatalkan pesanan mengembalikan stok satu kali. Pesanan selesai atau dibatalkan tidak dapat diaktifkan kembali.

Pembayaran masih dikonfirmasi manual dengan pelanggan. Tidak ada pemotongan uang, pengiriman email, integrasi kurir, atau pelacakan otomatis. Mengubah status tidak membuktikan pembayaran berhasil. Belum ada fitur akun pelanggan, harga reseller bertingkat, stok per varian, atau refund otomatis.

## Data dan pencadangan

- Default lokal: `instance/`.
- Produksi contoh Render: `/var/data/anredseller`, diatur oleh `ANREDSELLER_DATA_DIR`.
- `store.sqlite3`: produk, akun, sesi, dan pesanan.
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
