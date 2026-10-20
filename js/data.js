const KATEGORI = [
  { id: "sneakers", nama: "Sneakers", icon: "", gambar: "assets/shoe-1.png" },
  { id: "apparel", nama: "Apparel", icon: "", gambar: "assets/shirt.png" },
  { id: "essentials", nama: "Essentials", icon: "", gambar: "assets/polo.png" },
];
const PRODUK = [
  {
    id: 1,
    nama: "Nike Air Max Pulse",
    kategori: "sneakers",
    harga: 1899000,
    hargaAsli: 2199000,
    stok: 12,
    rating: 0,
    ulasan: 0,
    terjual: 0,
    deskripsi:
      "Nike Air Max Pulse. Siluet timeless dengan detail yang mudah dipadukan untuk gaya sehari-hari. Koleksi contoh pilihan Anredseller Periksa detail ukuran dan ketersediaan sebelum memesan.",
    gambar: "assets/shoe-1.png",
    gambarList: ["assets/shoe-1.png"],
    trending: true,
    rekomendasi: false,
    label: "New arrival",
    brand: "Nike",
    spesifikasi: {
      Koleksi: "Nike",
      Kondisi: "Baru",
      Kategori: "Sneakers",
      Catatan: "Produk katalog demonstrasi",
    },
  },
  {
    id: 2,
    nama: "Nike Air Jordan 1 Low",
    kategori: "sneakers",
    harga: 1699000,
    hargaAsli: 1999000,
    stok: 13,
    rating: 0,
    ulasan: 0,
    terjual: 0,
    deskripsi:
      "Nike Air Jordan 1 Low. Siluet timeless dengan detail yang mudah dipadukan untuk gaya sehari-hari. Koleksi contoh pilihan Anredseller Periksa detail ukuran dan ketersediaan sebelum memesan.",
    gambar: "assets/shoe-2.png",
    gambarList: ["assets/shoe-2.png"],
    trending: true,
    rekomendasi: false,
    label: "Best seller",
    brand: "Jordan",
    spesifikasi: {
      Koleksi: "Jordan",
      Kondisi: "Baru",
      Kategori: "Sneakers",
      Catatan: "Produk katalog demonstrasi",
    },
  },
  {
    id: 3,
    nama: "Nike Air Max 270",
    kategori: "sneakers",
    harga: 2199000,
    hargaAsli: 2499000,
    stok: 14,
    rating: 0,
    ulasan: 0,
    terjual: 0,
    deskripsi:
      "Nike Air Max 270. Siluet timeless dengan detail yang mudah dipadukan untuk gaya sehari-hari. Koleksi contoh pilihan Anredseller Periksa detail ukuran dan ketersediaan sebelum memesan.",
    gambar: "assets/shoe-3.png",
    gambarList: ["assets/shoe-3.png"],
    trending: true,
    rekomendasi: false,
    label: "New arrival",
    brand: "Nike",
    spesifikasi: {
      Koleksi: "Nike",
      Kondisi: "Baru",
      Kategori: "Sneakers",
      Catatan: "Produk katalog demonstrasi",
    },
  },
  {
    id: 4,
    nama: "Everyday Essential Tee",
    kategori: "apparel",
    harga: 249000,
    hargaAsli: 349000,
    stok: 15,
    rating: 0,
    ulasan: 0,
    terjual: 0,
    deskripsi:
      "Everyday Essential Tee. Siluet timeless dengan detail yang mudah dipadukan untuk gaya sehari-hari. Koleksi contoh pilihan Anredseller Periksa detail ukuran dan ketersediaan sebelum memesan.",
    gambar: "assets/shirt.png",
    gambarList: ["assets/shirt.png"],
    trending: true,
    rekomendasi: false,
    label: "Essential",
    brand: "Anred essentials",
    spesifikasi: {
      Koleksi: "Anred essentials",
      Kondisi: "Baru",
      Kategori: "Apparel",
      Catatan: "Produk katalog demonstrasi",
    },
  },
  {
    id: 5,
    nama: "Nike Air Jordan 1 Mid",
    kategori: "sneakers",
    harga: 1999000,
    hargaAsli: 2299000,
    stok: 16,
    rating: 0,
    ulasan: 0,
    terjual: 0,
    deskripsi:
      "Nike Air Jordan 1 Mid. Siluet timeless dengan detail yang mudah dipadukan untuk gaya sehari-hari. Koleksi contoh pilihan Anredseller Periksa detail ukuran dan ketersediaan sebelum memesan.",
    gambar: "assets/shoe-4.svg",
    gambarList: ["assets/shoe-4.svg"],
    trending: false,
    rekomendasi: true,
    label: "",
    brand: "Jordan",
    spesifikasi: {
      Koleksi: "Jordan",
      Kondisi: "Baru",
      Kategori: "Sneakers",
      Catatan: "Produk katalog demonstrasi",
    },
  },
  {
    id: 6,
    nama: "Relaxed Straight Denim",
    kategori: "apparel",
    harga: 549000,
    hargaAsli: 699000,
    stok: 17,
    rating: 0,
    ulasan: 0,
    terjual: 0,
    deskripsi:
      "Relaxed Straight Denim. Siluet timeless dengan detail yang mudah dipadukan untuk gaya sehari-hari. Koleksi contoh pilihan Anredseller Periksa detail ukuran dan ketersediaan sebelum memesan.",
    gambar: "assets/jeans.png",
    gambarList: ["assets/jeans.png"],
    trending: false,
    rekomendasi: true,
    label: "New arrival",
    brand: "Anred essentials",
    spesifikasi: {
      Koleksi: "Anred essentials",
      Kondisi: "Baru",
      Kategori: "Apparel",
      Catatan: "Produk katalog demonstrasi",
    },
  },
  {
    id: 7,
    nama: "Classic Check Shirt",
    kategori: "apparel",
    harga: 399000,
    hargaAsli: 499000,
    stok: 18,
    rating: 0,
    ulasan: 0,
    terjual: 0,
    deskripsi:
      "Classic Check Shirt. Siluet timeless dengan detail yang mudah dipadukan untuk gaya sehari-hari. Koleksi contoh pilihan Anredseller Periksa detail ukuran dan ketersediaan sebelum memesan.",
    gambar: "assets/check-shirt.png",
    gambarList: ["assets/check-shirt.png"],
    trending: false,
    rekomendasi: true,
    label: "",
    brand: "Anred essentials",
    spesifikasi: {
      Koleksi: "Anred essentials",
      Kondisi: "Baru",
      Kategori: "Apparel",
      Catatan: "Produk katalog demonstrasi",
    },
  },
  {
    id: 8,
    nama: "Contrast Panel Tee",
    kategori: "essentials",
    harga: 329000,
    hargaAsli: 429000,
    stok: 19,
    rating: 0,
    ulasan: 0,
    terjual: 0,
    deskripsi:
      "Contrast Panel Tee. Siluet timeless dengan detail yang mudah dipadukan untuk gaya sehari-hari. Koleksi contoh pilihan Anredseller Periksa detail ukuran dan ketersediaan sebelum memesan.",
    gambar: "assets/polo.png",
    gambarList: ["assets/polo.png"],
    trending: false,
    rekomendasi: true,
    label: "Best seller",
    brand: "Anred essentials",
    spesifikasi: {
      Koleksi: "Anred essentials",
      Kondisi: "Baru",
      Kategori: "Essentials",
      Catatan: "Produk katalog demonstrasi",
    },
  },
  {
    id: 9,
    nama: "Nike Air Jordan Retro",
    kategori: "sneakers",
    harga: 2299000,
    hargaAsli: 2599000,
    stok: 20,
    rating: 0,
    ulasan: 0,
    terjual: 0,
    deskripsi:
      "Nike Air Jordan Retro. Siluet timeless dengan detail yang mudah dipadukan untuk gaya sehari-hari. Koleksi contoh pilihan Anredseller Periksa detail ukuran dan ketersediaan sebelum memesan.",
    gambar: "assets/shoe-5.svg",
    gambarList: ["assets/shoe-5.svg"],
    trending: false,
    rekomendasi: false,
    label: "",
    brand: "Jordan",
    spesifikasi: {
      Koleksi: "Jordan",
      Kondisi: "Baru",
      Kategori: "Sneakers",
      Catatan: "Produk katalog demonstrasi",
    },
  },
  {
    id: 10,
    nama: "Nike Air Max Essential",
    kategori: "sneakers",
    harga: 1799000,
    hargaAsli: 1999000,
    stok: 21,
    rating: 0,
    ulasan: 0,
    terjual: 0,
    deskripsi:
      "Nike Air Max Essential. Siluet timeless dengan detail yang mudah dipadukan untuk gaya sehari-hari. Koleksi contoh pilihan Anredseller Periksa detail ukuran dan ketersediaan sebelum memesan.",
    gambar: "assets/shoe-6.svg",
    gambarList: ["assets/shoe-6.svg"],
    trending: false,
    rekomendasi: false,
    label: "",
    brand: "Nike",
    spesifikasi: {
      Koleksi: "Nike",
      Kondisi: "Baru",
      Kategori: "Sneakers",
      Catatan: "Produk katalog demonstrasi",
    },
  },
  {
    id: 11,
    nama: "Nike Air Jordan Court",
    kategori: "sneakers",
    harga: 1599000,
    hargaAsli: 1899000,
    stok: 22,
    rating: 0,
    ulasan: 0,
    terjual: 0,
    deskripsi:
      "Nike Air Jordan Court. Siluet timeless dengan detail yang mudah dipadukan untuk gaya sehari-hari. Koleksi contoh pilihan Anredseller Periksa detail ukuran dan ketersediaan sebelum memesan.",
    gambar: "assets/shoe-7.svg",
    gambarList: ["assets/shoe-7.svg"],
    trending: false,
    rekomendasi: false,
    label: "",
    brand: "Jordan",
    spesifikasi: {
      Koleksi: "Jordan",
      Kondisi: "Baru",
      Kategori: "Sneakers",
      Catatan: "Produk katalog demonstrasi",
    },
  },
];

