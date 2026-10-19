const storeIcons = {
  search: '<circle cx="10.5" cy="10.5" r="6.5"/><path d="m16 16 4.5 4.5"/>',
  bag: '<path d="M5 7h14l1 14H4L5 7Z"/><path d="M9 8V5a3 3 0 0 1 6 0v3"/>',
  heart:
    '<path d="M20.8 4.6a5.5 5.5 0 0 0-7.8 0L12 5.7l-1.1-1.1a5.5 5.5 0 0 0-7.8 7.8L12 21l8.8-8.6a5.5 5.5 0 0 0 0-7.8Z"/>',
  menu: '<path d="M3 6h18M3 12h18M3 18h18"/>',
  box: '<path d="m12 3 9 5-9 5-9-5 9-5Zm-9 5v10l9 5 9-5V8M12 13v10M7 5.7l9 5"/>',
  shield:
    '<path d="m12 3 8 3v6c0 5-8 9-8 9s-8-4-8-9V6l8-3Z"/><path d="m8 12 3 3 5-6"/>',
  truck:
    '<path d="M2 5h12v12H2ZM14 9h4l4 5v3h-8"/><circle cx="6" cy="18" r="2"/><circle cx="18" cy="18" r="2"/>',
  chat: '<path d="M21 11a9 9 0 0 1-9 9H4l-3 2 2-6a9 9 0 1 1 18-5Z"/><path d="M7 11h10"/>',
};
const icon = (name) =>
  `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${storeIcons[name] || ""}</svg>`;
const header = document.getElementById("store-header");
if (header)
  header.innerHTML = `<div class="announcement"><span>A little upgrade for your everyday.</span><a href="produk.html?sort=terbaru">Discover the new collection <svg class="arrow-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.4" aria-hidden="true"><path d="M5 19 19 5M5 5h14v14"/></svg></a></div><header class="store-header"><div class="store-header-inner"><button class="mobile-menu icon-button" aria-label="Buka menu" aria-expanded="false">${icon("menu")}</button><nav class="desktop-nav" aria-label="Navigasi utama"><a href="produk.html">Shop all</a><a href="produk.html?sort=terbaru">New arrivals <span class="nav-dot"></span></a><button data-dialog="about">Our story</button></nav><a class="wordmark" href="index.html" aria-label="Anredseller Beranda">Anredseller<span>•</span></a><div class="store-actions"><button class="icon-button" data-dialog="search" aria-label="Cari produk">${icon("search")}</button><button class="icon-button" data-dialog="wishlist" aria-label="Buka wishlist">${icon("heart")}</button><a class="icon-button cart-link" href="keranjang.html" aria-label="Buka keranjang">${icon("bag")}<span class="badge-keranjang">0</span></a></div></div><nav class="store-subnav" aria-label="Kategori"><a href="produk.html?kategori=sneakers">Sneakers</a><a href="produk.html?kategori=apparel">Apparel</a><a href="produk.html?kategori=essentials">Essentials</a><span></span><a href="produk.html?sort=terlaris">Best sellers</a><a href="produk.html?sort=diskon" class="sale-link">The good deals <svg class="arrow-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.4" aria-hidden="true"><path d="M5 19 19 5M5 5h14v14"/></svg></a></nav></header>`;
