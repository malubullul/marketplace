# Kode promo dan kolaborasi partner

Pemilik mengelola kode lewat **Admin → Kode promo → Buat kode promo**. Contoh kode `PARTNER15` hanya contoh penulisan; aplikasi tidak membuat atau mengaktifkan diskon otomatis. Kode lama yang dahulu ditulis tetap di JavaScript (`HEMAT10`, `ANRED15`, `SALE20`) juga harus dibuat secara eksplisit oleh pemilik jika ingin dipakai lagi.

## Pengaturan pemilik

- Kode unik 3–32 karakter: huruf Latin, angka, `-` dan `_`. Huruf kecil dinormalisasi ke huruf besar. Kode tidak dapat diganti setelah disimpan.
- Nama partner/brand ambassador opsional, maksimal 100 karakter. Pesanan menyimpan nama partner saat dibuat, sehingga perubahan nama tidak mengubah riwayat lama.
- Pilih persen bulat 1–100% atau potongan rupiah bulat Rp1–Rp10.000.000. Promo persen dapat diberi batas nominal potongan.
- Minimal belanja dihitung dari subtotal produk; diskon tidak mengurangi ongkir. Potongan dibatasi maksimal subtotal, sehingga total tidak negatif. Pecahan rupiah dibulatkan ke bawah. Aturan gratis ongkir toko tetap mengikuti subtotal sebelum promo.
- Tanggal mulai dan akhir opsional, ditampilkan dalam **WIB** tanpa bergantung zona waktu perangkat. Tanggal terakhir berlaku mencakup seluruh tanggal itu; waktu kedaluwarsa server bersifat eksklusif. Kosong berarti tanpa batas tanggal, bukan tanggal 0.
- Kuota total opsional. Batas per akun wajib minimal 1 dan default 1. Angka 0 ditolak, bukan diartikan tanpa batas. Untuk kode yang dapat dipakai ulang, naikkan batas per akun dengan sengaja.
- Kode baru disimpan nonaktif sampai pemilik mencentang **Aktifkan kode promo**. Nonaktifkan ketika kerja sama berakhir. Tidak ada penghapusan kode yang dapat menghilangkan riwayat atau menggunakan ulang identitas kode.
- Daftar menampilkan kuota terpakai, jumlah pesanan selesai dan nilai total pesanan selesai (termasuk ongkir). Angka selesai mengikuti konfirmasi status toko; bukan laporan transfer otomatis atau perhitungan komisi partner.

## Pembeli dan pesanan

Pembeli yang sudah masuk dapat memasukkan satu kode di keranjang atau checkout, melihat potongan serta total terbaru, dan menghapus/mengganti kode. Pemeriksaan promo memakai harga serta jumlah keranjang yang tersimpan di server. Perubahan isi keranjang meminta perhitungan ulang. Browser hanya menyimpan kodenya selama sesi tab, bukan daftar promo atau nominal diskon yang dipercaya server.

Preview tidak menahan kuota. Pesanan yang berhasil dibuat langsung menggunakan kuota, termasuk pesanan menunggu transfer WhatsApp. Pembatalan mengembalikan kuota; pesanan selesai tetap terhitung. Jika pesanan ditinggalkan belum dibayar, pemilik perlu membatalkannya untuk melepas stok dan kuota. Tidak ada batas waktu pembatalan otomatis yang baru.

Server memeriksa kembali status, periode, minimal belanja, kuota, batas per akun dan harga saat checkout. Jika promo tidak berlaku, pesanan ditolak tanpa mengurangi stok. Jika nilai diskon berubah dari yang ditampilkan, pembeli diminta menerapkan ulang kode sebelum checkout; aplikasi tidak diam-diam menaikkan total pesanan. Mengulang permintaan checkout dengan kunci yang sama mengembalikan pesanan lama, tanpa memakai kuota lagi.

Rincian pesanan pembeli, dashboard pemilik, halaman konfirmasi dan teks WhatsApp pembayaran mencantumkan kode serta potongan yang dicatat saat pesanan dibuat. Mengedit/menonaktifkan promo tidak mengubah pesanan lama.

## Penyimpanan dan pengamanan

