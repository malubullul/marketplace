const CART_KEY = "anredseller_cart";
const WISHLIST_KEY = "anredseller_wishlist";
function getKeranjang() {
  try {
    const items = JSON.parse(localStorage.getItem(CART_KEY)) || [];
    return Array.isArray(items)
      ? items.map((item) => ({ ...item, key: item.key || String(item.id) }))
      : [];
  } catch {
    return [];
  }
}
function simpanKeranjang(items) {
  localStorage.setItem(CART_KEY, JSON.stringify(items));
  updateBadgeKeranjang();
}
function cartLineKey(id, size = "", color = "") {
  return `${id}:${encodeURIComponent(size).replace(/'/g, "%27")}:${encodeURIComponent(color).replace(/'/g, "%27")}`;
}
function tambahKeKeranjang(id, jumlah = 1, ukuran = "", warna = "") {
  const product = getProdukById(id);
  if (!product) return false;
  if (product.stok <= 0) {
    tampilToast("Produk sedang habis.", "error");
    return false;
  }
  if (
    (product.ukuran?.length && !product.ukuran.includes(ukuran)) ||
    (product.warna?.length && !product.warna.includes(warna))
  ) {
    tampilToast("Pilih ukuran dan warna terlebih dahulu.", "warning");
    return false;
  }
  jumlah = Math.floor(Number(jumlah));
  if (!Number.isFinite(jumlah) || jumlah < 1) return false;
  const items = getKeranjang(),
    key = cartLineKey(id, ukuran, warna),
    existing = items.find((item) => item.key === key);
  const total = items
    .filter((item) => item.id === id)
    .reduce((sum, item) => sum + item.jumlah, 0);
  const available = product.stok - total;
  if (available <= 0) {
    tampilToast("Seluruh stok produk ini sudah ada di keranjang.", "warning");
    return false;
  }
  const quantity = Math.min(jumlah, available);
  if (existing) existing.jumlah += quantity;
  else
    items.push({
      key,
      id: product.id,
      nama: product.nama,
      harga: product.harga,
      gambar: product.gambar,
      stok: product.stok,
      jumlah: quantity,
      ukuran,
      warna,
    });
  simpanKeranjang(items);
  tampilToast(product.nama + " ditambahkan ke keranjang.", "success");
  return true;
}
function hapusDariKeranjang(key) {
  simpanKeranjang(getKeranjang().filter((item) => item.key !== String(key)));
}
function updateJumlah(key, jumlah) {
  const items = getKeranjang(),
    item = items.find((item) => item.key === String(key));
  if (!item) return;
  if (jumlah <= 0) {
    hapusDariKeranjang(key);
    return;
  }
  const others = items
    .filter((line) => line.id === item.id && line.key !== item.key)
    .reduce((sum, line) => sum + line.jumlah, 0);
  item.jumlah = Math.min(
    Math.max(1, Math.floor(jumlah)),
    Math.max(0, item.stok - others),
  );
  simpanKeranjang(items.filter((line) => line.jumlah > 0));
}
function syncCartCatalog() {
  if (katalogMode !== "server") return;
  const used = {};
  const items = getKeranjang().flatMap((item) => {
    const p = getProdukById(item.id);
    if (!p || p.stok <= 0) return [];
    if (
      (p.ukuran?.length && !p.ukuran.includes(item.ukuran)) ||
      (p.warna?.length && !p.warna.includes(item.warna))
    )
      return [];
    const quantity = Math.min(item.jumlah, p.stok - (used[p.id] || 0));
    used[p.id] = (used[p.id] || 0) + quantity;
    return quantity > 0
      ? [
          {
            ...item,
            nama: p.nama,
            harga: p.harga,
            gambar: p.gambar,
            stok: p.stok,
            jumlah: quantity,
          },
        ]
      : [];
  });
  simpanKeranjang(items);
}
function kosongkanKeranjang() {
  simpanKeranjang([]);
}
function hitungTotalKeranjang() {
  return getKeranjang().reduce(
    (sum, item) => sum + item.harga * item.jumlah,
    0,
  );
}
function hitungJumlahItem() {
  return getKeranjang().reduce((sum, item) => sum + item.jumlah, 0);
}
function updateBadgeKeranjang() {
  document.querySelectorAll(".badge-keranjang").forEach((el) => {
    const total = hitungJumlahItem();
    el.textContent = total;
    el.style.display = total ? "flex" : "none";
  });
}
function getWishlist() {
  try {
    const list = JSON.parse(localStorage.getItem(WISHLIST_KEY)) || [];
    return Array.isArray(list) ? list : [];
  } catch {
    return [];
  }
}
function toggleWishlist(id) {
  const list = getWishlist(),
    index = list.indexOf(id);
  if (index >= 0) list.splice(index, 1);
  else list.push(id);
  localStorage.setItem(WISHLIST_KEY, JSON.stringify(list));
  updateIkonWishlist();
  tampilToast(
    index >= 0 ? "Dihapus dari wishlist." : "Disimpan ke wishlist.",
    "info",
  );
}
function isInWishlist(id) {
  return getWishlist().includes(id);
}
function updateIkonWishlist() {
  document.querySelectorAll("[data-wishlist]").forEach((button) => {
    const id = Number(button.dataset.wishlist),
      selected = isInWishlist(id),
      p = getProdukById(id);
    button.classList.toggle("aktif", selected);
    button.setAttribute("aria-pressed", String(selected));
    if (p)
      button.setAttribute(
        "aria-label",
        `${selected ? "Hapus" : "Simpan"} ${p.nama} ${selected ? "dari" : "ke"} wishlist`,
      );
    button.textContent = selected ? "♥" : "♡";
  });
}
function tampilToast(message, type = "success") {
  let container = document.getElementById("toast-container");
  if (!container) {
    container = document.createElement("div");
    container.id = "toast-container";
    container.setAttribute("role", "status");
    container.setAttribute("aria-live", "polite");
    document.body.appendChild(container);
  }
  const toast = document.createElement("div");
  toast.className = "toast toast-" + type;
  toast.textContent = message;
  container.appendChild(toast);
  requestAnimationFrame(() => toast.classList.add("masuk"));
  setTimeout(() => toast.remove(), 4000);
}
document.addEventListener("DOMContentLoaded", async () => {
  await katalogSiap;
  updateBadgeKeranjang();
  updateIkonWishlist();
});
