# Mengelola gambar, WhatsApp, dan media sosial

Satu dashboard pemilik mengelola konten toko publik dari database yang sama, termasuk ketika admin dan toko memakai domain Vercel berbeda. Tidak perlu repository baru, environment variable baru, atau migrasi SQL tambahan untuk pengaturan ini. Tabel `metadata` yang sudah ada digunakan.

## Nomor WhatsApp

Buka **Admin → Kontak WhatsApp**. Nomor pembayaran dan customer service dapat diganti secara terpisah; gunakan format `08…` atau `+62…`, lalu **Simpan kontak**. Kosongkan nomor pembayaran untuk menonaktifkan tombolnya. Pengaturan ini sudah tersedia sebelumnya dan tetap memakai mekanisme penyimpanan yang sama.

## Foto tampilan toko

Buka **Admin → Tampilan toko**. Sembilan posisi tersedia:

- Lima foto slider di bagian paling atas halaman utama.
- Gambar kategori Sneakers dan Apparel.
- Foto banner “Good taste. Shared.”.
- Foto pada halaman akun pembeli, termasuk masuk/daftar/pemulihan password.

Pada setiap posisi, gunakan **Ganti foto/Unggah foto**, isi deskripsi untuk aksesibilitas, lalu atur **Fokus gambar** jika bagian penting foto terpotong. Foto lebar cocok untuk slider. Format JPG, PNG atau WebP, maksimal 4 MB dan 25 megapiksel; backend memeriksa isi file, memperbaiki orientasi, menghapus metadata saat konversi dan menyimpan WebP maksimal 2000px.

Tekan **Simpan perubahan gambar** untuk menerbitkan perubahan. Unggahan dan preview saja belum mengubah tampilan publik. **Hapus dari tampilan** menyembunyikan foto setelah disimpan. Penghapusan tetap berlaku setelah reload/restart dan tidak otomatis kembali ke gambar awal. **Pakai gambar awal** adalah tindakan eksplisit untuk memulihkan foto, deskripsi dan fokus bawaan pada posisi itu.

Slider menyesuaikan jumlah foto aktif: foto yang dihapus dilewati; satu foto menyembunyikan panah; jika semua dihapus, judul dan tombol belanja tetap tampil pada bidang olive. Gambar kategori yang dihapus menyisakan navigasi kategorinya, banner menyesuaikan kolomnya, dan halaman akun tetap memiliki teks dengan latar polos.

Foto produk dikelola lewat **Koleksi produk → Edit → Foto produk**, termasuk sampul dan galeri. Foto di keranjang/wishlist mengikuti produk; foto pada pesanan lama tetap menjadi bagian dari catatan pesanan. Menghapus foto dari posisi toko tidak menghapus objek penyimpanan yang mungkin masih dipakai posisi lain, produk, atau riwayat pesanan.

## Tautan media sosial di footer

Buka **Admin → Media sosial**. Semua kolom awalnya kosong:

- Instagram, TikTok, Facebook, YouTube, X, Threads.
- **Tautan lainnya** dengan nama sendiri, misalnya Pinterest atau Linktree.

Isi URL akun lengkap dengan `https://`, kemudian **Simpan media sosial**. Tautan tampil sebagai nama platform di bagian **Ikuti Anredseller**, di bawah menu footer dan di atas tulisan besar Anredseller. Tidak ada akun atau username contoh yang dipublikasikan. Kolom kosong disembunyikan; jika semuanya kosong, seluruh baris media sosial tidak tampil. Kosongkan URL dan simpan untuk menghapus tautan. Ini menyediakan tautan akun; tidak mendaftarkan akun baru pada platform eksternal.

Tautan membuka tab baru dengan `noopener noreferrer`. Domain platform standar diperiksa di server agar kolom Instagram tidak berisi domain lain. Tautan lainnya menerima domain HTTPS valid. `javascript:`, URL relatif, HTTP, kredensial di URL dan input berbahaya ditolak.

## Penyimpanan dan pembaruan

Muat ulang halaman publik untuk membaca pengaturan terbaru. Snapshot gambar disajikan oleh server pada HTML pertama, termasuk tanpa JavaScript, sehingga foto yang dihapus tidak sempat muncul kembali sebelum JavaScript berjalan. Footer memakai snapshot yang sama. Halaman publik dan API memakai `no-store` agar browser tidak memakai snapshot lama setelah reload.