Tidak perlu migrasi Supabase tambahan untuk fitur promo. Definisi tersimpan di tabel privat `metadata` dengan key `promo:<KODE>`. Snapshot promo tersimpan di dokumen pesanan yang sudah ada. Kuota dihitung dari pesanan selain `dibatalkan`, bukan penghitung di memori/browser. Penghitungan dan pencatatan pesanan berada dalam transaksi tulis yang sama, memakai `BEGIN IMMEDIATE` pada SQLite dan advisory transaction lock aplikasi pada PostgreSQL. Dua checkout bersamaan tidak dapat melewati kuota terakhir.

API pemilik memerlukan sesi pemilik, CSRF dan kunci gateway server bila memakai portal terpisah. Perubahan menggunakan pemeriksaan versi untuk mencegah tab lama menimpa perubahan baru. API pembeli memerlukan sesi pembeli dan CSRF, dengan anggaran 60 pemeriksaan per akun per 15 menit yang disimpan di database. Tidak ada endpoint publik untuk daftar kode/nama partner, tidak ada rahasia atau aturan diskon di JavaScript. Nama partner diperlakukan sebagai teks, bukan HTML.

Jumlah penggunaan dibaca dari JSON pesanan dengan fungsi JSON bawaan SQLite/PostgreSQL. Untuk toko ini pendekatan tersebut menghindari migrasi dan penghitung yang bisa menyimpang. Jika volume pesanan besar, tambahkan indeks ekspresi pada kode promo atau tabel redemption melalui migrasi sebelum meningkatkan beban; transaksi tulis aplikasi saat ini memang diserialkan untuk menjaga konsistensi stok.

## Verifikasi dan desain

- `tests/test_promos.py`: autentikasi/CSRF, pengaturan invalid dan tipe data, kode duplikat/immutable, versi lama, harga server, batas nominal/persen dan pembulatan, batas waktu persis, minimal belanja, kuota, isolasi per akun, pembatalan, retry idempotent, checkout bersamaan dan total preview yang berubah. Kontrak yang sama dijalankan pada SQLite dan PostgreSQL melalui `tests/test_postgres.py`.
- `tests/browser_promos_smoke.py`: portal admin dan toko pada origin berbeda, membuat/mengedit kode sungguhan, reload, keranjang, perubahan jumlah, error/hapus/pakai ulang, checkout, riwayat pesanan, teks WhatsApp dan pengamanan partner sebagai teks. Memeriksa editor/daftar/keranjang/checkout pada 320, 390, 768, 1440px serta landscape 844px. Seluruh data uji sementara; tidak membuka WhatsApp atau menyentuh database produksi.
- Arah visual admin mempertahankan **Framed sheet**, seed `2058406519`, Switzer dan olive/stone yang sudah disetujui. Tidak ada draw ulang atau perubahan homepage. Pertanyaan utama layar: kode mana yang berlaku dan berapa kuotanya terpakai? Daftar mengutamakan kode/partner, nominal dan status; tindakan utama adalah membuat kode. Bentuk diskon, minimum, batas, kuota total, batas akun, tanggal, status, partner dan versi adalah data nyata yang dirender; angka contoh hanya fixture pengujian. Header, daftar dan form memakai tepi yang sama, angka tabel rata kanan, dan daftar menjadi dua kolom rincian per kode di HP.
- Native taste-skill inspector pada 1440/768/390: admin **0 FAIL, 1 WARN**, keranjang **0 FAIL, 2 WARN**. Allowance `no-title` admin mengatasi probe yang membaca h1 login tersembunyi; h1 Kode promo tetap terlihat dan diperiksa lewat browser. WARN ruang kosong admin dipertahankan karena fixture hanya satu kode, tanpa menambah statistik/promo palsu. WARN ukuran judul dan bagian di bawah layar pada keranjang mempertahankan judul editorial serta rekomendasi/footer toko yang sudah ada. Kontras nominal diskon dan label ringkasan diperbaiki. Pemeriksaan gambar menemukan kode tertekuk pada tablet dan navigasi menimpa wordmark; daftar promo kini berubah ke rincian dua kolom pada tablet, sedangkan keranjang/checkout memakai menu pada lebar tersebut. Harga, jumlah, subtotal dan tombol hapus keranjang juga diberi area terpisah pada tablet.
- Verifikasi akhir: **150 tes backend**, **21 pemeriksaan layout fitur promo pada setiap backend** (SQLite/PostgreSQL), **231 pemeriksaan responsif** yang sudah ada dan alur belanja lengkap melalui portal terpisah lolos. Screenshot editor, daftar, keranjang serta checkout diperiksa pada desktop, tablet dan HP.
