// ============================================================
// KERANJANG.JS — Logic Halaman Keranjang
// ============================================================

const KUPON_VALID = {
  'HEMAT10': 0.10,  // 10% off
  'NUSANTARA15': 0.15, // 15% off
  'SALE20': 0.20,  // 20% off
};

let diskonKupon = 0;

document.addEventListener('DOMContentLoaded', () => {
  renderKeranjang();
  renderProdukSuka();
  initKupon();
  initSearch();
});

// ── Render Keranjang ───────────────────────────────────────
function renderKeranjang() {
  const kiri = document.getElementById('keranjang-kiri');
  const keranjang = getKeranjang();
  const jumlah = hitungJumlahItem();

  document.getElementById('subtitle-keranjang').textContent =
    jumlah > 0 ? `${jumlah} produk dalam keranjang` : 'Keranjang kamu masih kosong';

  if (keranjang.length === 0) {
    kiri.innerHTML = `
      <div class="keranjang-kosong">
        <div class="keranjang-kosong-ikon">🛒</div>
        <div class="keranjang-kosong-judul">Keranjang Kamu Kosong</div>
        <div class="keranjang-kosong-sub">Yuk, temukan produk favorit kamu dan tambahkan ke keranjang!</div>
        <a href="produk.html" class="btn-beli-sekarang" style="display:inline-flex;margin:0 auto">
          🛍️ Mulai Belanja
        </a>
      </div>
    `;
    document.getElementById('btn-checkout').disabled = true;
    updateRingkasan();
    return;
  }

  const headerHtml = `
    <div class="keranjang-header-col">
      <span></span>
      <span>Produk</span>
      <span>Harga Satuan</span>
      <span>Jumlah</span>
      <span>Subtotal</span>
      <span></span>
    </div>
  `;

  const itemsHtml = keranjang.map(item => `
    <div class="keranjang-item" id="item-${item.id}">
      <!-- Gambar -->
      <a href="detail.html?id=${item.id}">
        <div class="keranjang-gambar">
          <img src="${item.gambar}" alt="${item.nama}" loading="lazy">
        </div>
      </a>
      <!-- Nama -->
      <div>
        <a href="detail.html?id=${item.id}" class="keranjang-nama">${item.nama}</a>
        <div style="font-size:11px;color:var(--abu-teks);margin-top:4px">Stok: ${item.stok}</div>
      </div>
      <!-- Harga Satuan -->
      <div class="keranjang-harga">${formatHarga(item.harga)}</div>
      <!-- Jumlah -->
      <div class="keranjang-qty">
        <button onclick="kurangiItem(${item.id})">−</button>
        <span class="keranjang-qty-angka" id="qty-${item.id}">${item.jumlah}</span>
        <button onclick="tambahItem(${item.id})">+</button>
      </div>
      <!-- Subtotal -->
      <div class="keranjang-subtotal" id="subtotal-${item.id}">${formatHarga(item.harga * item.jumlah)}</div>
      <!-- Hapus -->
      <button class="btn-hapus-item" onclick="hapusItem(${item.id})" title="Hapus">✕</button>
    </div>
  `).join('');

  kiri.innerHTML = `
    ${headerHtml}
    ${itemsHtml}
    <div style="display:flex;justify-content:space-between;align-items:center;padding:16px;background:var(--abu-muda);border-radius:var(--radius-lg);margin-top:8px">
      <button onclick="konfirmasiKosongkan()" style="font-size:13px;color:var(--merah);font-weight:600;text-decoration:underline;background:none;border:none;cursor:pointer">
        🗑️ Kosongkan Keranjang
      </button>
      <a href="produk.html" style="font-size:13px;font-weight:600;color:var(--teks-hitam);display:flex;align-items:center;gap:4px">
        ← Lanjut Belanja
      </a>
    </div>
  `;

  document.getElementById('btn-checkout').disabled = false;
  updateRingkasan();
}

// ── Update Item ────────────────────────────────────────────
function kurangiItem(id) {
  const keranjang = getKeranjang();
  const item = keranjang.find(i => i.id === id);
  if (!item) return;
  if (item.jumlah <= 1) {
    if (confirm(`Hapus "${item.nama}" dari keranjang?`)) {
      hapusItem(id);
    }
    return;
  }
  updateJumlah(id, item.jumlah - 1);
  document.getElementById(`qty-${id}`).textContent = item.jumlah - 1;
  document.getElementById(`subtotal-${id}`).textContent = formatHarga(item.harga * (item.jumlah - 1));
  updateRingkasan();
}

