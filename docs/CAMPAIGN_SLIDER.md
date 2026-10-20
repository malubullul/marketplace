# Slider kampanye homepage

Homepage memakai lima foto: kampanye Archive yang sudah disetujui, ditambah empat foto editorial baru. Panah tipis di sisi foto mengikuti penempatan yang diminta pemilik. Warna olive/stone, Switzer, wordmark, dan arah editorial sebelumnya dipertahankan; ini pengembangan komponen kampanye, tanpa draw arah visual baru.

| Slide | Visual | Tujuan belanja |
| --- | --- | --- |
| The Archive | Pasangan dengan suede cokelat di lounge | Apparel |
| After Hours | Tailoring pasir/cokelat di koridor walnut | Apparel |
| City Uniform | Overshirt charcoal dan sneakers di courtyard | Sneakers |
| Soft Form | Cardigan oatmeal dan celana espresso | Apparel |
| Everyday Objects | Sneakers, kemeja terlipat dan tas kulit pada plinth | Essentials |

Foto baru digenerate khusus dengan nuansa curated fashion premium, tanpa tulisan reseller, branding pihak ketiga, gudang atau banner promosi. Semua file dan asal PNG dicatat di [SOURCES.md](../assets/SOURCES.md). Visual ini merupakan kampanye ilustratif, bukan bukti inventaris produk yang sedang dijual.

## Perilaku

- Panah sebelumnya/berikutnya berputar melalui kelima foto. Desktop juga memiliki lima indikator yang dapat dipilih; HP memakai penghitung ringkas agar tombol CS tetap memiliki ruang.
- Swipe horizontal bekerja pada foto di perangkat sentuh; gerakan vertikal tetap menggulir halaman. Tombol panah memiliki area tekan minimal 44px.
- Keyboard kiri/kanan bekerja ketika fokus berada dalam kampanye. Judul, deskripsi, alt foto, kategori tujuan dan penghitung diperbarui bersama. Pengumuman pembaca layar hanya terjadi setelah navigasi.
- Foto berpindah dengan crossfade 500ms. Preferensi reduced motion menonaktifkan transisi. Tidak ada autoplay yang menggeser foto saat pengunjung membaca.
- Foto tujuan dimuat/decode dahulu; jika gagal, foto dan tautan belanja sebelumnya tetap dapat dipakai. Navigasi cepat hanya menerapkan permintaan terakhir.
- Satu elemen gambar menjaga ukuran frame dan menghindari gambar ganda pada pembaca layar. Lapisan latar sementara hanya dipakai selama transisi. Tanpa JavaScript, foto dan CTA awal tetap tersedia, kontrol slider tersembunyi.
- Crop portrait HP mengikuti titik fokus setiap foto. Tinggi teks stabil agar halaman tidak meloncat saat slide berubah.

## File dan ukuran

`index.html` berisi fallback dan kontrol, `js/campaign.js` mengelola keadaan dan navigasi, dan `css/editorial.css` menata panah/penghitung. Tidak ada dependensi frontend baru. Kelima WebP berukuran total sekitar 597 KiB; foto pertama sekitar 157 KiB, dibandingkan PNG awal sekitar 2,1 MB. Dimensi dan komposisi asli tetap 1672×941; PNG asli dipertahankan. Aset lain yang memakai PNG lama tetap tersedia.

## Verifikasi

- `tests/browser_campaign_smoke.py`: **5 slide × 14 ukuran layar**, foto termuat, tautan kategori, layout stabil, kontrol tidak menutupi judul, panah dua arah, indikator desktop, keyboard, swipe sentuh sungguhan, gulir vertikal, navigasi cepat, tanpa autoplay, crossfade normal/reduced motion, pemulihan kegagalan gambar dan fallback tanpa JavaScript. Tidak ada uncaught JavaScript error.
- Suite responsif yang sudah ada: **231 pemeriksaan** pada 13 halaman/status dan 14 ukuran layar lolos.
- Native taste-skill CLI inspector pada 1440/768/390: **0 FAIL, 2 WARN**. Penghitung memakai `data-ui` hanya pada kelompok kontrol nyata; tidak ada allowance baru. WARN jumlah ukuran huruf mempertahankan skala produk/brand/footer toko yang sudah disetujui. WARN tanpa video dipertahankan karena permintaan ini untuk foto editorial, tanpa klip kampanye yang sesuai.
- Screenshot kelima slide diperiksa pada desktop, tablet dan HP, termasuk 320px. Pemeriksaan awal menemukan indikator HP bertabrakan dengan CS; HP kini hanya menampilkan penghitung. Foto model mempertahankan wajah dan siluet; still life berfokus pada sneakers, shirt dan tas dalam crop portrait.
- Sintaks JavaScript dan `git diff --check` lolos. Backend pembayaran, autentikasi dan pengaturan WA tidak diubah.

Penilaian internal setelah perbaikan: design 8,0 · usability 8,5 · creativity 7,0 · content 8,0 → 7,9/10. Ini penilaian kerja, bukan skor audit eksternal. Arah specimen catalogue sebelumnya (seed 530515494) tetap menjadi acuan. Tidak ada foto stok tambahan atau klaim inventaris baru.
