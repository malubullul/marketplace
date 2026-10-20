document.addEventListener("DOMContentLoaded", async () => {
  await katalogSiap;
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
        ? PRODUK.slice(0, 6)
        : PRODUK.filter((p) => p.kategori === button.dataset.collection).slice(
            0,
            6,
          );
    panel.innerHTML = products.length
      ? products.map(renderKartuProduk).join("")
      : '<p class="collection-empty">Koleksi ini sedang disiapkan. Coba kategori lainnya.</p>';
    const note = document.getElementById("collection-note");
    if (note)
      note.textContent = `${products.length} pilihan · ${button.textContent.trim()}`;
    window.dispatchEvent(new Event("store:products"));
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
  if (el) el.innerHTML = PRODUK.slice(0, 6).map(renderKartuProduk).join("");
}
function renderRekomendasi() {
  const el = document.getElementById("grid-rekomendasi");
  if (el) el.innerHTML = getProdukRekomendasi().map(renderKartuProduk).join("");
}
function renderKartuProduk(p) {
  const saved = isInWishlist(p.id);
  const stock =
    p.stok === 0 ? "Stok habis" : p.stok < 5 ? `Tersisa ${p.stok}` : "Tersedia";
  return `<article class="kartu-produk" data-ui data-produk-id="${p.id}"><div class="kartu-produk-gambar"><a href="detail.html?id=${p.id}" aria-label="Lihat ${h(p.nama)}"><img src="${productImage(p.gambar)}" alt="${h(p.nama)}" width="600" height="600" loading="lazy"></a>${p.label ? `<span class="kartu-label">${h(p.label)}</span>` : ""}<button aria-label="${saved ? "Hapus" : "Simpan"} ${h(p.nama)} ${saved ? "dari" : "ke"} wishlist" aria-pressed="${saved}" class="btn-wishlist ${saved ? "aktif" : ""}" data-wishlist="${p.id}" onclick="toggleWishlist(${p.id})">${wishlistIcon(saved)}</button><button class="btn-keranjang-cepat" onclick="tambahCepat(${p.id})" ${p.stok === 0 ? "disabled" : ""}>${p.stok === 0 ? "Stok habis" : "Pilih produk ↗"}</button></div><div class="kartu-produk-info"><div class="product-meta"><span>${h(p.brand)}</span><span>${stock}</span></div><a class="kartu-produk-nama" href="detail.html?id=${p.id}">${h(p.nama)}</a><div class="kartu-harga"><span class="harga-sekarang">${formatHarga(p.harga)}</span>${p.hargaAsli > p.harga ? `<span class="harga-asli">${formatHarga(p.hargaAsli)}</span>` : ""}</div></div></article>`;
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

async function tambahCepat(id) {
  const product = getProdukById(id);
  if (product?.ukuran?.length || product?.warna?.length) {
    location.href = "detail.html?id=" + id;
    return;
  }
  tambahKeKeranjang(id, 1);
}
