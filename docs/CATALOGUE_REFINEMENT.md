# Perbaikan katalog hitam Anredseller

28 Oktober 2026. Pemilik menolak tampilan katalog dan kategori pada versi hitam pertama: bidang krem terlalu luas, foto terasa dibingkai tebal, kategori terlalu besar dan miring. Perbaikan ini mengubah komposisinya, bukan sekadar mengganti warna.

Menggunakan [Taste Skill](../.agents/skills/design-taste-frontend/SKILL.md) dan [UI/UX Pro Max](../.agents/skills/ui-ux-pro-max/SKILL.md). Arah **The specimen catalogue**, seed `137921587`, dipertahankan. Kategori memakai pendekatan `list-menu-photo-bullets` dari alternatif daftar Taste: dua tujuan belanja yang nyata cocok menjadi menu bergambar ringkas. Tidak mengganti hero Archive yang sudah dipilih pemilik, font, aset foto, atau alur transaksi. Tidak ada draw baru atau foto eksternal baru. Pencarian UX terarah dipakai untuk kontras, ukuran target sentuh dan jarak kontrol.

Inventaris yang menentukan desain: kampanye Archive, lima foto kampanye, tiga kategori produk, foto unggahan pemilik dengan rasio berbeda, galeri hingga delapan foto, harga rupiah, wishlist, stok ukuran, pembayaran melalui WhatsApp, serta kontak CS terpisah. Klaim halaman: kampanye memperkenalkan koleksi; katalog memperlihatkan barang/harga/ketersediaan; menu kategori membawa pengunjung ke pilihan yang sesuai; bagian cara belanja menjelaskan pemesanan melalui WhatsApp.

Ide: kampanye Archive menjadi pembuka galeri malam, dan foto barang beserta harga menjadi isi galeri itu. Interaksi nyata tetap filter kategori, geser foto, wishlist dan memilih produk. Ini penyempurnaan pendekatan katalog fashion yang dikenal, bukan konsep visual yang unik terhadap semua pesaing.

## Perubahan

- Latar publik menjadi hitam netral `#101010`, dengan panel `#191919`, `#242424` dan hover `#303030`. Portal admin dan React 404 tetap memakai tema hitam dari versi sebelumnya.
- Bingkai krem tambahan di kartu produk dihapus. Foto menggunakan `object-fit: contain`, tanpa padding, filter, inversi, atau zoom yang memotong. Latar putih yang merupakan bagian dari foto unggahan tetap terlihat sebagai bagian foto.
- Frame katalog lebih ringkas di desktop, dengan proporsi khusus HP. Panah galeri 44×44 px dan jumlah foto berada di jalur bawah foto, sehingga tidak menutupi barang. Kontrol pada detail produk mempertahankan susunannya.
- Tombol pilih produk selalu terlihat di bawah informasi barang. Wishlist tetap terlihat dan dapat difokuskan. Perubahan renderer berlaku juga pada katalog, rekomendasi dan wishlist akun.
- Filter kategori menggunakan teks dengan bidang charcoal untuk pilihan aktif. Pada HP 390 px empat pilihan muat dalam satu baris; layar 320 px memakai susunan 2×2 yang seimbang.
- Kategori menjadi dua baris dengan thumbnail kecil pada desktop, dua kolom pada tablet dan daftar vertikal pada HP. Foto tidak diputar. Jika pemilik menghapus foto, teks dan tautan tetap berfungsi.
- Tombol CS mengambang menjadi ikon 48×48 px dengan nama aksesibel “Hubungi CS”; label penuh kembali ketika tombol berada di footer. Ini mengurangi area konten yang tertutup.
- Garis pemisah sekunder di bantuan pembayaran dan ulasan diganti jarak. Batas pada kontrol/form dipertahankan.

## Kritik screenshot

ROUND 1

Seen in one second: bingkai terang yang besar, lalu pakaian di dalamnya.

Idea (one sentence): katalog malam, tetapi bingkai krem mendominasi foto.

Live thing: filter kategori dan galeri foto yang berfungsi.

Layout words by section: hero=kampanye / produk=grid tinggi / kategori=dua poster miring / cara belanja=split / footer=wordmark.

Scores: design 6 · usability 7.5 · creativity 6 · content 7.5 → overall 6.6.

