# Tahap 01: keamanan transaksi

Perubahan ini memisahkan status pembayaran dari pemenuhan pesanan, menambahkan pemeriksaan email, pembatalan mandiri, batas pembayaran opsional, serta riwayat aktivitas privat. Pembayaran tetap melalui WhatsApp dan diperiksa manusia; tidak ada integrasi rekening, penarikan uang, atau refund otomatis.

## Pemilik: memeriksa pembayaran dan pesanan

1. Buka **Pesanan masuk → Lihat rincian**. Pembeli dapat menekan **Sudah transfer**, tetapi laporan itu belum menyatakan pembayaran lunas.
2. Cocokkan nominal dan referensi dengan mutasi rekening. Isi **Referensi pemeriksaan (hanya admin)** lalu tekan **Verifikasi pembayaran**. Identitas pemilik, waktu, dan referensi pemeriksaan disimpan oleh server; referensi dan identitas pemeriksa tidak dikirim ke pembeli.
3. Setelah pembayaran terverifikasi, status hanya dapat maju **Baru → Diproses → Dikirim → Selesai**. Pembeli melihat status pembayaran dan pemenuhan secara terpisah. Rating tetap mensyaratkan pesanan selesai.
4. **Tolak laporan transfer** mengembalikan pembayaran ke menunggu transfer dan memberikan jendela pembayaran penuh yang baru. Gunakan hanya sesudah pemeriksaan. **Tahan pembatalan otomatis** melindungi pesanan selama pemeriksaan; melepas penahanan juga memberikan jendela baru.

Pesanan yang sudah dibayar, dilaporkan transfer, ditahan, dikirim, atau selesai tidak dapat dibatalkan melalui pembatalan biasa. Refund/retur memerlukan penanganan CS dan termasuk tahap 02; jangan mengubah catatan pembayaran hanya untuk mengembalikan stok. Pembeli hanya dapat membatalkan pesanan miliknya yang masih baru, menunggu transfer, dan tidak ditahan. Perubahan dari tab lama ditolak: muat ulang rincian sebelum mencoba lagi.

Pesanan lama tanpa catatan pembayaran tidak dianggap sudah dibayar otomatis. Untuk pesanan lama yang sedang diproses/dikirim, pemilik memeriksa pembayaran terlebih dahulu sebelum melanjutkan status. Riwayat lama tetap dapat dibaca. Produk dengan pesanan aktif tidak dapat dihapus; gunakan **Simpan draf** untuk menyembunyikannya dari katalog.

## Batas pembayaran

**Admin → Keamanan transaksi** menyediakan pilihan aktif/nonaktif dan waktu 1–168 jam. Default **nonaktif**, dengan opsi awal 24 jam. Ketentuan ditampilkan sebelum checkout dan disalin ke pesanan saat dibuat. Perubahan pengaturan hanya berlaku untuk pesanan baru; mematikan pengaturan tidak membatalkan tenggat yang sudah disepakati pada pesanan sebelumnya. Pesanan lama tanpa tenggat tidak kedaluwarsa otomatis.

Setelah batas waktu, hanya pesanan baru yang masih menunggu transfer, belum dilaporkan transfer, dan tidak ditahan yang dapat kedaluwarsa. Stok dikembalikan satu kali dan kuota promo dilepas dalam transaksi yang sama. Pelanggan harus melaporkan transfer **sebelum tenggat**, dan pemilik perlu rutin memeriksa laporan. Transfer terlambat atau transfer yang tidak dilaporkan perlu ditangani melalui CS; aplikasi tidak bisa mengetahui mutasi rekening secara otomatis.

Pembersihan dijalankan saat katalog, checkout, preview promo, atau pesanan dibaca (maksimal 100 per permintaan). Ini bukan jaminan eksekusi tepat pada detik tenggat ketika toko tidak dikunjungi. Untuk pemeriksaan berkala tanpa kunjungan:

- Buat rahasia acak minimal 32 karakter dan simpan sebagai `CRON_SECRET` pada **project toko**. Jangan letakkan nilainya di Git atau URL.
- Konfigurasikan scheduler untuk `GET` atau `POST https://DOMAIN-TOKO/api/internal/expire-orders`, dengan header `Authorization: Bearer <CRON_SECRET>`. Endpoint memproses maksimal 500 pesanan per panggilan; ulangi secara berkala jika antrean besar.
- Vercel Cron dapat memakai header otomatis dari `CRON_SECRET`; jadwal dan batas frekuensinya harus mengikuti paket hosting. Repository belum memasang jadwal atau layanan berbayar secara otomatis.
- Tanpa secret endpoint menolak akses. Penahanan/laporan pembayaran tetap dihormati oleh scheduler.

## Aktivasi verifikasi email

Verifikasi memakai autentikasi aplikasi yang sudah ada dan Resend, bukan Supabase Auth atau login Google. Kode tersedia dengan rollout eksplisit agar deployment tidak memutus pendaftaran sebelum pengirim email siap.

