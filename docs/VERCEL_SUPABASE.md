# Vercel + Supabase: satu repository, dua project

Konfigurasi utama untuk kebutuhan ini: repository `malubullul/marketplace`, branch `main`, dua project Vercel, satu PostgreSQL Supabase, dan satu bucket foto privat. Konfigurasi Render tetap tersedia sebagai alternatif. Tidak perlu repository atau branch admin baru.

## 1. Siapkan database dan bucket

Pada project Supabase yang sudah dibuat, buka **SQL Editor → New query**. Jalankan isi dua file berikut, satu per satu:

1. [`migrations/001_supabase.sql`](../migrations/001_supabase.sql): tabel aplikasi, sesi, alamat, produk dan pesanan.
2. [`migrations/002_supabase_storage.sql`](../migrations/002_supabase_storage.sql): bucket privat `product-photos`.

Tabel berada pada schema **`anredseller`**, bukan `public`. Pilih schema tersebut ketika melihat tabel. Jangan menambahkannya ke daftar schema Data API yang diekspos. RLS aktif dan tidak ada kebijakan baca/tulis publik. Backend menggunakan koneksi PostgreSQL server; browser tidak mengakses tabel atau bucket secara langsung.

Migrasi dapat dijalankan ulang tanpa menghapus tabel/data. Jangan menjalankannya pada database produksi yang tidak berkaitan dengan aplikasi ini. Ini bukan migrasi otomatis data SQLite lama. Jika ada data toko nyata sebelumnya, cadangkan dan pindahkan melalui proses migrasi terpisah sebelum beralih; jangan menganggap data browser atau database lokal sudah tersalin ke Supabase.

## 2. Ambil pengaturan melalui dashboard

- **DATABASE_URL**: Supabase **Connect → Transaction pooler**, port `6543`. Ganti placeholder password pada connection string secara pribadi. Gunakan password database, bukan API key. Jika password memiliki karakter khusus, encode bagian password pada URI. Driver menonaktifkan prepared statements untuk transaction pooler dan memverifikasi TLS pada host jarak jauh.
- **SUPABASE_URL**: URL project yang ditampilkan Supabase.
- **SUPABASE_SECRET_KEY**: secret API key baru berawalan `sb_secret_`, digunakan hanya di backend untuk Storage. Ambil dari pengaturan API keys. Format legacy `SUPABASE_SERVICE_ROLE_KEY` juga didukung, tetapi cukup pilih salah satu.
- Buat dua rahasia acak yang berbeda, masing-masing minimal 32 karakter: `ANREDSELLER_SESSION_SECRET` dan `ANREDSELLER_ADMIN_GATEWAY_KEY`. Rahasia sesi harus stabil antar-deployment agar login tidak hilang. Kunci gateway harus identik di kedua project Vercel.

Masukkan rahasia langsung ke **Vercel → Project → Settings → Environment Variables**, tandai sebagai Sensitive bila tersedia. Jangan kirim ke chat atau unggah `.env` ke Git. Jika secret key pernah terkirim ke chat, buat penggantinya lalu nonaktifkan kunci lama sebelum memasangnya.

`SUPABASE_PUBLISHABLE_KEY` dan `SUPABASE_JWKS_URL` tidak diperlukan oleh implementasi ini. Akun pembeli/pemilik tetap memakai autentikasi aplikasi dan hash password, sekarang tersimpan di PostgreSQL. Akun tidak otomatis muncul di menu Supabase Authentication/Users.

## 3. Buat dua project Vercel

Impor repository yang sama dua kali melalui **Add New → Project**. Keduanya memilih production branch **`main`**:

| Pengaturan | Project toko | Project admin |
| --- | --- | --- |
| Nama contoh | `anredseller-store` | `anredseller-admin` |
| Root Directory | Root repository (`./`) | `admin-portal` |
| Framework Preset | Other | Other |
| Build/Output overrides | Hapus override static lama, gunakan default | Gunakan default |
| File konfigurasi | `vercel.json` di root | `admin-portal/vercel.json` |
| Python entrypoint | `server.py` | `app.py` |

Kedua file konfigurasi memakai builder Python, merutekan seluruh halaman/API ke Flask, dan memilih region Singapore (`sin1`) dekat database. Folder `.venv`, database lokal, environment files dan berkas pengembangan tidak diunggah sebagai aplikasi. Python dipatok ke 3.12. `requirements.txt` dipasang dari root masing-masing project. Ini aplikasi Python, bukan ekspor HTML statis dan bukan GitHub Pages.

Pada project toko lama yang sebelumnya hanya menyajikan HTML, hapus pengaturan Output Directory/Build Command statis yang bertentangan. Pastikan Root Directory tidak menunjuk `admin-portal`. Jika dashboard menampilkan peringatan bahwa `builds` dari `vercel.json` mengambil alih pengaturan build, itu sesuai konfigurasi explicit Python ini.

Gunakan URL **production** yang stabil dari dashboard, bukan URL preview commit yang dilindungi Vercel. Server admin harus dapat menghubungi production backend tanpa interstitial Deployment Protection. Toko publik memang harus bisa diakses pembeli. Setelah dua alamat production diketahui, isi variabel berikut lalu redeploy keduanya. Jika deployment awal belum lengkap, jangan anggap aplikasi sehat sampai pengaturan selesai.

Jika environment belum lengkap, halaman publik tetap dapat dibuka tetapi API mengembalikan 503 dan tidak menerima pendaftaran/pesanan. Aplikasi tidak membuat database SQLite sementara di Vercel. Setelah semua pengaturan dan migrasi selesai, redeploy untuk mengaktifkan backend.

## 4. Environment Variables

### Project toko — root repository

