// Only the code is remembered. Monetary amounts come from an authenticated quote.
let promoQuote = null, promoChecking = false, promoSerial = 0, promoTimer;
const promoCartKey = () => JSON.stringify(getKeranjang().map(item => [item.id,item.harga,item.jumlah,item.ukuran,item.warna,item.available,item.stok]));
function promoDiscount() {
  return promoQuote?.cartKey === promoCartKey() ? promoQuote.discount : 0;
}
function promoChanged() { window.dispatchEvent(new Event("promo:change")); }
function promoMessage(message, error = false) {
  const el = document.getElementById("promo-message");
  el.textContent = message;
  el.classList.toggle("promo-error", error);
  document.getElementById("promo-remove").hidden = !sessionStorage.getItem("checkout_kupon");
}
function promoReadyForCheckout() {
  return !sessionStorage.getItem("checkout_kupon") || (!promoChecking && promoQuote?.cartKey === promoCartKey());
}
async function checkPromo(code) {
  clearTimeout(promoTimer);
  const serial = ++promoSerial, cartKey = promoCartKey(), revision = shoppingState.revision;
  promoQuote = null;
  if (!code) {
    promoChecking = false;
    promoChanged();
    return;
  }
  promoChecking = true;
  document.getElementById("promo-apply").disabled = true;
  promoMessage("Memeriksa kode promo…");
  promoChanged();
  try {
    const {quote} = await customerRequest("/promo", {method:"POST", body:{code}});
    if (serial !== promoSerial) return;
    if (cartKey !== promoCartKey() || revision !== shoppingState.revision || quote.revision !== revision)
      throw new Error("Keranjang berubah. Muat ulang halaman untuk memeriksa promo kembali.");
    promoQuote = {...quote,cartKey};
    sessionStorage.setItem("checkout_kupon",quote.code);
    document.getElementById("promo-input").value = quote.code;
    promoMessage(`Kode ${quote.code} dipakai. Hemat ${formatHarga(quote.discount)}.`);
  } catch (error) {
    if (serial !== promoSerial) return;
    promoQuote = null;
    promoMessage(error.message + " Terapkan ulang atau hapus kode untuk melanjutkan.",true);
  } finally {
    if (serial === promoSerial) {
      promoChecking = false;
      document.getElementById("promo-apply").disabled = false;
      promoChanged();
    }
  }
}
function clearPromo() {
  clearTimeout(promoTimer);
  ++promoSerial;
  promoQuote = null;
  promoChecking = false;
  sessionStorage.removeItem("checkout_kupon");
  document.getElementById("promo-input").value = "";
  document.getElementById("promo-apply").disabled = false;
  promoMessage("Kode promo dihapus.");
  promoChanged();
}
document.addEventListener("DOMContentLoaded", async () => {
  await buyerReady;
  const input = document.getElementById("promo-input");
  if (!input) return;
  input.value = sessionStorage.getItem("checkout_kupon") || "";
  document.getElementById("promo-apply").addEventListener("click", async () => {
    if (!input.value.trim()) {
      promoMessage("Masukkan kode promo terlebih dahulu.",true);
      input.focus();
      return;
    }
    if (!(await requireBuyer())) return;
    const code = input.value.trim().toUpperCase();
    sessionStorage.setItem("checkout_kupon", code);
    checkPromo(code);
  });
  document.getElementById("promo-remove").addEventListener("click", clearPromo);
  input.addEventListener("keydown", event => {
    if (event.key === "Enter") {
      event.preventDefault();
      document.getElementById("promo-apply").click();
    }
  });
  if (buyerSession.authenticated && input.value) checkPromo(input.value);
});
window.addEventListener("customer:state", () => {
  if (document.readyState === "loading" || !document.getElementById("promo-input")) return;
  const code = sessionStorage.getItem("checkout_kupon");
  if (!code) return;
  ++promoSerial;
  promoQuote = null;
  promoChecking = true;
  promoChanged();
  clearTimeout(promoTimer);
  promoTimer = setTimeout(() => checkPromo(code),150);
});
