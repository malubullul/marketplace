// ============================================================
// CHECKOUT.JS — Logic Halaman Checkout
// ============================================================

let metodeBayarDipilih = 'transfer_bank';

document.addEventListener('DOMContentLoaded', () => {
  // Cek keranjang
  const keranjang = getKeranjang();
  if (keranjang.length === 0) {
    window.location.href = 'keranjang.html';
    return;
  }
  renderRingkasanCheckout();
});

// ── Ringkasan Checkout ─────────────────────────────────────
function renderRingkasanCheckout() {
  const keranjang = getKeranjang();
  const subtotal = parseInt(sessionStorage.getItem('checkout_subtotal') || hitungTotalKeranjang());
  const ongkir = parseInt(sessionStorage.getItem('checkout_ongkir') || 0);
  const diskon = parseInt(sessionStorage.getItem('checkout_diskon') || 0);
  const total = parseInt(sessionStorage.getItem('checkout_total') || subtotal);

  // Daftar Item
  const itemsEl = document.getElementById('ringkasan-items');
  if (itemsEl) {
    itemsEl.innerHTML = keranjang.map(item => `
      <div style="display:flex;align-items:center;gap:10px;padding:8px 0;border-bottom:1px solid var(--abu-border)">
        <img src="${item.gambar}" alt="${item.nama}" 
             style="width:48px;height:48px;border-radius:8px;object-fit:cover;flex-shrink:0;background:var(--abu-muda)">
        <div style="flex:1;min-width:0">
          <div style="font-size:13px;font-weight:600;color:var(--teks-hitam);overflow:hidden;white-space:nowrap;text-overflow:ellipsis">${item.nama}</div>
          <div style="font-size:12px;color:var(--abu-teks)">x${item.jumlah}</div>
        </div>
        <div style="font-size:13px;font-weight:700;color:var(--teks-hitam);white-space:nowrap">${formatHarga(item.harga * item.jumlah)}</div>
      </div>
    `).join('');
  }

  document.getElementById('co-subtotal').textContent = formatHarga(subtotal);
  
  const ongkirEl = document.getElementById('co-ongkir');
  if (ongkir === 0) {
    ongkirEl.textContent = 'GRATIS';
    ongkirEl.className = 'gratis';
  } else {
    ongkirEl.textContent = formatHarga(ongkir);
    ongkirEl.className = '';
  }
  
  if (diskon > 0) {
    document.getElementById('co-diskon-row').style.display = 'flex';
    document.getElementById('co-diskon').textContent = `-${formatHarga(diskon)}`;
  }

  document.getElementById('co-total').textContent = formatHarga(total);
}

// ── Pilih Metode Bayar ─────────────────────────────────────
function pilihMetode(el, metode) {
  document.querySelectorAll('.metode-item').forEach(m => m.classList.remove('aktif'));
  el.classList.add('aktif');
  metodeBayarDipilih = metode;
}

// ── Validasi Form ──────────────────────────────────────────
function validasiForm() {
  let valid = true;
  const fields = [
    { id: 'nama-depan', label: 'Nama depan wajib diisi' },
    { id: 'nama-belakang', label: 'Nama belakang wajib diisi' },
    { id: 'email', label: 'Email wajib diisi', type: 'email' },
    { id: 'nohp', label: 'Nomor HP wajib diisi' },
    { id: 'nama-penerima', label: 'Nama penerima wajib diisi' },
    { id: 'alamat', label: 'Alamat wajib diisi' },
    { id: 'provinsi', label: 'Pilih provinsi' },
    { id: 'kota', label: 'Kota wajib diisi' },
    { id: 'kodepos', label: 'Kode pos wajib diisi' },
  ];

  fields.forEach(f => {
    const el = document.getElementById(f.id);
    const errEl = document.getElementById(`err-${f.id}`);
    if (!el) return;
    
    let errMsg = '';
    const val = el.value.trim();
    
    if (!val) {
      errMsg = f.label;
    } else if (f.type === 'email' && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(val)) {
      errMsg = 'Format email tidak valid';
    } else if (f.id === 'kodepos' && !/^\d{5}$/.test(val)) {
      errMsg = 'Kode pos harus 5 digit angka';
    }

    if (errMsg) {
      el.classList.add('error');
      if (errEl) errEl.textContent = errMsg;
      valid = false;
    } else {
      el.classList.remove('error');
      if (errEl) errEl.textContent = '';
    }
  });

  return valid;
}

// ── Proses Checkout ────────────────────────────────────────
function prosesCheckout() {
  if (!validasiForm()) {
    // Scroll ke error pertama
    const firstErr = document.querySelector('.form-input.error, .form-select.error, .form-textarea.error');
    if (firstErr) firstErr.scrollIntoView({ behavior: 'smooth', block: 'center' });
    tampilToast('Lengkapi semua data yang diperlukan!', 'error');
    return;
  }

  const btn = document.getElementById('btn-pesan');
  btn.textContent = '⏳ Memproses Pesanan...';
  btn.disabled = true;
  btn.style.opacity = '0.7';

  // Simulasi proses pembayaran
  setTimeout(() => {
    // Simpan data pesanan
    const nomorPesanan = generateNomorPesanan();
    const keranjang = getKeranjang();
    const total = sessionStorage.getItem('checkout_total') || hitungTotalKeranjang();

    const dataPesanan = {
      nomor: nomorPesanan,
      tanggal: new Date().toLocaleDateString('id-ID', { day: '2-digit', month: 'long', year: 'numeric' }),
      nama: `${document.getElementById('nama-depan').value} ${document.getElementById('nama-belakang').value}`,
      email: document.getElementById('email').value,
      nohp: document.getElementById('nohp').value,
      alamat: document.getElementById('alamat').value,
      kota: document.getElementById('kota').value,
      provinsi: document.getElementById('provinsi').value,
      kodepos: document.getElementById('kodepos').value,
      kurir: document.getElementById('kurir').options[document.getElementById('kurir').selectedIndex].text,
      metode: metodeBayarDipilih,
      total: total,
      items: keranjang,
    };

    sessionStorage.setItem('pesanan_terakhir', JSON.stringify(dataPesanan));
    kosongkanKeranjang();
    window.location.href = 'konfirmasi.html';
  }, 2000);
}

// ── Generate Nomor Pesanan ─────────────────────────────────
function generateNomorPesanan() {
  const prefix = 'PN';
  const timestamp = Date.now().toString().slice(-8);
  const random = Math.floor(Math.random() * 1000).toString().padStart(3, '0');
  return `${prefix}${timestamp}${random}`;
}
