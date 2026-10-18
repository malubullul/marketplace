// ============================================================
// PRODUK.JS — Logic Halaman Daftar Produk
// ============================================================

const PER_HALAMAN = 9;
let halamanSekarang = 1;
let produkFiltered = [];

document.addEventListener('DOMContentLoaded', () => {
  initFilterKategori();
  initURLParams();
  initFilterEvents();
  initSortEvents();
  initSearchPage();
  renderProdukList();
});

// ── URL Params ─────────────────────────────────────────────
function initURLParams() {
  const params = new URLSearchParams(window.location.search);
  const kategori = params.get('kategori');
  const sort = params.get('sort');
  const q = params.get('q');

  if (kategori) {
    const radio = document.querySelector(`input[name="filter-kat"][value="${kategori}"]`);
    if (radio) radio.checked = true;
    const katObj = KATEGORI.find(k => k.id === kategori);
    if (katObj) {
      document.getElementById('page-judul').textContent = katObj.nama;
      document.getElementById('page-sub').textContent = `Temukan produk ${katObj.nama} terbaik`;
      document.getElementById('breadcrumb-aktif').textContent = katObj.nama;
    }
    // aktifkan nav link
    document.querySelectorAll('.nav-link').forEach(a => {
      a.classList.toggle('aktif', a.href.includes(`kategori=${kategori}`));
    });
  } else {
    document.querySelector('input[name="filter-kat"][value=""]').checked = true;
    document.getElementById('nav-semua')?.classList.add('aktif');
  }

  if (sort) {
    const sel = document.getElementById('sort-select');
    const map = { terlaris: 'terlaris', terbaru: 'terbaru', diskon: 'diskon', trending: 'terlaris' };
    if (map[sort] && sel) sel.value = map[sort];
  }

  if (q) {
    const input = document.getElementById('search-input');
    if (input) input.value = q;
    document.getElementById('page-judul').textContent = `Hasil: "${q}"`;
    document.getElementById('page-sub').textContent = 'Pencarian produk';
    document.getElementById('breadcrumb-aktif').textContent = `Pencarian`;
  }
}

// ── Filter Kategori Radio ──────────────────────────────────
function initFilterKategori() {
  const container = document.getElementById('filter-kategori-list');
  if (!container) return;
  
  const extraRadios = KATEGORI.map(k => `
    <label class="filter-checkbox-item">
      <input type="radio" name="filter-kat" value="${k.id}"> ${k.nama}
    </label>
  `).join('');
  
  container.innerHTML = `
    <label class="filter-checkbox-item">
      <input type="radio" name="filter-kat" value="" checked> Semua Kategori
    </label>
    ${extraRadios}
  `;
}

// ── Filter & Sort Events ───────────────────────────────────
function initFilterEvents() {
  document.querySelectorAll('input[name="filter-kat"]').forEach(r =>
    r.addEventListener('change', () => { halamanSekarang = 1; renderProdukList(); })
  );
  document.querySelectorAll('input[name="filter-rating"]').forEach(r =>
    r.addEventListener('change', () => { halamanSekarang = 1; renderProdukList(); })
  );
  const rangeHarga = document.getElementById('filter-harga-max');
  const labelHarga = document.getElementById('filter-harga-max-label');
  if (rangeHarga) {
    rangeHarga.addEventListener('input', () => {
      labelHarga.textContent = formatHarga(parseInt(rangeHarga.value));
      halamanSekarang = 1;
      renderProdukList();
    });
  }
  const stokCheck = document.getElementById('filter-stok');
  if (stokCheck) stokCheck.addEventListener('change', () => { halamanSekarang = 1; renderProdukList(); });

  document.getElementById('btn-reset')?.addEventListener('click', resetFilter);
}

function initSortEvents() {
  document.getElementById('sort-select')?.addEventListener('change', () => { halamanSekarang = 1; renderProdukList(); });
}

function initSearchPage() {
  const input = document.getElementById('search-input');
  const btn = document.getElementById('search-btn');
  if (!input) return;
  function doSearch() {
    const q = input.value.trim();
    const url = new URL(window.location.href);
    if (q) { url.searchParams.set('q', q); url.searchParams.delete('kategori'); }
    else { url.searchParams.delete('q'); }
    window.history.replaceState({}, '', url);
    document.getElementById('page-judul').textContent = q ? `Hasil: "${q}"` : 'Semua Produk';
    halamanSekarang = 1;
    renderProdukList();
  }
  btn?.addEventListener('click', doSearch);
  input.addEventListener('keypress', e => { if (e.key === 'Enter') doSearch(); });
}

