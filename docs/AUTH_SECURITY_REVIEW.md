# Review keamanan autentikasi Google dan polish halaman akun

Dilakukan dengan skill Trail of Bits [sharp-edges](../.agents/skills/sharp-edges/SKILL.md), terutama referensi authentication/session, konfigurasi, dan Python. Tampilan mengikuti [design-taste-frontend](../.agents/skills/design-taste-frontend/SKILL.md) serta arah Framed sheet dan palette/type Anredseller yang sudah dipilih. Ini review terarah pada autentikasi dan perubahan terkait; bukan sertifikasi keamanan seluruh aplikasi.

## Batas kepercayaan dan keputusan

| Permukaan | Keputusan dan bukti pengamanan |
| --- | --- |
| Masuk/daftar Google | Authorization Code + PKCE S256; state acak 256 bit, terikat browser dan disimpan sebagai hash; alur kedaluwarsa dalam 5 menit dan dikonsumsi atomik sebelum jaringan Google dipanggil. |
| Identitas eksternal | `google-auth` memeriksa tanda tangan, audience, issuer dan waktu token. Aplikasi membatasi algoritma RS256, menuntut nonce sesuai alur, audience/azp tepat, subject valid dan `email_verified` berupa boolean true. |
| Pertukaran code | Endpoint Google tetap, TLS diverifikasi, redirect HTTP tidak diikuti, timeout koneksi 3,05 detik dan baca 8 detik. Tidak ada opsi browser untuk mengganti issuer, kunci atau melewati verifikasi. |
| Tujuan kembali | Origin hanya dari konfigurasi HTTPS tervalidasi; halaman selanjutnya dibatasi pada route HTML toko. Callback tidak menerima tujuan eksternal atau mengandalkan Host pengunjung. |
| Email yang sudah terdaftar | Tidak menggabungkan akun otomatis berdasarkan email. Hubungkan Google hanya dari sesi akun yang aktif, setelah kata sandi lokal diverifikasi, dan dengan email Google yang sama. Callback harus masih terikat sesi pembeli yang memulai. |
| Koneksi Google | Subject menjadi kunci identitas stabil; tidak mengganti pemilik akun karena email Google berubah. Akun Google murni tidak mendapat password kosong yang bisa dipakai login. Melepas Google butuh password lokal dan tidak dapat menghapus satu-satunya metode masuk. |
| Sesi | Setelah autentikasi sesi pembeli dan CSRF dirotasi; token sesi disimpan sebagai hash. Logout-all mencabut semua sesi milik satu pembeli, tanpa menghapus sesi pemilik atau pembeli lain. Melepas Google juga mencabut sesi perangkat lain. |
| Cookie dan kebocoran token | HttpOnly + SameSite=Lax; Secure menjadi default di Vercel dan diwajibkan pada konfigurasi Google HTTPS. Callback memakai `no-store` dan `Referrer-Policy: no-referrer`. Access/refresh/ID token Google tidak disimpan atau dikirim ke frontend. |
| Penyimpanan | Dua tabel privat baru menggunakan RLS dan pembatasan role; tidak ada endpoint publik pembaca alur/identitas. SQLite tetap tersedia untuk pengembangan lokal. |
| Percobaan masuk | CSRF dan pembatasan percobaan tetap berlaku, termasuk awal Google, penghubungan, pelepasan dan ganti password. Password yang tidak cocok/akun yang tidak ada mengembalikan pesan masuk yang sama dan menjalankan pemeriksaan hash dummy. |

## Tiga sudut pandang penyalahgunaan

- Penyerang yang mengontrol request: state/code/next/Host tidak bisa memilih akun atau callback; issuer, audience, nonce, signature dan kepemilikan data diverifikasi di server.
- Pengembang yang menyalin konfigurasi: kredensial parsial, secret sesi lemah, HTTP produksi dan cookie non-Secure ditolak ketika Google diaktifkan. Tidak ada flag untuk menonaktifkan verifikasi token/TLS.
- Pengembang atau pengguna yang keliru menganggap email sebagai identitas: Google subject dipisah dari email, akun lama tidak digabung otomatis, dan penghubungan/pelepasan memerlukan autentikasi yang sesuai.

## Temuan konkret dan perbaikan

1. Middleware header sebelumnya menimpa `no-referrer` khusus callback menjadi `same-origin`. Uji negatif mendeteksi ini; middleware sekarang mempertahankan kebijakan route yang lebih ketat.
2. Default Secure cookie di project Vercel sebelumnya bergantung pada environment tambahan yang mudah terlupa. Default pada Vercel sekarang Secure, dan Google produksi menolak cookie tanpa Secure.
3. Penambahan tombol tampil/sembunyikan password membuat selector submit generik berpotensi menunjuk tombol yang salah. Handler sekarang memilih `button[type=submit]` secara eksplisit.
4. API password menangani akun yang tidak punya password lokal melalui jalur gagal yang eksplisit; pemeriksaan password tidak menganggap hash kosong sebagai izin masuk.
5. Parser tujuan kembali sekarang menangani URI yang rusak dengan tujuan default, bukan error server. Perubahan kata sandi dan pelepasan Google memeriksa ulang sesi di dalam transaksi sebelum mutasi.
6. Tampilan akun pada HP memprioritaskan formulir dan tombol masuk. Foto kampanye mengikuti formulir; halaman beranda tetap memakai komposisi kampanye yang sebelumnya disetujui. Tidak ada klaim keamanan absolut atau status verifikasi palsu dalam UI.

