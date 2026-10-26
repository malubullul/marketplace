const $ = (id) => document.getElementById(id);
const esc = (value) =>
  String(value ?? "").replace(
    /[&<>"']/g,
    (c) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[
        c
      ],
  );
const money = (value) => "Rp " + Number(value).toLocaleString("id-ID");
let csrf = "",
  products = [],
  orders = [],
  editing = null,
  photos = [],
  uploading = false,
  dirty = false,
  activePage = "products";
const categoryNames = {
  apparel: "Apparel",
  sneakers: "Sneakers",
  essentials: "Essentials",
};
const statusNames = {
  baru: "Menunggu pembayaran",
  diproses: "Diproses",
  dikirim: "Dikirim",
  selesai: "Selesai",
  dibatalkan: "Dibatalkan",
};
async function api(path, options = {}) {
  const headers = { ...options.headers };
  if (options.method && options.method !== "GET")
    headers["X-CSRF-Token"] = csrf;
  if (options.body && !(options.body instanceof FormData)) {
    headers["Content-Type"] = "application/json";
    options.body = JSON.stringify(options.body);
  }
  const response = await fetch(path, {
    ...options,
    headers,
    cache: "no-store",
  });
  const data = await response
    .json()
    .catch(() => ({ error: "Server tidak merespons. Coba lagi." }));
  if (!response.ok) {
    if (response.status === 401 && path !== "/api/login") {
      showLogin();
      await sessionInfo();
    }
    throw new Error(data.error || "Permintaan gagal.");
  }
  return data;
}
function message(text, error = false) {
  $("dashboard-message").hidden = false;
  $("dashboard-message").textContent = text;
  $("dashboard-message").classList.toggle("error", error);
}
function showLogin() {
  $("login-view").hidden = false;
  $("dashboard").hidden = true;
}
async function sessionInfo() {
  try {
    const state = await api("/api/session");
    csrf = state.csrf;
    $("setup-notice").hidden = state.configured;
    $("login-form").hidden = !state.configured;
    if (state.authenticated) {
      await openDashboard(state.email);
    } else showLogin();
  } catch (error) {
    showLogin();
    $("login-error").textContent =
      "Server Anredseller belum dapat diakses. Jalankan server lalu muat ulang halaman.";
  }
}
async function openDashboard(email) {
  $("owner-email").textContent = email;
  $("login-view").hidden = true;
  $("dashboard").hidden = false;
  await refresh();
  showPage(["products", "orders", "settings", "appearance", "socials", "promos"].includes(location.hash.slice(1)) ? location.hash.slice(1) : "products");
}
async function refresh() {
  try {
    const [catalog, incoming, contactData] = await Promise.all([
      api("/api/admin/products"),
      api("/api/admin/orders"),
      api("/api/admin/contacts"),
    ]);
    products = catalog.products;
    orders = incoming.orders;
    $("payment-whatsapp").value = contactData.contacts.payment_whatsapp;
    $("support-whatsapp").value = contactData.contacts.support_whatsapp;
    renderProducts();
    renderOrders();
    renderStats();
  } catch (error) {
    message(error.message, true);
  }
}
function renderStats() {
  $("stat-products").textContent = products.length;
  $("stat-published").textContent = products.filter((p) => p.published).length;
  $("stat-low").textContent = products.filter((p) => p.stok < 5).length;
  $("stat-orders").textContent = orders.filter(
    (o) => o.status === "baru",
  ).length;
  $("nav-count").textContent = products.length;
  $("orders-count").textContent = orders.filter(
    (o) => o.status === "baru",
  ).length;
}
function renderProducts() {
  const query = $("product-search").value.trim().toLowerCase(),
    filter = $("product-filter").value;
  const list = products.filter(
    (p) =>
      (!query || (p.nama + " " + p.brand).toLowerCase().includes(query)) &&
      (filter === "all" ||
        (filter === "published" && p.published) ||
        (filter === "draft" && !p.published) ||
        (filter === "low" && p.stok < 5)),
  );
  $("product-rows").innerHTML = list
    .map(
      (p) =>
        `<tr><td><div class="product-identity"><img src="${esc(p.gambar)}" alt="${esc(p.nama)}"><div><strong>${esc(p.nama)}</strong><small>${categoryNames[p.kategori] || esc(p.kategori)}${p.demo ? " · Contoh" : ""}</small></div></div></td><td data-label="Harga jual">${money(p.harga)}</td><td data-label="Total stok"><span class="${p.stok < 5 ? "badge low" : ""}">${p.stok} pcs</span></td><td data-label="Status"><span class="badge ${p.published ? "published" : ""}">${p.published ? "Terbit" : "Draf"}</span></td><td><div class="row-actions"><button data-edit="${p.id}" aria-label="Edit ${esc(p.nama)}">Edit</button><button class="delete-product" data-delete="${p.id}" aria-label="Hapus ${esc(p.nama)}">Hapus</button></div></td></tr>`,
    )
    .join("");
  $("products-empty").hidden = list.length > 0;
}
function renderOrders() {
  $("order-rows").innerHTML = orders
    .map(
      (order) =>
        `<tr><td><strong>${esc(order.nomor)}</strong><div class="order-meta">${new Date(order.created_at * 1000).toLocaleString("id-ID")}</div></td><td data-label="Pelanggan">${esc(order.nama_penerima || order.nama)}<div class="order-meta">${order.items.reduce((sum, line) => sum + line.jumlah, 0)} item</div></td><td data-label="Total">${money(order.total)}</td><td data-label="Status"><select class="order-status-select" data-order-status="${esc(order.nomor)}" aria-label="Status ${esc(order.nomor)}" ${["dibatalkan", "selesai"].includes(order.status) ? "disabled" : ""}>${Object.entries(
          statusNames,
        )
          .map(
            ([key, label]) =>
              `<option value="${key}" ${order.status === key ? "selected" : ""}>${label}</option>`,
          )
          .join(
            "",
          )}</select></td><td><div class="row-actions"><button data-order="${esc(order.nomor)}">Lihat pesanan</button></div></td></tr>`,
    )
    .join("");
  $("orders-empty").hidden = orders.length > 0;
}
function scrollActiveNavigation() {
  const navigation = document.querySelector(".sidebar nav");
  const active = navigation.querySelector(".nav-button.active");
  if (active && navigation.scrollWidth > navigation.clientWidth + 1)
    navigation.scrollLeft = Math.max(0, active.offsetLeft - navigation.offsetLeft - 10);
}
window.addEventListener("resize", scrollActiveNavigation);
function showPage(name) {
  activePage = name;
  history.replaceState({}, "", "#" + name);
  document.querySelector(".stats").hidden = !["products", "orders"].includes(name);
  $("products-page").hidden = name !== "products";
  $("orders-page").hidden = name !== "orders";
  $("settings-page").hidden = name !== "settings";
  $("appearance-page").hidden = name !== "appearance";
  $("socials-page").hidden = name !== "socials";
  $("promos-page").hidden = name !== "promos";
  if (name === "promos") loadPromos();
  if (["appearance", "socials"].includes(name) && !siteContentState) loadSiteSettings();
  $("page-breadcrumb").textContent =
    {products: "KOLEKSI", orders: "PESANAN", settings: "KONTAK WHATSAPP", appearance: "TAMPILAN TOKO", socials: "MEDIA SOSIAL", promos: "KODE PROMO"}[name];
  document
    .querySelectorAll("[data-page]")
    .forEach((button) =>
      button.classList.toggle("active", button.dataset.page === name),
    );
  scrollActiveNavigation();
}
function productError(text) {
  const error = $("product-error");
  error.hidden = !text;
  error.textContent = text;
  if (text) error.focus();
}
function renderPhotos() {
  $("photo-count").textContent = `${photos.length} dari 8 foto${photos.length ? ' · foto pertama menjadi sampul' : ''}`;
  $("photo-grid").innerHTML = photos
    .map(
      (url, index) =>
        `<div class="photo-item"><img src="${esc(url)}" alt="Foto produk ${index + 1}">${index === 0 ? '<span class="cover-tag">Sampul</span>' : ""}<div class="photo-actions">${index > 0 ? `<button type="button" data-cover="${index}">Jadikan sampul</button>` : "<span></span>"}<button type="button" data-remove-photo="${index}" aria-label="Hapus foto ${index + 1}">Hapus</button></div></div>`,
    )
    .join("");
}
function openEditor(product = null) {
  editing = product;
  photos = product ? [...product.gambarList] : [];
  $("product-form").reset();
  productError("");
  $("editor-title").textContent = product ? "Edit produk" : "Tambah produk";
  $("editor-status").textContent = product
    ? product.published
      ? "Saat ini: Terbit"
      : "Saat ini: Draf"
    : "Produk baru";
  const fields = {
    "product-name": "nama",
    "product-category": "kategori",
    "product-brand": "brand",
    "product-description": "deskripsi",
    "product-price": "harga",
    "product-old-price": "hargaAsli",
    "product-stock": "stok",
    "product-label": "label",
    "product-material": "bahan",
    "product-care": "perawatan",
  };
  for (const [id, key] of Object.entries(fields)) {
    if (product) $(id).value = product[key] ?? "";
  }
  if (product) {
    $("product-sizes").value = (product.ukuran || []).join(", ");
    $("product-colors").value = (product.warna || []).join(", ");
    $("product-featured").checked = product.trending;
    $("product-recommended").checked = product.rekomendasi;
  }
  $("upload-status").textContent = "";
  renderPhotos();
  dirty = false;
  $("product-dialog").showModal();
  $("product-name").focus();
}
function closeEditor() {
  if (uploading) {
    productError("Tunggu hingga unggahan foto selesai.");
    return;
  }
  if (dirty && !confirm("Perubahan belum disimpan. Tutup editor?")) return;
  $("product-dialog").close();
}
async function uploadFiles(fileList) {
  const files = [...fileList];
  if (!files.length) return;
  if (photos.length + files.length > 8) {
    productError("Maksimal 8 foto per produk.");
    return;
  }
  if (files.some((file) => file.size > 4 * 1024 * 1024)) {
    productError("Ukuran setiap foto maksimal 4 MB.");
    return;
  }
  if (
    files.some(
      (file) => !["image/jpeg", "image/png", "image/webp"].includes(file.type),
    )
  ) {
    productError("Gunakan foto JPG, PNG, atau WebP.");
    return;
  }
  uploading = true;
  setSaving(true);
  productError("");
  try {
    for (let i = 0; i < files.length; i++) {
      $("upload-status").textContent =
        `Mengunggah foto ${i + 1} dari ${files.length}…`;
      const form = new FormData();
      form.append("photo", files[i]);
      const response = await api("/api/admin/uploads", {
        method: "POST",
        body: form,
      });
      photos.push(response.url);
      dirty = true;
      renderPhotos();
    }
    $("upload-status").textContent = "Foto berhasil diunggah.";
  } catch (error) {
    productError(error.message);
    $("upload-status").textContent =
      "Unggahan belum selesai. Foto yang berhasil tetap tersimpan.";
  } finally {
    uploading = false;
    setSaving(false);
    $("product-photos").value = "";
  }
}
function setSaving(value) {
  $("product-form")
    .querySelectorAll('button[type="submit"]')
    .forEach((button) => (button.disabled = value));
  $("product-photos").disabled = value;
}
const splitOptions = (value) => [
  ...new Set(
    value
      .split(",")
      .map((value) => value.trim())
      .filter(Boolean),
  ),
];
$("product-form").addEventListener("input", () => (dirty = true));
$("product-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  if (uploading) return;
  productError("");
  if (!photos.length) {
    productError("Unggah minimal satu foto produk.");
    return;
  }
  const price = Number($("product-price").value),
    oldPrice = Number($("product-old-price").value) || price;
  if (oldPrice < price) {
    productError(
      "Harga sebelum diskon tidak boleh lebih kecil dari harga jual.",
    );
    return;
  }
  const product = {
    nama: $("product-name").value,
    kategori: $("product-category").value,
    brand: $("product-brand").value,
    deskripsi: $("product-description").value,
    harga: price,
    hargaAsli: oldPrice,
    stok: Number($("product-stock").value),
    ukuran: splitOptions($("product-sizes").value),
    warna: splitOptions($("product-colors").value),
    bahan: $("product-material").value,
    perawatan: $("product-care").value,
    label: $("product-label").value,
    trending: $("product-featured").checked,
    rekomendasi: $("product-recommended").checked,
    gambarList: photos,
    published: event.submitter?.value === "publish",
  };
  if (editing) product.version = editing.version;
  setSaving(true);
  try {
    await api("/api/admin/products" + (editing ? "/" + editing.id : ""), {
      method: editing ? "PUT" : "POST",
      body: product,
    });
    dirty = false;
    $("product-dialog").close();
    message(
      product.published
        ? "Produk berhasil diterbitkan. Pengunjung sekarang bisa melihatnya di katalog."
        : "Draf tersimpan. Produk ini belum ditampilkan di katalog publik.",
    );
    await refresh();
  } catch (error) {
    productError(error.message);
  } finally {
    setSaving(false);
  }
});
$("login-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  $("login-error").textContent = "";
  $("login-button").disabled = true;
  try {
    const result = await api("/api/login", {
      method: "POST",
      body: {
        email: $("login-email").value,
        password: $("login-password").value,
      },
    });
    csrf = result.csrf;
    $("login-password").value = "";
    await openDashboard(result.email);
  } catch (error) {
    $("login-error").textContent = error.message;
  } finally {
    $("login-button").disabled = false;
  }
});
$("logout-button").addEventListener("click", async () => {
  try {
    await api("/api/logout", { method: "POST" });
    showLogin();
    await sessionInfo();
  } catch (error) {
    message(error.message, true);
  }
});
$("add-product").addEventListener("click", () => openEditor());
$("product-search").addEventListener("input", renderProducts);
$("product-filter").addEventListener("change", renderProducts);
$("refresh-products").addEventListener("click", refresh);
$("refresh-orders").addEventListener("click", refresh);
$("product-photos").addEventListener("change", (event) =>
  uploadFiles(event.target.files),
);
$("upload-zone").addEventListener("dragover", (event) => {
  event.preventDefault();
  $("upload-zone").classList.add("dragging");
});
$("upload-zone").addEventListener("dragleave", () =>
  $("upload-zone").classList.remove("dragging"),
);
$("upload-zone").addEventListener("drop", (event) => {
  event.preventDefault();
  $("upload-zone").classList.remove("dragging");
  if (!uploading) uploadFiles(event.dataTransfer.files);
});
$("close-editor").addEventListener("click", closeEditor);
$("product-dialog").addEventListener("cancel", (event) => {
  event.preventDefault();
  closeEditor();
});
$("close-order").addEventListener("click", () => $("order-dialog").close());
document.addEventListener("click", async (event) => {
  const edit = event.target.closest("[data-edit]");
  if (edit)
    openEditor(products.find((p) => p.id === Number(edit.dataset.edit)));
  const deletion = event.target.closest("[data-delete]");
  if (deletion) {
    const product = products.find(
      (p) => p.id === Number(deletion.dataset.delete),
    );
    if (
      !confirm(
        `Hapus produk "${product.nama}"? Pesanan yang sudah tercatat tetap tersimpan.`,
      )
    )
      return;
    try {
      await api("/api/admin/products/" + product.id, { method: "DELETE" });
      message("Produk dihapus dari katalog.");
      await refresh();
    } catch (error) {
      message(error.message, true);
    }
  }
  const remove = event.target.closest("[data-remove-photo]");
  if (remove && !uploading) {
    photos.splice(Number(remove.dataset.removePhoto), 1);
    dirty = true;
    renderPhotos();
  }
  const cover = event.target.closest("[data-cover]");
  if (cover && !uploading) {
    photos.unshift(photos.splice(Number(cover.dataset.cover), 1)[0]);
    dirty = true;
    renderPhotos();
  }
  const nav = event.target.closest("[data-page]");
  if (nav) showPage(nav.dataset.page);
  if (event.target.closest("[data-open-products]")) showPage("products");
  const orderButton = event.target.closest("[data-order]");
  if (orderButton)
    openOrder(orders.find((o) => o.nomor === orderButton.dataset.order));
});
document.addEventListener("change", async (event) => {
  const select = event.target.closest("[data-order-status]");
  if (!select) return;
  const order = orders.find((o) => o.nomor === select.dataset.orderStatus),
    value = select.value;
  if (
    value === "dibatalkan" &&
    !confirm("Batalkan pesanan ini dan kembalikan stok produk?")
  ) {
    select.value = order.status;
    return;
  }
  if (order.status === "baru" && ["diproses", "dikirim", "selesai"].includes(value) &&
      !confirm("Sudah memeriksa transfer pelanggan? Lanjutkan hanya setelah pembayaran dikonfirmasi.")) {
    select.value = order.status;
    return;
  }
  select.disabled = true;
  try {
    await api("/api/admin/orders/" + order.nomor, {
      method: "PATCH",
      body: { status: value },
    });
    message("Status pesanan diperbarui.");
    await refresh();
  } catch (error) {
    select.value = order.status;
    message(error.message, true);
  } finally {
    select.disabled = ["selesai", "dibatalkan"].includes(order.status);
  }
});
function openOrder(order) {
  $("order-details").innerHTML =
    `<span class="eyebrow">RINCIAN PESANAN</span><h2 id="order-title">${esc(order.nomor)}</h2><span class="badge new">${statusNames[order.status]}</span><div class="order-info"><div><span>Penerima</span><strong>${esc(order.nama_penerima || order.nama)}</strong></div><div><span>Email / Nomor HP</span><strong>${esc(order.email)} / ${esc(order.nohp)}</strong></div><div><span>Alamat pengiriman</span><strong>${esc(order.alamat)}, ${esc(order.kota)}, ${esc(order.provinsi)} ${esc(order.kodepos)}</strong></div><div><span>Catatan pelanggan</span><strong>${esc(order.catatan) || "Tidak ada catatan"}</strong></div><div><span>Pembayaran</span><strong>Transfer dibantu lewat WhatsApp pembayaran</strong></div>${order.promo ? `<div><span>Kode promo / Partner</span><strong>${esc(order.promo.code)}${order.promo.partner ? " / " + esc(order.promo.partner) : ""}</strong></div>` : ""}</div><div class="order-items">${order.items.map((item) => `<div class="order-item"><img src="${esc(item.gambar)}" alt="${esc(item.nama)}"><div><strong>${esc(item.nama)}</strong><small>${esc([item.ukuran, item.warna].filter(Boolean).join(" / "))} · ${item.jumlah} pcs</small></div><span>${money(item.harga * item.jumlah)}</span></div>`).join("")}</div><div class="order-info"><div><span>Subtotal / Ongkir / Diskon</span><strong>${money(order.subtotal)} / ${money(order.ongkir)} / −${money(order.diskon)}</strong></div></div><div class="order-total">Total ${money(order.total)}</div>`;
  $("order-dialog").showModal();
}
async function initializePortal() {
  try {
    const config = await api('/portal-config');
    if (config.shop_url) {
      document.querySelectorAll('[data-store-link]').forEach((link) => {
        link.href = config.shop_url;
      });
    }
  } catch (error) {
    // Session errors below provide the connection status to the owner.
  }
  await sessionInfo();
}
initializePortal();

