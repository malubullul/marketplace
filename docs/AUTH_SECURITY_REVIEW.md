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

Verifikasi email saat pendaftaran dan pemulihan melalui SMS belum tersedia. Pemulihan kata sandi melalui email tersedia setelah Resend diaktifkan; lihat [panduan rating dan pemulihan](REVIEWS_AND_RECOVERY.md). Pemantauan penyalahgunaan, kebijakan proxy/rate limiting di hosting, dan backup perlu dioperasikan sesuai kebutuhan produksi.

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

## Rating dan pemulihan email

Peninjauan kembali memakai skill Trail of Bits `sharp-edges` untuk konfigurasi pengirim, token sekali pakai, pencabutan sesi, dan kegagalan provider. URL reset menggunakan origin tetap dan fragmen yang segera dihapus; tidak menerima origin dari header permintaan. Token memiliki masa hidup tetap 30 menit dan disimpan sebagai hash. Perubahan password dan konsumsi token berada dalam satu transaksi, termasuk pada permintaan bersamaan.

Email dan respons bersifat sama untuk alamat terdaftar/belum terdaftar; batas pengiriman berlaku per IP dan digest alamat. Token untuk alamat belum terdaftar tidak dapat mengubah akun. Tidak ada kredensial provider atau data pribadi penerima dalam log kegagalan. Domain pengirim harus terverifikasi sebelum menerima pelanggan umum.

Rating memerlukan pembelian milik sesi pembeli dengan status selesai; ID/nama pembeli dari payload tidak menentukan pemilik ulasan. Satu rating per akun/produk ditegakkan oleh primary key. Ringkasan dan jumlah terjual dihitung dari tabel ulasan/item pesanan, bukan angka yang dapat dikirim dari editor produk. API publik menyamarkan nama dan tidak memuat email, ID akun atau nomor pesanan.

Verifikasi rating/pemulihan: **104 tes backend lolos tanpa skip** pada SQLite/PostgreSQL; browser fitur baru lolos pada kedua backend, 231 pemeriksaan responsif regresi dan 15 layout fitur baru per backend lolos. Pengirim email memakai fixture lokal. Belum mengirim email produksi atau memigrasikan Supabase pengguna.

## Pengaturan tampilan dan media sosial

Kontrol konten memakai sesi pemilik/CSRF serta allowlist gateway yang sama; akun pembeli tidak memperoleh hak edit. Foto harus berasal dari aset bawaan yang diizinkan atau upload yang diperiksa server. URL gambar eksternal tidak diterima. Tautan sosial dibatasi HTTPS/domain platform dan tidak diambil oleh backend; label/deskripsi diperlakukan sebagai teks dan penutup script pada snapshot JSON di-escape. Versi pengaturan diperiksa dalam transaksi untuk mencegah tab/perangkat menimpa perubahan terbaru. Data disimpan di metadata privat yang sudah ada, tanpa tabel atau hak Data API baru. Lihat [panduan konten dan hasil pengujian](STORE_CONTENT.md).

## Kode promo partner

Peninjauan `sharp-edges` mencakup pengaturan nol/null, tipe boolean yang menyerupai angka, batas diskon, tanggal dan kuota: nol hanya berarti minimum belanja nol; kuota/per-akun nol ditolak. Null secara eksplisit berarti tanpa batas pada tanggal/kuota total/cap. Kode baru tidak aktif otomatis, kode lama yang ditulis tetap di program dihapus, dan pembeli tidak dapat mengubah pengaturannya. Gateway admin, sesi pemilik dan CSRF tetap wajib; versi pengaturan mencegah penimpaan dari tab lama.

Preview memakai akun/keranjang server dan memiliki anggaran pemeriksaan tersimpan per akun. Server tidak memercayai persentase, harga total atau diskon dari browser; nilai diskon yang diharapkan hanya dipakai untuk menolak total yang berubah. Validasi promo dan stok serta penulisan snapshot pesanan berlangsung atomik dalam transaksi. Penggunaan dihitung dari pesanan yang tidak dibatalkan, sehingga retry, pembatalan berulang, dua checkout bersamaan dan pergantian instance tidak menggandakan kuota. Snapshot lama tidak diubah ketika promo dinonaktifkan atau nominal/partner diedit. Nama partner di-escape sebagai teks pada antarmuka; kode potongan juga dicantumkan pada handoff WhatsApp, tanpa mengirim pesan otomatis.

Verifikasi fitur promo: **150 tes backend lolos tanpa skip** pada SQLite dan PostgreSQL sementara, termasuk 14 kontrak promo pada masing-masing backend. Browser promo di dua origin lolos pada kedua backend dengan 21 pemeriksaan layout per backend (5 ukuran layar), termasuk menu tablet. Pengujian alur belanja yang sudah ada juga lolos melalui portal admin terpisah. Tidak mengubah database produksi atau mengirim WhatsApp. Lihat [perilaku dan batas operasional promo](PROMO_CODES.md).

## Tahap 01 audit transaksi

Peninjauan mengikuti [Trail of Bits Sharp Edges](../.agents/skills/sharp-edges/SKILL.md) untuk pengaturan yang rawan salah pakai. Flag verifikasi hanya menerima `0`/`1`; jika diwajibkan tetapi tabel/pengirim belum siap, signup dan checkout ditolak. Akun lama harus membuktikan email, menetapkan password baru, dan mencabut sesi lama. Token baru tidak boleh mengambil alih akun yang dibuat setelah token diterbitkan. Token hanya disimpan sebagai hash, dibatasi waktu/pengiriman dan dikonsumsi atomik.

Status pembayaran terpisah dari pemenuhan, dengan pemeriksaan mutasi rekening oleh pemilik, referensi privat opsional, transisi berurutan, dan versi untuk menolak perubahan dari tab lama. Pembayaran terverifikasi/laporan transfer/penahanan melarang pembatalan biasa. Tenggat nonaktif sampai admin memilihnya dan checkout mengonfirmasi ketentuan terbaru. Kedaluwarsa dan pembatalan mengembalikan stok/kuota satu kali; pesanan lama tanpa tenggat tidak diubah. Aktivitas menggunakan metadata privat dan daftar detail yang diizinkan, bukan isi permintaan mentah.

Hasil lokal: **191 tes backend** lulus (189 suite gabungan dan 2 kontrak tambahan), browser tahap 01 pada kedua database, serta regresi belanja/rating/pemulihan/WhatsApp/promo dan 231 pemeriksaan responsif. Ini bukan audit eksternal atau bukti layanan produksi sudah aktif. [Panduan aktivasi dan batas fitur](TRANSACTION_SAFETY.md) memisahkan kode yang selesai dari konfigurasi Resend, migrasi 005, dan scheduler yang belum dipasang di hosting pengguna.
