function wishlistIcon(selected = false) {
  return `<svg viewBox="0 0 24 24" fill="${selected ? "currentColor" : "none"}" stroke="currentColor" stroke-width="1.5" aria-hidden="true"><path d="M20.8 4.6a5.5 5.5 0 0 0-7.8 0L12 5.7l-1.1-1.1a5.5 5.5 0 0 0-7.8 7.8L12 21l8.8-8.6a5.5 5.5 0 0 0 0-7.8Z"/></svg>`;
}
let buyerSession = { authenticated: false, customer: null, csrf: "" };
let shoppingState = { cart: [], wishlist: [], revision: 0 };
let shoppingQueue = Promise.resolve();
async function customerRequest(path, options = {}) {
  const headers = { ...options.headers };
  if (options.method && options.method !== "GET") {
    headers["X-CSRF-Token"] = buyerSession.csrf;
    headers["Content-Type"] = "application/json";
  }
  const response = await fetch("/api/customer" + path, {
    ...options,
    headers,
    body: options.body === undefined ? undefined : JSON.stringify(options.body),
    cache: "no-store",
  });
  const data = await response
    .json()
    .catch(() => ({ error: "Layanan akun belum dapat diakses." }));
  if (!response.ok) {
    if (response.status === 401) {
      buyerSession = {
        authenticated: false,
        customer: null,
        csrf: buyerSession.csrf,
      };
      shoppingState = { cart: [], wishlist: [], revision: 0 };
      updateBadgeKeranjang();
      updateIkonWishlist();
    }
    const error = new Error(data.error || "Permintaan belum berhasil.");
    error.status = response.status;
    throw error;
  }
  return data;
}
function applyShoppingState(state) {
  if (!state) return;
  if (state.customer_id && state.customer_id !== buyerSession.customer?.id) {
    location.reload();
    return;
  }
  if (state.revision < shoppingState.revision) return;
  shoppingState = state;
  updateBadgeKeranjang();
  updateIkonWishlist();
  window.dispatchEvent(new CustomEvent("customer:state", { detail: state }));
}
const buyerReady = (async () => {
  await katalogSiap;
  if (katalogMode !== "server") return;
  try {
    buyerSession = await customerRequest("/session");
    if (buyerSession.authenticated) {
      const data = await customerRequest("/state");
      applyShoppingState(data.state);
    }
  } catch (error) {
    buyerSession.error = error.message;
  }
  window.dispatchEvent(new Event("customer:session"));
})();
function buyerLoginUrl(
  next = location.pathname.split("/").pop() + location.search,
) {
  return "akun.html?next=" + encodeURIComponent(next || "index.html");
}
async function requireBuyer() {
  await buyerReady;
  if (katalogMode !== "server") {
    tampilToast("Layanan akun memerlukan server Anredseller.", "error");
    return false;
  }
  if (!buyerSession.authenticated) {
    location.href = buyerLoginUrl();
    return false;
  }
  return true;
}
function clearBuyerBrowserData() {
  for (const key of [
    "pesanan_terakhir",
    "checkout_request_key",
    "checkout_kupon",
    "checkout_subtotal",
    "checkout_total",
    "checkout_ongkir",
    "checkout_diskon",
  ])
    sessionStorage.removeItem(key);
}
function signalCustomerAuthChange() {
  try {
    localStorage.setItem(
      "anredseller_auth_changed",
      Date.now() + ":" + Math.random(),
    );
  } catch {}
}
window.addEventListener("storage", (event) => {
  if (event.key === "anredseller_auth_changed") {
    clearBuyerBrowserData();
    location.reload();
  }
});
async function customerLogout() {
  await customerRequest("/logout", { method: "POST" });
  clearBuyerBrowserData();
  signalCustomerAuthChange();
  shoppingState = { cart: [], wishlist: [], revision: 0 };
  location.replace("akun.html");
}
function getKeranjang() {
  return shoppingState.cart;
}
function getWishlist() {
  return shoppingState.wishlist;
}
function isInWishlist(id) {
  return getWishlist().includes(id);
}
function cartLineKey(id, size = "", color = "") {
  return `${id}:${encodeURIComponent(size).replace(/'/g, "%27")}:${encodeURIComponent(color).replace(/'/g, "%27")}`;
}
function stockGroupKey(item) { return item.stock_key || String(item.id); }
async function mutateShopping(path, body) {
  if (!(await requireBuyer())) return false;
  const job = shoppingQueue
    .catch(() => {})
    .then(async () => {
      try {
        const data = await customerRequest(path, { method: "POST", body });
        applyShoppingState(data.state);
        return true;
      } catch (error) {
        tampilToast(error.message, "error");
        if (error.status === 401) location.href = buyerLoginUrl();
        return false;
      }
    });
  shoppingQueue = job;
  return job;
}
async function tambahKeKeranjang(id, jumlah = 1, ukuran = "", warna = "") {
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
  const success = await mutateShopping("/cart", {
    action: "add",
    id,
    jumlah,
    ukuran,
    warna,
  });
  if (success) tampilToast(product.nama + " ditambahkan ke keranjang.");
  return success;
}
async function hapusDariKeranjang(key) {
  return mutateShopping("/cart", { action: "remove", key });
}
async function updateJumlah(key, jumlah) {
  return mutateShopping("/cart", { action: "update", key, jumlah });
}
function syncCartCatalog() {} // Prices and availability are resolved by the server.
async function kosongkanKeranjang() {
  return mutateShopping("/cart", { action: "clear" });
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
async function toggleWishlist(id) {
  const saved = isInWishlist(id);
  const success = await mutateShopping("/wishlist", { id });
  if (success)
    tampilToast(
      saved ? "Dihapus dari wishlist." : "Disimpan di wishlist akunmu.",
      "info",
    );
  return success;
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
    button.innerHTML = wishlistIcon(selected);
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
  await buyerReady;
  updateBadgeKeranjang();
  updateIkonWishlist();
});
let refreshingBuyer = false;
async function refreshBuyerState() {
  await buyerReady;
  if (!buyerSession.authenticated || refreshingBuyer) return;
  refreshingBuyer = true;
  try {
    const data = await customerRequest("/state");
    applyShoppingState(data.state);
  } catch (error) {
    if (error.status === 401) {
      clearBuyerBrowserData();
      location.reload();
    } else
      tampilToast(
        "Belum dapat memperbarui keranjang. Muat ulang halaman.",
        "info",
      );
  } finally {
    refreshingBuyer = false;
  }
}
window.addEventListener("focus", refreshBuyerState);
document.addEventListener("visibilitychange", () => {
  if (document.visibilityState === "visible") refreshBuyerState();
});

window.addEventListener("pageshow", (event) => {
  if (event.persisted) location.reload();
});