$("contacts-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const result = $("contacts-result"), button = $("save-contacts");
  result.hidden = true;
  button.disabled = true;
  try {
    const data = await api("/api/admin/contacts", {method: "PUT", body: {
      payment_whatsapp: $("payment-whatsapp").value,
      support_whatsapp: $("support-whatsapp").value,
    }});
    $("payment-whatsapp").value = data.contacts.payment_whatsapp;
    $("support-whatsapp").value = data.contacts.support_whatsapp;
    result.textContent = "Kontak tersimpan. Tautan WhatsApp di toko mengikuti nomor ini.";
    result.className = "notice";
  } catch (error) {
    result.textContent = error.message;
    result.className = "notice error";
  } finally {
    result.hidden = false;
    button.disabled = false;
  }
});

// Public presentation settings use the same authenticated backend as products.
let siteContentState = null, siteSlots = [], sitePlatforms = [], siteLoading = false;
let siteUploading = false, siteSaving = false;
const siteDirty = { images: false, socials: false };
function siteResult(section, text, error = false) {
  const result = $("site-" + section + "-result");
  result.textContent = text;
  result.className = "notice" + (error ? " error" : "");
  result.hidden = !text;
}
function siteButtons() {
  document.querySelectorAll('#site-images-form input,#site-socials-form input').forEach(input => {
    input.disabled = !siteContentState || siteUploading || siteSaving || siteLoading;
  });
  for (const id of ["save-site-images", "save-site-images-bottom", "save-site-socials"])
    $(id).disabled = !siteContentState || siteUploading || siteSaving || siteLoading;
  document.querySelectorAll('[data-site-upload],[data-site-remove],[data-site-restore]').forEach(button => {
    button.disabled = siteUploading || siteSaving || (button.hasAttribute('data-site-remove') && !siteContentState?.images[button.dataset.siteRemove].src);
  });
}
async function loadSiteSettings(force = false) {
  if (siteLoading || siteUploading || siteSaving) return;
  if (force && (siteDirty.images || siteDirty.socials) && !confirm("Muat ulang pengaturan dan batalkan perubahan gambar/media sosial yang belum disimpan?")) return;
  siteLoading = true;siteButtons();
  try {
    const data = await api("/api/admin/content");
    siteContentState = data.content;siteSlots = data.slots;sitePlatforms = data.platforms;
    siteDirty.images = siteDirty.socials = false;
    renderSiteImages();renderSiteSocials();
    siteResult("images", "");siteResult("socials", "");
  } catch (error) {message(error.message, true);}
  finally {siteLoading = false;siteButtons();}
}
function renderSiteImages() {
  $("site-image-settings").innerHTML = siteSlots.map(slot => {
    const image = siteContentState.images[slot.id];
    return `<article class="site-photo-setting" data-site-slot="${slot.id}"><div class="site-photo-preview${slot.id === 'account_editorial' ? ' account-photo-preview' : ''}">${image.src ? `<img src="${esc(image.src)}" alt="${esc(image.alt)}" style="object-position:${image.position}% center">` : '<span>Foto tidak ditampilkan</span>'}</div><div class="site-photo-fields"><h3>${esc(slot.label)}</h3><div class="site-photo-actions"><button type="button" class="button secondary" data-site-upload="${slot.id}">${image.src ? 'Ganti foto' : 'Unggah foto'}</button><input type="file" id="site-file-${slot.id}" data-site-file="${slot.id}" accept="image/jpeg,image/png,image/webp" hidden><button type="button" class="settings-text-link" data-site-remove="${slot.id}"${!image.src ? ' disabled' : ''}>Hapus dari tampilan</button><button type="button" class="settings-text-link" data-site-restore="${slot.id}">Pakai gambar awal</button></div><label for="site-alt-${slot.id}">Deskripsi gambar</label><input type="text" id="site-alt-${slot.id}" data-site-alt="${slot.id}" maxlength="240" value="${esc(image.alt)}"><label for="site-position-${slot.id}">Fokus gambar: <output id="site-focus-${slot.id}">${image.position}%</output></label><div class="site-focus-control"><span>Kiri</span><input id="site-position-${slot.id}" type="range" min="0" max="100" value="${image.position}" data-site-position="${slot.id}" aria-label="Fokus ${esc(slot.label)}"><span>Kanan</span></div></div></article>`;
  }).join("");
}
function renderSiteSocials() {
  const socials = siteContentState.socials;
  $("site-social-settings").innerHTML = `<div class="site-social-grid">${sitePlatforms.map(platform => `<div><label for="site-social-${platform.id}">${esc(platform.label)}</label><input id="site-social-${platform.id}" name="${platform.id}" type="url" inputmode="url" maxlength="2048" placeholder="https://…" value="${esc(socials[platform.id])}" autocomplete="off"></div>`).join("")}</div><div class="site-other-social"><h3>Tautan lainnya</h3><p>Untuk akun atau halaman lain, misalnya Linktree atau Pinterest.</p><label for="site-social-other_label">Nama yang tampil di footer</label><input id="site-social-other_label" name="other_label" maxlength="40" value="${esc(socials.other_label)}" placeholder="Contoh: Pinterest"><label for="site-social-other_url">Tautan HTTPS</label><input id="site-social-other_url" name="other_url" type="url" inputmode="url" maxlength="2048" value="${esc(socials.other_url)}" placeholder="https://…" autocomplete="off"></div>`;
}
async function saveSiteSection(section, event) {
  event.preventDefault();
  if (!siteContentState || siteUploading || siteSaving) return;
  const value = section === "images" ? structuredClone(siteContentState.images) : Object.fromEntries([...sitePlatforms.map(p => p.id),"other_label","other_url"].map(key => [key,$("site-social-"+key).value]));
  siteSaving = true;siteButtons();siteResult(section, "");
  try {
    const data = await api("/api/admin/content", {method:"PUT", body:{section, version:siteContentState.version, [section]:value}});
    siteContentState.version = data.content.version;
    siteContentState[section] = data.content[section];siteDirty[section] = false;
    siteResult(section, section === "images" ? "Gambar tersimpan. Muat ulang toko publik untuk melihat perubahan." : "Media sosial tersimpan. Tautan yang terisi kini tampil di footer toko publik.");
  } catch (error) {siteResult(section, error.message, true);}
  finally {siteSaving = false;siteButtons();}
}
$("site-images-form").addEventListener("submit", event => saveSiteSection("images",event));
$("site-socials-form").addEventListener("submit", event => saveSiteSection("socials",event));
$("site-socials-form").addEventListener("input", () => {siteDirty.socials = true;siteResult("socials","Perubahan belum disimpan.");});
$("site-images-form").addEventListener("input", event => {
  if (!siteContentState || siteSaving) return;
  const alt = event.target.dataset.siteAlt, position = event.target.dataset.sitePosition;
  if (alt) siteContentState.images[alt].alt = event.target.value;
  if (position) {
    const value = Number(event.target.value);siteContentState.images[position].position = value;
    $("site-focus-"+position).textContent = value+"%";
    document.querySelector(`[data-site-slot="${position}"] img`)?.style.setProperty("object-position",value+"% center");
  }
  if (alt || position) {siteDirty.images = true;siteResult("images","Perubahan belum disimpan.");}
});
document.addEventListener("click", event => {
  if (event.target.closest("[data-reload-content]")) loadSiteSettings(true);
  if (!siteContentState || siteUploading || siteSaving) return;
  const upload = event.target.closest("[data-site-upload]");
  if (upload) $("site-file-"+upload.dataset.siteUpload).click();
  const remove = event.target.closest("[data-site-remove]"), restore = event.target.closest("[data-site-restore]");
  if (remove || restore) {
    const key = remove ? remove.dataset.siteRemove : restore.dataset.siteRestore;
    if (remove) siteContentState.images[key].src = "";
    else siteContentState.images[key] = structuredClone(siteSlots.find(slot => slot.id === key).default_image);
    siteDirty.images = true;renderSiteImages();siteButtons();siteResult("images","Perubahan belum disimpan.");
  }
});
document.addEventListener("change", async event => {
  const key = event.target.dataset.siteFile;
  if (!key || !event.target.files.length || siteUploading || siteSaving) return;
  const file = event.target.files[0];event.target.value = "";
  if (!['image/jpeg','image/png','image/webp'].includes(file.type) || file.size > 4*1024*1024) {
    siteResult("images","Gunakan JPG, PNG, atau WebP maksimal 4 MB.",true);return;
  }
  siteUploading = true;siteButtons();siteResult("images","Mengunggah foto…");
  try {
    const form = new FormData();form.append("photo",file);
    const uploaded = await api("/api/admin/uploads",{method:"POST",body:form});
    siteContentState.images[key].src = uploaded.url;
    if (!siteContentState.images[key].alt.trim()) siteContentState.images[key].alt = siteSlots.find(slot => slot.id === key).label;
    siteDirty.images = true;renderSiteImages();siteResult("images","Foto berhasil diunggah. Simpan perubahan gambar untuk menerbitkannya.");
  } catch(error) {siteResult("images",error.message,true);}
  finally {siteUploading = false;siteButtons();}
});
window.addEventListener("beforeunload", event => {
  if (dirty || siteDirty.images || siteDirty.socials || siteUploading) {event.preventDefault();event.returnValue="";}
});

