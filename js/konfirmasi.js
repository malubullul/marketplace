document.addEventListener("DOMContentLoaded", async () => {
  await buyerReady;
  if (!(await requireBuyer())) return;
  const number =
    new URLSearchParams(location.search).get("order") ||
    sessionStorage.getItem("pesanan_terakhir");
  if (!number || !/^ANR-[A-F0-9]{12}$/.test(number)) {
    location.replace("akun.html#orders");
    return;
  }
  let order;
  try {
    order = (await customerRequest("/orders/" + encodeURIComponent(number)))
      .order;
  } catch (error) {
    document.getElementById("konfirmasi-sub").textContent = error.message;
    document.getElementById("nomor-pesanan").textContent = "—";
    document.getElementById("confirmation-status").textContent = "Pesanan belum dapat dimuat";
    document.getElementById("confirmation-status-note").textContent = "Muat ulang halaman atau buka Pesanan saya untuk mencoba kembali.";
    return;
  }
  document.getElementById("nomor-pesanan").textContent = order.nomor;
  if (order.status === "dibatalkan") document.querySelector(".konfirmasi-judul").textContent = "Pesanan dibatalkan.";
  document.getElementById("konfirmasi-sub").textContent =
    `Terima kasih, ${order.nama}. Rincian pesananmu tersimpan di akun.`;
  document.getElementById("confirmation-status").textContent = customerOrderStatus(order);
  document.getElementById("confirmation-status-note").textContent = order.status === "baru" && order.payment?.status !== "verified"
    ? "Membuka WhatsApp atau mengirim bukti transfer belum mengubah status. Toko akan memeriksa pembayaranmu."
    : "Untuk pertanyaan mengenai pesanan ini, hubungi customer service.";
  if (order.status === "baru" && order.payment?.status !== "verified") {
    document.getElementById("payment-next-step").hidden = false;
    const link = document.getElementById("payment-whatsapp-link");
    const contacts = await storeContactsReady;
    const url = paymentWhatsAppUrl(contacts, order);
    if (url) {
      link.href = url;
      link.removeAttribute("aria-disabled");
      link.innerHTML = `${icon("chat")} Lanjut pembayaran via WhatsApp`;
    } else {
      link.textContent = "WhatsApp pembayaran belum tersedia";
      document.getElementById("payment-whatsapp-note").textContent = "Kontak pembayaran belum tersedia. Pesanan tetap tersimpan; hubungi CS atau cek kembali nanti.";
    }
  }
  const fields = [
    ["Nama penerima", order.nama_penerima || order.nama],
    ["Email", order.email],
    ["Nomor HP", order.nohp],
    [
      "Alamat pengiriman",
      [order.alamat, order.kota, order.provinsi, order.kodepos].join(", "),
    ],
    ["Pembayaran", orderPaymentText(order)],
    [
      "Tanggal pesanan",
      new Date(order.created_at * 1000).toLocaleString("id-ID"),
    ],
    ["Subtotal produk", formatHarga(order.subtotal)],
    ...(order.promo ? [["Kode promo", order.promo.code]] : []),
    ["Diskon", "−" + formatHarga(order.diskon)],
    ["Estimasi ongkir", formatHarga(order.ongkir)],
    ["Total pesanan", formatHarga(order.total)],
  ];
  document.getElementById("detail-pesanan").innerHTML = fields
    .map(
      ([label, value]) =>
        `<div class="konfirmasi-detail-baris"><span>${h(label)}</span><span>${h(value)}</span></div>`,
    )
    .join("");
  mountOrderSafety(document.getElementById("detail-pesanan"), order, () => location.reload());
  document.getElementById("grid-rekomendasi-konfirmasi").innerHTML =
    PRODUK.filter((p) => p.rekomendasi || p.trending)
      .slice(0, 4)
      .map(renderKartuProduk)
      .join("");
  updateIkonWishlist();
});