// Fungsi helper
function getProdukById(id) {
  return PRODUK.find((p) => p.id === parseInt(id));
}

function getProdukByKategori(kategoriId) {
  return PRODUK.filter((p) => p.kategori === kategoriId);
}

function getProdukTrending() {
  return PRODUK.filter((p) => p.trending);
}

function getProdukRekomendasi() {
  return PRODUK.filter((p) => p.rekomendasi);
}

function formatHarga(angka) {
  return "Rp " + angka.toLocaleString("id-ID");
}

function hitungDiskon(harga, hargaAsli) {
  return Math.round((1 - harga / hargaAsli) * 100);
}

function renderBintang(rating) {
  const penuh = Math.floor(rating);
  const setengah = rating % 1 >= 0.5;
  let html = "";
  for (let i = 0; i < penuh; i++)
    html += '<span class="bintang-penuh">★</span>';
  if (setengah) html += '<span class="bintang-setengah">★</span>';
  for (let i = penuh + (setengah ? 1 : 0); i < 5; i++)
    html += '<span class="bintang-kosong">☆</span>';
  return html;
}

// Fashion leads the edit; sneakers complete the collection.
PRODUK.sort(
  (a, b) =>
    [4, 6, 7, 8, 1, 2, 3, 5, 9, 10, 11].indexOf(a.id) -
    [4, 6, 7, 8, 1, 2, 3, 5, 9, 10, 11].indexOf(b.id),
);