// Partner promotions share the store's database and owner session.
let promoList = [], editingPromo = null, promoSaving = false, promoLoadSerial = 0;
const promoDate = (seconds) => seconds === null ? "" : new Date(seconds * 1000 + 7 * 3600000).toISOString().slice(0,10);
function promoState(promo) {
  const now = Date.now() / 1000;
  if (!promo.active) return "Nonaktif";
  if (promo.expires_at !== null && now >= promo.expires_at) return "Kedaluwarsa";
  if (promo.starts_at !== null && now < promo.starts_at) return "Terjadwal";
  if (promo.usage_limit !== null && promo.used >= promo.usage_limit) return "Kuota habis";
  return "Aktif";
}
async function loadPromos() {
  const serial = ++promoLoadSerial;
  $("promo-list-status").textContent = "Memuat kode promo…";
  $("refresh-promos").disabled = true;
  try {
    const result = await api("/api/admin/promos");
    if (serial !== promoLoadSerial) return;
    promoList = result.promos;
    renderPromos();
  } catch (error) {
    if (serial === promoLoadSerial) $("promo-list-status").textContent = error.message + " Tekan Muat ulang untuk mencoba lagi.";
  } finally {
    if (serial === promoLoadSerial) $("refresh-promos").disabled = false;
  }
}
function renderPromos() {
  const query = $("promo-search").value.trim().toLowerCase();
  const list = promoList.filter(p => (p.code + " " + p.partner).toLowerCase().includes(query));
  $("promo-list-status").textContent = `${list.length} kode promo${query ? " ditemukan" : " tersimpan"}`;
  $("promos-empty").hidden = list.length > 0;
  $("promos-empty").querySelector("h2").textContent = query ? "Kode promo tidak ditemukan." : "Belum ada kode promo.";
  $("promo-rows").innerHTML = list.map(p => {
    const state = promoState(p);
    const dates = [p.starts_at === null ? "Mulai sekarang" : "Mulai " + promoDate(p.starts_at), p.expires_at === null ? "tanpa tanggal akhir" : "s.d. " + promoDate(p.expires_at)].join(" · ");
    return `<tr><td><strong>${esc(p.code)}</strong><small>${esc(p.partner) || "Promo toko"}</small></td><td data-label="Diskon" class="promo-number"><strong>${p.kind === "percent" ? p.value + "%" : money(p.value)}</strong><small>Min. ${money(p.min_subtotal)}${p.max_discount === null ? "" : " · maks. " + money(p.max_discount)}</small></td><td data-label="Kuota terpakai" class="promo-number">${p.used}${p.usage_limit === null ? " / tanpa batas" : " / " + p.usage_limit}<small>${p.per_customer_limit} kali per akun</small></td><td data-label="Pesanan selesai" class="promo-number">${p.completed}<small>${money(p.completed_sales)}</small></td><td data-label="Status"><span class="badge ${state === "Aktif" ? "published" : ""}">${state}</span><small>${esc(dates)} WIB</small></td><td><div class="row-actions"><button data-edit-promo="${esc(p.code)}" aria-label="Edit promo ${esc(p.code)}">Edit</button></div></td></tr>`;
  }).join("");
}
function updatePromoPreview() {
  const percent = $("promo-kind").value === "percent";
  $("promo-value-label").textContent = percent ? "Besar diskon (%)" : "Besar potongan (Rp)";
  $("promo-value").max = percent ? "100" : "10000000";
  $("promo-cap-label").hidden = !percent;
  $("promo-cap").disabled = !percent;
  const amount = Number($("promo-value").value);
  const description = percent ? amount + "%" : money(amount);
  const cap = percent && $("promo-cap").value ? ", maksimal " + money($("promo-cap").value) : "";
  $("promo-preview").textContent = `Diskon ${description}${cap}, minimal belanja ${money($("promo-min").value)}. ${$("promo-active").checked ? "Berlaku sesuai jadwal dan kuota setelah disimpan." : "Kode belum dapat dipakai sampai diaktifkan."}`;
}
function openPromo(promo = null) {
  editingPromo = promo;
  $("promo-form").reset();
  $("promo-title").textContent = promo ? "Edit kode promo" : "Buat kode promo";
  $("promo-error").textContent = "";
  const fields = {code:"code",partner:"partner",kind:"kind",value:"value",min:"min_subtotal",cap:"max_discount",limit:"usage_limit",person:"per_customer_limit"};
  for (const [id,key] of Object.entries(fields)) if (promo) $("promo-"+id).value = promo[key] ?? "";
  $("promo-code").readOnly = !!promo;
  $("promo-start").value = promo ? promoDate(promo.starts_at) : "";
  // Expires_at is exclusive midnight immediately after the chosen last valid date.
  $("promo-end").value = promo && promo.expires_at !== null ? promoDate(promo.expires_at - 1) : "";
  $("promo-active").checked = promo?.active || false;
  updatePromoPreview();
  $("promo-dialog").showModal();
}
function closePromo() { if (!promoSaving) $("promo-dialog").close(); }
$("add-promo").addEventListener("click", () => openPromo());
$("refresh-promos").addEventListener("click", loadPromos);
$("promo-search").addEventListener("input", renderPromos);
$("close-promo").addEventListener("click", closePromo);
$("cancel-promo").addEventListener("click", closePromo);
$("promo-dialog").addEventListener("cancel", event => { if (promoSaving) event.preventDefault(); });
$("promo-form").addEventListener("input", updatePromoPreview);
$("promo-rows").addEventListener("click", event => {
  const button = event.target.closest("[data-edit-promo]");
  if (button) openPromo(promoList.find(p => p.code === button.dataset.editPromo));
});
$("promo-form").addEventListener("submit", async event => {
  event.preventDefault();
  if (promoSaving) return;
  const integer = (id, optional = false) => $(id).value === "" && optional ? null : Number($(id).value);
  const date = (id, end = false) => !$(id).value ? null : Math.floor(Date.parse($(id).value + "T00:00:00+07:00") / 1000) + (end ? 86400 : 0);
  const payload = {
    code: $("promo-code").value.trim().toUpperCase(), partner: $("promo-partner").value.trim(),
    kind: $("promo-kind").value, value: integer("promo-value"), min_subtotal: integer("promo-min"),
    max_discount: $("promo-kind").value === "percent" ? integer("promo-cap",true) : null,
    starts_at: date("promo-start"), expires_at: date("promo-end",true),
    usage_limit: integer("promo-limit",true), per_customer_limit: integer("promo-person"),
    active: $("promo-active").checked, version: editingPromo?.version || "0"
  };
  promoSaving = true;
  $("promo-error").textContent = "";
  const controls = [...$("promo-form").querySelectorAll("input,select,button")];
  const disabled = controls.map(control => control.disabled);
  controls.forEach(control => control.disabled = true);
  $("save-promo").textContent = "Menyimpan…";
  try {
    await api("/api/admin/promos" + (editingPromo ? "/" + encodeURIComponent(editingPromo.code) : ""), {method: editingPromo ? "PUT" : "POST", body: payload});
    $("promo-dialog").close();
    message("Kode promo " + payload.code + " tersimpan" + (payload.active ? "." : " sebagai nonaktif."));
    await loadPromos();
  } catch (error) {
    $("promo-error").textContent = error.message;
    $("promo-error").focus();
  } finally {
    promoSaving = false;
    controls.forEach((control,index) => control.disabled = disabled[index]);
    $("save-promo").textContent = "Simpan kode promo";
  }
});
