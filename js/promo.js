// Only the code is remembered. Monetary amounts come from an authenticated quote.
let promoQuote = null, promoChecking = false, promoSerial = 0, promoTimer;
let promoCandidate = "", promoCheckoutPending = false;
const promoCartKey = () => JSON.stringify(getKeranjang().map(item => [item.id,item.harga,item.jumlah,item.ukuran,item.warna,item.available,item.stok]));
function appliedPromoQuote() {
  return !promoChecking && promoQuote?.cartKey === promoCartKey() && promoQuote.revision === shoppingState.revision ? promoQuote : null;
}
function promoDiscount() {
  return appliedPromoQuote()?.discount || 0;
}
function promoChanged() { window.dispatchEvent(new Event("promo:change")); }
function promoMessage(message, error = false) {
  const el = document.getElementById("promo-message");
  el.textContent = message;
  el.classList.toggle("promo-error", error);
  document.getElementById("promo-remove").hidden = !document.getElementById("promo-input").value.trim();
}
function promoControlsDisabled(disabled) {
  for (const id of ["promo-input", "promo-apply", "promo-remove"]) document.getElementById(id).disabled = disabled;
}
function promoForCheckout() {
  // Freeze exactly the total displayed when the buyer submits. An unfinished
  // optional check must not add a discount while the order is in flight.
  const quote = appliedPromoQuote();
  clearTimeout(promoTimer);
  ++promoSerial;
  promoChecking = false;
  promoCheckoutPending = true;
  if (!quote) {
    promoQuote = null;
    promoCandidate = "";
    sessionStorage.removeItem("checkout_kupon");
    if (document.getElementById("promo-input").value.trim()) promoMessage("Pesanan dilanjutkan tanpa kode promo.");
    promoChanged();
  }
  promoControlsDisabled(true);
  return {coupon: quote?.code || "", expected_discount: quote?.discount || 0};
}
function finishPromoCheckout() {
  promoCheckoutPending = false;
  promoControlsDisabled(false);
}
async function checkPromo(code) {
  if (promoCheckoutPending) return;
  clearTimeout(promoTimer);
  const serial = ++promoSerial, cartKey = promoCartKey(), revision = shoppingState.revision;
  promoQuote = null;
  promoCandidate = code;
  sessionStorage.removeItem("checkout_kupon");
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
    promoCandidate = "";
    sessionStorage.removeItem("checkout_kupon");
    promoMessage(error.message + " Kamu tetap bisa melanjutkan pesanan tanpa promo.",true);
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
  promoCandidate = "";
  promoChecking = false;
  sessionStorage.removeItem("checkout_kupon");
  document.getElementById("promo-input").value = "";
  promoControlsDisabled(promoCheckoutPending);
  promoMessage("Kode promo dihapus. Kamu bisa melanjutkan pesanan tanpa promo.");
  promoChanged();
}
document.addEventListener("DOMContentLoaded", async () => {
  await buyerReady;
  const input = document.getElementById("promo-input");
  if (!input) return;
  input.value = sessionStorage.getItem("checkout_kupon") || "";
  document.getElementById("promo-apply").addEventListener("click", async () => {
    if (!input.value.trim()) {
      clearPromo();
      return;
    }
    if (!(await requireBuyer())) return;
    const code = input.value.trim().toUpperCase();
    checkPromo(code);
  });
  document.getElementById("promo-remove").addEventListener("click", clearPromo);
  input.addEventListener("input", () => {
    clearTimeout(promoTimer);
    ++promoSerial;
    promoQuote = null;
    promoCandidate = "";
    promoChecking = false;
    sessionStorage.removeItem("checkout_kupon");
    promoControlsDisabled(false);
    promoMessage(input.value.trim() ? "Klik Gunakan untuk menerapkan kode, atau lanjutkan pesanan tanpa promo." : "Kode promo opsional. Kamu bisa langsung melanjutkan pesanan.");
    promoChanged();
  });
  input.addEventListener("keydown", event => {
    if (event.key === "Enter") {
      event.preventDefault();
      document.getElementById("promo-apply").click();
    }
  });
  if (buyerSession.authenticated && input.value) checkPromo(input.value);
});
window.addEventListener("customer:state", () => {
  if (promoCheckoutPending || document.readyState === "loading" || !document.getElementById("promo-input")) return;
  const code = promoCandidate || sessionStorage.getItem("checkout_kupon");
  if (!code) return;
  ++promoSerial;
  promoQuote = null;
  promoChecking = true;
  sessionStorage.removeItem("checkout_kupon");
  promoChanged();
  clearTimeout(promoTimer);
  promoTimer = setTimeout(() => checkPromo(code),150);
});
