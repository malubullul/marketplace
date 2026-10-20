# Galeri foto produk

## Mengunggah empat foto dari admin

1. Buka **Koleksi produk → Tambah produk** atau **Edit** produk yang sudah ada.
2. Pada **Foto produk**, klik **Pilih beberapa foto atau tarik ke sini**. Pilih empat foto sekaligus, atau tambahkan satu per satu.
3. Penghitung menunjukkan jumlah foto yang sudah diunggah. Pilih **Jadikan sampul** pada foto yang ingin ditampilkan pertama. Foto dapat dihapus sebelum produk disimpan.
4. Klik **Terbitkan produk**. Foto tersimpan di backend yang sama dan tersedia di toko publik setelah halaman dimuat ulang. **Simpan draf** tetap menyembunyikan produk dari publik.

Upload sebelumnya sudah mendukung 1–8 foto. Batas itu tetap dipertahankan agar produk lama tidak kehilangan foto; empat foto didukung tanpa migrasi database. Format tetap JPG/PNG/WebP, maksimal 4 MB per file, dengan pemeriksaan dan konversi server yang sudah ada.

## Yang dilihat pembeli

- **Kartu produk** di homepage, katalog, produk serupa, rekomendasi, dan wishlist memakai foto lengkap dari `gambarList`.
- Produk dengan beberapa foto menampilkan panah tipis dan penghitung, misalnya **1 / 4**. Pembeli dapat menggeser foto di HP, memakai panah, atau tombol keyboard kiri/kanan saat fokus berada pada galeri. Home/End memilih foto pertama/terakhir.
- **Halaman detail** menampilkan panah, penghitung, dan thumbnail berbentuk tombol. Thumbnail aktif mengikuti foto yang dipilih melalui panah maupun swipe.
- Mengetuk foto kartu tetap membuka detail produk. Gesture swipe tidak membuka tautan secara tidak sengaja; gulir vertikal tetap berjalan.
- Produk dengan satu foto tetap memiliki tampilan biasa tanpa panah/penghitung. Foto tambahan tidak dibuat atau digandakan otomatis; pemilik perlu mengunggah foto asli produk.

Foto tujuan dimuat dan didecode sebelum tampil. Gagal memuat foto mempertahankan foto sebelumnya dan memberikan pesan; navigasi cepat hanya menerapkan pilihan terakhir. Animasi pendek mengikuti preferensi reduced motion. Galeri pada produk berbeda menyimpan posisi masing-masing. Kontrol memakai event delegation sehingga tetap bekerja setelah filter, pencarian, atau wishlist dirender ulang.

## Implementasi dan tampilan

`renderProductGallery` dan pengendali di `js/app.js` digunakan oleh semua kartu dan oleh `js/detail.js`. Tidak ada dependensi baru, perubahan API, atau perubahan login/pembayaran. Daftar foto dan urutan sampul tetap memakai kontrak `gambarList`/`gambar` yang sudah ada.

Komponen melanjutkan [taste-skill](../.agents/skills/design-taste-frontend/SKILL.md) dan gaya Anredseller: olive/stone, Switzer, chevron tipis, serta area tekan minimal 44px. Tidak ada draw arah baru untuk pengembangan komponen ini. Thumbnail detail berukuran ringkas dan foto utama dibatasi tinggi agar nama produk tetap terlihat di tablet. Kontras breadcrumb, jumlah hasil, dan teks sekunder detail diperbaiki.

## Verifikasi

- `tests/browser_product_gallery_smoke.py`: empat file benar-benar diunggah melalui portal admin terpisah; sampul diganti, produk diterbitkan, lalu dibuka ulang untuk memastikan urutan tersimpan. Keempat URL foto publik teruji tersedia.
- Pengujian kartu dan detail di **320/390/768/1440/844 landscape**: semua foto, panah berputar, thumbnail, keyboard, swipe sentuh sungguhan tanpa navigasi tidak sengaja, tap biasa menuju detail, gulir vertikal, filter homepage, galeri independen, wishlist, kegagalan gambar, dan produk satu foto. Tidak ada uncaught JavaScript error.
- Alur browser belanja/admin yang sudah ada lolos dengan origin terpisah, termasuk checkout dan riwayat pesanan privat.
- Suite responsif yang sudah ada: **231 pemeriksaan**, 13 halaman/status dan 14 ukuran layar, lolos.
- Native taste-skill inspector dijalankan pada katalog/detail dengan 4 foto, pada 1440/768/390. Mode app dipakai untuk interface katalog/varian/pembelian: **0 FAIL**. Allowance `emoji` hanya mempertahankan simbol bintang rating yang sudah ada. WARN mengenai ukuran judul, label kategori dan nada warna brand dipertahankan sesuai desain toko; temuan kontras ditindaklanjuti. Tidak ada klaim seluruh halaman lolos aturan marketing/landing page atau audit keamanan baru.
- Screenshot kartu, detail dan form admin diperiksa. Foto pada pengujian berasal dari aset fixture sementara, bukan tambahan inventaris produksi. Database dan bucket Supabase produksi tidak dipakai oleh pengujian ini.

Penilaian internal komponen: design 7,5 · usability 8,5 · creativity 6,5 · content 8,0 → 7,7/10. Batas utama tetap kebutuhan foto asli dari berbagai sudut milik pemilik toko.