function tambahItem(id) {
  const keranjang = getKeranjang();
  const item = keranjang.find(i => i.id === id);
  if (!item) return;
  if (item.jumlah >= item.stok) {
    tampilToast(`Stok hanya ${item.stok}!`, 'warning');
    return;
  }
  updateJumlah(id, item.jumlah + 1);
  document.getElementById(`qty-${id}`).textContent = item.jumlah + 1;
  document.getElementById(`subtotal-${id}`).textContent = formatHarga(item.harga * (item.jumlah + 1));
  updateRingkasan();
}

function hapusItem(id) {
  hapusDariKeranjang(id);
  renderKeranjang();
}

function konfirmasiKosongkan() {
  if (confirm('Yakin ingin mengosongkan semua keranjang?')) {
    kosongkanKeranjang();
    renderKeranjang();
  }
}

// ── Update Ringkasan ───────────────────────────────────────
function updateRingkasan() {
  const subtotal = hitungTotalKeranjang();
  const jumlah = hitungJumlahItem();
  const diskon = Math.round(subtotal * diskonKupon);
  const ongkir = subtotal >= 200000 ? 0 : 15000;
  const total = subtotal - diskon + ongkir;

  document.getElementById('jumlah-item-ringkasan').textContent = jumlah;
  document.getElementById('subtotal-ringkasan').textContent = formatHarga(subtotal);
  
  const ongkirEl = document.getElementById('ongkir-ringkasan');
  if (ongkir === 0) {
    ongkirEl.textContent = 'GRATIS';
    ongkirEl.className = 'gratis';
  } else {
    ongkirEl.textContent = formatHarga(ongkir);
    ongkirEl.className = '';
  }

  if (diskon > 0) {
    document.getElementById('baris-diskon-kupon').style.display = 'flex';
    document.getElementById('diskon-kupon-val').textContent = `-${formatHarga(diskon)}`;
  } else {
    document.getElementById('baris-diskon-kupon').style.display = 'none';
  }

  document.getElementById('total-ringkasan').textContent = formatHarga(total);

  // Simpan ke sessionStorage untuk checkout
  sessionStorage.setItem('checkout_subtotal', subtotal);
  sessionStorage.setItem('checkout_ongkir', ongkir);
  sessionStorage.setItem('checkout_diskon', diskon);
  sessionStorage.setItem('checkout_total', total);
}

// ── Kupon ──────────────────────────────────────────────────
function initKupon() {
  document.getElementById('btn-kupon')?.addEventListener('click', () => {
    const kode = document.getElementById('kupon-input').value.trim().toUpperCase();
    const pesanEl = document.getElementById('kupon-pesan');

    if (!kode) {
      pesanEl.textContent = '⚠️ Masukkan kode kupon terlebih dahulu.';
      pesanEl.style.color = 'var(--bintang)';
      return;
    }

    if (KUPON_VALID[kode]) {
      diskonKupon = KUPON_VALID[kode];
      const persen = Math.round(diskonKupon * 100);
      pesanEl.textContent = `✅ Kupon "${kode}" berhasil! Diskon ${persen}% diterapkan.`;
      pesanEl.style.color = 'var(--hijau)';
      updateRingkasan();
    } else {
      diskonKupon = 0;
      pesanEl.textContent = `❌ Kode kupon "${kode}" tidak valid atau sudah kadaluwarsa.`;
      pesanEl.style.color = 'var(--merah)';
      updateRingkasan();
    }
  });

  document.getElementById('kupon-input')?.addEventListener('keypress', e => {
    if (e.key === 'Enter') document.getElementById('btn-kupon')?.click();
  });
}

// ── Produk Suka ────────────────────────────────────────────
function renderProdukSuka() {
  const el = document.getElementById('grid-suka');
  if (!el) return;
  const produk = PRODUK.filter(p => p.trending || p.rekomendasi).slice(0, 5);
  el.innerHTML = produk.map((p, i) => renderKartuProduk(p, i)).join('');
  updateIkonWishlist();
}

// ── Search ─────────────────────────────────────────────────
function initSearch() {
  const input = document.getElementById('search-input');
  const btn = document.getElementById('search-btn');
  if (!input) return;
  function doSearch() {
    const q = input.value.trim();
    if (q) window.location.href = `produk.html?q=${encodeURIComponent(q)}`;
  }
  btn?.addEventListener('click', doSearch);
  input.addEventListener('keypress', e => { if (e.key === 'Enter') doSearch(); });
}
