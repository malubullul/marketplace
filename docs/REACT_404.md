# Halaman 404 React

Komponen `oversized-404-numeral.tsx` yang diminta kini digunakan untuk URL toko publik yang tidak ditemukan, termasuk `/404.html` sebagai pratinjau. Respons tetap **HTTP 404**, bukan redirect atau status 200. Teks memakai Bahasa Indonesia, font Switzer dan warna stone/olive Anredseller. Error API tetap JSON; aset hilang tetap 404; portal admin tetap memakai aplikasinya sendiri.

## Struktur dan dependensi

Sebelumnya toko tidak memiliki React, TypeScript, Tailwind maupun struktur shadcn. Dukungan ini ditambahkan khusus untuk halaman error. Halaman toko lainnya tetap menggunakan HTML/Jinja, `css/`, dan `js/`.

| Lokasi | Isi |
| --- | --- |
| `components/ui/oversized-404-numeral.tsx` | Komponen 404 utama |
| `components/ui/button.tsx` | Button shadcn dengan Radix Slot dan CVA |
| `lib/utils.ts` | `cn()` dengan clsx dan tailwind-merge |
| `frontend/error-page/demo.tsx` | Komposisi demo yang juga dipakai halaman nyata |
| `frontend/error-page/client.tsx` | Hydration React untuk tindakan kembali |
| `frontend/error-page/server.tsx` | Render HTML saat build |
| `frontend/styles/error-page.css` | Sumber Tailwind v4, font dan token warna |
| `components.json`, `tsconfig.json` | Konfigurasi shadcn, TypeScript dan alias `@/` ke root repo |
| `404.html`, `css/generated/`, `js/generated/` | Hasil build yang dilayani Flask |

`components/ui` adalah folder pada root repositori, bukan folder `/components` di root sistem operasi. Lokasi ini menyamakan alias impor `@/components/ui/...`, penempatan komponen shadcn dan pemindaian kelas Tailwind. Sumber TypeScript tidak dapat diakses lewat URL publik.

Dependensi produksi: React, React DOM, lucide-react, @radix-ui/react-slot, class-variance-authority, clsx dan tailwind-merge. Tool build: TypeScript, esbuild, Tailwind CSS dan CLI Tailwind. Versi tepat dan dependensi transitif dikunci dalam `package-lock.json`.

Contoh yang dikirim memakai API `render`/`nativeButton`, tetapi implementasi Button yang disertakan memakai Radix `asChild`. Integrasi menggunakan `asChild` dengan anak `<a>` agar menghasilkan tautan semantik, tanpa `<button>` membungkus tautan. Target sentuh minimal 44px.

## Mengembangkan di repositori ini

Node.js 22+ diperlukan untuk mengubah/build komponen; Python tetap menjalankan toko. Hasil build sudah disertakan sehingga hosting tidak membutuhkan Node saat menerima permintaan.

```sh
npm ci
npm run build:ui
.venv/bin/python server.py run
```

Buka `http://127.0.0.1:8000/404.html`. Setelah mengedit TSX atau CSS sumber, jalankan `npm run build:ui` lalu commit sumber **dan** hasil build. Periksa hasil build tidak tertinggal dengan `npm run check:ui`. Jangan mengedit file di `css/generated`, `js/generated` atau `404.html` secara manual. CSS hanya memindai komponen React yang relevan dan hanya dimuat oleh halaman error. Nama aset menggunakan versi hash pada URL untuk pembaruan cache.

Konfigurasi Vercel Python yang ada tetap dipakai. Source frontend dan `node_modules` dikecualikan dari deployment; tiga aset dan HTML hasil build ikut dikirim. API, database dan proses checkout tidak membutuhkan dependensi React ini.

## Jika membuat proyek React/shadcn baru melalui CLI

Untuk proyek baru terpisah, bukan menjalankan scaffolder di atas toko Flask ini:

```sh
npm create vite@latest anredseller-ui-demo -- --template react-ts
cd anredseller-ui-demo
npm install
npm install tailwindcss @tailwindcss/vite
npm install -D @types/node
```

Tambahkan `tailwindcss()` dari `@tailwindcss/vite` ke array `plugins` pada `vite.config.ts` bersama `react()`. Tambahkan `import path from "node:path"` dan `resolve: { alias: { "@": path.resolve(__dirname, "./src") } }`. Pada `tsconfig.json` serta `tsconfig.app.json`, tambahkan `compilerOptions.baseUrl: "."` dan `compilerOptions.paths: { "@/*": ["./src/*"] }`. Masukkan `@import "tailwindcss";` ke `src/index.css`, lalu jalankan:

```sh
npx shadcn@latest init
npx shadcn@latest add button
npm install lucide-react @radix-ui/react-slot class-variance-authority clsx tailwind-merge
```

Pastikan Button hasil CLI sesuai API komponen; contoh di repo ini memakai Radix `asChild`. Vite dengan alias `@/` ke `src/` memakai `src/components/ui`; proyek Flask ini memakai `components/ui` karena aliasnya menuju root repo. Tidak perlu menjalankan scaffolder lagi untuk repo ini karena konfigurasi dan komponen sudah tersedia.

## Navigasi dan fallback

“Ke beranda” menuju `/`. “Kembali” memakai riwayat browser hanya jika terdapat halaman sebelumnya dari origin toko yang sama. Kunjungan langsung, referrer eksternal, JavaScript dinonaktifkan atau bundle gagal dimuat menuju `/produk.html`. Tautan tetap dapat dibuka di tab baru. Tidak ada URL pengguna yang disisipkan ke halaman error. Angka dekoratif tersembunyi dari pembaca layar, sementara heading menyebut Error 404. Build HTML menggunakan komponen React yang sama sehingga tidak ada salinan desain fallback terpisah untuk dipelihara.

Verifikasi:

```sh
npm run check:ui
.venv/bin/python -m unittest discover -s tests -p test_not_found.py
python3 tests/browser_not_found_smoke.py
```

Integrasi diverifikasi dengan typecheck dan kecocokan build; 5 tes kontrak halaman 404, 12 tes server toko, dan 7 tes portal admin lolos. Pemeriksaan browser pada 7 ukuran layar mencakup hydration, navigasi keyboard, asal riwayat kembali, fallback JavaScript, dan ketiadaan overflow horizontal. Screenshot desktop, HP 320px, dan landscape diperiksa. `npm audit --omit=dev` melaporkan nol kerentanan yang diketahui pada dependensi produksi saat instalasi; ini bukan jaminan audit keamanan menyeluruh.
