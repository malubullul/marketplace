document.addEventListener("DOMContentLoaded", () => {
  renderTrending();
  renderRekomendasi();
  if (!document.getElementById("grid-produk-list")) initSearch();
  initNewsletter();
  const tabs = [...document.querySelectorAll("[data-collection]")];
  const panel = document.getElementById("grid-trending");
  if (!panel || !tabs.length) return;
  panel.setAttribute("role", "tabpanel");
  panel.tabIndex = 0;
  const selectCollection = (button) => {
    tabs.forEach((tab) => {
      const selected = tab === button;
      tab.classList.toggle("selected", selected);
      tab.setAttribute("aria-selected", String(selected));
      tab.tabIndex = selected ? 0 : -1;
    });
    panel.setAttribute("aria-labelledby", button.id);
    const products =
      button.dataset.collection === "all"
        ? PRODUK.slice(0, 4)
        : PRODUK.filter((p) => p.kategori === button.dataset.collection).slice(
            0,
            4,
          );
    panel.innerHTML = products.map(renderKartuProduk).join("");
    updateIkonWishlist();
  };
  tabs.forEach((button, index) => {
    button.id = `collection-tab-${button.dataset.collection}`;
    button.setAttribute("aria-controls", panel.id);
    button.addEventListener("click", () => selectCollection(button));
    button.addEventListener("keydown", (event) => {
      let next;
      if (event.key === "ArrowRight") next = (index + 1) % tabs.length;
      else if (event.key === "ArrowLeft")
        next = (index - 1 + tabs.length) % tabs.length;
      else if (event.key === "Home") next = 0;
      else if (event.key === "End") next = tabs.length - 1;
      else return;
      event.preventDefault();
      tabs[next].focus();
      selectCollection(tabs[next]);
    });
  });
  selectCollection(
    tabs.find((tab) => tab.classList.contains("selected")) || tabs[0],
  );
});
function renderKategori() {}
function renderTrending() {
  const el = document.getElementById("grid-trending");
  if (el) el.innerHTML = PRODUK.slice(0, 4).map(renderKartuProduk).join("");
}
function renderRekomendasi() {
  const el = document.getElementById("grid-rekomendasi");
  if (el) el.innerHTML = getProdukRekomendasi().map(renderKartuProduk).join("");
}
function renderKartuProduk(p) {
  return `<article class="kartu-produk" data-produk-id="${p.id}"><div class="kartu-produk-gambar"><a href="detail.html?id=${p.id}" aria-label="Lihat ${p.nama}"><img src="${p.gambar}" alt="${p.nama}" loading="lazy"></a>${p.label ? `<span class="kartu-label">${p.label}</span>` : ""}<button aria-label="Simpan ${p.nama} ke wishlist" class="btn-wishlist ${isInWishlist(p.id) ? "aktif" : ""}" data-wishlist="${p.id}" onclick="toggleWishlist(${p.id})">${isInWishlist(p.id) ? "♥" : "♡"}</button><button class="btn-keranjang-cepat" onclick="tambahKeKeranjang(${p.id},1)">+ Tambah ke keranjang</button></div><div class="kartu-produk-info"><div class="product-meta"><span>${p.brand}</span><span>${p.kategori === "sneakers" ? "UNISEX" : "EVERYDAY"}</span></div><a class="kartu-produk-nama" href="detail.html?id=${p.id}">${p.nama}</a><div class="kartu-harga"><span class="harga-sekarang">${formatHarga(p.harga)}</span><span class="harga-asli">${formatHarga(p.hargaAsli)}</span></div><div class="product-colors" aria-label="Warna sesuai foto produk"><i></i><span>Selected for you</span></div></div></article>`;
}
function attachProdukEvents() {
  updateIkonWishlist();
}
function initSearch() {
  const input = document.getElementById("search-input"),
    btn = document.getElementById("search-btn");
  if (!input || input.dataset.bound) return;
  input.dataset.bound = "true";
  const run = () => {
    if (input.value.trim())
      location.href = "produk.html?q=" + encodeURIComponent(input.value.trim());
  };
  btn?.addEventListener("click", run);
  input.addEventListener("keydown", (e) => {
    if (e.key === "Enter") run();
  });
}
function initNewsletter() {
  document.querySelectorAll("#newsletter-form").forEach((form) =>
    form.addEventListener("submit", (e) => {
      e.preventDefault();
      const email = form.querySelector("input").value.trim();
      if (!email) return;
      try {
        localStorage.setItem("curated_newsletter_interest", email);
        const message =
          "Minatmu tersimpan di perangkat ini. Pengiriman email belum diaktifkan.";
        const status = document.getElementById("newsletter-status");
        if (status) status.textContent = message;
        else tampilToast(message, "info");
        form.reset();
      } catch {
        tampilToast("Penyimpanan browser tidak tersedia. Coba lagi.", "error");
      }
    }),
  );
}
