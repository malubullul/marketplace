// ============================================================
// CHECKOUT.JS — Logic Halaman Checkout
// ============================================================

let metodeBayarDipilih = "manual";

document.addEventListener("DOMContentLoaded", async () => {
  await buyerReady;
  if (!(await requireBuyer())) return;
  // Cek keranjang
  const keranjang = getKeranjang();
  if (keranjang.length === 0) {
    window.location.href = "keranjang.html";
    return;
  }
  renderRingkasanCheckout();
  await loadCheckoutAddresses();
});

// ── Ringkasan Checkout ─────────────────────────────────────
function renderRingkasanCheckout() {
  const keranjang = getKeranjang();
  const subtotal = hitungTotalKeranjang();
  const coupons = { HEMAT10: 10, ANRED15: 15, SALE20: 20 };
  const diskon = Math.floor(
    (subtotal * (coupons[sessionStorage.getItem("checkout_kupon")] || 0)) / 100,
  );
  const ongkir = subtotal >= 200000 ? 0 : 15000;
  const total = subtotal - diskon + ongkir;

  // Daftar Item
  const itemsEl = document.getElementById("ringkasan-items");
  if (itemsEl) {
    itemsEl.innerHTML = keranjang
      .map(
        (item) => `
      <div style="display:flex;align-items:center;gap:10px;padding:8px 0;border-bottom:1px solid var(--abu-border)">
        <img src="${productImage(item.gambar)}" alt="${h(item.nama)}"
             style="width:48px;height:48px;border-radius:8px;object-fit:cover;flex-shrink:0;background:var(--abu-muda)">
        <div style="flex:1;min-width:0">
          <div style="font-size:13px;font-weight:600;color:var(--teks-hitam);overflow:hidden;white-space:nowrap;text-overflow:ellipsis">${h(item.nama)}</div>
          <div style="font-size:12px;color:var(--abu-teks)">x${item.jumlah}</div>
        </div>
        <div style="font-size:13px;font-weight:700;color:var(--teks-hitam);white-space:nowrap">${formatHarga(item.harga * item.jumlah)}</div>
      </div>
    `,
      )
      .join("");
  }

  document.getElementById("co-subtotal").textContent = formatHarga(subtotal);

  const ongkirEl = document.getElementById("co-ongkir");
  if (ongkir === 0) {
    ongkirEl.textContent = "GRATIS";
    ongkirEl.className = "gratis";
  } else {
    ongkirEl.textContent = formatHarga(ongkir);
    ongkirEl.className = "";
  }

  if (diskon > 0) {
    document.getElementById("co-diskon-row").style.display = "flex";
    document.getElementById("co-diskon").textContent =
      `-${formatHarga(diskon)}`;
  }

  document.getElementById("co-total").textContent = formatHarga(total);
}

// ── Pilih Metode Bayar ─────────────────────────────────────
function pilihMetode(el, metode) {
  document
    .querySelectorAll(".metode-item")
    .forEach((m) => m.classList.remove("aktif"));
  el.classList.add("aktif");
  metodeBayarDipilih = metode;
}

// ── Validasi Form ──────────────────────────────────────────
function validasiForm() {
  let valid = true;
  const fields = [
    { id: "nama-depan", label: "Nama depan wajib diisi" },

    { id: "email", label: "Email wajib diisi", type: "email" },
    { id: "nohp", label: "Nomor HP wajib diisi" },
    { id: "nama-penerima", label: "Nama penerima wajib diisi" },
    { id: "alamat", label: "Alamat wajib diisi" },
    { id: "provinsi", label: "Pilih provinsi" },
    { id: "kota", label: "Kota wajib diisi" },
    { id: "kodepos", label: "Kode pos wajib diisi" },
  ];

  fields.forEach((f) => {
    const el = document.getElementById(f.id);
    const errEl = document.getElementById(`err-${f.id}`);
    if (!el) return;

    let errMsg = "";
    const val = el.value.trim();

    if (!val) {
      errMsg = f.label;
    } else if (f.type === "email" && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(val)) {
      errMsg = "Format email tidak valid";
    } else if (f.id === "kodepos" && !/^\d{5}$/.test(val)) {
      errMsg = "Kode pos harus 5 digit angka";
    }

    if (errMsg) {
      el.classList.add("error");
      if (errEl) errEl.textContent = errMsg;
      valid = false;
    } else {
      el.classList.remove("error");
      if (errEl) errEl.textContent = "";
    }
  });

  return valid;
}

