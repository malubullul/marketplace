# Ukuran dan stok produk

Admin dapat mengelola stok per ukuran pada satu produk, misalnya S 5, M 8, L 4, XL 3. Setiap ukuran berdiri sendiri; angka total merupakan jumlah stok tersedia semua ukuran. Persediaan warna masih digabung pada ukuran yang sama, bukan dipisah per kombinasi ukuran/warna.

## Memasukkan dan menambah stok

1. Buka **Admin → Koleksi produk → Tambah produk / Edit**.
2. Pada **Ukuran & stok**, aktifkan **Kelola stok per ukuran**.
3. Pilih S, M, L, XL, atau ukuran lainnya lalu tekan **Tambah ukuran**. Masukkan stok tersedia pada baris masing-masing. Untuk nomor sepatu atau ukuran khusus, pilih **Ukuran lain…** dan masukkan satu ukuran saja.
4. Untuk restok, isi **Tambah (pcs)** pada baris ukuran yang sudah ada lalu tekan **Tambah**. Contoh M 3 ditambah 5 menjadi M 8. Ukuran lain tetap sama. Ukuran baru dapat ditambahkan pada produk yang sama.
5. Tekan **Simpan draf** atau **Terbitkan produk** untuk menyimpan. Penambahan pada editor belum diterapkan ke toko sebelum disimpan. Total stok otomatis, tidak diisi ulang secara terpisah.

Ukuran tidak boleh duplikat; `s` dinormalisasi menjadi `S`. Satu baris tidak boleh berisi gabungan seperti `S M XL`. Stok nol berarti ukuran habis. Maksimal 20 ukuran, total maksimal satu juta unit. Produk tanpa ukuran dapat tetap memakai kolom stok biasa. Setelah stok per ukuran diaktifkan dan disimpan, klien lama tidak bisa menimpanya dengan stok gabungan.

Daftar produk admin menampilkan total dan ringkasan stok tiap ukuran. Di toko, pilihan ukuran ditampilkan satu per satu dengan stoknya, ukuran habis tidak dapat dipilih, dan jumlah pembelian dibatasi sesuai ukuran yang dipilih. Keranjang serta ringkasan checkout mencantumkan ukuran.

## Produk lama

Data lama tidak dibagi rata atau ditebak. Jika produk sebelumnya memiliki total 20 pcs, aktifkan pengelolaan ukuran dan alokasikan tepat 20 pcs ke ukuran yang benar terlebih dahulu, misalnya S 5, M 8, L 4, XL 3. Sesudah pembagian pertama disimpan, tiap ukuran bisa direstok atau disesuaikan. Label lama seperti `S m xl` akan disarankan sebagai S, M, dan XL di editor, tanpa mengarang persediaannya.

Pembagian stok lama dan penghapusan ukuran ditolak bila menghilangkan tempat pengembalian stok pesanan aktif. Selesaikan atau batalkan pesanan terkait dahulu. Ukuran yang sudah dipakai pesanan aktif tetap bisa direstok; ukuran baru juga dapat ditambahkan. Pembeli yang memiliki pilihan ukuran lama di keranjang perlu menggantinya dengan pilihan ukuran yang tersedia.

## Saat ada pesanan

- **Checkout berhasil:** stok ukuran yang dibeli langsung dicadangkan, sehingga tidak bisa dijual dua kali. Dua pembeli yang berebut satu stok S tidak bisa memakai stok M untuk menutupi kekurangannya. Harga, ukuran, jumlah, stok dan promo diperiksa dalam satu transaksi database.
- **Pembayaran, Diproses, Dikirim, Selesai:** stok tetap terpotong; tidak dikurangi dua kali saat selesai. Jumlah terjual tetap mengikuti pesanan selesai.
- **Dibatalkan atau kedaluwarsa:** stok kembali satu kali ke ukuran asal, termasuk setelah admin melakukan restok. Aturan penahanan, laporan transfer dan larangan pembatalan pesanan dibayar/dikirim tetap mengikuti [keamanan transaksi](TRANSACTION_SAFETY.md).
- **Editor admin terbuka ketika checkout masuk:** penyimpanan dari versi lama ditolak agar stok baru tidak tertimpa. Muat ulang produk sebelum melanjutkan edit.

Rincian stok tersimpan sebagai `stokUkuran` pada dokumen produk yang sudah ada; total `stok` dan pilihan `ukuran` diturunkan dari rincian tersebut oleh server. Tidak memerlukan migrasi SQL baru atau database terpisah. Pesanan lama dan produk yang belum dikonversi tetap dapat dibaca.

## Pengujian

`tests/test_size_stock.py` mencakup validasi, total, transaksi beberapa ukuran, pembelian stok terakhir secara bersamaan, pooling warna dalam ukuran yang sama, keranjang/promo, restok, pembatalan/kedaluwarsa, konflik versi, dan konversi stok lama tanpa mengubah jumlah persediaan. Kontrak yang sama berjalan pada PostgreSQL melalui `tests/test_postgres.py`.

`tests/browser_size_stock_smoke.py` menjalankan editor S/M/L/XL, restok M, ukuran habis, batas jumlah, keranjang beberapa ukuran, checkout, konfirmasi pembayaran, penyelesaian tanpa potongan ganda, dan penambahan XXL pada produk yang sama. Menggunakan toko/admin berbeda origin serta ukuran layar 320, 390, 768, 844 landscape, dan 1440px; tidak mengubah database produksi atau mengirim WhatsApp/email.

Hasil pemeriksaan perubahan ini: 106 kontrak SQLite yang sudah ada, 8 kontrak stok ukuran SQLite, dan 101 kontrak PostgreSQL lulus (215 pemeriksaan berhasil). Browser ukuran lulus pada kedua database dengan 10 pemeriksaan layout per database. Regresi belanja melalui portal admin terpisah, browser promo (21 layout), dan suite responsif umum (231 pemeriksaan) juga lulus. Screenshot editor/detail diperiksa pada HP dan desktop. Database produksi belum diubah oleh pengujian ini.
