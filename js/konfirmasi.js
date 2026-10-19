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
    return;
  }
  document.getElementById("nomor-pesanan").textContent = order.nomor;
  document.getElementById("konfirmasi-sub").textContent =
    `Terima kasih, ${order.nama}. Pesananmu sudah dikirim ke toko dan menunggu konfirmasi.`;
  const fields = [
    ["Nama penerima", order.nama_penerima || order.nama],
    ["Email", order.email],
    ["Nomor HP", order.nohp],
    [
      "Alamat pengiriman",
      [order.alamat, order.kota, order.provinsi, order.kodepos].join(", "),
    ],
    ["Pembayaran", "Konfirmasi manual dengan toko"],
    [
      "Tanggal pesanan",
      new Date(order.created_at * 1000).toLocaleString("id-ID"),
    ],
    ["Total pesanan", formatHarga(order.total)],
  ];
  document.getElementById("detail-pesanan").innerHTML = fields
    .map(
      ([label, value]) =>
        `<div class="konfirmasi-detail-baris"><span>${h(label)}</span><span>${h(value)}</span></div>`,
    )
    .join("");
  document.getElementById("grid-rekomendasi-konfirmasi").innerHTML =
    PRODUK.filter((p) => p.rekomendasi || p.trending)
      .slice(0, 4)
      .map(renderKartuProduk)
      .join("");
  updateIkonWishlist();
});
