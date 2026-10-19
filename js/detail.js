// ============================================================
// DETAIL.JS — Logic Halaman Detail Produk
// ============================================================

let produkAktif = null;
let jumlahDipilih = 1;
let tabAktif = "deskripsi";

document.addEventListener("DOMContentLoaded", () => {
  const params = new URLSearchParams(window.location.search);
  const id = params.get("id");

  if (!id) {
    window.location.href = "produk.html";
    return;
  }

  produkAktif = getProdukById(id);
  if (!produkAktif) {
    window.location.href = "produk.html";
    return;
  }

  renderDetail(produkAktif);
  renderProdukSerupa(produkAktif);
  initSearch();
});

// ── Render Detail ──────────────────────────────────────────
function renderDetail(p) {
  document.title = `${p.nama} — Anredseller`;
  document.querySelector('meta[name="description"]').content =
    p.deskripsi.slice(0, 160);

  // Breadcrumb
  const katObj = KATEGORI.find((k) => k.id === p.kategori);
  document.getElementById("bc-kategori").textContent = katObj?.nama || "Produk";
  document.getElementById("bc-kategori").href =
    `produk.html?kategori=${p.kategori}`;
  document.getElementById("bc-nama").textContent = p.nama;

  const diskon = hitungDiskon(p.harga, p.hargaAsli);
  const hemat = p.hargaAsli - p.harga;

  // Stok
  const stokHtml =
    p.stok === 0
      ? `<span class="stok-indikator stok-habis"></span><span style="color:var(--merah)">Stok Habis</span>`
      : p.stok < 10
        ? `<span class="stok-indikator stok-menipis"></span><span style="color:var(--bintang)">Tersisa ${p.stok} item</span>`
        : `<span class="stok-indikator stok-ada"></span><span style="color:var(--hijau)">Stok Tersedia (${p.stok})</span>`;

  // Galeri thumbs
  const thumbsHtml = p.gambarList
    .map(
      (img, i) => `
    <div class="galeri-thumb-item ${i === 0 ? "aktif" : ""}" onclick="gantiGambar('${img}', this)">
      <img src="${img}" alt="${p.nama} ${i + 1}" loading="lazy">
    </div>
  `,
    )
    .join("");

  // Spesifikasi
  const spekHtml = Object.entries(p.spesifikasi || {})
    .map(
      ([k, v]) => `
    <tr><td>${k}</td><td>${v}</td></tr>
  `,
    )
    .join("");

  // Ulasan sample
  const ulasanSample = generateUlasanSample(p);

  const wrapper = document.getElementById("detail-wrapper");
  wrapper.innerHTML = `
    <!-- GALERI -->
    <div class="detail-galeri fade-in">
      <div class="galeri-utama">
        <img src="${p.gambarList[0]}" alt="${p.nama}" id="gambar-utama">
      </div>
      ${p.gambarList.length > 1 ? `<div class="galeri-thumb">${thumbsHtml}</div>` : ""}
    </div>

    <!-- INFO -->
    <div class="detail-info fade-in-up">
      <div class="detail-badge-kategori">${katObj?.icon || ""} ${katObj?.nama || ""}</div>
      <h1 class="detail-nama">${p.nama}</h1>
      
      <div class="detail-meta">
        <div class="detail-rating">
          ${renderBintang(p.rating)}
          <span style="font-size:13px;font-weight:600;color:var(--teks-hitam)">${p.rating}</span>
        </div>
        <span style="font-size:13px;color:var(--abu-teks)">(${p.ulasan.toLocaleString("id-ID")} ulasan)</span>
        <span class="detail-teks">•</span>
        <span class="detail-terjual" style="font-size:13px;color:var(--abu-teks)">${p.terjual.toLocaleString("id-ID")} terjual</span>
      </div>

      <div class="detail-stok" style="margin-bottom:16px; font-size:13px">
        ${stokHtml}
      </div>

      <!-- HARGA -->
      <div class="detail-harga-box">
        <div class="detail-harga-sekarang">${formatHarga(p.harga)}</div>
        <div class="detail-harga-asli">
          <span>${formatHarga(p.hargaAsli)}</span>
          <div class="detail-harga-badge">Hemat ${diskon}%</div>
        </div>
        <div class="detail-hemat">💰 Kamu hemat ${formatHarga(hemat)}</div>
      </div>

      <div class="detail-divider"></div>

      <!-- JUMLAH -->
      <div class="detail-label">Jumlah:</div>
      <div class="detail-qty">
        <button class="qty-btn" id="qty-kurang" onclick="ubahJumlah(-1)" ${p.stok === 0 ? "disabled" : ""}>−</button>
        <input type="number" class="qty-input" id="qty-input" value="${jumlahDipilih}" min="1" max="${p.stok}" 
               onchange="setJumlah(parseInt(this.value))" ${p.stok === 0 ? "disabled" : ""}>
        <button class="qty-btn" id="qty-tambah" onclick="ubahJumlah(1)" ${p.stok === 0 ? "disabled" : ""}>+</button>
      </div>

      <!-- AKSI -->
      <div class="detail-aksi">
        <button class="btn-beli-sekarang" id="btn-beli" onclick="beliSekarang()" ${p.stok === 0 ? 'disabled style="opacity:0.4;pointer-events:none"' : ""}>
          ⚡ Beli Sekarang
        </button>
        <button class="btn-tambah-keranjang-detail" id="btn-tambah" onclick="tambahKeranjang()" ${p.stok === 0 ? 'disabled style="opacity:0.4;pointer-events:none"' : ""}>
          🛒 Keranjang
        </button>
      </div>

      ${p.stok === 0 ? '<div style="text-align:center;color:var(--merah);font-size:13px;font-weight:600;margin-bottom:16px">⚠️ Maaf, produk ini sedang tidak tersedia</div>' : ""}

      <!-- JAMINAN -->
      <div class="detail-jaminan">
        <div class="jaminan-item"><span class="ji">🔒</span> Pembayaran Aman</div>
        <div class="jaminan-item"><span class="ji">↩️</span> Garansi 30 Hari</div>
        <div class="jaminan-item"><span class="ji">🚚</span> Gratis Ongkir</div>
      </div>

      <div class="detail-divider"></div>

      <!-- TABS -->
      <div class="tabs-detail">
        <div class="tabs-header">
          <button class="tab-btn aktif" onclick="gantiTab('deskripsi', this)">Deskripsi</button>
          <button class="tab-btn" onclick="gantiTab('spesifikasi', this)">Spesifikasi</button>
          <button class="tab-btn" onclick="gantiTab('ulasan', this)">Ulasan (${p.ulasan.toLocaleString("id-ID")})</button>
        </div>

        <!-- Tab Deskripsi -->
        <div class="tab-konten aktif" id="tab-deskripsi">
          <p class="tab-deskripsi">${p.deskripsi}</p>
        </div>

        <!-- Tab Spesifikasi -->
        <div class="tab-konten" id="tab-spesifikasi">
          ${spekHtml ? `<table class="tabel-spek">${spekHtml}</table>` : '<p style="color:var(--abu-teks);font-size:14px">Spesifikasi tidak tersedia.</p>'}
        </div>

        <!-- Tab Ulasan -->
        <div class="tab-konten" id="tab-ulasan">
          ${ulasanSample}
        </div>
      </div>
    </div>
  `;
}

