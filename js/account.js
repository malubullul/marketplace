const accountElement = (id) => document.getElementById(id);
let accountAddresses = [],
  accountOrders = [],
  editingAddress = null,
  currentAccountPanel = "profile";
const accountStatus = {
  baru: "Menunggu konfirmasi",
  diproses: "Diproses",
  dikirim: "Dikirim",
  selesai: "Selesai",
  dibatalkan: "Dibatalkan",
};
function accountMessage(text, error = false) {
  const element = accountElement("account-message");
  element.textContent = text;
  element.hidden = !text;
  element.classList.toggle("error", error);
}
function formError(id, text) {
  const element = accountElement(id);
  element.textContent = text;
  if (text) element.focus();
}
function safeAccountNext() {
  const requested =
    new URLSearchParams(location.search).get("next") || "akun.html";
  try {
    const url = new URL(requested, location.href);
    if (
      url.origin === location.origin &&
      /^\/(index|produk|detail|keranjang|checkout|konfirmasi|akun)\.html$/.test(
        url.pathname,
      )
    )
      return url.pathname + url.search + url.hash;
  } catch {}
  return "akun.html";
}
function showAuth(mode = "login") {
  accountElement("customer-auth").hidden = false;
  accountElement("customer-dashboard").hidden = true;
  accountElement("account-loading").hidden = true;
  accountElement("buyer-login-form").hidden = mode !== "login";
  accountElement("buyer-register-form").hidden = mode !== "register";
  accountElement("show-login").classList.toggle("selected", mode === "login");
  accountElement("show-register").classList.toggle(
    "selected",
    mode === "register",
  );
  accountElement("show-login").setAttribute(
    "aria-pressed",
    String(mode === "login"),
  );
  accountElement("show-register").setAttribute(
    "aria-pressed",
    String(mode === "register"),
  );
  accountElement("auth-title").textContent =
    mode === "login" ? "Masuk ke Anredseller." : "Buat akunmu.";
}
accountElement("show-login").addEventListener("click", () => showAuth("login"));
accountElement("show-register").addEventListener("click", () =>
  showAuth("register"),
);
for (const mode of ["login", "register"]) {
  accountElement("buyer-" + mode + "-form").addEventListener(
    "submit",
    async (event) => {
      event.preventDefault();
      const button = event.currentTarget.querySelector('button[type="submit"]'),
        errorId = "buyer-" + mode + "-error";
      formError(errorId, "");
      if (
        mode === "register" &&
        accountElement("buyer-register-password").value !==
          accountElement("buyer-register-confirm").value
      ) {
        formError(errorId, "Kedua kata sandi harus sama.");
        return;
      }
      button.disabled = true;
      const data = {
        email: accountElement("buyer-" + mode + "-email").value,
        password: accountElement("buyer-" + mode + "-password").value,
      };
      if (mode === "register") {
        data.nama = accountElement("buyer-register-name").value;
        data.nohp = accountElement("buyer-register-phone").value;
      }
      try {
        await customerRequest("/" + mode, { method: "POST", body: data });
        clearBuyerBrowserData();
        signalCustomerAuthChange();
        location.replace(safeAccountNext());
      } catch (error) {
        formError(errorId, error.message);
      } finally {
        button.disabled = false;
      }
    },
  );
}
function renderProfile() {
  const customer = buyerSession.customer;
  accountElement("customer-name").textContent = customer.nama;
  accountElement("customer-avatar").textContent = customer.nama
    .trim()
    .slice(0, 1)
    .toUpperCase();
  accountElement("profile-name").value = customer.nama;
  accountElement("profile-email").value = customer.email;
  accountElement("profile-phone").value = customer.nohp;
  renderAccountSecurity();
}
function renderAddresses() {
  accountElement("customer-address-list").innerHTML = accountAddresses.length
    ? accountAddresses
        .map(
          (address) =>
            `<article class="address-card"><h3>${h(address.label)}${address.is_default ? '<span class="account-badge">Utama</span>' : ""}</h3><strong>${h(address.nama_penerima)}</strong><p>${h(address.nohp)}</p><p>${h(address.alamat)}</p><p>${h(address.kota)}, ${h(address.provinsi)} ${h(address.kodepos)}</p><div class="address-actions"><button data-edit-address="${address.id}">Ubah</button>${!address.is_default ? `<button data-default-address="${address.id}">Jadikan utama</button>` : ""}<button class="delete" data-delete-address="${address.id}">Hapus</button></div></article>`,
        )
        .join("")
    : '<div class="account-empty"><h3>Ke mana favoritmu dikirim?</h3><p>Tambahkan alamat pertama agar checkout berikutnya lebih mudah.</p></div>';
}
function renderCustomerOrders() {
  const filter = accountElement("customer-order-filter").value,
    list = accountOrders.filter(
      (order) => filter === "all" || order.status === filter,
    );
  accountElement("customer-order-count").textContent = accountOrders.length;
  accountElement("customer-order-list").innerHTML = list.length
    ? list
        .map(
          (order) =>
            `<article class="customer-order-card"><div class="customer-order-top"><div><strong>${h(order.nomor)}</strong><small>${new Date(order.created_at * 1000).toLocaleDateString("id-ID", { dateStyle: "long" })}</small></div><span class="account-badge">${accountStatus[order.status] || h(order.status)}</span></div><div class="customer-order-items"><img src="${productImage(order.items[0].gambar)}" alt="${h(order.items[0].nama)}"><div><strong>${h(order.items[0].nama)}</strong><small>${order.items.reduce((total, item) => total + item.jumlah, 0)} item${order.items.length > 1 ? " dalam " + order.items.length + " pilihan" : ""}</small></div></div><div class="customer-order-bottom"><span>Total pesanan<strong>${formatHarga(order.total)}</strong></span><button class="account-button secondary" data-customer-order="${h(order.nomor)}">Lihat rincian</button></div></article>`,
        )
        .join("")
    : '<div class="account-empty"><h3>Belum ada pesanan di sini.</h3><p>Pesanan dari akunmu akan tersimpan di halaman ini.</p><a href="produk.html">Jelajahi koleksi</a></div>';
}
function renderAccountWishlist() {
  accountElement("customer-wish-count").textContent = getWishlist().length;
  accountElement("customer-wishlist").innerHTML = getWishlist().length
    ? getWishlist()
        .map((id) => {
          const product = getProdukById(id);
          return product
            ? renderKartuProduk(product)
            : `<article class="account-empty"><h3>Produk tidak tersedia</h3><p>Produk ini belum dapat ditampilkan di katalog.</p><button class="account-button secondary" data-unavailable-wish="${id}">Hapus dari wishlist</button></article>`;
        })
        .join("")
    : '<div class="account-empty"><h3>Simpan yang kamu suka.</h3><p>Ketuk ikon hati pada produk untuk menyimpannya ke akun.</p><a href="produk.html">Cari favoritmu</a></div>';
  updateIkonWishlist();
}
async function loadAccount() {
  try {
    const [profile, addresses, history, state] = await Promise.all([
      customerRequest("/profile"),
      customerRequest("/addresses"),
      customerRequest("/orders"),
      customerRequest("/state"),
    ]);
    buyerSession.customer = profile.customer;
    accountAddresses = addresses.addresses;
    accountOrders = history.orders;
    applyShoppingState(state.state);
    renderProfile();
    renderAddresses();
    renderCustomerOrders();
    renderAccountWishlist();
    accountElement("customer-auth").hidden = true;
    accountElement("customer-dashboard").hidden = false;
    accountElement("account-loading").hidden = true;
  } catch (error) {
    if (error.status === 401) showAuth();
    else {
      accountElement("account-loading").textContent = error.message;
      accountMessage(error.message, true);
    }
  }
}
const accountPanels = {
  profile: [
    "Profil saya",
    "Detail kecil untuk pengalaman belanja yang lebih personal.",
  ],
  addresses: [
    "Alamat tersimpan",
    "Alamat favorit, siap untuk pengiriman berikutnya.",
  ],
  orders: ["Pesanan saya", "Ikuti setiap perjalanan koleksi pilihanmu."],
  wishlist: ["Wishlist", "Semua yang kamu suka, menunggu di sini."],
};
function showAccountPanel(name) {
  if (!accountPanels[name]) name = "profile";
  currentAccountPanel = name;
  for (const key of Object.keys(accountPanels))
    accountElement("panel-" + key).hidden = key !== name;
  document.querySelectorAll("[data-customer-panel]").forEach((button) => {
    const selected = button.dataset.customerPanel === name;
    button.classList.toggle("active", selected);
    if (selected) button.setAttribute("aria-current", "page");
    else button.removeAttribute("aria-current");
  });
  accountElement("customer-panel-title").textContent =
    accountPanels[name][0] + ".";
  accountElement("customer-panel-description").textContent =
    accountPanels[name][1];
  history.replaceState(
    {},
    "",
    location.pathname + location.search + "#" + name,
  );
  accountMessage("");
}
accountElement("customer-profile-form").addEventListener(
  "submit",
  async (event) => {
    event.preventDefault();
    const button = event.currentTarget.querySelector('button[type="submit"]');
    button.disabled = true;
    try {
      const data = await customerRequest("/profile", {
        method: "PUT",
        body: {
          nama: accountElement("profile-name").value,
          nohp: accountElement("profile-phone").value,
        },
      });
      buyerSession.customer = data.customer;
      renderProfile();
      accountMessage("Profilmu berhasil disimpan.");
    } catch (error) {
      accountMessage(error.message, true);
    } finally {
      button.disabled = false;
    }
  },
);
accountElement("customer-password-form").addEventListener(
  "submit",
  async (event) => {
    event.preventDefault();
    if (
      accountElement("password-new").value !==
      accountElement("password-confirm").value
    ) {
      accountMessage("Kedua kata sandi baru harus sama.", true);
      return;
    }
    const button = event.currentTarget.querySelector('button[type="submit"]');
    button.disabled = true;
    try {
      const data = await customerRequest("/password", {
        method: "POST",
        body: {
          current_password: accountElement("password-current").value,
          password: accountElement("password-new").value,
        },
      });
      buyerSession.csrf = data.csrf;
      signalCustomerAuthChange();
      event.target.reset();
      accountMessage(
        "Kata sandi diperbarui. Perangkat lain telah keluar dari akun.",
      );
    } catch (error) {
      accountMessage(error.message, true);
    } finally {
      button.disabled = false;
    }
  },
);
function openAddressEditor(address = null) {
  editingAddress = address;
  accountElement("customer-address-form").reset();
  accountElement("address-title").textContent = address
    ? "Ubah alamat"
    : "Tambah alamat";
  formError("address-error", "");
  const fields = {
    "address-label": "label",
    "address-recipient": "nama_penerima",
    "address-phone": "nohp",
    "address-street": "alamat",
    "address-city": "kota",
    "address-province": "provinsi",
    "address-postcode": "kodepos",
  };
  if (address)
    for (const [id, key] of Object.entries(fields))
      accountElement(id).value = address[key];
  else {
    accountElement("address-recipient").value = buyerSession.customer.nama;
    accountElement("address-phone").value = buyerSession.customer.nohp;
  }
  accountElement("address-default").checked = address
    ? address.is_default
    : accountAddresses.length === 0;
  accountElement("address-dialog").showModal();
}
accountElement("customer-address-form").addEventListener(
  "submit",
  async (event) => {
    event.preventDefault();
    const button = event.currentTarget.querySelector('button[type="submit"]');
    button.disabled = true;
    formError("address-error", "");
    const data = {
      label: accountElement("address-label").value,
      nama_penerima: accountElement("address-recipient").value,
      nohp: accountElement("address-phone").value,
      alamat: accountElement("address-street").value,
      kota: accountElement("address-city").value,
      provinsi: accountElement("address-province").value,
      kodepos: accountElement("address-postcode").value,
      is_default: accountElement("address-default").checked,
    };
    try {
      await customerRequest(
        "/addresses" + (editingAddress ? "/" + editingAddress.id : ""),
        { method: editingAddress ? "PUT" : "POST", body: data },
      );
      accountElement("address-dialog").close();
      await loadAccount();
      accountMessage("Alamat berhasil disimpan.");
    } catch (error) {
      formError("address-error", error.message);
    } finally {
      button.disabled = false;
    }
  },
);
accountElement("add-address").addEventListener("click", () =>
  openAddressEditor(),
);
accountElement("close-address").addEventListener("click", () =>
  accountElement("address-dialog").close(),
);
accountElement("close-customer-order").addEventListener("click", () =>
  accountElement("customer-order-dialog").close(),
);
accountElement("customer-order-filter").addEventListener(
  "change",
  renderCustomerOrders,
);
accountElement("refresh-account").addEventListener("click", loadAccount);
accountElement("customer-logout").addEventListener("click", async () => {
  try {
    await customerLogout();
  } catch (error) {
    accountMessage(error.message, true);
  }
});
document.addEventListener("click", async (event) => {
  const panel = event.target.closest("[data-customer-panel]");
  if (panel) {
    showAccountPanel(panel.dataset.customerPanel);
    if (panel.dataset.customerPanel === "orders") {
      try {
        accountOrders = (await customerRequest("/orders")).orders;
        renderCustomerOrders();
      } catch (error) {
        accountMessage(error.message, true);
      }
    }
  }
  const edit = event.target.closest("[data-edit-address]");
  if (edit)
    openAddressEditor(
      accountAddresses.find(
        (address) => address.id === Number(edit.dataset.editAddress),
      ),
    );
  const deletion = event.target.closest("[data-delete-address]");
  if (
    deletion &&
    confirm(
      "Hapus alamat ini dari akun? Pesanan lama tetap menggunakan alamat yang tercatat.",
    )
  ) {
    try {
      await customerRequest("/addresses/" + deletion.dataset.deleteAddress, {
        method: "DELETE",
      });
      await loadAccount();
      accountMessage("Alamat dihapus.");
    } catch (error) {
      accountMessage(error.message, true);
    }
  }
  const primary = event.target.closest("[data-default-address]");
  if (primary) {
    const address = accountAddresses.find(
      (address) => address.id === Number(primary.dataset.defaultAddress),
    );
    try {
      await customerRequest("/addresses/" + address.id, {
        method: "PUT",
        body: { ...address, is_default: true },
      });
      await loadAccount();
      accountMessage("Alamat utama diperbarui.");
    } catch (error) {
      accountMessage(error.message, true);
    }
  }
  const unavailable = event.target.closest("[data-unavailable-wish]");
  if (unavailable) {
    await toggleWishlist(Number(unavailable.dataset.unavailableWish));
    renderAccountWishlist();
  }
  const order = event.target.closest("[data-customer-order]");
  if (order) {
    try {
      const data = await customerRequest(
        "/orders/" + encodeURIComponent(order.dataset.customerOrder),
      );
      showCustomerOrder(data.order);
    } catch (error) {
      accountMessage(error.message, true);
    }
  }
});
function showCustomerOrder(order) {
  const rows = [
    ["Penerima", order.nama_penerima],
    ["Nomor HP", order.nohp],
    [
      "Alamat",
      [order.alamat, order.kota, order.provinsi, order.kodepos].join(", "),
    ],
    ["Pembayaran", "Dikonfirmasi manual oleh toko"],
    ["Catatan", order.catatan || "Tidak ada catatan"],
  ];
  accountElement("customer-order-details").innerHTML =
    `<span class="eyebrow">RINCIAN PESANAN</span><h2 id="customer-order-title">${h(order.nomor)}</h2><span class="account-badge">${accountStatus[order.status]}</span>${rows.map(([label, value]) => `<div class="account-receipt-row"><span>${h(label)}</span>${h(value)}</div>`).join("")}<div class="account-receipt-items">${order.items.map((item) => `<div class="customer-order-items"><img src="${productImage(item.gambar)}" alt="${h(item.nama)}"><div><strong>${h(item.nama)}</strong><small>${h([item.ukuran, item.warna].filter(Boolean).join(" / "))} · ${item.jumlah} pcs</small></div><span>${formatHarga(item.harga * item.jumlah)}</span></div>`).join("")}</div><div class="account-receipt-row"><span>Subtotal / Ongkir / Diskon</span>${formatHarga(order.subtotal)} / ${formatHarga(order.ongkir)} / −${formatHarga(order.diskon)}</div><div class="account-receipt-total">${formatHarga(order.total)}</div>`;
  accountElement("customer-order-dialog").showModal();
}
window.addEventListener("customer:state", () => {
  if (buyerSession.authenticated && document.readyState !== "loading")
    renderAccountWishlist();
});
(async () => {
  await buyerReady;
  if (katalogMode !== "server") {
    showAuth();
    formError(
      "buyer-login-error",
      "Layanan akun membutuhkan server Anredseller.",
    );
    return;
  }
  updateGoogleAccess();
  const authCode = new URLSearchParams(location.search).get("auth");
  const authError = googleAuthErrors[authCode];
  if (authCode) {
    const clean = new URL(location.href);
    clean.searchParams.delete("auth");
    history.replaceState({}, "", clean.pathname + clean.search + clean.hash);
  }
  if (authCode === "google-success" && buyerSession.authenticated) {
    clearBuyerBrowserData();
    signalCustomerAuthChange();
    const next = safeAccountNext();
    if (next !== "/akun.html" && next !== "akun.html") {
      location.replace(next);
      return;
    }
    history.replaceState({}, "", "akun.html");
  }
  if (!buyerSession.authenticated) {
    showAuth();
    if (authError) {
      accountElement("google-auth-error").hidden = false;
      formError("google-auth-error", authError);
    }
  } else {
    await loadAccount();
    showAccountPanel(location.hash.slice(1) || "profile");
    if (authError) accountMessage(authError, true);
  }
})();

