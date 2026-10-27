# Anredseller: tema hitam editorial

Permintaan pemilik, 28 Oktober 2026: ganti tema menjadi hitam dengan desain yang tetap matang. Perubahan mencakup toko publik, akun, checkout, rincian pesanan, portal admin dan halaman React 404. Tema ini menjadi tampilan utama, termasuk ketika perangkat memakai mode terang.

Menggunakan [Taste Skill](../.agents/skills/design-taste-frontend/SKILL.md) dan [UI/UX Pro Max](../.agents/skills/ui-ux-pro-max/SKILL.md). Hasil pencarian `dark mode oled contrast` dipakai untuk hierarki permukaan, `color-scheme: dark`, fokus dan kontras. Saran neon/glow dari dataset tidak dipakai karena tidak sesuai arah fashion Anredseller. Pencarian `luxury fashion monochrome` menguatkan penggunaan tipografi besar dan antarmuka monokrom.

## Arah dan peran warna

Taste Skill menghasilkan **The specimen catalogue**, seed `137921587`; admin **True-black flat**, seed `1211460812`. Ini restyle: komposisi Archive, lima foto, crop HP, Switzer dan wordmark serif yang sudah disetujui dipertahankan. Hero plinth dari sheet tidak menggantikan kampanye yang sudah dipilih pemilik. Tidak memakai aset, font, animasi atau dependensi baru.

Ide: kampanye Archive Anredseller menjadi pembuka sebuah galeri malam, sementara foto produk tetap menunjukkan warna barang aslinya. Interaksi utamanya tetap menjelajahi koleksi, menggeser foto dan memilih ukuran dengan stok nyata. Admin mempertahankan produk, stok ukuran dan pesanan sebagai pusat layar.

| Peran | Warna | Penggunaan |
| --- | --- | --- |
| Latar | `#101210` | Halaman, navigasi, footer |
| Permukaan | `#191c19` | Panel, kartu informasi, modal |
| Permukaan lebih tinggi | `#252925` | Isian readonly, pilihan aktif, bagian editor |
| Teks utama | `#efeee7` | Judul, harga, isi |
| Teks sekunder | `#b8bcb2` | Metadata dan petunjuk yang tetap terbaca |
| Aksi utama | `#e5e4d8` / `#131610` | Tombol ivory dengan teks gelap |
| Batas kontrol | `#778370` | Input dan aksi sekunder |
| Status | Hijau lembut / merah lembut / amber | Pembayaran, error, stok dan rating; selalu disertai teks |

Permukaan dibedakan lewat terang-gelap, tanpa glow atau gradien dekoratif baru. Foto tidak diinvert atau diberi filter. Blend multiply lama dilepas agar produk tidak menghitam di atas latar baru. Bidang foto dan kartu kategori memakai alas terang yang disengaja supaya baju hitam tetap terlihat. Scrim pada foto kampanye tetap berfungsi untuk keterbacaan.

Palet dan pemetaan komponen publik berada di bagian tema `css/editorial.css`; portal memakai bagian tema pada stylesheet kanonisnya. Alias lama seperti `--olive` menunjuk aksi ivory untuk kompatibilitas komponen. Warna scope lama pada cart/detail ditimpa secara eksplisit, termasuk judul/header, badge keranjang, input, autofill, error dan fokus. 404 memiliki token yang sama pada sumber Tailwind dan hasil build yang diprerender. `theme-color` mengikuti latar hitam.

## Pemeriksaan dan kritik render

ROUND 1
Seen in one second: kampanye Archive tetap dominan, tetapi label dan bidang data belum konsisten gelap.
Idea (one sentence): Archive menjadi pembuka galeri malam dengan warna produk asli sebagai fokus.
Live thing: slider kampanye dan pilihan ukuran dengan ketersediaan stok.
Layout words by section: hero=campaign / collection=specimens / categories=paired photographs / shopping=split / footer=wordmark.
Scores: design 6 · usability 5 · creativity 6.5 · content 8 → overall 5.9.
Caps applied: kontras teks dan panel belum selesai.
Top three problems (most visible first), each with the screenshot it shows in and the fix:
1. `admin-products-390.png`: panel tabel masih putih dengan teks terang. Terapkan permukaan charcoal pada tabel dan area foto editor.
2. `home-1440.png`: logo dan angka slider mengikuti token latar gelap. Beri peran teks di atas foto secara eksplisit.
3. `checkout-390.png` dan `detail-390.png`: token teks hijau lama terlalu redup. Petakan metadata, badge dan alamat tersimpan ke peran tema baru.