if (header && document.body.classList.contains("archive-home")) {
  const ticker = `<span>FREE SHIPPING OVER IDR 200K</span><span class="ticker-dot">•</span><span>ANREDSELLER ARCHIVE</span><span class="ticker-dot">•</span>`;
  header.innerHTML = `
    <div class="archive-announcement" aria-label="Gratis ongkir untuk pembelian mulai Rp200.000 — Anredseller Archive">
      <div class="archive-ticker" aria-hidden="true"><div>${ticker.repeat(4)}</div><div>${ticker.repeat(4)}</div></div>
    </div>
    <header class="store-header archive-header">
      <div class="store-header-inner">
        <button class="mobile-menu icon-button" aria-label="Buka menu" aria-expanded="false" aria-controls="store-navigation">${icon("menu")}</button>
        <nav class="desktop-nav" id="store-navigation" aria-label="Navigasi utama">
          <a href="produk.html">Shop all</a>
          <a href="produk.html?sort=terbaru">New arrivals</a>
          <a href="produk.html?kategori=apparel">Apparel</a>
          <a href="produk.html?kategori=sneakers">Sneakers</a>
          <a href="produk.html?kategori=essentials">Essentials</a>
          <button data-dialog="about">Our story</button>
        </nav>
        <a class="wordmark" href="index.html" aria-label="Anredseller Beranda">Anredseller</a>
        <div class="store-actions">
          <button class="icon-button" data-dialog="wishlist" aria-label="Buka wishlist">${icon("heart")}</button>
          <button class="icon-button" data-dialog="search" aria-label="Cari produk">${icon("search")}</button>
          <a class="icon-button cart-link" href="keranjang.html" aria-label="Buka keranjang">${icon("bag")}<span class="badge-keranjang">0</span></a>
        </div>
      </div>
    </header>`;
}
const mainContent = document.querySelector("main, .page-banner, .breadcrumb");
if (mainContent) {
  mainContent.id = "main-content";
  mainContent.tabIndex = -1;
  const skipLink = document.createElement("a");
  skipLink.className = "skip-link";
  skipLink.href = "#main-content";
  skipLink.textContent = "Langsung ke konten";
  document.body.prepend(skipLink);
}
const navigation = document.querySelector(".desktop-nav");
if (navigation) {
  const savedItems = document.createElement("button");
  savedItems.className = "mobile-wishlist";
  savedItems.dataset.dialog = "wishlist";
  savedItems.textContent = "Wishlist";
  navigation.appendChild(savedItems);
}
const footer = document.getElementById("store-footer");
if (footer)
  footer.innerHTML = `<footer class="store-footer"><div class="footer-top"><div><a class="wordmark" href="index.html">Anredseller<span>•</span></a><p>A good find changes your day.<br>Find yours here.</p></div><div><h3>THE COLLECTION</h3><a href="produk.html?kategori=sneakers">Sneakers</a><a href="produk.html?kategori=apparel">Apparel</a><a href="produk.html?kategori=essentials">Essentials</a><a href="produk.html?sort=diskon">The good deals</a></div><div><h3>LET'S TALK</h3><button data-dialog="help">Bantuan & FAQ</button><button data-dialog="shipping">Pengiriman & pengembalian</button><button data-dialog="reseller">Program reseller</button></div><div><h3>A LITTLE ABOUT US</h3><button data-dialog="about">Our story</button><button data-dialog="privacy">Privasi</button><a href="admin.html">Area pemilik</a><span class="footer-location">Based in Indonesia.<br>Curated for everywhere.</span></div></div><div class="footer-bottom"><span>© ${new Date().getFullYear()} Anredseller. All good things reserved.</span><span>Pembayaran dikonfirmasi oleh toko</span><span>GOOD TASTE IS ALWAYS IN SEASON. <svg class="arrow-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.4" aria-hidden="true"><path d="M5 19 19 5M5 5h14v14"/></svg></span></div></footer>`;
document
  .querySelectorAll("[data-icon]")
  .forEach((el) => (el.innerHTML = icon(el.dataset.icon)));
const dialog = document.createElement("dialog");
dialog.className = "store-dialog";
dialog.innerHTML =
  '<button class="dialog-close" aria-label="Tutup dialog">✕</button><div id="dialog-content"></div>';
