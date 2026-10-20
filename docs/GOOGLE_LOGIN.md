# Login dan daftar Google untuk Anredseller

Kode login Google sudah disiapkan. Tombol aktif setelah pemilik memasang konfigurasi berikut. Saat belum dikonfigurasi, login email tetap berjalan dan tombol Google menjelaskan bahwa metode itu belum tersedia.

Domain toko yang dikonfirmasi pemilik: **https://marketplace-theta-ebon.vercel.app**.

## 1. Siapkan client Google

Di [Google Cloud Console](https://console.cloud.google.com/), pilih/buat project dan buka **Google Auth Platform** (atau **APIs & Services → OAuth consent screen / Credentials** pada antarmuka lama).

1. Isi Branding dengan nama **Anredseller** dan email dukungan/kontak milikmu.
2. Atur audience External bila toko terbuka untuk umum. Selama status Testing, tambahkan akun penguji ke Test users. Gunakan status publik yang sesuai sebelum melayani semua pembeli.
3. Gunakan scope `openid`, `email`, dan `profile` saja. Website tidak meminta akses Gmail, Drive atau kontak.
4. Buat **OAuth client → Web application**.
5. Pada **Authorized redirect URIs**, tambahkan alamat persis ini, tanpa garis miring terakhir:

   ```text
   https://marketplace-theta-ebon.vercel.app/api/customer/google/callback
   ```

6. Simpan Client ID dan Client Secret di pengaturan Vercel di langkah 3. Jangan memasukkannya ke kode frontend atau GitHub. Jangan memakai secret Supabase sebagai Google Client Secret.

Alur ini berjalan di server; Google Identity Services SDK tidak dipasang di browser. Authorized JavaScript origins tidak dibutuhkan oleh implementasi ini.

## 2. Tambahkan tabel privat di Supabase

Buka **Supabase → SQL Editor → New query**, salin isi [003_google_login.sql](../migrations/003_google_login.sql), lalu klik **Run**. SQL ini dijalankan di SQL Editor, bukan di Windows Command Prompt.

Migrasi menambah tabel identitas Google dan alur login sementara. Tabel memakai RLS, tidak memberikan akses kepada `anon`/`authenticated`, dan berada di schema privat `anredseller`. Katalog, akun dan pesanan yang sudah ada tetap digunakan. Untuk instalasi baru melalui terminal, `python server.py init-db` juga menjalankan migrasi ini.

## 3. Isi environment variables di Vercel

Pada **project toko publik**, bukan project admin, buka **Settings → Environment Variables** dan isi untuk Production:

| Nama | Nilai |
| --- | --- |
| `GOOGLE_CLIENT_ID` | Client ID Web application dari Google, berakhiran `.apps.googleusercontent.com` |
| `GOOGLE_CLIENT_SECRET` | Client Secret dari client Google yang sama |
| `ANREDSELLER_PUBLIC_ORIGIN` | `https://marketplace-theta-ebon.vercel.app` |
| `ANREDSELLER_SECURE_COOKIES` | `1` |

Setelah tersimpan, redeploy project toko dari commit terbaru. Ketiganya harus konsisten; konfigurasi setengah terisi atau origin produksi tanpa HTTPS ditolak. Client Secret tidak muncul di respons API, URL kembali, session cookie atau file JavaScript.

Jika nanti pindah domain, ubah origin di Vercel dan redirect URI di Google bersama-sama. Redirect URI tidak dibentuk dari header Host atau input pengunjung.

## 4. Coba alurnya

- **Pembeli baru:** klik Lanjut dengan Google, pilih akun Google, lalu akun pembeli dibuat. Nama dan email terisi; nomor HP/alamat dilengkapi untuk pengiriman. Website tidak meminta atau menyimpan kata sandi Google.
- **Pembeli Google lama:** identitas Google yang sama membuka akun dan data belanja yang sama.
- **Sudah punya akun email:** masuk dengan kata sandi Anredseller, buka Profil saya → Keamanan akun → Hubungkan Google. Konfirmasi kata sandi saat ini, lalu pilih Google dengan email yang sama. Akun tidak otomatis digabung berdasarkan email.
- **Lepas Google:** akun yang punya kata sandi dapat memutuskan koneksi setelah konfirmasi kata sandi. Perangkat lain keluar. Akun yang hanya memakai Google tidak dapat melepaskan satu-satunya metode masuknya.
- **Cabut sesi:** Keluar dari semua perangkat mencabut semua sesi pembeli tersebut, termasuk perangkat sekarang. Akun pembeli lain dan sesi pemilik toko tidak terpengaruh.
- **Batal/error:** pembeli kembali ke halaman akun dengan pesan yang jelas. Status pesanan dan keranjang tidak diambil dari parameter callback.

Akun tersimpan di tabel aplikasi `anredseller.customers`, dengan identitas Google di `anredseller.customer_google_identities`. Akun ini tidak muncul di daftar Supabase Authentication/Users, karena aplikasi tetap memakai sistem sesi yang sama dengan katalog dan checkout yang sudah ada.

## Batas verifikasi

Pengujian otomatis memakai database lokal SQLite dan PostgreSQL, token yang benar-benar ditandatangani RSA, dan respons Google tiruan. Tidak ada akun Google asli atau secret produksi yang dipakai. Pengujian langsung dengan Google baru dapat dilakukan setelah pemilik memasang konfigurasi di atas.

Email/kata sandi tetap tersedia. Verifikasi email, pemulihan kata sandi lewat email, SMS OTP, Apple/Facebook login dan pembayaran otomatis belum ditambahkan dalam perubahan ini. Tidak ada indikator verifikasi atau tombol pemulihan yang berpura-pura sudah bekerja.
