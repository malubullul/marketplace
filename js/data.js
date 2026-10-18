// ============================================================
// DATA PRODUK & KATEGORI — PASAR NUSANTARA
// ============================================================

const KATEGORI = [
  { id: 'elektronik',    nama: 'Elektronik',    icon: '🎧', gambar: 'https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=120&q=80' },
  { id: 'fashion',       nama: 'Fashion',       icon: '👗', gambar: 'https://images.unsplash.com/photo-1523381210434-271e8be1f52b?w=120&q=80' },
  { id: 'rumah',         nama: 'Rumah & Taman', icon: '🛋️', gambar: 'https://images.unsplash.com/photo-1555041469-a586c61ea9bc?w=120&q=80' },
  { id: 'kecantikan',    nama: 'Kecantikan',    icon: '💄', gambar: 'https://images.unsplash.com/photo-1512496015851-a90fb38ba796?w=120&q=80' },
  { id: 'bayi',          nama: 'Bayi & Anak',   icon: '🧸', gambar: 'https://images.unsplash.com/photo-1515488042361-ee00e0ddd4e4?w=120&q=80' },
  { id: 'olahraga',      nama: 'Olahraga',      icon: '⚽', gambar: 'https://images.unsplash.com/photo-1517649763962-0c623066013b?w=120&q=80' },
  { id: 'buku',          nama: 'Buku',          icon: '📚', gambar: 'https://images.unsplash.com/photo-1481627834876-b7833e8f5570?w=120&q=80' },
  { id: 'makanan',       nama: 'Makanan',       icon: '🛒', gambar: 'https://images.unsplash.com/photo-1542838132-92c53300491e?w=120&q=80' },
];