// ── Galeri ─────────────────────────────────────────────────
function gantiGambar(src, el) {
  document.getElementById("gambar-utama").src = src;
  document
    .querySelectorAll(".galeri-thumb-item")
    .forEach((t) => t.classList.remove("aktif"));
  el.classList.add("aktif");
}

// ── Jumlah ─────────────────────────────────────────────────
function ubahJumlah(delta) {
  setJumlah(jumlahDipilih + delta);
}
function setJumlah(val) {
  if (!produkAktif) return;
  jumlahDipilih = Math.max(1, Math.min(val, produkAktif.stok));
  document.getElementById("qty-input").value = jumlahDipilih;
}

// ── Aksi ───────────────────────────────────────────────────
function tambahKeranjang() {
  if (!produkAktif || produkAktif.stok === 0) return;
  tambahKeKeranjang(produkAktif.id, jumlahDipilih);
}
function beliSekarang() {
  if (!produkAktif || produkAktif.stok === 0) return;
  tambahKeKeranjang(produkAktif.id, jumlahDipilih);
  setTimeout(() => {
    window.location.href = "keranjang.html";
  }, 600);
}

// ── Tab ────────────────────────────────────────────────────
function gantiTab(nama, btn) {
  document
    .querySelectorAll(".tab-btn")
    .forEach((b) => b.classList.remove("aktif"));
  document
    .querySelectorAll(".tab-konten")
    .forEach((c) => c.classList.remove("aktif"));
  btn.classList.add("aktif");
  document.getElementById(`tab-${nama}`)?.classList.add("aktif");
}

