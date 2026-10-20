const storeIcons = {
  user: '<circle cx="12" cy="8" r="4"/><path d="M4 22v-2a8 8 0 0 1 16 0v2"/>',
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

// Destinations are public store settings; messages only leave the site on a user's click.
const storeContactsReady = fetch("/api/store/contacts", {cache: "no-store"})
  .then(async (response) => {
    if (!response.ok) throw new Error("Kontak belum tersedia.");
    return (await response.json()).contacts || {};
  })
  .catch(() => ({}));
function whatsAppUrl(number, text) {
  if (typeof number !== "string" || !/^[1-9][0-9]{7,14}$/.test(number)) return null;
  return "https://wa.me/" + number + "?text=" + encodeURIComponent(text);
}
function paymentWhatsAppUrl(contacts, order) {
  const items = order.items.slice(0, 10).map((item) =>
    `- ${item.nama.slice(0, 100)}${[item.ukuran, item.warna].filter(Boolean).length ? " (" + [item.ukuran, item.warna].filter(Boolean).join(" / ") + ")" : ""} x${item.jumlah}`);
  if (order.items.length > 10) items.push(`- dan ${order.items.length - 10} produk lainnya`);
  return whatsAppUrl(contacts.payment_whatsapp,
    ["Halo Anredseller, saya ingin membayar pesanan:", order.nomor, "", ...items, "",
     "Total pesanan: " + formatHarga(order.total),
     "Mohon instruksi transfer dan konfirmasi pembayaran. Terima kasih."].join("\n"));
}
const header = document.getElementById("store-header");
if (header)
  header.innerHTML = `<div class="announcement"><span>A little upgrade for your everyday.</span><a href="produk.html?sort=terbaru">Discover the new collection <svg class="arrow-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.4" aria-hidden="true"><path d="M5 19 19 5M5 5h14v14"/></svg></a></div><header class="store-header"><div class="store-header-inner"><button class="mobile-menu icon-button" aria-label="Buka menu" aria-expanded="false">${icon("menu")}</button><nav class="desktop-nav" aria-label="Navigasi utama"><a href="produk.html">Shop all</a><a href="produk.html?sort=terbaru">New arrivals <span class="nav-dot"></span></a><button data-dialog="about">Our story</button></nav><a class="wordmark" href="index.html" aria-label="Anredseller Beranda">Anredseller<span>•</span></a><div class="store-actions"><button class="icon-button" data-dialog="search" aria-label="Cari produk">${icon("search")}</button><a class="icon-button customer-account-link" href="akun.html" aria-label="Akun pembeli">${icon("user")}</a><a class="icon-button cart-link" href="keranjang.html" aria-label="Buka keranjang">${icon("bag")}<span class="badge-keranjang">0</span></a></div></div><nav class="store-subnav" aria-label="Kategori"><a href="produk.html?kategori=sneakers">Sneakers</a><a href="produk.html?kategori=apparel">Apparel</a><a href="produk.html?kategori=essentials">Essentials</a><span></span><a href="produk.html?sort=terlaris">Best sellers</a><a href="produk.html?sort=diskon" class="sale-link">The good deals <svg class="arrow-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.4" aria-hidden="true"><path d="M5 19 19 5M5 5h14v14"/></svg></a></nav></header>`;
if (header && document.body.classList.contains("archive-home")) {
  const ticker = `<span>Gratis ongkir mulai Rp200.000</span><span>The Archive by Anredseller</span>`;
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
          <a class="icon-button customer-account-link" href="akun.html" aria-label="Akun pembeli">${icon("user")}</a>
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
  const accountLink = document.createElement("a");
  accountLink.href = "akun.html";
  accountLink.textContent = "Akun saya / Masuk";
  accountLink.className = "menu-account-link";
  navigation.prepend(accountLink);
}
const footer = document.getElementById("store-footer");
if (footer)
  footer.innerHTML = `<footer class="store-footer"><div class="footer-top"><div class="footer-invitation"><h2>Your next good find.</h2><p>Fashion yang kamu pilih.<br>Karakter yang kamu bawa.</p><a class="text-link" href="produk.html">Jelajahi katalog ${icon("bag")}</a></div><nav aria-label="Koleksi footer"><h3>Koleksi</h3><a href="produk.html?kategori=sneakers">Sneakers</a><a href="produk.html?kategori=apparel">Apparel</a><a href="produk.html?kategori=essentials">Essentials</a><a href="produk.html?sort=diskon">Pilihan diskon</a></nav><nav aria-label="Bantuan footer"><h3>Di sini untukmu</h3><button type="button" data-support-open>Hubungi CS via WhatsApp</button><button data-dialog="help">Bantuan & FAQ</button><button data-dialog="shipping">Pengiriman</button><button data-dialog="reseller">Program reseller</button><button data-dialog="privacy">Privasi</button></nav><nav aria-label="Akun footer"><h3>Anredseller</h3><a href="akun.html">Akun & pesanan</a><button data-dialog="wishlist">Wishlist</button><button data-dialog="about">Tentang kami</button><a href="admin.html">Area pemilik</a></nav></div><a class="footer-wordmark" href="index.html" aria-label="Anredseller beranda">Anredseller</a><div class="footer-bottom"><span>© ${new Date().getFullYear()} Anredseller</span><span>Pembayaran dibantu via WhatsApp</span><a href="#main-content">Kembali ke atas ↑</a></div></footer>`;

const supportPanel = document.createElement("dialog");
supportPanel.className = "support-dialog";
supportPanel.id = "support-dialog";
supportPanel.setAttribute("aria-labelledby", "support-title");
supportPanel.innerHTML = `<button class="support-close" type="button" aria-label="Tutup bantuan">×</button><span class="payment-step-label">ANREDSELLER CUSTOMER SERVICE</span><h2 id="support-title">Bisa kami bantu?</h2><p>Tanya soal produk, ukuran, pengiriman, atau pesananmu lewat WhatsApp CS.</p><a id="support-whatsapp-link" class="whatsapp-action" target="_blank" rel="noopener noreferrer" aria-disabled="true">Menyiapkan WhatsApp…</a><p id="support-availability" class="payment-note" role="status"></p><div class="support-payment-note">Ingin membayar pesanan?<br><a href="akun.html#orders">Buka pesanan untuk menghubungi admin pembayaran →</a></div>`;
document.body.appendChild(supportPanel);
const supportLauncher = document.createElement("button");
supportLauncher.type = "button";
supportLauncher.className = "support-launcher";
supportLauncher.dataset.supportOpen = "";
supportLauncher.setAttribute("aria-haspopup", "dialog");
supportLauncher.setAttribute("aria-controls", "support-dialog");
supportLauncher.innerHTML = `${icon("chat")} <span>Hubungi CS</span>`;
document.body.appendChild(supportLauncher);
supportPanel.querySelector(".support-close").addEventListener("click", () => supportPanel.close());
document.addEventListener("click", async (event) => {
  if (!event.target.closest("[data-support-open]")) return;
  if (!supportPanel.open) supportPanel.showModal();
  const contacts = await storeContactsReady;
  const link = document.getElementById("support-whatsapp-link");
  const url = whatsAppUrl(contacts.support_whatsapp, "Halo CS Anredseller, saya ingin bertanya tentang produk atau pesanan.");
  if (url) {
    link.href = url;
    link.removeAttribute("aria-disabled");
    link.innerHTML = `${icon("chat")} Chat CS via WhatsApp`;
    document.getElementById("support-availability").textContent = "Percakapan akan dilanjutkan di WhatsApp. Kirim pesanmu untuk memulai.";
  } else {
    link.removeAttribute("href");
    link.setAttribute("aria-disabled", "true");
    link.textContent = "WhatsApp CS belum tersedia";
    document.getElementById("support-availability").textContent = "Kontak CS belum tersedia. Coba kembali nanti.";
  }
});
document
  .querySelectorAll("[data-icon]")
  .forEach((el) => (el.innerHTML = icon(el.dataset.icon)));
const dialog = document.createElement("dialog");
dialog.className = "store-dialog";
dialog.innerHTML =
  '<button class="dialog-close" aria-label="Tutup dialog"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" aria-hidden="true"><path d="m6 6 12 12M18 6 6 18"/></svg></button><div id="dialog-content"></div>';
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
    "Setelah checkout, lanjutkan pembayaran melalui tombol WhatsApp pada rincian pesanan. Admin pembayaran memberikan instruksi transfer dan memeriksa bukti pembayaran. Untuk pertanyaan belanja, hubungi nomor CS yang terpisah.",
  ],
  shipping: [
    "From us, to your everyday.",
    "Opsi pengiriman tersedia pada halaman checkout. Rincian ongkir dapat dilihat pada ringkasan keranjang.",
    "Pengiriman dan pembayaran dikonfirmasi langsung oleh toko. Ongkir yang tampil adalah estimasi berdasarkan tarif toko.",
  ],
  privacy: [
    "Your details, thoughtfully kept.",
    "Profil, alamat, wishlist, keranjang, dan pesanan tersimpan di akun pembeli. Kamu dapat mengaksesnya setelah masuk di perangkat lain.",
    "Data pesanan hanya dapat dilihat oleh pembeli yang bersangkutan dan pemilik toko yang sudah login.",
  ],
  reseller: [
    "Good things. Better together.",
    "Bangun koleksi pilihan untuk pelangganmu lewat konsep program reseller Anredseller",
    "Program akan mencakup katalog pilihan, informasi stok, dan panduan pemesanan. Harga reseller, minimum order, dan kontak admin belum ditetapkan.",
  ],
};
async function openStoreDialog(type) {
  if (type === "wishlist" && !(await requireBuyer())) return;
  if (type === "search") {
    dialogContent.innerHTML =
      '<h2>Cari favoritmu.</h2><form class="dialog-search" action="produk.html"><input name="q" type="search" placeholder="Cari sneakers, kaos, atau brand…" aria-label="Cari produk" required><button type="submit">Cari <svg class="arrow-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.4" aria-hidden="true"><path d="M5 19 19 5M5 5h14v14"/></svg></button></form><p>Coba: Nike, Jordan, essential</p>';
  } else if (type === "wishlist") {
    const list = getWishlist().map(getProdukById).filter(Boolean);
    dialogContent.innerHTML =
      "<h2>Koleksi tersimpan.</h2>" +
      (list.length
        ? '<div class="wishlist-list">' +
          list
            .map(
              (p) =>
                `<div><a href="detail.html?id=${p.id}"><img src="${productImage(p.gambar)}" alt="${h(p.nama)}"><span>${h(p.nama)}<small>${formatHarga(p.harga)}</small></span></a><button data-remove-wish="${p.id}" aria-label="Hapus ${h(p.nama)}"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" aria-hidden="true"><path d="m6 6 12 12M18 6 6 18"/></svg></button></div>`,
            )
            .join("") +
          "</div>"
        : '<p>Belum ada produk tersimpan. Ketuk ikon hati pada produk yang kamu suka.</p><a class="solid-link" href="produk.html">Temukan favoritmu <svg class="arrow-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.4" aria-hidden="true"><path d="M5 19 19 5M5 5h14v14"/></svg></a>');
  } else {
    const copy = info[type] || info.help;
    dialogContent.innerHTML = `<h2>${copy[0]}</h2><p>${copy[1]}</p><p>${copy[2]}</p>${type === "reseller" ? '<a class="solid-link" href="produk.html">Jelajahi katalog contoh <svg class="arrow-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.4" aria-hidden="true"><path d="M5 19 19 5M5 5h14v14"/></svg></a>' : ""}`;
  }
  const title = dialogContent.querySelector("h2");
  title.id = "store-dialog-title";
  dialog.setAttribute("aria-labelledby", title.id);
  dialog.showModal();
}
document.addEventListener("click", async (e) => {
  const trigger = e.target.closest("[data-dialog]");
  if (trigger) {
    e.preventDefault();
    openStoreDialog(trigger.dataset.dialog);
  }
  const remove = e.target.closest("[data-remove-wish]");
  if (remove) {
    await toggleWishlist(Number(remove.dataset.removeWish));
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

window.addEventListener("customer:session", () => {
  document
    .querySelectorAll(".customer-account-link")
    .forEach((link) =>
      link.setAttribute(
        "aria-label",
        buyerSession.authenticated
          ? "Akun " + buyerSession.customer.nama
          : "Masuk atau daftar pembeli",
      ),
    );
});

// Small entrances support the editorial reading order without hiding any content.
if (
  !matchMedia("(prefers-reduced-motion: reduce)").matches &&
  "IntersectionObserver" in window
) {
  const observed = new WeakSet();
  const observer = new IntersectionObserver(
    (entries) => {
      entries.forEach(({ target, isIntersecting }) => {
        if (!isIntersecting) return;
        target.classList.add(
          target.matches(".campaign-photo, .reseller-photo")
            ? "arriving-picture"
            : "arriving",
        );
        observer.unobserve(target);
      });
    },
    { threshold: 0.12 },
  );
  const observeEditorial = () => {
    document
      .querySelectorAll(
        ".campaign h1, .campaign p, .campaign .solid-link, .section-topline h2, .section-topline p, .section-topline .text-link, .kartu-produk, .editorial-card, .reseller-content h2, .reseller-content p, .reseller-photo, .newsletter-edit h2, .newsletter-edit form, .footer-invitation, .footer-top nav",
      )
      .forEach((target, index) => {
        if (observed.has(target)) return;
        observed.add(target);
        target.style.setProperty("--arrival-delay", `${(index % 3) * 65}ms`);
        observer.observe(target);
      });
  };
  observeEditorial();
  window.addEventListener("store:products", observeEditorial);
}
