// Reviews belong to verified buyers; identities and eligibility come from the server.
async function initProductReviews(product) {
  const panel = document.getElementById("tab-ulasan");
  panel.innerHTML = `<section class="buyer-reviews" data-ui aria-label="Ulasan pembeli">
    <div class="review-summary"><h3>Ulasan pembeli</h3><p id="review-summary-text"></p><small>Rating dari pembeli dengan pesanan selesai.</small></div>
    <div id="review-editor"><p role="status">Memeriksa kelayakan rating…</p></div>
    <div id="review-list" aria-live="polite"></div>
    <p id="review-load-error" class="review-error" role="alert"></p>
    <button type="button" class="review-secondary" id="review-more" hidden>Lihat ulasan lainnya</button>
  </section>`;
  let nextOffset = 0;
  const more = document.getElementById("review-more");
  function metrics() {
    const rating = product.metrics_ready === false ? "Rating belum tersedia" : product.ulasan ? product.rating.toFixed(1) : "Belum ada rating";
    const sold = product.metrics_ready === false ? "—" : product.terjual.toLocaleString("id-ID");
    document.getElementById("review-summary-text").textContent = product.ulasan ? `${rating} / 5 · ${product.ulasan.toLocaleString("id-ID")} ulasan` : rating;
    document.getElementById("product-review-metrics").innerHTML = `<span class="detail-rating">${product.ulasan ? renderBintang(product.rating) : ""} <strong>${rating}</strong></span>${product.metrics_ready === false ? "" : `<span>(${product.ulasan.toLocaleString("id-ID")} ulasan)</span>`}<span class="detail-terjual">${sold} terjual</span>`;
    document.getElementById("reviews-tab").textContent = `Ulasan (${product.ulasan.toLocaleString("id-ID")})`;
  }
  metrics();
  async function loadReviews(reset = false) {
    more.disabled = true;
    document.getElementById("review-load-error").textContent = "";
    const offset = reset ? 0 : nextOffset;
    try {
      const response = await fetch(`/api/products/${product.id}/reviews?offset=${offset}`, { cache: "no-store" });
      if (!response.ok) throw new Error("Ulasan belum dapat dimuat. Coba lagi.");
      const data = await response.json();
      const html = data.reviews.map(review => `<article class="buyer-review"><div class="buyer-review-heading"><strong>${h(review.name)}</strong><span>Pembelian terverifikasi</span></div><div class="buyer-review-rating"><span aria-label="${review.rating} dari 5 bintang">${renderBintang(review.rating)}</span><time datetime="${new Date(review.created_at * 1000).toISOString()}">${new Date(review.created_at * 1000).toLocaleDateString("id-ID", { dateStyle: "medium" })}</time></div>${review.comment ? `<p>${h(review.comment)}</p>` : ""}${review.updated_at > review.created_at ? '<small>Ulasan diperbarui</small>' : ''}</article>`).join("");
      const list = document.getElementById("review-list");
      if (reset || offset === 0) list.innerHTML = html || '<p class="review-empty">Belum ada ulasan. Jadilah pembeli pertama yang berbagi pengalaman.</p>';
      else list.insertAdjacentHTML("beforeend", html);
      nextOffset = data.next_offset;
      more.hidden = nextOffset === null;
      more.textContent = "Lihat ulasan lainnya";
    } catch (error) {
      document.getElementById("review-load-error").textContent = error.message;
      more.hidden = false;
      more.textContent = "Coba muat ulasan lagi";
    } finally {
      more.disabled = false;
    }
  }
  more.addEventListener("click", () => loadReviews());
  async function editor() {
    await buyerReady;
    const target = document.getElementById("review-editor");
    if (katalogMode !== "server") {
      target.innerHTML = '<p class="review-note">Rating tersedia saat toko terhubung ke server.</p>';
      return;
    }
    if (!buyerSession.authenticated) {
      target.innerHTML = `<p class="review-note"><a href="${buyerLoginUrl(`detail.html?id=${product.id}#ulasan`)}">Masuk untuk memberi rating →</a><br>Rating tersedia setelah pesananmu selesai.</p>`;
      return;
    }
    try {
      const data = await customerRequest(`/products/${product.id}/review`);
      if (!data.eligible) {
        target.innerHTML = '<p class="review-note">Kamu bisa memberi rating setelah pesanan produk ini selesai. <a href="akun.html#orders">Lihat pesananmu →</a></p>';
        return;
      }
      const saved = data.review;
      target.innerHTML = `<form id="product-review-form" class="product-review-form"><h4>${saved ? "Rating darimu" : "Bagaimana produk pilihanmu?"}</h4><fieldset class="rating-fieldset"><legend>Pilih rating</legend><div class="rating-options">${[1,2,3,4,5].map(value => `<label class="rating-option${saved && value <= saved.rating ? " selected" : ""}"><input type="radio" name="product-rating" value="${value}" aria-label="${value} bintang" required${saved?.rating === value ? " checked" : ""}><span aria-hidden="true">★</span></label>`).join("")}</div></fieldset><label class="review-comment-label" for="review-comment">Ceritakan pengalamanmu <span>(opsional)</span></label><textarea id="review-comment" maxlength="1000" rows="4" placeholder="Bagaimana ukuran, bahan, dan kualitasnya?" aria-describedby="review-privacy">${h(saved?.comment || "")}</textarea><small id="review-privacy">Maksimal 1.000 karakter. Jangan sertakan nomor HP atau alamat; ulasan ini tampil untuk umum.</small><p class="review-error" id="review-form-error" role="alert" tabindex="-1"></p><p class="review-success" id="review-form-success" role="status"></p><button type="submit" class="review-submit">${saved ? "Simpan perubahan rating" : "Kirim rating"}</button></form>`;
      const form = document.getElementById("product-review-form");
      form.addEventListener("change", () => {
        const value = Number(new FormData(form).get("product-rating"));
        form.querySelectorAll(".rating-option").forEach((label,index) => label.classList.toggle("selected", index < value));
      });
      form.addEventListener("submit", async event => {
        event.preventDefault();
        const button = form.querySelector('[type="submit"]');
        button.disabled = true;
        document.getElementById("review-form-error").textContent = "";
        document.getElementById("review-form-success").textContent = "";
        try {
          const result = await customerRequest(`/products/${product.id}/review`, { method: "PUT", body: { rating: Number(new FormData(form).get("product-rating")), comment: document.getElementById("review-comment").value } });
          Object.assign(product, result.metrics);
          product.metrics_ready = true;
          metrics();
          await loadReviews(true);
          button.textContent = "Simpan perubahan rating";
          document.getElementById("review-form-success").textContent = "Ratingmu tersimpan. Terima kasih sudah berbagi.";
        } catch (error) {
          const message = document.getElementById("review-form-error");
          message.textContent = error.message;
          message.focus();
        } finally {
          button.disabled = false;
        }
      });
    } catch (error) {
      target.innerHTML = `<p class="review-note">${h(error.message)}</p><button type="button" class="review-secondary" id="review-editor-retry">Periksa ulang akun</button>`;
      document.getElementById("review-editor-retry").addEventListener("click", editor);
    }
  }
  await Promise.all([loadReviews(true), editor()]);
}