1. Siapkan domain pengirim Resend dan variabel `RESEND_API_KEY`, `ANREDSELLER_EMAIL_FROM`, serta `ANREDSELLER_PUBLIC_URL` melalui [panduan email](REVIEWS_AND_RECOVERY.md). Domain toko boleh tetap `vercel.app`; pengirim email membutuhkan domain yang DNS-nya dapat dikelola.
2. Untuk Supabase yang sudah menjalankan migrasi 001 dan 004, jalankan [005_email_verification.sql](../migrations/005_email_verification.sql) melalui SQL Editor. Migrasi dapat diulang, tidak menghapus akun, dan tidak menganggap akun lama terverifikasi. Tabel tetap privat dengan RLS dan tanpa akses `PUBLIC`, `anon`, atau `authenticated`. Cold start tidak memigrasikan database produksi.
3. Pada project toko Vercel, isi **`ANREDSELLER_REQUIRE_VERIFIED_EMAIL=1`**, kemudian redeploy. Nilai yang diterima hanya `0` atau `1`; bukan `true`/`false`.
4. Buka **Admin → Keamanan transaksi** untuk melihat kesiapan konfigurasi. Status siap menunjukkan konfigurasi dan tabel tersedia, bukan bukti email sudah terkirim. Uji pengiriman ke alamat milik sendiri dan periksa inbox/spam sebelum membuka pendaftaran umum.

Saat aktif, pendaftaran hanya meminta email. Akun belum dibuat dan belum login sampai tautan dipakai, nama/nomor HP diisi, dan kata sandi baru ditentukan. Akun lama tetap bisa login dan membaca riwayat, tetapi harus membuktikan email sebelum membuat pesanan baru. Verifikasi akun lama menetapkan kata sandi baru dan mencabut seluruh sesi lama untuk mencegah akun yang sebelumnya didaftarkan orang lain tetap dapat diakses oleh orang tersebut.

Tautan berlaku 30 menit, sekali pakai, acak 256 bit; hanya hash token disimpan. Tautan dikirim ke origin HTTPS terkonfigurasi, token pada `#verify=` segera dihapus dari alamat browser. Permintaan dibatasi per IP dan per alamat; pesan dan jalur pengiriman sama untuk email baru/lama. Token yang diterbitkan sebelum suatu akun dibuat tidak boleh mengambil alih akun yang kemudian muncul. Reset kata sandi yang berhasil juga menjadi bukti kepemilikan email ketika migrasi 005 sudah tersedia, lalu mencabut sesi dan tautan tertunda.

Jika flag `1` aktif tetapi migrasi/pengirim belum siap, pendaftaran baru dan checkout ditolak dengan pesan layanan belum siap. Tidak ada penurunan diam-diam ke pendaftaran tanpa verifikasi. Default flag `0` mempertahankan pendaftaran lama; ini hanya mode kompatibilitas sebelum aktivasi dan **belum melindungi pendaftaran dengan verifikasi wajib**.

## Riwayat aktivitas dan batas operasional

**Admin → Riwayat aktivitas** mencatat login/logout pemilik, perubahan produk, foto, promo, kontak, konten, ketentuan pembayaran, pesanan dan pembayaran sejak fitur dipasang. Riwayat per pesanan tersedia pada rincian. Data menggunakan tabel `metadata` privat yang sudah ada; tidak memerlukan migrasi tambahan selain email. Pagination memakai cursor, bukan daftar semua aktivitas sekaligus. Kredensial, token, isi formulir, dan alamat pembeli tidak dimasukkan ke aktivitas.

Log membantu penelusuran operasional tetapi belum merupakan arsip tahan manipulasi oleh administrator database. Backup/retensi, MFA pemilik, pemantauan, laporan keuangan, stok varian, resi, ongkir aktual, retur/refund, dan notifikasi email status masih tercantum dalam [roadmap](ROADMAP.md).

## Pengujian lokal

```sh
.venv/bin/python -m unittest discover -s tests -p 'test_*.py'
python3 tests/browser_transaction_safety_smoke.py
```

Set `ANREDSELLER_TEST_DATABASE_URL` hanya ke PostgreSQL sementara untuk menguji database tersebut. Suite menjalankan kondisi bersamaan, isolasi akun, CSRF, status final, pembayaran privat, stok/kuota promo, migrasi yang belum tersedia, token kedaluwarsa/sekali pakai, dan pencabutan sesi. Browser memakai origin toko/admin terpisah, outbox email lokal, serta lima ukuran layar. Tidak mengirim email/WhatsApp, memindahkan uang, atau mengubah Supabase produksi.

Hasil pemeriksaan 27 Oktober 2026:

- 189 kontrak backend pada suite gabungan SQLite/PostgreSQL lulus tanpa skip, lalu dua kontrak tambahan untuk penolakan laporan dan pelepasan penahanan lulus pada kedua database (191 total).
- Browser tahap 01 lulus pada SQLite dan PostgreSQL: pendaftaran lewat email, verifikasi, checkout dengan ketentuan, laporan transfer, verifikasi privat, pemenuhan berurutan, pembatalan pembeli, akun, dan pagination aktivitas melalui gateway. Masing-masing 17 pemeriksaan layout pada lebar 320, 390, 768, 844 landscape, dan 1440px.
- Regresi belanja dengan admin/toko berbeda origin, rating/pemulihan (15 layout), WhatsApp (5 viewport), dan promo (21 layout) lulus. Suite responsif umum lulus 231 pemeriksaan pada 13 halaman/status dan 14 ukuran layar.
- Screenshot desktop dan HP diperiksa; menu admin dapat digulir pada layar pendek, tombol transaksi memiliki area sentuh minimal 44px, dan tombol CS tidak menutupi formulir akun. Pemeriksaan sintaks Python/JavaScript serta whitespace diff lulus.

Hasil ini berasal dari lingkungan sementara. Pengiriman email sungguhan, pemasangan scheduler, migrasi Supabase pengguna, dan uji transaksi produksi belum dilakukan.