Gambar dan media sosial memiliki tombol simpan terpisah. Penyimpanan satu bagian mempertahankan bagian lainnya serta pengaturan WhatsApp. Penyimpanan memeriksa versi untuk mencegah tab/perangkat lama menimpa perubahan lebih baru. Jika ada konflik, gunakan **Muat ulang pengaturan** lalu ulangi perubahan. Dashboard memperingatkan sebelum meninggalkan perubahan yang belum disimpan. Navigasi admin pada layar kecil dapat digeser horizontal dan mengikuti menu aktif.

## Keamanan dan verifikasi

API pengaturan admin membutuhkan sesi pemilik, CSRF dan gateway server bila memakai portal terpisah. Pengunjung dan pembeli tidak dapat mengubah pengaturan. API publik hanya memuat gambar/presentasi dan tautan yang memang dipublikasikan; tidak mengungkap akun, rahasia hosting, atau metadata lain. Gambar harus berupa aset bawaan yang diizinkan atau upload lokal tervalidasi, bukan URL gambar eksternal. Deskripsi/label tidak dijalankan sebagai HTML atau template. Snapshot JSON meng-escape penutup tag script.

Pengujian memakai akun/database/storage sementara dan tidak membuka tautan medsos atau mengirim pesan WhatsApp. Jalankan:

```sh
.venv/bin/python -m unittest discover -s tests -p 'test_*.py'
python3 tests/browser_store_content_smoke.py
python3 tests/browser_campaign_smoke.py
python3 tests/responsive_smoke.py
ANREDSELLER_TEST_ADMIN_PORTAL=1 python3 tests/browser_smoke.py
```

Untuk PostgreSQL, set `ANREDSELLER_TEST_DATABASE_URL` hanya ke database uji sementara. Kedua proyek Vercel perlu memakai commit terbaru karena allowlist API dan antarmuka admin ikut diperbarui; pengaturan koneksi dan gateway yang ada tetap digunakan.

### Verifikasi perubahan ini

- **122 tes backend lolos tanpa skip** pada SQLite dan PostgreSQL sementara, termasuk sembilan kontrak pengaturan konten pada masing-masing database. Cakupan meliputi otorisasi/CSRF, persistensi, penghapusan/restorasi, payload berbahaya, validasi URL/gambar, escaping HTML/JSON, dan penyimpanan konkuren. Kontrak konten diulang setelah penambahan validasi tipe/Unicode dan tetap lolos.
- Browser portal admin dan toko pada origin terpisah lolos di SQLite serta PostgreSQL/Storage fixture: unggah nyata, preview sebelum terbit, penyimpanan gambar, dua/satu/nol slide, kategori/banner/akun, tautan sosial kosong/terisi/dihapus, penolakan HTTP, restore, reload dan HTML tanpa JavaScript. **25 pemeriksaan layout baru** pada lima ukuran layar untuk setiap backend.
- **231 pemeriksaan responsif regresi** pada 13 halaman/status dan 14 ukuran layar lolos. Kelima foto kampanye pada 14 ukuran layar, navigasi keyboard/touch/error/reduced-motion/no-JS lolos. Alur belanja lengkap serta WhatsApp dengan admin/toko berbeda origin juga lolos; tidak ada pesan atau navigasi ke platform eksternal sungguhan.
- Snapshot desktop/tablet/ponsel diperiksa dengan Taste Skill, mengikuti arah **Framed sheet** admin dan tipografi/warna toko yang sudah disetujui. Native inspector: Tampilan toko **0 FAIL/1 WARN**, Media sosial **0 FAIL/0 WARN**, katalog/footer **0 FAIL/3 WARN**. Peringatan yang dipertahankan adalah tepi menu admin yang bisa digeser dan karakter tampilan katalog lama (warna netral, ukuran judul dan panjang daftar). Flag admin `no-title` hanya menangani probe yang membaca h1 login tersembunyi; judul h1 pengaturan yang terlihat diverifikasi. Flag `emoji` hanya untuk bintang rating katalog.
- Tombol CS tetap mengambang saat berbelanja dan menempel di ruang bawah footer saat footer terlihat, sehingga tidak menutupi judul atau tautan sosial. Penanda `data-ui` dilepas dari pembungkus halaman katalog; kartu produk tetap menjadi unit interaktifnya.
- Sintaks Python/JavaScript dan `git diff --check` lolos. Artefak screenshot berada di workspace `preview/store-content/`, memakai pengaturan/akun contoh khusus pengujian, bukan akun atau foto produksi.

Halaman HTML publik dirender oleh backend agar pengaturan gambar berlaku sejak respons pertama. Jalankan server Flask atau deployment Vercel; membuka file HTML mentah langsung bukan cara menjalankan toko ini.
