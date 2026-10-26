// ============================================================
// DETAIL.JS — Logic Halaman Detail Produk
// ============================================================

let produkAktif = null;
let jumlahDipilih = 1;
let tabAktif = "deskripsi";

document.addEventListener("DOMContentLoaded", async () => {
  await katalogSiap;
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
  await initProductReviews(produkAktif);
  if (location.hash === "#ulasan") {
    gantiTab("ulasan", document.getElementById("reviews-tab"));
    document.getElementById("reviews-tab").scrollIntoView({ block: "start" });
  }
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

  // Spesifikasi
  const spekHtml = Object.entries(p.spesifikasi || {})
    .map(
      ([k, v]) => `
    <tr><td>${h(k)}</td><td>${h(v)}</td></tr>
  `,
    )
    .join("");

  const wrapper = document.getElementById("detail-wrapper");
  wrapper.innerHTML = `
    <!-- GALERI -->
    <div class="detail-galeri fade-in">
      ${renderProductGallery(p, true)}
    </div>

    <!-- INFO -->
    <div class="detail-info fade-in-up">
      <div class="detail-badge-kategori">${katObj?.icon || ""} ${katObj?.nama || ""}</div>
      <h1 class="detail-nama">${h(p.nama)}</h1>
      
      <div class="detail-meta" id="product-review-metrics">
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

      <div class="product-options">
        ${p.ukuran?.length ? `<label for="pilihan-ukuran">Ukuran<select id="pilihan-ukuran" required><option value="">Pilih ukuran</option>${p.ukuran.map((value) => `<option value="${h(value)}">${h(value)}</option>`).join("")}</select></label>` : ""}
        ${p.warna?.length ? `<label for="pilihan-warna">Warna<select id="pilihan-warna" required><option value="">Pilih warna</option>${p.warna.map((value) => `<option value="${h(value)}">${h(value)}</option>`).join("")}</select></label>` : ""}
      </div>
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
           Beli Sekarang
        </button>
        <button class="btn-tambah-keranjang-detail" id="btn-tambah" onclick="tambahKeranjang()" ${p.stok === 0 ? 'disabled style="opacity:0.4;pointer-events:none"' : ""}>
           Keranjang
        </button>
      </div>

      ${p.stok === 0 ? '<div style="text-align:center;color:var(--merah);font-size:13px;font-weight:600;margin-bottom:16px">⚠️ Maaf, produk ini sedang tidak tersedia</div>' : ""}

      <!-- JAMINAN -->
      <div class="detail-jaminan">
        <div class="jaminan-item"><span class="ji"></span> Pesan langsung di website</div>
        <div class="jaminan-item"><span class="ji">↩️</span> Tanya CS sebelum memesan</div>
        <div class="jaminan-item"><span class="ji"></span> Pembayaran lewat WhatsApp</div>
      </div>

      <div class="detail-divider"></div>

      <!-- TABS -->
      <div class="tabs-detail">
        <div class="tabs-header">
          <button class="tab-btn aktif" onclick="gantiTab('deskripsi', this)">Deskripsi</button>
          <button class="tab-btn" onclick="gantiTab('spesifikasi', this)">Spesifikasi</button>
          <button class="tab-btn" id="reviews-tab" onclick="gantiTab('ulasan', this)">Ulasan (${p.ulasan.toLocaleString("id-ID")})</button>
        </div>

        <!-- Tab Deskripsi -->
        <div class="tab-konten aktif" id="tab-deskripsi">
          <p class="tab-deskripsi">${h(p.deskripsi)}</p>
        </div>

        <!-- Tab Spesifikasi -->
        <div class="tab-konten" id="tab-spesifikasi">
          ${spekHtml ? `<table class="tabel-spek">${spekHtml}</table>` : '<p style="color:var(--abu-teks);font-size:14px">Spesifikasi tidak tersedia.</p>'}
        </div>

        <!-- Tab Ulasan -->
        <div class="tab-konten" id="tab-ulasan">
          <p role="status">Memuat ulasan pembeli…</p>
        </div>
      </div>
    </div>
  `;
}

// ── Jumlah ─────────────────────────────────────────────────
function ubahJumlah(delta) {
  setJumlah(jumlahDipilih + delta);
}
function setJumlah(val) {
  if (!produkAktif) return;
  jumlahDipilih = Math.max(
    1,
    Math.min(Number.isFinite(val) ? val : 1, produkAktif.stok),
  );
  document.getElementById("qty-input").value = jumlahDipilih;
}

// ── Aksi ───────────────────────────────────────────────────
async function tambahKeranjang() {
  if (!produkAktif || produkAktif.stok === 0) return;
  return tambahKeKeranjang(
    produkAktif.id,
    jumlahDipilih,
    document.getElementById("pilihan-ukuran")?.value || "",
    document.getElementById("pilihan-warna")?.value || "",
  );
}
async function beliSekarang() {
  if (!produkAktif || produkAktif.stok === 0) return;
  if (!(await tambahKeranjang())) return;
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