document.body.appendChild(dialog);
const dialogContent = dialog.querySelector("#dialog-content");
const info = {
  about: [
    "A good find. A better everyday.",
    "Anredseller adalah konsep toko reseller untuk sneakers, apparel, dan barang pilihan sehari-hari. Kami percaya gaya personal dimulai dari pilihan yang kamu suka.",
    "Koleksi produk dikelola oleh pemilik toko. Produk contoh perlu diganti sebelum toko mulai beroperasi.",
  ],
  help: [
    "How can we help?",
    "Cari produk melalui ikon pencarian, pilih koleksi, lalu tambahkan favoritmu ke keranjang. Pesanan dapat dicoba sampai konfirmasi.",
    "Pesanan dikirim ke toko untuk dikonfirmasi. Pembayaran dan pengiriman belum diproses otomatis.",
  ],
  shipping: [
    "From us, to your everyday.",
    "Opsi pengiriman tersedia pada halaman checkout. Rincian ongkir dapat dilihat pada ringkasan keranjang.",
    "Pengiriman dan pembayaran dikonfirmasi langsung oleh toko. Ongkir yang tampil adalah estimasi berdasarkan tarif toko.",
  ],
  privacy: [
    "Your details, thoughtfully kept.",
    "Wishlist dan keranjang tersimpan di browser. Data yang kamu kirim saat checkout disimpan oleh toko untuk memproses pesanan.",
    "Email dan alamat pesanan hanya tersedia bagi pemilik toko yang sudah login.",
  ],
  reseller: [
    "Good things. Better together.",
    "Bangun koleksi pilihan untuk pelangganmu lewat konsep program reseller Anredseller",
    "Program akan mencakup katalog pilihan, informasi stok, dan panduan pemesanan. Harga reseller, minimum order, dan kontak admin belum ditetapkan.",
  ],
};
function openStoreDialog(type) {
  if (type === "search") {
    dialogContent.innerHTML =
      '<div class="eyebrow">FIND YOUR NEXT FAVORITE</div><h2>What are you looking for?</h2><form class="dialog-search" action="produk.html"><input name="q" type="search" placeholder="Cari sneakers, kaos, atau brand…" aria-label="Cari produk" required><button type="submit">Cari <svg class="arrow-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.4" aria-hidden="true"><path d="M5 19 19 5M5 5h14v14"/></svg></button></form><p>Coba: Nike, Jordan, essential</p>';
  } else if (type === "wishlist") {
    const list = getWishlist().map(getProdukById).filter(Boolean);
    dialogContent.innerHTML =
      '<div class="eyebrow">SAVED FOR LATER</div><h2>Your good finds.</h2>' +
      (list.length
        ? '<div class="wishlist-list">' +
          list
            .map(
              (p) =>
                `<div><a href="detail.html?id=${p.id}"><img src="${productImage(p.gambar)}" alt="${h(p.nama)}"><span>${h(p.nama)}<small>${formatHarga(p.harga)}</small></span></a><button data-remove-wish="${p.id}" aria-label="Hapus ${h(p.nama)}">✕</button></div>`,
            )
            .join("") +
          "</div>"
        : '<p>Belum ada produk tersimpan. Ketuk ikon hati pada produk yang kamu suka.</p><a class="solid-link" href="produk.html">Temukan favoritmu <svg class="arrow-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.4" aria-hidden="true"><path d="M5 19 19 5M5 5h14v14"/></svg></a>');
  } else {
    const copy = info[type] || info.help;
    dialogContent.innerHTML = `<div class="eyebrow">Anredseller / ${type.toUpperCase()}</div><h2>${copy[0]}</h2><p>${copy[1]}</p><p>${copy[2]}</p>${type === "reseller" ? '<a class="solid-link" href="produk.html">Jelajahi katalog contoh <svg class="arrow-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.4" aria-hidden="true"><path d="M5 19 19 5M5 5h14v14"/></svg></a>' : ""}`;
  }
  const title = dialogContent.querySelector("h2");
  title.id = "store-dialog-title";
  dialog.setAttribute("aria-labelledby", title.id);
  dialog.showModal();
}
document.addEventListener("click", (e) => {
  const trigger = e.target.closest("[data-dialog]");
  if (trigger) {
    e.preventDefault();
    openStoreDialog(trigger.dataset.dialog);
  }
  const remove = e.target.closest("[data-remove-wish]");
  if (remove) {
    toggleWishlist(Number(remove.dataset.removeWish));
    dialog.close();
    openStoreDialog("wishlist");
  }
});
dialog
  .querySelector(".dialog-close")
  .addEventListener("click", () => dialog.close());
dialog.addEventListener("click", (e) => {
  if (e.target === dialog) {
    const b = dialog.getBoundingClientRect();
    if (
      e.clientX < b.left ||
      e.clientX > b.right ||
      e.clientY < b.top ||
      e.clientY > b.bottom
    )
      dialog.close();
  }
});
document.querySelector(".mobile-menu")?.addEventListener("click", (e) => {
  const b = e.currentTarget;
  const open = b.getAttribute("aria-expanded") !== "true";
  b.setAttribute("aria-expanded", String(open));
  document.querySelector(".desktop-nav").classList.toggle("mobile-open", open);
});
function closeStoreMenu() {
  document
    .querySelector(".mobile-menu")
    ?.setAttribute("aria-expanded", "false");
  document.querySelector(".desktop-nav")?.classList.remove("mobile-open");
}
document.addEventListener("keydown", (e) => {
  if (e.key === "Escape" && !dialog.open) {
    const focusWasInMenu = navigation?.contains(document.activeElement);
    closeStoreMenu();
    if (focusWasInMenu) document.querySelector(".mobile-menu")?.focus();
  }
});
document.addEventListener("click", (e) => {
  if (!e.target.closest(".store-header")) closeStoreMenu();
});
updateBadgeKeranjang();
