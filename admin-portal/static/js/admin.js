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
  baru: "Baru",
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
}
async function refresh() {
  try {
    const [catalog, incoming] = await Promise.all([
      api("/api/admin/products"),
      api("/api/admin/orders"),
    ]);
    products = catalog.products;
    orders = incoming.orders;
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
function showPage(name) {
  activePage = name;
  $("products-page").hidden = name !== "products";
  $("orders-page").hidden = name !== "orders";
  $("page-breadcrumb").textContent =
    name === "products" ? "KOLEKSI" : "PESANAN";
  document
    .querySelectorAll("[data-page]")
    .forEach((button) =>
      button.classList.toggle("active", button.dataset.page === name),
    );
}
function productError(text) {
  const error = $("product-error");
  error.hidden = !text;
  error.textContent = text;
  if (text) error.focus();
}
function renderPhotos() {
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
    `<span class="eyebrow">RINCIAN PESANAN</span><h2 id="order-title">${esc(order.nomor)}</h2><span class="badge new">${statusNames[order.status]}</span><div class="order-info"><div><span>Penerima</span><strong>${esc(order.nama_penerima || order.nama)}</strong></div><div><span>Email / Nomor HP</span><strong>${esc(order.email)} / ${esc(order.nohp)}</strong></div><div><span>Alamat pengiriman</span><strong>${esc(order.alamat)}, ${esc(order.kota)}, ${esc(order.provinsi)} ${esc(order.kodepos)}</strong></div><div><span>Catatan pelanggan</span><strong>${esc(order.catatan) || "Tidak ada catatan"}</strong></div><div><span>Pembayaran</span><strong>Konfirmasi manual dengan pelanggan</strong></div></div><div class="order-items">${order.items.map((item) => `<div class="order-item"><img src="${esc(item.gambar)}" alt="${esc(item.nama)}"><div><strong>${esc(item.nama)}</strong><small>${esc([item.ukuran, item.warna].filter(Boolean).join(" / "))} · ${item.jumlah} pcs</small></div><span>${money(item.harga * item.jumlah)}</span></div>`).join("")}</div><div class="order-info"><div><span>Subtotal / Ongkir / Diskon</span><strong>${money(order.subtotal)} / ${money(order.ongkir)} / −${money(order.diskon)}</strong></div></div><div class="order-total">Total ${money(order.total)}</div>`;
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
