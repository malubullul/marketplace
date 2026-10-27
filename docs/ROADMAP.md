# Roadmap audit Anredseller

Sumber: audit yang diberikan pemilik pada 27 Oktober 2026. Pemilik memilih **seluruh roadmap secara bertahap**. Setiap tahap perlu diuji dengan data percobaan; hasil kode lokal tidak membuktikan konfigurasi atau alur produksi sudah berhasil.

| Tahap | Ruang lingkup | Status |
| --- | --- | --- |
| 01 — Amankan transaksi | Email-first signup/verifikasi akun lama, status pembayaran privat, urutan status pesanan, pembatalan mandiri, batas pembayaran opsional, audit log | Implementasi dan pengujian lokal selesai; aktivasi email memerlukan migrasi 005 dan Resend di hosting |
| 02 — Stok dan pengiriman | SKU dan stok ukuran/warna, data supplier/harga modal privat, ketersediaan/pre-order, kurir/layanan/resi, ongkir berdasarkan tujuan, retur/refund terstruktur | Stok per ukuran, restok dan pembatalan ukuran sudah diimplementasikan; SKU, kombinasi warna, supplier dan pengiriman/retur belum |
| 03 — Operasional toko | Notifikasi, kebijakan toko yang disetujui pemilik, laporan penjualan/margin, MFA admin, backup dan latihan restore, monitoring, penguatan CSP | Belum diimplementasikan |
| 04 — Pemasaran dan pengalaman belanja | Metadata produk dari server, Open Graph/canonical/sitemap/structured data, filter varian dan pencarian/pagination server, analitik, kemudahan belanja pengunjung | Belum diimplementasikan |

## Keputusan yang sudah diterapkan pada tahap 01

- WhatsApp tetap menjadi jalur pembayaran dan CS. Laporan transfer pembeli belum berarti uang diterima; pemilik mencocokkan mutasi rekening lalu memilih **Tandai sudah dibayar → Konfirmasi**. Referensi opsional; identitas admin dan waktu dicatat otomatis.
- Pesanan tidak boleh melompat dari baru ke selesai. Pesanan yang dikirim atau sudah dibayar tidak boleh dibatalkan melalui jalur pembatalan biasa.
- Batas waktu nonaktif secara default; admin memilih 1–168 jam dan ketentuan diperlihatkan sebelum checkout. Pesanan lama tanpa batas waktu tetap tidak memiliki batas waktu.
- Transfer yang dilaporkan atau sedang ditahan untuk diperiksa terlindung dari kedaluwarsa otomatis. Dua permintaan yang bersamaan tidak boleh mengembalikan stok dua kali.
- Akun lama tidak ditandai terverifikasi berdasarkan umur atau keberadaan email. Verifikasi menetapkan kata sandi baru dan mencabut sesi lama. Google login tetap tidak digunakan.
- Seluruh perubahan tetap berada dalam satu repository, branch `main`, dan dua project/domain Vercel dengan satu backend/database bersama.

Petunjuk pemilik dan aktivasi: [Keamanan transaksi](TRANSACTION_SAFETY.md).

## Urutan pekerjaan berikutnya

Tahap 02 sudah memiliki [stok per ukuran](SIZE_STOCK.md), editor/restok, pilihan ukuran di toko, dan penguncian checkout/pembatalan dengan kompatibilitas stok lama. Berikutnya adalah SKU dan stok per kombinasi ukuran/warna, supplier dan pengiriman. Informasi supplier dan harga modal wajib dipisahkan dari respons publik. Pengiriman manual dengan nomor resi dapat dikerjakan sebelum integrasi tarif kurir; layanan ongkir otomatis memerlukan provider dan kredensial dari pemilik. Refund perlu catatan pemeriksaan yang terpisah dari pengembalian stok.

Tahap 03 tidak boleh menerbitkan kebijakan retur, jaminan, identitas badan usaha, atau angka keuntungan yang belum disetujui/tersedia. Monitoring dan email operasional harus menghindari data pribadi serta punya pengaturan pengiriman yang jelas. Backup baru dinyatakan teruji setelah berhasil direstore ke database terpisah.

Tahap 04 harus memakai harga, stok dan rating nyata untuk SEO. Uji perangkat Android/iPhone fisik, jaringan lambat/putus, akses keyboard/pembaca layar, dan penerimaan produksi tetap diperlukan setelah pengujian otomatis.