| Nama | Isi |
| --- | --- |
| `DATABASE_URL` | Connection string Transaction pooler PostgreSQL |
| `SUPABASE_URL` | URL project Supabase |
| `SUPABASE_SECRET_KEY` | Kunci server baru, hanya di project toko |
| `SUPABASE_STORAGE_BUCKET` | `product-photos` |
| `ANREDSELLER_SESSION_SECRET` | Rahasia sesi stabil minimal 32 karakter |
| `ANREDSELLER_ADMIN_GATEWAY_KEY` | Rahasia gateway minimal 32 karakter |
| `ANREDSELLER_ADMIN_PORTAL_URL` | Origin production admin, misalnya `https://anredseller-admin.vercel.app` |
| `ANREDSELLER_SECURE_COOKIES` | `1` |

### Project admin — folder `admin-portal`

| Nama | Isi |
| --- | --- |
| `ANREDSELLER_BACKEND_URL` | Origin production toko, misalnya `https://anredseller-store.vercel.app` |
| `ANREDSELLER_ADMIN_GATEWAY_KEY` | Nilai yang sama persis dengan project toko |
| `ANREDSELLER_SECURE_COOKIES` | `1` |
| `ANREDSELLER_SHOP_URL` | Opsional; default mengikuti backend |

Jangan memasang password database atau secret Supabase pada project admin; admin memakai gateway server. URL contoh belum merupakan deployment/domain yang dibuat untukmu. Semua URL berupa origin tanpa path/query. Environment Variables harus dipasang pada scope **Production**, dan perubahan membutuhkan redeploy. Untuk Preview, gunakan project/database pengujian terpisah; jangan memberi preview yang tidak ditinjau akses ke data produksi.

## 5. Buat akun pemilik

Tidak ada pendaftaran admin publik atau password bawaan. Vercel tidak menyediakan terminal server permanen untuk langkah interaktif. Pilih salah satu cara berikut:

**Tanpa memasukkan koneksi database ke terminal:** pada checkout pribadi dengan dependencies terpasang, jalankan:

```sh
.venv/bin/python scripts/create_owner_sql.py
```

Masukkan email dan password pribadi pada terminal; password tidak tampil. Helper menghasilkan SQL berisi hash password, bukan password asli. Salin hasilnya ke Supabase SQL Editor dan jalankan. Jangan unggah hasil SQL itu ke Git. Perintah tidak mengganti akun yang sudah ada.

**Jika memiliki terminal pribadi dengan environment database yang sudah dimuat:** jalankan `.venv/bin/python server.py create-admin`. Gunakan `.venv/bin/python server.py reset-password` bila perlu mengganti password dan mencabut sesi lama. Jangan menuliskan kredensial di command yang masuk Git atau chat.

## 6. Verifikasi

1. `/api/health` toko dan admin mengembalikan JSON `status: ok`.
2. Halaman utama admin menampilkan login. Login dengan akun pemilik yang dibuat pada langkah 5.
3. Unggah foto maksimal **4 MB/foto** (8 foto/produk), simpan draf, lalu terbitkan. Batas 4 MB memberi ruang untuk multipart di bawah batas request serverless Vercel. Foto dikonversi menjadi WebP dan disimpan di bucket privat; URL browser tetap `/uploads/<id>.webp` melalui backend.
4. Produk terbit terlihat di toko. Katalog cloud awal memang kosong, tidak otomatis diisi produk demonstrasi.
5. Daftar sebagai pembeli, simpan alamat, tambah keranjang, lalu checkout. Pesanan muncul pada akun pembeli dan admin. Pembeli lain tidak bisa membacanya.
6. `/admin` pada toko mengarah ke domain admin. API admin langsung pada toko ditolak tanpa kunci gateway, sementara katalog dan akun pembeli tetap berfungsi.

Health check 503 biasanya berarti migrasi belum dijalankan, connection string salah, atau backend belum tersedia. Periksa Vercel logs secara pribadi; jangan menempelkan secret ke chat. Jika login admin gagal, periksa akun pemilik, kunci gateway identik, dua URL production, dan apakah backend terhalang Deployment Protection. Foto gagal: periksa bucket privat dan secret key baru pada project toko.

## Domain sendiri dan pembaruan

Pasang domain publik pada project toko dan subdomain/domain admin pada project admin. Setelah DNS/HTTPS aktif, ubah dua variabel URL antarproject dan redeploy. Cookie masing-masing domain tetap terpisah. Push ke branch `main` dapat memperbarui kedua project yang terhubung ke branch tersebut.

## Batas dan pengujian

Transaksi PostgreSQL aplikasi menggunakan satu advisory lock per schema untuk menjaga stok dan idempotensi di beberapa instance serverless. Ini cocok untuk toko awal dengan trafik ringan; bukan arsitektur marketplace besar. Aplikasi tidak menjalankan DDL atau menulis file sesi/produk di cold start PostgreSQL. Koneksi ditutup setelah setiap request. Pembayaran, email dan pengiriman masih manual.

```sh
.venv/bin/python -m unittest discover -s tests -v
ANREDSELLER_TEST_DATABASE_URL=<URL_DATABASE_UJI_LOKAL> .venv/bin/python -m unittest discover -s tests -v
ANREDSELLER_TEST_DATABASE_URL=<URL_DATABASE_UJI_LOKAL> ANREDSELLER_TEST_ADMIN_PORTAL=1 python3 tests/browser_smoke.py
```

Test PostgreSQL memakai schema sementara yang dihapus sesudahnya; jangan menunjuk database produksi. Pengujian Storage menggunakan server HTTP tiruan yang menguji kontrak Supabase, bukan bucket cloud milikmu. Keberhasilan pengujian lokal tidak berarti project Supabase/Vercel sudah dihubungkan atau dipublikasikan.