// ── Produk Serupa ──────────────────────────────────────────
function renderProdukSerupa(p) {
  const el = document.getElementById("grid-serupa");
  if (!el) return;
  const serupa = PRODUK.filter(
    (x) => x.kategori === p.kategori && x.id !== p.id,
  ).slice(0, 5);
  if (serupa.length === 0) {
    el.innerHTML =
      '<p style="color:var(--abu-teks);font-size:14px">Belum ada produk serupa.</p>';
    return;
  }
  el.innerHTML = serupa.map((x, i) => renderKartuProduk(x, i)).join("");
  updateIkonWishlist();
}

// ── Generate Ulasan Sample ────────────────────────────────
function generateUlasanSample(p) {
  const nama = ["Budi S.", "Siti R.", "Andi P.", "Dewi K.", "Fajar M."];
  const komentar = [
    "Produk sangat bagus, sesuai deskripsi! Packaging aman, pengiriman cepat.",
    "Kualitasnya memuaskan, harga juga sepadan. Recommended!",
    "Sudah beli 2 kali, tidak mengecewakan. Seller terpercaya.",
    "Barang original, persis seperti foto. Sangat puas dengan pembelian ini.",
    "Pengiriman cepat, barang rapih dikemas. Pasti beli lagi.",
  ];
  const tanggal = [
    "18 Okt 2024",
    "15 Okt 2024",
    "10 Okt 2024",
    "5 Okt 2024",
    "1 Okt 2024",
  ];
  const ratings = [5, 5, 4, 5, 4];

  const distribusi = { 5: 60, 4: 25, 3: 10, 2: 3, 1: 2 };

  let html = `
    <div class="ulasan-ringkasan">
      <div>
        <div class="ulasan-angka-besar">${p.rating}</div>
        <div class="ulasan-bintang-besar" style="color:var(--bintang)">${renderBintang(p.rating)}</div>
        <div class="ulasan-total-teks">${p.ulasan.toLocaleString("id-ID")} ulasan</div>
      </div>
      <div class="ulasan-bar">
        ${[5, 4, 3, 2, 1]
          .map(
            (n) => `
          <div class="ulasan-bar-row">
            <span class="ulasan-bar-label">${n}</span>
            <div class="ulasan-bar-track">
              <div class="ulasan-bar-fill" style="width:${distribusi[n]}%"></div>
            </div>
            <span class="ulasan-bar-persen">${distribusi[n]}%</span>
          </div>
        `,
          )
          .join("")}
      </div>
    </div>
  `;

  for (let i = 0; i < 5; i++) {
    html += `
      <div class="ulasan-item">
        <div class="ulasan-header">
          <div class="ulasan-avatar">${nama[i][0]}</div>
          <div>
            <div class="ulasan-nama">${nama[i]}</div>
            <div style="color:var(--bintang);font-size:13px">${"★".repeat(ratings[i])}${"☆".repeat(5 - ratings[i])}</div>
          </div>
          <div class="ulasan-tanggal">${tanggal[i]}</div>
        </div>
        <div class="ulasan-teks">${komentar[i]}</div>
      </div>
    `;
  }

  return html;
}

// ── Search ─────────────────────────────────────────────────
function initSearch() {
  const input = document.getElementById("search-input");
  const btn = document.getElementById("search-btn");
  if (!input) return;
  function doSearch() {
    const q = input.value.trim();
    if (q) window.location.href = `produk.html?q=${encodeURIComponent(q)}`;
  }
  btn?.addEventListener("click", doSearch);
  input.addEventListener("keypress", (e) => {
    if (e.key === "Enter") doSearch();
  });
}