const PRODUK = [
  // ELEKTRONIK
  {
    id: 1, nama: 'Earbuds Nirkabel Pro', kategori: 'elektronik', harga: 599000, hargaAsli: 899000,
    stok: 24, rating: 4.8, ulasan: 1243, terjual: 3820,
    deskripsi: 'Earbuds nirkabel premium dengan teknologi Active Noise Cancellation, koneksi Bluetooth 5.3, dan baterai tahan hingga 36 jam. Dilengkapi case pengisian daya dan desain ergonomis yang nyaman dipakai seharian.',
    gambar: 'https://images.unsplash.com/photo-1590658268037-6bf12165a8df?w=600&q=80',
    gambarList: [
      'https://images.unsplash.com/photo-1590658268037-6bf12165a8df?w=600&q=80',
      'https://images.unsplash.com/photo-1484704849700-f032a568e944?w=600&q=80',
      'https://images.unsplash.com/photo-1614680376573-df3480f0c6ff?w=600&q=80',
    ],
    trending: true, rekomendasi: false, label: 'Terlaris',
    spesifikasi: { 'Driver': '10mm Dynamic', 'Frekuensi': '20Hz - 20kHz', 'Konektivitas': 'Bluetooth 5.3', 'Baterai': '6+30 jam', 'Bobot': '5.8g/earbud' }
  },
  {
    id: 2, nama: 'Smartwatch Series X', kategori: 'elektronik', harga: 1250000, hargaAsli: 1899000,
    stok: 8, rating: 4.7, ulasan: 978, terjual: 2100,
    deskripsi: 'Smartwatch canggih dengan layar AMOLED 1.9 inci, monitor detak jantung 24 jam, GPS built-in, dan ketahanan air hingga 50 meter. Kompatibel dengan Android & iOS.',
    gambar: 'https://images.unsplash.com/photo-1523275335684-37898b6baf30?w=600&q=80',
    gambarList: [
      'https://images.unsplash.com/photo-1523275335684-37898b6baf30?w=600&q=80',
      'https://images.unsplash.com/photo-1579586337278-3befd40fd17a?w=600&q=80',
    ],
    trending: true, rekomendasi: true, label: 'Diskon 34%',
    spesifikasi: { 'Layar': 'AMOLED 1.9"', 'GPS': 'Built-in', 'Sensor': 'HR, SpO2, Gyro', 'Baterai': '7 hari', 'Water Resistance': '5ATM' }
  },
  {
    id: 3, nama: 'Speaker Bluetooth Premium', kategori: 'elektronik', harga: 390000, hargaAsli: 590000,
    stok: 45, rating: 4.6, ulasan: 654, terjual: 1890,
    deskripsi: 'Speaker portable dengan suara 360° yang jernih dan bass yang kuat. Tahan air IPX7, baterai 20 jam, dan fitur TWS untuk menggabungkan dua speaker.',
    gambar: 'https://images.unsplash.com/photo-1608043152269-423dbba4e7e1?w=600&q=80',
    gambarList: [
      'https://images.unsplash.com/photo-1608043152269-423dbba4e7e1?w=600&q=80',
      'https://images.unsplash.com/photo-1545454675-3531b543be5d?w=600&q=80',
    ],
    trending: false, rekomendasi: true, label: '',
    spesifikasi: { 'Output': '20W', 'Bluetooth': '5.0', 'Baterai': '20 jam', 'Water Resistance': 'IPX7', 'Bobot': '540g' }
  },
  {
    id: 4, nama: 'Laptop Ultrabook Slim', kategori: 'elektronik', harga: 8999000, hargaAsli: 11500000,
    stok: 5, rating: 4.9, ulasan: 321, terjual: 450,
    deskripsi: 'Laptop ultrabook tipis hanya 13.5mm dengan prosesor terbaru, RAM 16GB, SSD 512GB, dan layar IPS 14" resolusi 2K. Baterai tahan 12 jam untuk produktivitas tanpa batas.',
    gambar: 'https://images.unsplash.com/photo-1496181133206-80ce9b88a853?w=600&q=80',
    gambarList: [
      'https://images.unsplash.com/photo-1496181133206-80ce9b88a853?w=600&q=80',
      'https://images.unsplash.com/photo-1525547719571-a2d4ac8945e2?w=600&q=80',
    ],
    trending: false, rekomendasi: false, label: 'Stok Terbatas',
    spesifikasi: { 'Prosesor': 'Core i7 Gen 13', 'RAM': '16GB LPDDR5', 'Storage': '512GB NVMe', 'Layar': '14" 2K IPS', 'Baterai': '12 jam' }
  },
  {
    id: 5, nama: 'Kamera Mirrorless 24MP', kategori: 'elektronik', harga: 12500000, hargaAsli: 15000000,
    stok: 3, rating: 4.8, ulasan: 189, terjual: 230,
    deskripsi: 'Kamera mirrorless full-frame 24 megapiksel dengan sistem autofokus AI, video 4K 60fps, dan stabilisasi gambar 5-axis. Cocok untuk fotografer profesional maupun pemula.',
    gambar: 'https://images.unsplash.com/photo-1516035069371-29a1b244cc32?w=600&q=80',
    gambarList: [
      'https://images.unsplash.com/photo-1516035069371-29a1b244cc32?w=600&q=80',
    ],
    trending: false, rekomendasi: false, label: 'Premium',
    spesifikasi: { 'Sensor': 'Full-Frame 24MP', 'Video': '4K 60fps', 'AF': 'AI Eye-Tracking', 'ISO': '100-51200', 'Baterai': '400 foto' }
  },

  // FASHION
  {
    id: 6, nama: 'Jaket Parka Premium', kategori: 'fashion', harga: 349000, hargaAsli: 599000,
    stok: 32, rating: 4.5, ulasan: 845, terjual: 2200,
    deskripsi: 'Jaket parka premium bahan waterproof dengan lapisan fleece hangat di dalam. Tersedia dalam berbagai ukuran S-XXL dan 5 pilihan warna. Cocok untuk outdoor maupun casual.',
    gambar: 'https://images.unsplash.com/photo-1551028719-00167b16eac5?w=600&q=80',
    gambarList: [
      'https://images.unsplash.com/photo-1551028719-00167b16eac5?w=600&q=80',
      'https://images.unsplash.com/photo-1548126032-079a0fb0099d?w=600&q=80',
    ],
    trending: true, rekomendasi: false, label: 'Best Seller',
    spesifikasi: { 'Bahan': 'Polyester Waterproof', 'Ukuran': 'S - XXL', 'Warna': '5 Pilihan', 'Lapisan': 'Fleece', 'Perawatan': 'Machine Wash' }
  },
  {
    id: 7, nama: 'Sepatu Sneakers Kasual', kategori: 'fashion', harga: 459000, hargaAsli: 699000,
    stok: 18, rating: 4.6, ulasan: 1102, terjual: 3100,
    deskripsi: 'Sneakers kasual dengan sol karet anti-slip dan insole memory foam untuk kenyamanan maksimal. Upper berbahan mesh breathable yang ringan dan berventilasi.',
    gambar: 'https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=600&q=80',
    gambarList: [
      'https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=600&q=80',
      'https://images.unsplash.com/photo-1608231387042-66d1773070a5?w=600&q=80',
    ],
    trending: true, rekomendasi: true, label: 'Terpopuler',
    spesifikasi: { 'Upper': 'Mesh Breathable', 'Sol': 'Karet Anti-slip', 'Insole': 'Memory Foam', 'Ukuran': '38-45', 'Warna': '8 Pilihan' }
  },
  {
    id: 8, nama: 'Hoodie Oversize Polos', kategori: 'fashion', harga: 299000, hargaAsli: 450000,
    stok: 56, rating: 4.7, ulasan: 2341, terjual: 5600,
    deskripsi: 'Hoodie oversize bahan cotton fleece tebal 280gsm, nyaman dan hangat. Tersedia dalam 12 pilihan warna netral. Jahitan rapi double-stitch untuk ketahanan jangka panjang.',
    gambar: 'https://images.unsplash.com/photo-1556821840-3a63f15732ce?w=600&q=80',
    gambarList: [
      'https://images.unsplash.com/photo-1556821840-3a63f15732ce?w=600&q=80',
    ],
    trending: false, rekomendasi: true, label: '',
    spesifikasi: { 'Bahan': 'Cotton Fleece 280gsm', 'Ukuran': 'S-3XL (Oversize)', 'Warna': '12 Pilihan', 'Jahitan': 'Double Stitch', 'Perawatan': 'Cold Wash' }
  },

  // RUMAH
  {
    id: 9, nama: 'Lilin Aromaterapi Soy Wax', kategori: 'rumah', harga: 189000, hargaAsli: 290000,
    stok: 78, rating: 4.8, ulasan: 632, terjual: 1890,
    deskripsi: 'Lilin aromaterapi premium dari 100% soy wax dengan aroma lavender, vanilla, dan sandalwood. Waktu bakar hingga 55 jam. Dikemas dalam toples kaca cantik yang bisa digunakan kembali.',
    gambar: 'https://images.unsplash.com/photo-1602178506555-a04ce9e50571?w=600&q=80',
    gambarList: [
      'https://images.unsplash.com/photo-1602178506555-a04ce9e50571?w=600&q=80',
    ],
    trending: true, rekomendasi: false, label: 'Eco-Friendly',
    spesifikasi: { 'Bahan': '100% Soy Wax', 'Aroma': 'Lavender/Vanilla/Sandalwood', 'Durasi Bakar': '55 jam', 'Kemasan': 'Toples Kaca', 'Berat': '250g' }
  },
  {
    id: 10, nama: 'Set Bantal Sofa Mewah', kategori: 'rumah', harga: 350000, hargaAsli: 500000,
    stok: 22, rating: 4.5, ulasan: 289, terjual: 670,
    deskripsi: 'Set 4 bantal sofa dengan sarung berbahan velvet premium. Isian memory foam yang mempertahankan bentuk. Tersedia berbagai motif dan warna yang cocok untuk berbagai gaya interior.',
    gambar: 'https://images.unsplash.com/photo-1555041469-a586c61ea9bc?w=600&q=80',
    gambarList: [
      'https://images.unsplash.com/photo-1555041469-a586c61ea9bc?w=600&q=80',
    ],
    trending: false, rekomendasi: false, label: '',
    spesifikasi: { 'Isi': '4 Bantal', 'Sarung': 'Velvet Premium', 'Isian': 'Memory Foam', 'Ukuran': '45x45cm', 'Perawatan': 'Dry Clean' }
  },
  {
    id: 11, nama: 'Tanaman Hias Pot Gantung', kategori: 'rumah', harga: 125000, hargaAsli: 180000,
    stok: 40, rating: 4.4, ulasan: 445, terjual: 1200,
    deskripsi: 'Tanaman hias pothos dalam pot gantung keramik minimalis. Tanaman mudah dirawat dan tahan banting, cocok untuk dekorasi rumah maupun kantor.',
    gambar: 'https://images.unsplash.com/photo-1416879595882-3373a0480b5b?w=600&q=80',
    gambarList: [
      'https://images.unsplash.com/photo-1416879595882-3373a0480b5b?w=600&q=80',
    ],
    trending: false, rekomendasi: true, label: '',
    spesifikasi: { 'Jenis': 'Pothos Hijau', 'Pot': 'Keramik Minimalis', 'Diameter': '15cm', 'Tinggi': '20-30cm', 'Perawatan': 'Mudah' }
  },

  // KECANTIKAN
  {
    id: 12, nama: 'Set Skincare Lengkap', kategori: 'kecantikan', harga: 249000, hargaAsli: 390000,
    stok: 35, rating: 4.9, ulasan: 1142, terjual: 3400,
    deskripsi: 'Set skincare lengkap 5 langkah: cleanser, toner, serum vitamin C, moisturizer, dan sunscreen SPF50. Formula hipoalergenik cocok untuk semua jenis kulit termasuk kulit sensitif.',
    gambar: 'https://images.unsplash.com/photo-1612817288484-6f916006741a?w=600&q=80',
    gambarList: [
      'https://images.unsplash.com/photo-1612817288484-6f916006741a?w=600&q=80',
    ],
    trending: true, rekomendasi: true, label: 'BPOM Approved',
    spesifikasi: { 'Isi': '5 Produk', 'Formula': 'Hipoalergenik', 'Cocok untuk': 'Semua jenis kulit', 'Volume': '30-50ml/produk', 'Sertifikasi': 'BPOM RI' }
  },
  {
    id: 13, nama: 'Palette Eyeshadow 18 Warna', kategori: 'kecantikan', harga: 199000, hargaAsli: 350000,
    stok: 28, rating: 4.7, ulasan: 876, terjual: 2800,
    deskripsi: 'Palette eyeshadow 18 warna dengan formula pigmented tinggi, mudah diaplikasikan dan tahan lama hingga 12 jam. Tersedia finishing matte, shimmer, dan glitter.',
    gambar: 'https://images.unsplash.com/photo-1512496015851-a90fb38ba796?w=600&q=80',
    gambarList: [
      'https://images.unsplash.com/photo-1512496015851-a90fb38ba796?w=600&q=80',
    ],
    trending: false, rekomendasi: true, label: '',
    spesifikasi: { 'Warna': '18 Shade', 'Finishing': 'Matte/Shimmer/Glitter', 'Ketahanan': '12 jam', 'Berat': '150g', 'Sertifikasi': 'Halal MUI' }
  },

  // BAYI
  {
    id: 14, nama: 'Stroller Bayi Premium', kategori: 'bayi', harga: 990000, hargaAsli: 1550000,
    stok: 7, rating: 4.8, ulasan: 234, terjual: 380,
    deskripsi: 'Stroller bayi dengan kerangka aluminium ringan namun kuat, suspensi 4 roda untuk kenyamanan bayi, canopy UV protection, dan kursi reversible. Dilipat dalam 1 langkah mudah.',
    gambar: 'https://images.unsplash.com/photo-1515488042361-ee00e0ddd4e4?w=600&q=80',
    gambarList: [
      'https://images.unsplash.com/photo-1515488042361-ee00e0ddd4e4?w=600&q=80',
    ],
    trending: false, rekomendasi: true, label: 'SNI Certified',
    spesifikasi: { 'Rangka': 'Aluminium', 'Beban Maks': '22kg', 'Usia': '0-3 tahun', 'Bobot': '7.5kg', 'Garansi': '2 tahun' }
  },

  // OLAHRAGA
  {
    id: 15, nama: 'Dumbbell Set 10kg', kategori: 'olahraga', harga: 550000, hargaAsli: 750000,
    stok: 15, rating: 4.6, ulasan: 387, terjual: 890,
    deskripsi: 'Set dumbbell adjustable 2-10kg dengan handle anti-slip dan material besi cor berkualitas. Dilengkapi stand penyimpanan. Cocok untuk latihan di rumah.',
    gambar: 'https://images.unsplash.com/photo-1571019614242-c5c5dee9f50b?w=600&q=80',
    gambarList: [
      'https://images.unsplash.com/photo-1571019614242-c5c5dee9f50b?w=600&q=80',
    ],
    trending: false, rekomendasi: false, label: '',
    spesifikasi: { 'Berat': '2-10kg (Adjustable)', 'Material': 'Besi Cor', 'Handle': 'Anti-slip', 'Termasuk': 'Stand Storage', 'Garansi': '1 tahun' }
  },
  {
    id: 16, nama: 'Yoga Mat Non-Slip 6mm', kategori: 'olahraga', harga: 199000, hargaAsli: 320000,
    stok: 60, rating: 4.7, ulasan: 1023, terjual: 3200,
    deskripsi: 'Yoga mat premium bahan TPE ramah lingkungan, ketebalan 6mm untuk kenyamanan lutut dan sendi. Permukaan double-sided non-slip dan mudah dibersihkan.',
    gambar: 'https://images.unsplash.com/photo-1544367567-0f2fcb009e0b?w=600&q=80',
    gambarList: [
      'https://images.unsplash.com/photo-1544367567-0f2fcb009e0b?w=600&q=80',
    ],
    trending: false, rekomendasi: false, label: 'Eco-Friendly',
    spesifikasi: { 'Bahan': 'TPE Eco-Friendly', 'Ketebalan': '6mm', 'Ukuran': '183 x 61cm', 'Bobot': '1.1kg', 'Warna': '6 Pilihan' }
  },

  // BUKU
  {
    id: 17, nama: 'Atomic Habits (Terjemahan)', kategori: 'buku', harga: 95000, hargaAsli: 138000,
    stok: 120, rating: 4.9, ulasan: 4520, terjual: 12000,
    deskripsi: 'Buku best-seller internasional oleh James Clear, terjemahan resmi bahasa Indonesia. Panduan praktis untuk membangun kebiasaan baik dan membuang kebiasaan buruk.',
    gambar: 'https://images.unsplash.com/photo-1544716278-ca5e3f4abd8c?w=600&q=80',
    gambarList: [
      'https://images.unsplash.com/photo-1544716278-ca5e3f4abd8c?w=600&q=80',
    ],
    trending: false, rekomendasi: false, label: '#1 Best Seller',
    spesifikasi: { 'Penulis': 'James Clear', 'Penerbit': 'Gramedia', 'Halaman': '352', 'Bahasa': 'Indonesia', 'ISBN': '9786020651774' }
  },

  // MAKANAN
  {
    id: 18, nama: 'Kopi Arabika Single Origin 500g', kategori: 'makanan', harga: 185000, hargaAsli: 250000,
    stok: 90, rating: 4.8, ulasan: 891, terjual: 2800,
    deskripsi: 'Kopi arabika single origin Toraja, dipanggang medium roast untuk cita rasa seimbang antara keasaman dan kemanisan. Dikemas dalam kantong zipper dengan one-way valve untuk menjaga kesegaran.',
    gambar: 'https://images.unsplash.com/photo-1514432324607-a09d9b4aefdd?w=600&q=80',
    gambarList: [
      'https://images.unsplash.com/photo-1514432324607-a09d9b4aefdd?w=600&q=80',
    ],
    trending: false, rekomendasi: false, label: 'Premium',
    spesifikasi: { 'Asal': 'Toraja, Sulawesi', 'Roast': 'Medium', 'Berat': '500g', 'Penggilingan': 'Whole Bean / Ground', 'Kemasan': 'Ziplock Valve' }
  },
];

// Fungsi helper
function getProdukById(id) {
  return PRODUK.find(p => p.id === parseInt(id));
}

function getProdukByKategori(kategoriId) {
  return PRODUK.filter(p => p.kategori === kategoriId);
}

function getProdukTrending() {
  return PRODUK.filter(p => p.trending);
}

function getProdukRekomendasi() {
  return PRODUK.filter(p => p.rekomendasi);
}

function formatHarga(angka) {
  return 'Rp ' + angka.toLocaleString('id-ID');
}

function hitungDiskon(harga, hargaAsli) {
  return Math.round((1 - harga / hargaAsli) * 100);
}

function renderBintang(rating) {
  const penuh = Math.floor(rating);
  const setengah = rating % 1 >= 0.5;
  let html = '';
  for (let i = 0; i < penuh; i++) html += '<span class="bintang-penuh">★</span>';
  if (setengah) html += '<span class="bintang-setengah">★</span>';
  for (let i = penuh + (setengah ? 1 : 0); i < 5; i++) html += '<span class="bintang-kosong">☆</span>';
  return html;
}
