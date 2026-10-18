// ============================================================
// APP.JS — Logic Halaman Beranda
// ============================================================

document.addEventListener('DOMContentLoaded', () => {
  renderKategori();
  renderTrending();
  renderRekomendasi();
  initSearch();
  initNewsletter();
});

// ── Render Kategori ────────────────────────────────────────
function renderKategori() {
  const el = document.getElementById('grid-kategori');
  if (!el) return;
  el.innerHTML = KATEGORI.map(k => `
    <div class="kartu-kategori fade-in-up" onclick="window.location='produk.html?kategori=${k.id}'" style="cursor:pointer">
      <div class="kategori-ikon">
        <span style="font-size:28px">${k.icon}</span>
      </div>
      <div class="kategori-nama">${k.nama}</div>
    </div>
  `).join('');
}

// ── Render Trending ────────────────────────────────────────
function renderTrending() {
  const el = document.getElementById('grid-trending');
  if (!el) return;
  const produk = getProdukTrending();
  el.innerHTML = produk.map((p, i) => renderKartuProduk(p, i)).join('');
  attachProdukEvents(el);
}

// ── Render Rekomendasi ─────────────────────────────────────
function renderRekomendasi() {
  const el = document.getElementById('grid-rekomendasi');
  if (!el) return;
  const produk = getProdukRekomendasi();
  el.innerHTML = produk.map((p, i) => renderKartuProduk(p, i)).join('');
  attachProdukEvents(el);
}

// ── Render Kartu Produk ────────────────────────────────────
function renderKartuProduk(p, delay = 0) {
  const diskon = hitungDiskon(p.harga, p.hargaAsli);
  const stokHtml = p.stok === 0
    ? '<span class="badge-stok-habis">● Stok Habis</span>'
    : p.stok < 10
    ? `<span class="badge-stok-menipis">● Tersisa ${p.stok}</span>`
    : '';

  const labelHtml = p.label
    ? `<div class="kartu-label ${p.label === 'Stok Terbatas' || p.label === 'Stok Habis' ? 'merah' : ''}">${p.label}</div>`
    : '';

  return `
    <div class="kartu-produk fade-in-up" 
         style="animation-delay:${delay * 0.08}s"
         onclick="window.location='detail.html?id=${p.id}'"
         data-produk-id="${p.id}">
      <div class="kartu-produk-gambar">
        <img src="${p.gambar}" alt="${p.nama}" loading="lazy">
        ${labelHtml}
        <button class="btn-wishlist ${isInWishlist(p.id) ? 'aktif' : ''}" 
                data-wishlist="${p.id}"
                onclick="event.stopPropagation(); toggleWishlist(${p.id})">
          ${isInWishlist(p.id) ? '♥' : '♡'}
        </button>
        ${p.stok > 0 ? `
        <button class="btn-keranjang-cepat" onclick="event.stopPropagation(); tambahKeKeranjang(${p.id}, 1)">
          🛒 Tambah ke Keranjang
        </button>` : ''}
      </div>
      <div class="kartu-produk-info">
        <div class="kartu-produk-kategori">${KATEGORI.find(k => k.id === p.kategori)?.nama || ''}</div>
        <div class="kartu-produk-nama">${p.nama}</div>
        <div class="kartu-rating">
          ${renderBintang(p.rating)}
          <span class="rating-angka">${p.rating}</span>
          <span class="rating-ulasan">(${p.ulasan.toLocaleString('id-ID')})</span>
        </div>
        ${stokHtml}
        <div class="kartu-harga" style="margin-top:${stokHtml ? '6px' : '0'}">
          <span class="harga-sekarang">${formatHarga(p.harga)}</span>
          <span class="harga-asli">${formatHarga(p.hargaAsli)}</span>
          <span class="persen-diskon">-${diskon}%</span>
        </div>
      </div>
    </div>
  `;
}

// ── Attach Events ──────────────────────────────────────────
function attachProdukEvents(container) {
  // Events sudah ditangani inline di HTML
  updateIkonWishlist();
}

// ── Search ─────────────────────────────────────────────────
function initSearch() {
  const input = document.getElementById('search-input');
  const btn = document.getElementById('search-btn');
  if (!input) return;

  function doSearch() {
    const q = input.value.trim();
    if (q) {
      window.location.href = `produk.html?q=${encodeURIComponent(q)}`;
    }
  }

  btn?.addEventListener('click', doSearch);
  input.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') doSearch();
  });
}

// ── Newsletter ─────────────────────────────────────────────
function initNewsletter() {
  const form = document.getElementById('newsletter-form');
  if (!form) return;
  form.addEventListener('submit', (e) => {
    e.preventDefault();
    const email = form.querySelector('input').value;
    if (email) {
      tampilToast(`✉️ Terima kasih! ${email} telah didaftarkan.`, 'success');
      form.reset();
    }
  });
}
