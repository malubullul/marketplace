# Rating, jumlah terjual, dan lupa kata sandi

## Cara pembeli memberi rating

1. Toko memverifikasi pembayaran WhatsApp, memproses, mengirim, lalu menandai pesanan **Selesai** di admin.
2. Pembeli membuka **Akun → Pesanan saya → Lihat rincian → Nilai [produk]**. Rating juga tersedia pada tab **Ulasan** di detail produk.
3. Pilih 1–5 bintang dan komentar opsional maksimal 1.000 karakter. Rating dapat diperbarui; satu akun menyumbang satu rating per produk meskipun membeli beberapa kali.

Kelayakan diperiksa di server menggunakan pemilik pesanan dan produk yang benar-benar dibeli. Login admin, pesanan belum selesai, dan pesanan dibatalkan tidak memenuhi syarat. Nama publik disamarkan menjadi inisial; email, alamat, nomor HP, ID akun dan nomor pesanan tidak diterbitkan. Komentar di-escape sebagai teks. Pembeli diingatkan agar tidak menulis data pribadi.

**Terjual** adalah jumlah unit pada pesanan berstatus `selesai`, bukan jumlah klik, checkout, atau jumlah pesanan. Contoh: satu pesanan berisi dua ukuran dari produk yang sama dengan jumlah 1 dan 2 menambah **3 terjual**. Mengulangi penyimpanan status selesai tidak menambah angka dua kali. Pesanan batal atau menunggu pembayaran tidak dihitung. Angka rating/terjual contoh tidak lagi digunakan.

## Migrasi database yang sudah berjalan

Di **Supabase → SQL Editor**, jalankan isi [004_reviews_recovery.sql](../migrations/004_reviews_recovery.sql). Database baru memerlukan `001_supabase.sql` terlebih dahulu. Alternatif dengan environment lokal yang sudah terhubung: `python server.py init-db`, yang menjalankan migrasi 001, 004, dan 005 secara berurutan.

Migrasi dapat diulang, tidak menghapus akun/produk/pesanan, dan mengisi `order_items` dari pesanan lama. Tabel `order_items`, `product_reviews`, dan `password_resets` berada di schema privat `anredseller`, memakai RLS dan tanpa hak akses Data API untuk `PUBLIC`, `anon`, atau `authenticated`. Semua akses melalui backend. Tidak diperlukan service-role key di browser.

Sebaiknya jalankan migrasi sebelum deployment. Jika belum dijalankan, katalog dan checkout tetap tersedia, metrik baru ditandai belum tersedia, dan ulasan/pemulihan belum diaktifkan. Item pesanan selama masa ini ikut diisi ketika migrasi dijalankan. Cold start Vercel tidak menjalankan migrasi otomatis. SQLite lokal membuat tabel dan mengisi item lama saat startup.

## Menyiapkan Resend untuk lupa kata sandi