// ── Proses Checkout ────────────────────────────────────────
async function prosesCheckout() {
  if (!(await requireBuyer())) return;
  if (!validasiForm()) {
    document.querySelector(".error")?.focus();
    tampilToast("Lengkapi data pemesan dan penerima.", "error");
    return;
  }
  const errorEl = document.getElementById("checkout-error");
  errorEl.textContent = "";
  if (katalogMode !== "server") {
    errorEl.textContent =
      "Pemesanan memerlukan server Anredseller. Pratinjau statis tidak dapat mengirim pesanan.";
    return;
  }
  const btn = document.getElementById("btn-pesan");
  btn.disabled = true;
  btn.textContent = "Mengirim pesanan…";
  let key = sessionStorage.getItem("checkout_request_key");
  if (!key) {
    key = crypto.randomUUID
      ? crypto.randomUUID()
      : Array.from(crypto.getRandomValues(new Uint8Array(16)), (value) =>
          value.toString(16).padStart(2, "0"),
        ).join("");
    sessionStorage.setItem("checkout_request_key", key);
  }
  const val = (id) => document.getElementById(id).value.trim();
  const body = {
    customer: {
      nama: val("nama-depan") + " " + val("nama-belakang"),
      nama_penerima: val("nama-penerima"),
      email: val("email"),
      nohp: val("nohp"),
      alamat: val("alamat"),
      kota: val("kota"),
      provinsi: val("provinsi"),
      kodepos: val("kodepos"),
    },
    items: getKeranjang().map((item) => ({
      id: item.id,
      jumlah: item.jumlah,
      harga: item.harga,
      ukuran: item.ukuran || "",
      warna: item.warna || "",
    })),
    coupon: sessionStorage.getItem("checkout_kupon") || "",
    catatan: val("catatan"),
    address_id: document.getElementById("checkout-address-select").value
      ? Number(document.getElementById("checkout-address-select").value)
      : null,
    save_address:
      !document.getElementById("checkout-address-select").value &&
      document.getElementById("save-checkout-address").checked,
  };
  try {
    const response = await fetch("/api/orders", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Idempotency-Key": key,
        "X-CSRF-Token": buyerSession.csrf,
      },
      body: JSON.stringify(body),
    });
    const data = await response.json();
    if (response.status === 401) {
      location.href = buyerLoginUrl("checkout.html");
      return;
    }
    if (!response.ok)
      throw new Error(data.error || "Pesanan belum terkirim. Coba lagi.");
    sessionStorage.setItem("pesanan_terakhir", data.order.nomor);
    applyShoppingState(data.state);
    sessionStorage.removeItem("checkout_request_key");
    sessionStorage.removeItem("checkout_kupon");
    location.href =
      "konfirmasi.html?order=" + encodeURIComponent(data.order.nomor);
  } catch (error) {
    errorEl.textContent = error.message;
    errorEl.focus();
    btn.disabled = false;
    btn.textContent = "Kirim pesanan ke toko";
  }
}

let checkoutAddresses = [];
async function loadCheckoutAddresses() {
  const profile = buyerSession.customer,
    names = profile.nama.trim().split(/\s+/);
  document.getElementById("nama-depan").value = names[0];
  document.getElementById("nama-belakang").value = names.slice(1).join(" ");
  document.getElementById("email").value = profile.email;
  document.getElementById("nama-penerima").value = profile.nama;
  document.getElementById("nohp").value = profile.nohp;
  try {
    checkoutAddresses = (await customerRequest("/addresses")).addresses;
    const select = document.getElementById("checkout-address-select");
    select.innerHTML =
      '<option value="">Alamat baru</option>' +
      checkoutAddresses
        .map(
          (address) =>
            `<option value="${address.id}">${h(address.label)} — ${h(address.nama_penerima)}${address.is_default ? " (Utama)" : ""}</option>`,
        )
        .join("");
    select.value = String(
      checkoutAddresses.find((address) => address.is_default)?.id || "",
    );
    const choose = () => {
      const address = checkoutAddresses.find(
        (address) => String(address.id) === select.value,
      );
      document.getElementById("checkout-save-label").hidden = !!address;
      if (address)
        for (const [id, key] of Object.entries({
          "nama-penerima": "nama_penerima",
          nohp: "nohp",
          alamat: "alamat",
          kota: "kota",
          provinsi: "provinsi",
          kodepos: "kodepos",
        }))
          document.getElementById(id).value = address[key];
    };
    select.addEventListener("change", choose);
    choose();
    for (const id of [
      "nama-penerima",
      "nohp",
      "alamat",
      "kota",
      "provinsi",
      "kodepos",
    ])
      document.getElementById(id).addEventListener("input", () => {
        if (select.value) {
          select.value = "";
          document.getElementById("checkout-save-label").hidden = false;
        }
      });
  } catch (error) {
    document.getElementById("checkout-error").textContent = error.message;
  }
}

window.addEventListener("customer:state", () => {
  if (
    document.readyState !== "loading" &&
    document.getElementById("ringkasan-items")
  )
    renderRingkasanCheckout();
});
