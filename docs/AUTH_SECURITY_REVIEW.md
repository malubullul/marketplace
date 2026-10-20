# Keamanan akun Anredseller

Login pembeli menggunakan email dan kata sandi. Fitur login Google dihapus atas permintaan pemilik sebelum aktivasi produksi. Tombol, alur penghubungan, callback, konfigurasi, dependensi khusus dan pembuatan tabel Google tidak lagi disertakan.

Data akun, alamat, keranjang dan pesanan tidak dihapus. Jika migrasi Google pernah dijalankan di database eksternal, tabel lama tidak dihapus secara otomatis; aplikasi tidak lagi menggunakannya. Tidak ada migrasi destruktif pada perubahan ini.

## Perlindungan yang dipertahankan

- Password disimpan sebagai hash, bukan teks asli. Login menolak akun tanpa hash password yang valid dan menggunakan pemeriksaan hash dummy pada kegagalan untuk mengurangi perbedaan waktu respons.
- Token sesi disimpan sebagai hash dan dirotasi setelah autentikasi. Cookie HttpOnly dan SameSite=Lax; Secure default pada Vercel.
- Perubahan data memerlukan autentikasi dan token CSRF. Percobaan login dan penggantian password dibatasi.
- Ganti password memerlukan password lama dan mencabut sesi perangkat lain. Keluar dari semua perangkat hanya mencabut sesi pembeli yang bersangkutan.
- Data pribadi dibatasi sesuai akun pembeli; portal admin tetap memiliki autentikasi terpisah.

Peninjauan sebelumnya menggunakan skill Trail of Bits [sharp-edges](../.agents/skills/sharp-edges/SKILL.md). Ini peninjauan terarah, bukan sertifikasi keamanan seluruh aplikasi.

## Batas

Verifikasi email dan pemulihan kata sandi melalui email/SMS belum tersedia. Pemantauan penyalahgunaan, kebijakan proxy/rate limiting di hosting, dan backup perlu dioperasikan sesuai kebutuhan produksi.

Pengujian memakai database dan akun sementara; tidak mengubah data Supabase produksi. Hasil verifikasi saat penghapusan Google:

- 33 tes backend lolos; 1 kontrak PostgreSQL dilewati karena database uji PostgreSQL tidak dikonfigurasi pada pemeriksaan ini.
- Pengujian browser daftar/login email, alamat, wishlist, keranjang lintas perangkat, checkout dan riwayat pesanan lolos, termasuk dengan origin admin/publik terpisah.
- 231 pemeriksaan responsif pada 13 halaman/status dan 14 ukuran layar lolos.
- Regresi memastikan endpoint Google tidak tersedia, tidak terdaftar di routing, dan kontrol Google tidak ada di halaman akun.
- Sintaks JavaScript dan git diff --check lolos.

## Pembayaran dan CS melalui WhatsApp

Pengaturan dua nomor membutuhkan sesi pemilik, CSRF, serta gateway portal admin bila digunakan. Nomor divalidasi dan dinormalisasi di server; API tidak menerima URL tujuan bebas. Respons publik hanya berisi dua nomor kontak toko. Login pembeli tidak memberikan izin mengubahnya.

Pesan pembayaran dibuat dari pesanan yang dibaca melalui endpoint privat pemilik pesanan, berisi referensi, produk dan total. Alamat, email dan nomor HP pembeli tidak dimasukkan otomatis ke pesan. Pesan hanya disiapkan saat tautan diklik; situs tidak mengirim pesan lewat API WhatsApp. Klik tautan tidak mengubah status pesanan atau menandakan pembayaran lunas.

Verifikasi backend terbaru: **73 tes lolos tanpa skip**, mencakup SQLite dan PostgreSQL sementara, otorisasi pengaturan, CSRF, normalisasi, penyimpanan ulang, penolakan URL berbahaya, dan jalur gateway admin. Lihat [panduan dan verifikasi WhatsApp](WHATSAPP.md).