function resetFilter() {
  document.querySelector('input[name="filter-kat"][value=""]').checked = true;
  document.querySelector('input[name="filter-rating"][value="0"]').checked = true;
  const range = document.getElementById('filter-harga-max');
  if (range) { range.value = 15000000; document.getElementById('filter-harga-max-label').textContent = 'Rp15.000.000'; }
  const stok = document.getElementById('filter-stok');
  if (stok) stok.checked = false;
  document.getElementById('sort-select').value = 'default';
  halamanSekarang = 1;
  renderProdukList();
}

// ── Render Produk List ─────────────────────────────────────
function renderProdukList() {
  const params = new URLSearchParams(window.location.search);
  const q = params.get('q') || document.getElementById('search-input')?.value?.trim() || '';
  const filterKat = document.querySelector('input[name="filter-kat"]:checked')?.value || '';
  const filterRating = parseFloat(document.querySelector('input[name="filter-rating"]:checked')?.value || 0);
  const filterHargaMax = parseInt(document.getElementById('filter-harga-max')?.value || 15000000);
  const filterStok = document.getElementById('filter-stok')?.checked || false;
  const sort = document.getElementById('sort-select')?.value || 'default';

  // Filter
  let hasil = PRODUK.filter(p => {
    if (filterKat && p.kategori !== filterKat) return false;
    if (q && !p.nama.toLowerCase().includes(q.toLowerCase()) && !p.deskripsi.toLowerCase().includes(q.toLowerCase())) return false;
    if (p.harga > filterHargaMax) return false;
    if (p.rating < filterRating) return false;
    if (filterStok && p.stok === 0) return false;
    return true;
  });

  // Sort
  switch (sort) {
    case 'terlaris': hasil.sort((a, b) => b.terjual - a.terjual); break;
    case 'terbaru': hasil.sort((a, b) => b.id - a.id); break;
    case 'harga-asc': hasil.sort((a, b) => a.harga - b.harga); break;
    case 'harga-desc': hasil.sort((a, b) => b.harga - a.harga); break;
    case 'rating': hasil.sort((a, b) => b.rating - a.rating); break;
    case 'diskon': hasil.sort((a, b) => hitungDiskon(b.harga, b.hargaAsli) - hitungDiskon(a.harga, a.hargaAsli)); break;
    default: break;
  }

  produkFiltered = hasil;
  document.getElementById('count-produk').textContent = hasil.length;

  // Paginasi
  const totalHalaman = Math.ceil(hasil.length / PER_HALAMAN);
  const mulai = (halamanSekarang - 1) * PER_HALAMAN;
  const halaman = hasil.slice(mulai, mulai + PER_HALAMAN);

  const grid = document.getElementById('grid-produk-list');
  const empty = document.getElementById('empty-state');

  if (halaman.length === 0) {
    grid.innerHTML = '';
    empty.style.display = 'block';
  } else {
    empty.style.display = 'none';
    grid.innerHTML = halaman.map((p, i) => renderKartuProduk(p, i)).join('');
    updateIkonWishlist();
  }

  renderPaginasi(totalHalaman);
  
  // Scroll ke atas grid
  grid.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

// ── Paginasi ───────────────────────────────────────────────
function renderPaginasi(total) {
  const el = document.getElementById('paginasi');
  if (!el || total <= 1) { el.innerHTML = ''; return; }

  let html = '';
  html += `<button class="paginasi-btn" onclick="gantiHalaman(${halamanSekarang - 1})" ${halamanSekarang === 1 ? 'disabled' : ''}>‹</button>`;
  
  for (let i = 1; i <= total; i++) {
    if (i === 1 || i === total || Math.abs(i - halamanSekarang) <= 1) {
      html += `<button class="paginasi-btn ${i === halamanSekarang ? 'aktif' : ''}" onclick="gantiHalaman(${i})">${i}</button>`;
    } else if (Math.abs(i - halamanSekarang) === 2) {
      html += `<span class="paginasi-btn" style="cursor:default;pointer-events:none">…</span>`;
    }
  }
  
  html += `<button class="paginasi-btn" onclick="gantiHalaman(${halamanSekarang + 1})" ${halamanSekarang === total ? 'disabled' : ''}>›</button>`;
  el.innerHTML = html;
}

function gantiHalaman(hal) {
  halamanSekarang = hal;
  renderProdukList();
}
