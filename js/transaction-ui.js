const paymentLabels = {pending: "Menunggu transfer", reported: "Transfer dilaporkan · menunggu pemeriksaan", verified: "Sudah dibayar", unrecorded: "Riwayat verifikasi belum tercatat"};
function orderPaymentText(order) {
  if (order.status === "dibatalkan") return "Pesanan dibatalkan · pembayaran ditutup";
  return paymentLabels[order.payment?.status || (order.status === "baru" ? "pending" : "unrecorded")];
}
function customerOrderStatus(order) {
  if (order.status === "baru" && order.payment?.status === "verified") return "Pembayaran diterima · menunggu diproses";
  if (order.status === "baru" && order.payment?.status === "reported") return "Menunggu pemeriksaan pembayaran";
  return {baru:"Menunggu pembayaran",diproses:"Diproses",dikirim:"Dikirim",selesai:"Selesai",dibatalkan:"Dibatalkan"}[order.status] || order.status;
}
function mountOrderSafety(container, order, refresh) {
  const box = document.createElement("section");
  box.className = "transaction-panel";
  const pending = order.status === "baru" && order.payment?.status === "pending";
  box.innerHTML = `<h3>Pembayaran pesanan</h3><p>${h(orderPaymentText(order))}</p>${order.payment_deadline ? `<p>Batas pembayaran: <strong>${h(new Date(order.payment_deadline * 1000).toLocaleString("id-ID"))}</strong></p>` : ""}${order.payment_hold || order.payment?.status === "reported" ? '<p>Pembatalan otomatis ditahan selama pembayaran diperiksa.</p>' : ""}${order.cancellation_reason === "kedaluwarsa" ? '<p>Batas pembayaran lewat. Stok dan kuota promo telah dilepas.</p>' : ""}${pending ? '<p>Setelah transfer, tekan “Sudah transfer” agar pesanan ditahan selama admin memeriksa. Laporan ini belum menjadi bukti pembayaran terverifikasi.</p><div class="transaction-actions"><button type="button" class="account-button primary" data-order-action="payment">Sudah transfer</button><button type="button" class="account-button secondary" data-order-action="cancel">Batalkan pesanan</button></div>' : ""}<p class="transaction-result" role="status"></p><button type="button" class="auth-text-action" data-order-action="refresh">Muat ulang status</button>`;
  if (order.payment_hold) box.querySelector('[data-order-action="cancel"]')?.remove();
  container.appendChild(box);
  box.addEventListener("click", async event => {
    const button = event.target.closest("[data-order-action]");
    if (!button) return;
    const action = button.dataset.orderAction;
    if (action === "cancel" && !confirm("Batalkan pesanan yang belum dibayar ini? Stok dan kuota promo akan dikembalikan.")) return;
    button.disabled = true;
    try {
      const data = await customerRequest("/orders/" + encodeURIComponent(order.nomor) + (action === "refresh" ? "" : "/" + action), action === "refresh" ? {} : {method: "POST", body: {version: order.version}});
      refresh(data.order);
    } catch (error) {
      box.querySelector(".transaction-result").textContent = error.message;
      button.disabled = false;
    }
  });
}