Caps applied: kreativitas pendekatan umum; tidak ada klaim konsep yang unik.

Top three problems (most visible first), each with the screenshot it shows in and the fix:

1. Screenshot pemilik, katalog desktop: pinggiran terang dan tombol di atas barang bersaing dengan foto. Hilangkan pinggiran tambahan dan pindahkan kontrol ke bawah.
2. Screenshot pemilik, kategori desktop: poster raksasa dan foto miring memperpanjang halaman. Ganti dengan menu kategori kecil yang tetap dapat diedit lewat admin.
3. Screenshot HP putaran awal: filter menyisakan satu pilihan di baris berikutnya; tombol CS menutup isi. Rapikan filter dan perkecil tombol mengambang.

ROUND 2

Seen in one second: barang yang bisa dipilih pada bidang hitam; kategori mudah dipindai.

Idea (one sentence): kampanye membuka galeri, lalu foto barang, harga dan kategori memandu pilihan.

Live thing: filter, galeri sentuh/tombol, wishlist dan pilih produk tetap berfungsi.

Layout words by section: hero=kampanye / produk=grid foto dan informasi / kategori=menu bergambar / cara belanja=split / footer=wordmark.

Scores: design 7.5 · usability 8 · creativity 6.5 · content 7.5 → overall 7.5.

Caps applied: kreativitas tetap dibatasi pendekatan fashion yang umum. Angka adalah penilaian internal atas screenshot, bukan nilai dari pengguna atau auditor eksternal.

Top three problems (most visible first), each with the screenshot it shows in and the fix:

1. `after-products-1440.jpg`: latar foto asli masih berbeda antarproduk. Frame dan fit sudah konsisten; standardisasi foto berikutnya dilakukan lewat unggahan admin, tanpa memanipulasi warna barang.
2. `after-categories-390.jpg`: foto pakaian bawaan masih mempunyai latar terang. Kini hanya thumbnail kecil, bukan seluruh panel. Pemilik tetap dapat mengganti fotonya.
3. `mobile-page-01.jpg`: hero dan copy memerlukan scroll pada HP. Susunan ini dipertahankan agar dua model tidak terpotong dan teks tetap terbaca.

## Pemeriksaan

- Taste lint: **0 FAIL**, satu peringatan batas tombol rating yang merupakan kontrol nyata.
- Taste inspector: **0 FAIL**, tiga peringatan. Ivory adalah teks, bukan latar krem; ukuran font melayani wordmark/hero/harga/keterangan; tidak menambahkan video yang tidak relevan ke kampanye foto yang sudah dipilih. Emoji rating yang sudah ada diperbolehkan oleh opsi inspector.
- Semua fold dan contact sheet desktop 1440, tablet 768, HP 390 dibuka dan diperiksa. Screenshot bagian produk/kategori juga diperiksa pada 320 px. Fixture menggunakan tiga produk sementara dan aset lokal; bukan katalog produksi.
- **231 pemeriksaan responsif**, 13 halaman/status dan 14 viewport portrait/landscape lulus.
- **82 pemeriksaan tampilan** toko/admin serta perjalanan belanja hingga pembayaran/rating lulus; **6.587 sampel teks**, nol pasangan halaman/viewport gagal ambang kontras. Pemeriksaan otomatis tidak mengukur kontras foto atau menggantikan audit aksesibilitas penuh.
- Galeri: upload empat foto melalui portal admin, persistensi urutan/sampul, tombol, keyboard, swipe asli, filter halaman utama, wishlist dan kegagalan foto lulus pada lima ukuran layar; tanpa error JavaScript.
- CMS: sembilan slot foto, unggahan, penghapusan/pemulihan, kategori tanpa foto, media sosial dan SSR tanpa JavaScript lulus pada dua origin dengan 25 pemeriksaan layout.
- WhatsApp: edit kontak melalui admin, pembukaan bantuan/pembayaran, kontak kosong dan pesanan terproses lulus pada lima viewport; tidak menghubungi server WhatsApp.
- Pemeriksaan akhir khusus dua bagian pada empat ukuran layar memastikan layout, kontras teks, nama aksesibel CS, target sentuh galeri, dan foto tidak terpotong atau difilter.

Artefak lokal: `/workspace/preview/catalogue-refine/` dan `.taste-skill/catalogue-refine/`. Tidak ada perubahan skema atau data produksi.
