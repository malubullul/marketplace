# Pembayaran dan customer service lewat WhatsApp

## Mengganti nomor tanpa mengedit kode

1. Masuk ke domain admin yang biasa digunakan, atau buka `/admin.html` dari toko jika portal terpisah belum dipasang.
2. Pilih **Kontak WhatsApp** pada navigasi admin.
3. Ubah **Nomor WA pembayaran** dan/atau **Nomor WA customer service**. Format `08…`, `62…`, atau `+62…` diterima. Untuk nomor luar Indonesia, sertakan kode negara.
4. Klik **Simpan kontak**. Nomor disimpan di database toko yang sama dan dipakai saat halaman toko dimuat kembali. Tidak perlu mengedit GitHub atau mengisi environment variable Vercel.

Menu ini juga dapat dibuka lewat `/#settings` di domain admin. Nomor awal sesuai permintaan pemilik:

| Tujuan | Nomor awal |
| --- | --- |
| Pembayaran | 087729766809 |
| Customer service | 082335963140 |

Nomor awal hanya dipakai selama belum ada pengaturan tersimpan. Mengosongkan nomor secara sengaja menonaktifkan tautan untuk jalur tersebut; aplikasi tidak menggantinya dengan nomor jalur lain atau mengembalikan nomor awal. Pastikan nomor yang dipasang aktif di WhatsApp.

## Alur pembeli

1. Pembeli masuk/daftar menggunakan email dan kata sandi, memilih produk, lalu mengisi alamat checkout.
2. **Buat pesanan & lanjut pembayaran** menyimpan pesanan dan membuka halaman konfirmasi. Harga, total dan stok tetap dihitung/diperiksa server; pengiriman ulang checkout tidak membuat pesanan ganda.
3. **Lanjut pembayaran via WhatsApp** membuka nomor pembayaran dengan pesan yang sudah memuat nomor pesanan, produk/varian/jumlah dan total. Pembeli perlu memeriksa lalu mengirim pesan tersebut.
4. Admin pembayaran memberi instruksi transfer dan menerima bukti di percakapan WhatsApp. Situs tidak mengunggah bukti transfer atau menyimpan rekening baru pada perubahan ini.
5. Setelah memeriksa transfer, pemilik mengubah status pesanan ke **Diproses** melalui **Pesanan masuk**. Ada konfirmasi sebelum meninggalkan status **Menunggu pembayaran**.

Membuka WhatsApp atau mengirim bukti pembayaran tidak otomatis membuat pesanan lunas. Pembeli dapat melanjutkan pembayaran dari **Akun → Pesanan → Lihat rincian → Lanjut pembayaran**. Pesanan yang sudah diproses, dikirim, selesai, atau dibatalkan tidak menampilkan tombol pembayaran kembali.

**Hubungi CS** tersedia sebagai tombol bantuan di toko, footer, dan checkout. Panel bantuan menjelaskan tugas CS dan membuka nomor CS yang terpisah. Pembayaran diarahkan kembali ke rincian pesanan.

## Penyimpanan dan akses

- `GET /api/store/contacts`: hanya dua nomor kontak bisnis, tanpa data pelanggan.
- `GET/PUT /api/admin/contacts`: hanya pemilik; perubahan membutuhkan CSRF. Portal admin meneruskan endpoint melalui gateway yang sudah ada.
- `metadata.store_contacts`: satu dokumen pengaturan di SQLite lokal atau schema privat PostgreSQL produksi. Tabel metadata sudah ada; tidak perlu migrasi baru.
- Tujuan browser selalu `https://wa.me/<nomor>`; input berupa URL/HTML, parameter tambahan, tipe data lain atau nomor di luar batas ditolak.
- Pesan tidak memasukkan email, alamat atau nomor HP pembeli secara otomatis. Tidak ada API WhatsApp Business, pesan otomatis yang dikirim server, payment gateway, atau konfirmasi bank otomatis.

## Tampilan dan verifikasi

Komponen mengikuti [taste-skill](../.agents/skills/design-taste-frontend/SKILL.md) dan gaya Framed sheet sebelumnya, seed 2058406519: Switzer, warna stone/olive, formulir berlabel, dan tombol yang cukup besar untuk HP. Tidak ada arah visual baru atau foto tambahan. Menu kontak menyembunyikan ringkasan statistik agar pengaturan nomor langsung terlihat. Pertanyaan layar: ke nomor mana pembayaran dan bantuan pelanggan diarahkan?

- **73 tes backend lolos** tanpa skip pada SQLite dan PostgreSQL sementara.
- Alur browser admin/publik terpisah lolos: ganti nomor lewat formulir, simpan, muat ulang, WhatsApp pembayaran/CS terpisah, total sesuai server, akses ulang dari riwayat, dan kondisi nomor dinonaktifkan.
- Browser memeriksa bahwa membuka WhatsApp tetap meninggalkan pesanan pada status `baru`. Tujuan WhatsApp dicegat lokal dalam pengujian; tidak menghubungi atau mengirim pesan ke nomor sungguhan.
- **231 pemeriksaan responsif** pada 13 halaman/status dan 14 ukuran layar lolos. Komponen baru diperiksa tambahan pada 1440, 768, 390, 320, dan 844px landscape.
- Screenshot kontak, pembayaran dan CS diperiksa pada desktop dan HP. Formulir kontak serta tombol pembayaran/CS memakai data aplikasi nyata dari fixture sementara; produk/foto toko tetap aset contoh yang sudah didokumentasikan.

Pemeriksaan tambahan memakai fungsi native `probe/layout/app` dan aturan `judge/judgeLayout/judgeApp` dari taste-skill pada browser Playwright yang sama, di 1440/768/390: **0 FAIL** setelah perbaikan kontras. Ini pemeriksaan fungsi native terhadap layar autentikasi yang sudah dibuka, bukan klaim menjalankan CLI inspector pada sesi login baru. Allowance `no-title` hanya untuk pengaturan admin, karena probe mengambil h1 login yang tersembunyi sebelum h1 pengaturan yang terlihat; jumlah h1 yang terlihat diverifikasi satu. WARN yang dipertahankan: judul ringkas sesuai layar transaksi, skala huruf yang mencakup footer/produk toko lama, serta rincian/rekomendasi yang memang berada setelah tombol pembayaran. Screenshot diperiksa kembali setelah perbaikan.

Tombol CS melayang mengikuti permintaan pemilik untuk bantuan seperti situs broker. Pada checkout dan konfirmasi pembayaran, bantuan memakai tombol dalam alur halaman agar tidak menutupi formulir atau tombol pembayaran pada HP.
