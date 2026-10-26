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

- `tests/browser_campaign_smoke.py`: **5 slide × 16 ukuran layar**, termasuk desktop lebar 1535×777 dan 1920×900, foto termuat, tautan kategori, layout stabil, kontrol tidak menutupi judul, panah dua arah, indikator desktop, keyboard, swipe sentuh sungguhan, gulir vertikal, navigasi cepat, tanpa autoplay, crossfade normal/reduced motion, pemulihan kegagalan gambar dan fallback tanpa JavaScript. Tidak ada uncaught JavaScript error.
- Suite responsif yang sudah ada: **231 pemeriksaan** pada 13 halaman/status dan 14 ukuran layar lolos.
- Native taste-skill CLI inspector pada 1440/768/390: **0 FAIL, 2 WARN**. Penghitung memakai `data-ui` hanya pada kelompok kontrol nyata; tidak ada allowance baru. WARN jumlah ukuran huruf mempertahankan skala produk/brand/footer toko yang sudah disetujui. WARN tanpa video dipertahankan karena permintaan ini untuk foto editorial, tanpa klip kampanye yang sesuai.
- Screenshot kelima slide diperiksa pada desktop, tablet dan HP, termasuk 320px. Pemeriksaan awal menemukan indikator HP bertabrakan dengan CS; HP kini hanya menampilkan penghitung. Foto model mempertahankan wajah dan siluet; still life berfokus pada sneakers, shirt dan tas dalam crop portrait.
- Sintaks JavaScript dan `git diff --check` lolos. Backend pembayaran, autentikasi dan pengaturan WA tidak diubah.

Penilaian internal setelah perbaikan: design 8,0 · usability 8,5 · creativity 7,0 · content 8,0 → 7,9/10. Ini penilaian kerja, bukan skor audit eksternal. Arah specimen catalogue sebelumnya (seed 530515494) tetap menjadi acuan. Tidak ada foto stok tambahan atau klaim inventaris baru.

## Pembingkaian Archive setelah pengaturan admin

Pengaturan admin sempat memberi `object-position: 90% center` pada foto Archive bawaan, sehingga bagian atas foto terpotong pada desktop lebar. Preset ini kini kembali mengikuti CSS awal: `center top` pada desktop di atas 1100px dan `90% top` pada layar lebih kecil. Ini juga berlaku pada pengaturan bawaan yang sudah tersimpan, tanpa migrasi data. File WebP 1672×941 tidak diubah. Pengaturan posisi horizontal tetap berlaku jika pemilik mengubahnya; foto pengganti dari admin tetap mengikuti titik fokus pilihannya.

Perbandingan foto dengan versi sebelum pengaturan admin (`2cb479c`) cocok piksel demi piksel pada 1535×777, 1920×900, 1440×1000 dan 390×844. Sembilan pengujian pengaturan konten dan pemeriksaan slider pada 16 ukuran layar lolos.

## Parallax pada pembuka homepage

Efek gerak berlapis dari komponen `parallax-scrolling.tsx` yang dikirim pemilik diadaptasi di `js/parallax-scrolling.js`. Foto bergerak sebesar 28% jarak gulir dan kelompok teks sebesar 8%, maksimal 32px. Foto utama dan latar crossfade memakai perpindahan yang sama; panah, penghitung, menu, dan bagian katalog mengikuti gulir halaman biasa. Tidak ada zoom, perubahan dimensi, maupun perubahan titik fokus foto saat halaman dibuka. Gambar tetap dikelola melalui admin.

Implementasi mengikuti HTML/Jinja, CSS, dan JavaScript yang sudah dipakai toko: komponen perilakunya di `js/`, gaya di `css/editorial.css`. Contoh React/TypeScript, shadcn, Tailwind, GSAP, dan Lenis tidak diperlukan untuk efek ini. Tidak ada gambar demo eksternal, scroll-jacking, build Node tambahan, atau perubahan konfigurasi Vercel. Tidak ada bagian intro tambahan yang menunda pengunjung menuju katalog.

Parallax aktif pada lebar minimal 761px dan tinggi minimal 600px. HP, layar landscape pendek, preferensi reduced motion, serta halaman tanpa foto memakai tampilan statis. Perubahan ukuran layar dan preferensi gerak langsung diterapkan. Tanpa JavaScript, konten pertama dan tautan belanja tetap tersedia. Listener gulir bersifat pasif; pembaruan dibatasi satu per animation frame dan berhenti saat foto berada di luar layar atau tab disembunyikan. Transform teks dinonaktifkan selama tombol belanja mendapat fokus keyboard.

Pemeriksaan khusus: `python3 tests/browser_parallax_smoke.py`. Lolos untuk gulir native, gerak desktop/tablet, keselarasan crossfade, tombol tetap pada posisi layout, fokus keyboard, kembali ke atas, perubahan reduced motion, lima ukuran layar statis, serta fallback tanpa foto, tanpa JavaScript, dan gagal memuat efek. Screenshot desktop sebelum/sesudah scroll dan HP diperiksa setelah animasi masuk selesai. Regresi slider 5 foto × 16 viewport, pengaturan admin/publik dengan 25 pemeriksaan layout, dan 9 tes backend konten juga lolos.
