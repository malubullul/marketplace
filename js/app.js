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
function renderProductGallery(p, detail = false) {
  const photos = [...new Set((Array.isArray(p.gambarList) && p.gambarList.length ? p.gambarList : [p.gambar]).map(productImage))];
  const multiple = photos.length > 1;
  const image = `<img class="product-gallery-image" ${detail ? 'id="gambar-utama"' : 'width="600" height="600" loading="lazy"'} src="${photos[0]}" alt="${h(p.nama)} — foto 1 dari ${photos.length}" draggable="false">`;
  const chevron = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.4" aria-hidden="true"><path d="m9 5 7 7-7 7"/></svg>';
  return `<div class="product-gallery${detail ? ' product-gallery-detail' : ''}" data-product-gallery data-product-photos="${h(JSON.stringify(photos))}" data-product-name="${h(p.nama)}" data-photo-index="0" role="group" aria-label="Foto ${h(p.nama)}"${multiple ? ' aria-roledescription="carousel"' : ''}>
    <div class="product-photo-stage${detail ? ' galeri-utama' : ''}" data-product-photo-stage>
      ${detail ? image : `<a class="product-photo-link" href="detail.html?id=${p.id}" aria-label="Lihat ${h(p.nama)}">${image}</a>`}
      ${multiple ? `<button class="product-photo-arrow product-photo-previous" type="button" data-product-photo-move="-1" aria-label="Foto sebelumnya untuk ${h(p.nama)}">${chevron}</button><button class="product-photo-arrow product-photo-next" type="button" data-product-photo-move="1" aria-label="Foto berikutnya untuk ${h(p.nama)}">${chevron}</button>
        <span class="product-photo-counter${detail ? '' : ' product-photo-counter-card'}" data-ui aria-hidden="true"><span data-product-photo-current>1</span> / ${photos.length}</span>
        <span class="product-gallery-status" role="status" aria-live="polite" aria-atomic="true"></span>` : ''}
    </div>
    ${detail && multiple ? `<div class="galeri-thumb">${photos.map((photo,i) => `<button type="button" class="galeri-thumb-item${i===0 ? ' aktif' : ''}" data-product-photo-index="${i}" aria-label="Lihat foto ${i+1} dari ${photos.length}: ${h(p.nama)}" aria-pressed="${i===0}"><img src="${photo}" alt="" loading="lazy" draggable="false"></button>`).join('')}</div>` : ''}
  </div>`;
}
function renderKartuProduk(p) {
  const saved = isInWishlist(p.id);
  const stock =
    p.stok === 0 ? "Stok habis" : p.stok < 5 ? `Tersisa ${p.stok}` : "Tersedia";
  return `<article class="kartu-produk" data-ui data-produk-id="${p.id}"><div class="kartu-produk-gambar">${renderProductGallery(p)}${p.label ? `<span class="kartu-label">${h(p.label)}</span>` : ""}<button aria-label="${saved ? "Hapus" : "Simpan"} ${h(p.nama)} ${saved ? "dari" : "ke"} wishlist" aria-pressed="${saved}" class="btn-wishlist ${saved ? "aktif" : ""}" data-wishlist="${p.id}" onclick="toggleWishlist(${p.id})">${wishlistIcon(saved)}</button><button class="btn-keranjang-cepat" onclick="tambahCepat(${p.id})" ${p.stok === 0 ? "disabled" : ""}>${p.stok === 0 ? "Stok habis" : "Pilih produk ↗"}</button></div><div class="kartu-produk-info"><div class="product-meta"><span>${h(p.brand)}</span><span>${stock}</span></div><a class="kartu-produk-nama" href="detail.html?id=${p.id}">${h(p.nama)}</a><div class="kartu-harga"><span class="harga-sekarang">${formatHarga(p.harga)}</span>${p.hargaAsli > p.harga ? `<span class="harga-asli">${formatHarga(p.hargaAsli)}</span>` : ""}</div><div class="product-rating-line"><span>${p.metrics_ready === false ? "Rating belum tersedia" : p.ulasan ? `${renderBintang(p.rating)} <span>${p.rating.toFixed(1)} (${p.ulasan})</span>` : "Belum ada rating"}</span><span>${p.metrics_ready === false ? "—" : p.terjual.toLocaleString("id-ID")} terjual</span></div></div></article>`;
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

// Delegated controls also cover cards re-rendered by filters, search and wishlist.
(() => {
  const galleries = new WeakMap();
  const cache = new Map();
  let gesture = null;
  function stateFor(gallery) {
    if (!galleries.has(gallery)) {
      galleries.set(gallery, {photos: JSON.parse(gallery.dataset.productPhotos), index: 0, requested: 0, serial: 0, suppressUntil: 0});
    }
    return galleries.get(gallery);
  }
  function loadPhoto(src) {
    if (!cache.has(src)) {
      cache.set(src, new Promise((resolve, reject) => {
        const photo = new Image();
        const failed = () => { cache.delete(src); reject(new Error('image')); };
        photo.onload = () => photo.decode().then(() => resolve()).catch(failed);
        photo.onerror = failed;
        photo.src = src;
      }));
    }
    return cache.get(src);
  }
  async function showPhoto(gallery, index) {
    const state = stateFor(gallery);
    if (state.photos.length < 2) return;
    const next = (index + state.photos.length) % state.photos.length;
    state.requested = next;
    const request = ++state.serial;
    const stage = gallery.querySelector('[data-product-photo-stage]');
    if (next === state.index) { stage.removeAttribute('aria-busy'); return; }
    stage.setAttribute('aria-busy', 'true');
    try {
      await loadPhoto(productImage(state.photos[next]));
      if (request !== state.serial || !gallery.isConnected) return;
      const image = gallery.querySelector('.product-gallery-image');
      image.src = productImage(state.photos[next]);
      image.alt = `${gallery.dataset.productName} — foto ${next + 1} dari ${state.photos.length}`;
      if (!matchMedia('(prefers-reduced-motion: reduce)').matches && image.animate)
        image.animate([{opacity: .45}, {opacity: 1}], {duration: 180, easing: 'ease-out'});
      state.index = next;
      gallery.dataset.photoIndex = String(next);
      gallery.querySelectorAll('[data-product-photo-index]').forEach((button, i) => {
        button.classList.toggle('aktif', i === next);
        button.setAttribute('aria-pressed', String(i === next));
      });
      const count = gallery.querySelector('[data-product-photo-current]');
      if (count) count.textContent = String(next + 1);
      gallery.querySelector('.product-gallery-status').textContent = `Foto ${next + 1} dari ${state.photos.length}: ${gallery.dataset.productName}.`;
    } catch {
      if (request !== state.serial) return;
      state.requested = state.index;
      const message = 'Foto belum dapat dimuat. Coba lagi; foto sebelumnya tetap tersedia.';
      gallery.querySelector('.product-gallery-status').textContent = message;
      if (typeof tampilToast === 'function') tampilToast(message, 'error');
    } finally {
      if (request === state.serial) stage.removeAttribute('aria-busy');
    }
  }
  document.addEventListener('click', (event) => {
    const gallery = event.target.closest('[data-product-gallery]');
    if (!gallery) return;
    const state = stateFor(gallery);
    // A horizontal gesture must never accidentally follow the product link.
    if (event.target.closest('.product-photo-link') && performance.now() < state.suppressUntil) {
      event.preventDefault();
      event.stopPropagation();
      return;
    }
    const move = event.target.closest('[data-product-photo-move]');
    const thumbnail = event.target.closest('[data-product-photo-index]');
    if (move || thumbnail) {
      event.preventDefault();
      showPhoto(gallery, thumbnail ? Number(thumbnail.dataset.productPhotoIndex) : state.requested + Number(move.dataset.productPhotoMove));
    }
  }, true);
  document.addEventListener('keydown', (event) => {
    const gallery = event.target.closest('[data-product-gallery]');
    if (!gallery || event.altKey || event.ctrlKey || event.metaKey || event.shiftKey) return;
    const state = stateFor(gallery);
    if (state.photos.length < 2) return;
    if (!['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key)) return;
    event.preventDefault();
    const next = event.key === 'Home' ? 0 : event.key === 'End' ? state.photos.length - 1
      : state.requested + (event.key === 'ArrowRight' ? 1 : -1);
    showPhoto(gallery, next);
  });
  document.addEventListener('pointerdown', (event) => {
    gesture = null;
    if (event.pointerType === 'mouse' || !event.isPrimary || event.target.closest('button')) return;
    const stage = event.target.closest('[data-product-photo-stage]');
    if (!stage) return;
    const gallery = stage.closest('[data-product-gallery]');
    if (stateFor(gallery).photos.length < 2) return;
    gesture = {gallery, id: event.pointerId, x: event.clientX, y: event.clientY};
  });
  document.addEventListener('pointerup', (event) => {
    if (!gesture || gesture.id !== event.pointerId) return;
    const {gallery, x, y} = gesture;
    gesture = null;
    const dx = event.clientX - x, dy = event.clientY - y;
    if (Math.abs(dx) < 35 || Math.abs(dx) < Math.abs(dy) * 1.5) return;
    const state = stateFor(gallery);
    state.suppressUntil = performance.now() + 500;
    showPhoto(gallery, state.requested + (dx < 0 ? 1 : -1));
  });
  document.addEventListener('pointercancel', () => { gesture = null; });
})();