const googleAuthErrors = {
  "google-unavailable": "Google belum tersedia. Silakan masuk dengan email.",
  "google-invalid":
    "Sesi masuk Google sudah berakhir atau tidak valid. Silakan coba lagi.",
  "google-cancelled":
    "Masuk dengan Google dibatalkan. Kamu bisa mencoba lagi atau menggunakan email.",
  "google-failed": "Masuk dengan Google belum berhasil. Silakan coba lagi.",
  "google-email-exists":
    "Email ini sudah memiliki akun. Masuk dengan kata sandi, lalu hubungkan Google dari Keamanan akun.",
  "google-link-mismatch":
    "Pilih akun Google dengan email yang sama dengan akun Anredseller-mu.",
};
function updateGoogleAccess() {
  const enabled = buyerSession.providers?.google === true;
  accountElement("google-login").disabled = !enabled;
  accountElement("google-availability").textContent = enabled
    ? "Pertama kali di sini? Akunmu dibuat saat kamu melanjutkan."
    : "Google belum tersedia. Gunakan email untuk saat ini.";
}
function renderAccountSecurity() {
  const customer = buyerSession.customer;
  if (!customer) return;
  const hasPassword = customer.has_password !== false;
  accountElement("password-settings").hidden = !hasPassword;
  accountElement("email-method-status").textContent = hasPassword
    ? "Aktif"
    : "Tidak digunakan";
  accountElement("google-method-status").textContent = customer.google_linked
    ? "Terhubung"
    : "Belum terhubung";
  accountElement("google-connect").hidden =
    !hasPassword || buyerSession.providers?.google !== true;
  accountElement("google-connect").textContent = customer.google_linked
    ? "Putuskan koneksi Google"
    : "Hubungkan Google";
  const note = accountElement("google-account-note");
  note.hidden = hasPassword;
  note.textContent = hasPassword
    ? ""
    : "Kamu masuk dengan Google. Atur kata sandi dan verifikasi dua langkah melalui akun Google-mu.";
  accountElement("google-profile-note").hidden = !!customer.nohp;
}
async function startGoogle(intent = "login", password = "") {
  const data = await customerRequest("/google/start", {
    method: "POST",
    body: {
      intent,
      current_password: password,
      next: intent === "link" ? "/akun.html" : safeAccountNext(),
    },
  });
  const url = new URL(data.url);
  if (
    url.origin !== "https://accounts.google.com" ||
    url.pathname !== "/o/oauth2/v2/auth"
  )
    throw new Error("Tujuan masuk Google tidak valid.");
  location.assign(url.href);
}
accountElement("google-login").addEventListener("click", async (event) => {
  const button = event.currentTarget;
  button.disabled = true;
  formError("google-auth-error", "");
  try {
    await startGoogle();
  } catch (error) {
    accountElement("google-auth-error").hidden = false;
    formError("google-auth-error", error.message);
    button.disabled = false;
  }
});
accountElement("google-connect").addEventListener("click", () => {
  const unlink = buyerSession.customer.google_linked;
  accountElement("google-security-form").reset();
  formError("google-security-error", "");
  accountElement("google-security-title").textContent = unlink
    ? "Putuskan koneksi Google"
    : "Hubungkan Google";
  accountElement("google-security-description").textContent = unlink
    ? "Setelah diputuskan, gunakan email dan kata sandi untuk masuk. Perangkat lain akan keluar."
    : "Konfirmasi kata sandi, lalu pilih akun Google dengan email yang sama.";
  accountElement("submit-google-security").textContent = unlink
    ? "Putuskan koneksi"
    : "Lanjut ke Google";
  accountElement("google-security-dialog").showModal();
});
accountElement("cancel-google-security").addEventListener("click", () =>
  accountElement("google-security-dialog").close(),
);
accountElement("google-security-form").addEventListener(
  "submit",
  async (event) => {
    event.preventDefault();
    const button = accountElement("submit-google-security");
    button.disabled = true;
    formError("google-security-error", "");
    const password = accountElement("google-current-password").value;
    try {
      if (buyerSession.customer.google_linked) {
        const data = await customerRequest("/google/unlink", {
          method: "POST",
          body: { current_password: password },
        });
        buyerSession.csrf = data.csrf;
        buyerSession.customer = data.customer;
        signalCustomerAuthChange();
        renderAccountSecurity();
        accountElement("google-security-dialog").close();
        accountMessage(
          "Koneksi Google diputuskan. Kamu tetap bisa masuk dengan email dan kata sandi.",
        );
      } else await startGoogle("link", password);
    } catch (error) {
      formError("google-security-error", error.message);
    } finally {
      accountElement("google-security-form").reset();
      button.disabled = false;
    }
  },
);
// Labels remain attached to their inputs; visibility is an explicit, reversible choice.
document
  .querySelectorAll('.account-page input[type="password"]')
  .forEach((input) => {
    const wrapper = document.createElement("div");
    wrapper.className = "password-field";
    input.before(wrapper);
    wrapper.appendChild(input);
    const toggle = document.createElement("button");
    toggle.type = "button";
    toggle.className = "password-toggle";
    toggle.setAttribute("aria-controls", input.id);
    toggle.setAttribute("aria-pressed", "false");
    toggle.setAttribute("aria-label", "Tampilkan kata sandi");
    toggle.innerHTML =
      '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" aria-hidden="true"><path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12Z"/><circle cx="12" cy="12" r="3"/></svg>';
    toggle.addEventListener("click", () => {
      const show = input.type === "password";
      input.type = show ? "text" : "password";
      toggle.setAttribute("aria-pressed", String(show));
      toggle.setAttribute(
        "aria-label",
        show ? "Sembunyikan kata sandi" : "Tampilkan kata sandi",
      );
    });
    wrapper.appendChild(toggle);
  });

accountElement("logout-all-devices").addEventListener(
  "click",
  async (event) => {
    const button = event.currentTarget;
    button.disabled = true;
    try {
      await customerRequest("/logout-all", { method: "POST" });
      clearBuyerBrowserData();
      signalCustomerAuthChange();
      location.replace("akun.html");
    } catch (error) {
      accountMessage(error.message, true);
      button.disabled = false;
    }
  },
);