Buka [Resend](https://resend.com), buat akun, lalu:

1. Tambahkan domain pengirim pada menu **Domains**. Bisa memakai subdomain seperti `mail.anredseller.com`.
2. Salin persis record DNS yang diberikan Resend ke penyedia DNS domain. Tunggu status **Verified**. Gunakan record dari dashboard; jangan menebak nilai SPF/DKIM.
3. Buat API key dengan izin **Sending access** untuk domain itu.
4. Pada **Vercel → project toko publik → Settings → Environment Variables**, isi:

```dotenv
ANREDSELLER_PUBLIC_URL=https://marketplace-theta-ebon.vercel.app
ANREDSELLER_EMAIL_FROM=akun@mail.DOMAIN-MILIKMU.com
RESEND_API_KEY=ISI_DI_VERCEL_SAJA
```

Alamat `ANREDSELLER_EMAIL_FROM` harus berada di domain yang sudah diverifikasi. Ganti contoh dengan domain milikmu. Domain website boleh tetap `vercel.app`; domain email pengirim harus bisa kamu kelola DNS-nya. Jangan menambahkan key ke repository, HTML, atau JavaScript. Ketiga variabel hanya untuk **project toko**, bukan project admin. Setelah mengisi variabel Production, redeploy project toko. Preview sebaiknya memakai origin dan pengiriman terpisah agar tautan tidak mengarah ke produksi.

Tanpa konfigurasi pengirim, tombol **Lupa kata sandi?** tetap menjelaskan bahwa email belum aktif, menonaktifkan pengiriman, dan menyediakan akses CS. Aplikasi tidak berpura-pura mengirim email. Konfigurasi pengirim yang terisi sebagian/tidak aman ditolak. Kesalahan provider ditampilkan sebagai kegagalan pengiriman tanpa membeberkan data provider atau akun.

Domain pengirim Resend yang belum diverifikasi hanya cocok untuk pengujian terbatas sesuai aturan Resend; belum cukup untuk mengirim ke semua pelanggan.

## Alur dan batas keamanan

- Pembeli memasukkan email, menerima tautan berlaku **30 menit**, membuat kata sandi **12–128 karakter**, lalu masuk kembali.
- Token acak 256 bit, hanya hash SHA-256 yang disimpan. Token pada fragmen `#reset=…` tidak dikirim pada permintaan halaman atau referrer; JavaScript segera menghapus fragmen dari alamat dan menyimpan token hanya di memori. Jangan membagikan tautannya.
- Tautan memakai origin HTTPS dari konfigurasi; header `Host` atau URL dari permintaan tidak bisa mengganti tujuannya. Permintaan provider memakai endpoint HTTPS tetap, validasi sertifikat bawaan dan menolak redirect.
- Permintaan pengiriman dibatasi 10 per IP per 15 menit, maksimal 3 pengiriman per alamat per 15 menit. Alamat pembatas disimpan sebagai digest. Percobaan reset juga dibatasi. Tambahkan proteksi hosting sesuai trafik bila nanti tumbuh.
- Respons, pengiriman email, dan kegagalan provider sama untuk alamat terdaftar maupun belum terdaftar. Email menggunakan kalimat bersyarat yang sama. Token untuk alamat belum terdaftar tidak terkait akun dan tidak dapat dipakai, termasuk apabila alamat itu kemudian mendaftar. Ini mencegah pengungkapan keberadaan akun melalui waktu pengiriman/error provider; batas pengiriman mencegah spam berulang.
- Mengirim permintaan saja tidak mengubah kata sandi atau mengeluarkan perangkat. Token dipakai secara atomik; dua permintaan bersamaan hanya bisa menghasilkan satu perubahan yang berhasil.
- Reset berhasil mencabut seluruh sesi pembeli itu dan semua tautan resetnya. Tidak otomatis login dan tidak memengaruhi akun lain atau sesi admin. Ganti password biasa juga membatalkan tautan reset yang masih tertunda.
- Ini pemulihan **akun pembeli**. Akun pemilik tetap menggunakan prosedur CLI `reset-password` yang sudah ada. Google login tetap tidak diaktifkan.

Mengisi email saja belum membuktikan kepemilikannya. [Tahap 01 keamanan transaksi](TRANSACTION_SAFETY.md) menambahkan pendaftaran melalui tautan email dan verifikasi akun lama; aktivasi memerlukan migrasi 005 dan flag hosting. Setelah migrasi 005 tersedia, reset kata sandi yang berhasil juga mencatat bukti kepemilikan email dan membatalkan tautan verifikasi tertunda. MFA admin dan otomatisasi pembayaran/pengiriman masih menjadi pekerjaan terpisah.

## Pengujian

```sh
.venv/bin/python -m unittest discover -s tests -p 'test_*.py'
python3 tests/browser_reviews_recovery_smoke.py
ANREDSELLER_TEST_ADMIN_PORTAL=1 python3 tests/browser_smoke.py
python3 tests/responsive_smoke.py
```

Set `ANREDSELLER_TEST_DATABASE_URL` hanya ke PostgreSQL sementara untuk menjalankan kontrak database dan browser pada PostgreSQL. Tidak menggunakan database produksi. Pengiriman Resend diganti pengirim/outbox lokal sementara dalam pengujian; tidak ada email sungguhan dikirim. Pengiriman produksi perlu diperiksa setelah domain dan key Resend diaktifkan.

### Hasil verifikasi perubahan ini

- **104 tes backend lolos tanpa skip** pada SQLite dan PostgreSQL sementara. Termasuk rating tanpa pembelian/CSRF, validasi, identitas, rata-rata, pembaruan konkuren, jumlah unit, pengulangan migrasi, fallback sebelum migrasi, expiry/replay reset, pencabutan sesi, balapan konsumsi token, error/redirect provider, dan penolakan konfigurasi tidak aman.
- Browser rating/pemulihan lolos pada SQLite dan PostgreSQL dengan outbox sementara: daftar → pesanan selesai → rating → edit → katalog → lupa password → reset → sesi dicabut → masuk ulang; termasuk XSS, tautan lama, navigasi fragmen pada tab yang sudah terbuka dan kegagalan pengiriman. **15 pemeriksaan layout** pada 320, 390, 768, 844 landscape dan 1440px pada setiap backend.
- **231 pemeriksaan responsif** pada 13 halaman/status dan 14 ukuran layar lolos. Regresi belanja lengkap dengan origin toko/admin terpisah juga lolos.
- Pemeriksaan sintaks JavaScript/Python dan `git diff --check` lolos.
- Mengikuti arah visual Taste Skill yang sudah dipilih; komponen baru mempertahankan Switzer, batu/olive, bidang datar, tombol sentuh 44px dan fokus keyboard. Screenshot diperiksa pada desktop/tablet/ponsel. Native inspector `--app --allow emoji`: reset **0 FAIL/1 WARN**; detail ulasan **0 FAIL/3 WARN**. Allowance hanya untuk glif bintang rating yang sudah digunakan. Peringatan tersisa mengenai bidang foto akun, label kategori/tipografi produk yang dipertahankan, dan viewport berjangkar langsung ke tab ulasan; tidak ada kegagalan kontras baru. Kontras badge diskon diperbaiki setelah inspeksi.

Artefak pemeriksaan disimpan di workspace `preview/reviews-recovery/`, bukan sebagai foto/ulasan toko produksi. Aplikasi memakai akun dan pesanan contoh hanya pada fixture pengujian. Pengiriman email produksi dan perubahan database Supabase pengguna belum dilakukan oleh pengujian ini.