## Pengujian dan hasil

Fixture Google hanya hidup dalam proses pengujian; tidak ada switch produksi yang mengaktifkan token uji atau menonaktifkan tanda tangan.

- `tests/test_google_login.py`: Google sign-in/sign-up, password-only isolation, invalid issuer/audience/azp/nonce/times, missing or false email verification, wrong RSA keys, unsigned/HS256 tokens, one-use state with an old cookie replay, browser binding, expiry, duplicate parameters, collisions, linking/unlinking, logout during linking, CSRF, throttling, provider cancellation/failure, malformed next URLs and Host-header injection. Google ID tokens are verified with real RSA cryptography in these tests.
- **79 backend tests passed** across **SQLite and a real temporary PostgreSQL server**, including the new Google cases and session revocation cases. Production Supabase is not used by tests.
- Existing shopping browser workflow passes with **separate storefront/admin origins**, including owner publishing, customer registration, saved addresses, wishlist, cross-device cart, checkout, private order history and logout.
- New Google browser workflow passes at **1440, 768, 390, 320 and 844px landscape** with a local provider fixture: actual callback, signup, local RSA token verification, password visibility, wrong-password linking refusal, linking, unlinking, logout-all and no uncaught page errors.
- Existing responsive suite: **231 checks**, 13 pages/states and 14 viewport sizes, including long content, forms and dialogs.
- Taste-skill account inspector: **0 FAIL, 1 WARN** at 1440/768/390. Remaining warning is the deliberate breathing space in the campaign photograph, not an empty data panel; it preserves the existing editorial image. No rule allowances needed for this account screen.
- `pip-audit --no-deps --disable-pip -r requirements.txt` checked all **23 explicitly pinned installed dependencies**: no known vulnerabilities reported on 2026-10-20. This is a point-in-time dependency result.
- JavaScript syntax, Python imports/compilation, `pip check` and `git diff --check` pass.

## Batas dan pengaturan pemilik

- Konfigurasi Google Cloud/Vercel serta migrasi database di project Supabase asli harus dilakukan pemilik; lihat [panduan aktivasi](GOOGLE_LOGIN.md). Tidak ada kredensial produksi yang diberikan/dipakai pada perubahan ini.
- Pengujian provider memakai token RSA lokal dan HTTP Google tiruan, bukan layanan Google asli. Persetujuan/publishing di Google belum diuji langsung.
- Cookie/session aplikasi tidak otomatis berakhir ketika pengguna keluar dari Google; gunakan logout Anredseller atau Keluar dari semua perangkat. Sesi pembeli memiliki masa berlaku 30 hari sesuai implementasi yang sudah ada.
- Verifikasi email dan pemulihan password berbasis email/SMS masih membutuhkan layanan transaksional dan belum disediakan. Tidak ditambahkan penggabungan akun atau reset password yang hanya mempercayai email dari browser.
- Pembatasan percobaan masih memakai alamat koneksi yang diberikan server. Kebijakan proxy/rate limiting di edge dan pemantauan penyalahgunaan produksi perlu disesuaikan dengan trafik hosting sesungguhnya; header forwarded dari browser tidak langsung dipercaya sebagai identitas.
- Skill keamanan dan dependency audit membantu menguji batas yang diketahui, tidak menjamin aplikasi bebas dari seluruh kerentanan.

## Catatan taste-skill

Komponen akun melanjutkan Framed sheet, seed 2058406519, dengan Switzer/Georgia dan warna stone/olive yang sudah dipilih; tidak ada redraw arah beranda. Form yang benar-benar bekerja menjadi live element, termasuk login Google, mode daftar, toggle password, serta pengelolaan koneksi. Foto kampanye tetap aset demonstrasi yang sudah didokumentasikan di `assets/SOURCES.md`; logo G mengikuti merek Google, bukan ilustrasi produk.

ROUND 1: form desktop jelas, tetapi foto mendahului seluruh pilihan login pada HP. Form dipindah ke urutan pertama pada HP. Font heading akun dan dialog diseragamkan, backdrop dialog dibuat flat, dan screenshot diperiksa ulang.

ROUND 2: pertanyaan “bagaimana saya masuk?” terjawab dari judul dan tombol Google/email. Tidak ada kontrol login yang membutuhkan horizontal scroll pada 320px, tablet atau landscape. Skor penilaian internal: design 7,5 · usability 8,0 · creativity 6,5 · content 7,5 → **7,5/10**. Keterbatasan utama tetap foto kampanye contoh dan kebutuhan konfigurasi Google produksi oleh pemilik. Ini penilaian internal, bukan hasil audit independen atau penghargaan desain.
