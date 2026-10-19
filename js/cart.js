// ============================================================
// CART.JS — Manajemen Keranjang Belanja (localStorage)
// ============================================================

const CART_KEY = "pasar_nusantara_cart";
const WISHLIST_KEY = "pasar_nusantara_wishlist";

// ── KERANJANG ──────────────────────────────────────────────

function getKeranjang() {
  try {
    return JSON.parse(localStorage.getItem(CART_KEY)) || [];
  } catch {
    return [];
  }
}

function simpanKeranjang(keranjang) {
  localStorage.setItem(CART_KEY, JSON.stringify(keranjang));
  updateBadgeKeranjang();
}

function tambahKeKeranjang(produkId, jumlah = 1) {
  const produk = getProdukById(produkId);
  if (!produk) return false;
  if (produk.stok === 0) {
    tampilToast("Produk habis!", "error");
    return false;
  }

  const keranjang = getKeranjang();
  const idx = keranjang.findIndex((item) => item.id === produk.id);

  if (idx > -1) {
    const totalBaru = keranjang[idx].jumlah + jumlah;
    if (totalBaru > produk.stok) {
      tampilToast(`Stok hanya ${produk.stok} tersisa!`, "warning");
      keranjang[idx].jumlah = produk.stok;
    } else {
      keranjang[idx].jumlah = totalBaru;
    }
  } else {
    keranjang.push({
      id: produk.id,
      nama: produk.nama,
      harga: produk.harga,
      gambar: produk.gambar,
      stok: produk.stok,
      jumlah: Math.min(jumlah, produk.stok),
    });
  }

  simpanKeranjang(keranjang);
  tampilToast(`${produk.nama} ditambahkan ke keranjang!`, "success");
  return true;
}

function hapusDariKeranjang(produkId) {
  const keranjang = getKeranjang().filter((item) => item.id !== produkId);
  simpanKeranjang(keranjang);
}

function updateJumlah(produkId, jumlah) {
  const keranjang = getKeranjang();
  const idx = keranjang.findIndex((item) => item.id === produkId);
  if (idx === -1) return;
  if (jumlah <= 0) {
    hapusDariKeranjang(produkId);
    return;
  }
  keranjang[idx].jumlah = Math.min(jumlah, keranjang[idx].stok);
  simpanKeranjang(keranjang);
}

function kosongkanKeranjang() {
  simpanKeranjang([]);
}

function hitungTotalKeranjang() {
  return getKeranjang().reduce(
    (total, item) => total + item.harga * item.jumlah,
    0,
  );
}

function hitungJumlahItem() {
  return getKeranjang().reduce((total, item) => total + item.jumlah, 0);
}

function updateBadgeKeranjang() {
  const jumlah = hitungJumlahItem();
  document.querySelectorAll(".badge-keranjang").forEach((el) => {
    el.textContent = jumlah;
    el.style.display = jumlah > 0 ? "flex" : "none";
  });
}

// ── WISHLIST ───────────────────────────────────────────────

function getWishlist() {
  try {
    return JSON.parse(localStorage.getItem(WISHLIST_KEY)) || [];
  } catch {
    return [];
  }
}

function toggleWishlist(produkId) {
  const list = getWishlist();
  const idx = list.indexOf(produkId);
  if (idx > -1) {
    list.splice(idx, 1);
    tampilToast("Dihapus dari wishlist", "info");
  } else {
    list.push(produkId);
    tampilToast("Ditambahkan ke wishlist ❤️", "success");
  }
  localStorage.setItem(WISHLIST_KEY, JSON.stringify(list));
  updateIkonWishlist();
}

function isInWishlist(produkId) {
  return getWishlist().includes(produkId);
}

function updateIkonWishlist() {
  document.querySelectorAll("[data-wishlist]").forEach((btn) => {
    const id = parseInt(btn.dataset.wishlist);
    const selected = isInWishlist(id);
    const produk = getProdukById(id);
    btn.setAttribute("aria-pressed", String(selected));
    if (produk)
      btn.setAttribute(
        "aria-label",
        `${selected ? "Hapus" : "Simpan"} ${produk.nama} ${selected ? "dari" : "ke"} wishlist`,
      );
    if (selected) {
      btn.classList.add("aktif");
      btn.innerHTML = "♥";
    } else {
      btn.classList.remove("aktif");
      btn.innerHTML = "♡";
    }
  });
}

// ── TOAST NOTIFICATION ─────────────────────────────────────

function tampilToast(pesan, tipe = "success") {
  let container = document.getElementById("toast-container");
  if (!container) {
    container = document.createElement("div");
    container.id = "toast-container";
    container.setAttribute("role", "status");
    container.setAttribute("aria-live", "polite");
    document.body.appendChild(container);
  }

  const toast = document.createElement("div");
  toast.className = `toast toast-${tipe}`;

  const ikon =
    { success: "✅", error: "❌", warning: "⚠️", info: "ℹ️" }[tipe] || "✅";
  toast.innerHTML = `<span class="toast-ikon">${ikon}</span><span>${pesan}</span>`;

  container.appendChild(toast);
  requestAnimationFrame(() => toast.classList.add("masuk"));

  setTimeout(() => {
    toast.classList.add("keluar");
    setTimeout(() => toast.remove(), 400);
  }, 3000);
}

// Init badge saat halaman load
document.addEventListener("DOMContentLoaded", () => {
  updateBadgeKeranjang();
  updateIkonWishlist();
});