ROUND 2
Seen in one second: kampanye hangat, navigasi ivory dan koleksi produk pada galeri hitam.
Idea (one sentence): Archive menjadi pembuka galeri malam dengan warna produk asli sebagai fokus.
Live thing: slider dan stok ukuran bekerja bersama alur belanja nyata.
Layout words by section: hero=campaign / collection=specimens / categories=paired photographs / shopping=split / footer=wordmark.
Scores: design 8 · usability 8.5 · creativity 6.5 · content 8 → overall 7.9.
Caps applied: kreativitas tetap dibatasi karena ini restyle struktur yang sudah ada, bukan konsep situs baru.
Top three problems (most visible first), each with the screenshot it shows in and the fix:
1. `desktop-page-01.jpg`: foto katalog contoh masih beragam latar. Dipertahankan sebagai aset produk yang ada; pemilik dapat menggantinya melalui admin.
2. `tablet-page-01.jpg`: wordmark dan metadata membutuhkan beberapa tingkat ukuran. Hierarki lama dipertahankan untuk keterbacaan; tidak mengecilkan teks demi jumlah token font.
3. `mobile-fold.jpg`: tinggi kampanye membutuhkan gulir pada HP kecil. Crop dua model dan konten yang mengalir dipertahankan; tombol tidak dipotong untuk memaksakan satu layar.

Skor adalah penilaian kerja internal. Native Taste inspector pada 1440/768/390: homepage **sebelum 3 FAIL/2 WARN → sesudah 0 FAIL/3 WARN**; admin **0 FAIL/0 WARN → 0 FAIL/1 WARN**. Peringatan akhir: ukuran type yang diwarisi, ketiadaan video, serta probe `palette-cream` yang mendeteksi teks ivory sebagai latar; latar sebenarnya `#101210`. Tidak menambah video tanpa materi baru yang relevan. Flag `emoji` hanya mempertahankan bintang rating yang sudah ada. Admin memakai `no-title` karena probe membaca h1 login yang tersembunyi sebelum h1 dashboard yang terlihat; judul aktual diperiksa lewat browser. Tidak menyembunyikan elemen aplikasi untuk memenuhi inspector.

## Validasi

- `tests/browser_dark_theme_smoke.py`: **82 pemeriksaan layout**, **6.533 sampel teks**, **0 pasangan halaman/viewport dengan kegagalan kontras** pada latar datar. Ukuran 320, 390, 768 dan 1440px; toko/admin berbeda origin. Mencakup login, register, katalog, detail, keranjang, checkout nyata, receipt, profil, pesanan, editor stok, pengaturan, konfirmasi pembayaran, aktivitas dan form rating setelah pesanan selesai.
- Ambang 4,5:1 untuk teks normal dan 3:1 untuk teks besar. Teks di atas foto diperiksa melalui screenshot; pemeriksaan otomatis ini bukan audit WCAG penuh atau uji perangkat fisik.
- Regresi belanja melalui portal terpisah lulus, termasuk upload, draft/terbit, alamat, cart, checkout dan isolasi akun. **231 pemeriksaan responsif** pada 13 halaman/status dan 14 ukuran portrait/landscape lulus; crop hero HP tetap sesuai.
- TypeScript/build React 404 dan pemeriksaan kecocokan hasil build lulus; **5 tes backend halaman 404** lulus. Tidak mengubah skema database, alur pembayaran atau data produksi.

Artefak berada di `preview/black-theme/`, `.taste-skill/black-before`, `.taste-skill/black-after`, `.taste-skill/black-admin-before` dan `.taste-skill/black-admin-after` pada workspace pengujian. Screenshot memakai akun, produk dan pesanan sementara, bukan bukti deployment produksi.