// All browsers load the published catalog from the same server database.
let katalogMode = "loading";
let katalogError = "";
function h(value) {
  return String(value ?? "").replace(
    /[&<>"']/g,
    (char) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[
        char
      ],
  );
}
function productImage(value) {
  return /^(assets\/[a-zA-Z0-9_-]+\.(png|jpe?g|webp|svg)|\/uploads\/[a-f0-9]{32}\.webp)$/.test(
    value || "",
  )
    ? value
    : "assets/shirt.png";
}
const katalogSiap = (async () => {
  if (location.protocol === "file:") {
    katalogMode = "preview";
    return;
  }
  try {
    const response = await fetch("/api/products", { cache: "no-store" });
    if (response.status === 404) {
      katalogMode = "preview";
      return;
    }
    if (!response.ok)
      throw new Error("Katalog belum dapat dimuat. Coba muat ulang halaman.");
    const data = await response.json();
    if (!Array.isArray(data.products))
      throw new Error("Respons katalog tidak valid.");
    PRODUK.splice(0, PRODUK.length, ...data.products);
    katalogMode = "server";
  } catch (error) {
    katalogMode = "error";
    katalogError =
      "Katalog belum dapat dimuat. Periksa koneksi lalu muat ulang halaman.";
    PRODUK.length = 0;
  }
})();
document.addEventListener("DOMContentLoaded", async () => {
  await katalogSiap;
  if (katalogMode === "preview" || katalogMode === "error") {
    const banner = document.createElement("p");
    banner.className = "catalog-notice";
    banner.setAttribute("role", "status");
    banner.textContent =
      katalogMode === "preview"
        ? "Pratinjau katalog contoh. Jalankan server Anredseller untuk mengelola produk dan menerima pesanan."
        : katalogError;
    (document.querySelector("main") || document.body).prepend(banner);
  }
});
