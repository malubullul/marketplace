// A deliberately manual campaign carousel: no timer moves the customer's view.
(async () => {
  const carousel = document.getElementById("campaign-carousel");
  if (!carousel) return;

  const defaults = [
    {
      name: "The Archive", image: "assets/archive-campaign.webp",
      heading: ["The Archive.", "Worn your way."],
      description: "Fashion, sneakers, dan pilihan sehari-hari. Temukan yang terasa seperti kamu.",
      href: "produk.html?kategori=apparel",
      alt: "Dua model mengenakan jaket suede cokelat di lounge bernuansa kayu gelap.",
      crop: "",
    },
    {
      name: "After Hours", image: "assets/campaign-after-hours.webp",
      heading: ["After hours.", "Always in style."],
      description: "Warna hangat, siluet tenang. Pilihan untuk rencana yang tak perlu terburu-buru.",
      href: "produk.html?kategori=apparel",
      alt: "Dua model dengan tailoring warna pasir dan cokelat di koridor hotel berpanel walnut.",
      crop: "86% center",
    },
    {
      name: "City Uniform", image: "assets/campaign-city-uniform.webp",
      heading: ["City uniform.", "Your own rhythm."],
      description: "Lapisan ringan dan sneakers favorit. Bergerak nyaman, dari pagi sampai nanti.",
      href: "produk.html?kategori=sneakers",
      alt: "Model memakai overshirt charcoal, celana hitam, dan sneakers putih di halaman beton modern.",
      crop: "84% center",
    },
    {
      name: "Soft Form", image: "assets/campaign-soft-form.webp",
      heading: ["Soft form.", "Quiet confidence."],
      description: "Tekstur lembut dan potongan yang mengalir. Detail kecil yang terasa berbeda.",
      href: "produk.html?kategori=apparel",
      alt: "Model memakai cardigan oatmeal, celana espresso, dan tas kulit di studio bernuansa olive.",
      crop: "84% center",
    },
    {
      name: "Everyday Objects", image: "assets/campaign-everyday-objects.webp",
      heading: ["Everyday objects.", "Well chosen."],
      description: "Sneakers, tas, dan pelengkap sehari-hari. Sedikit pilihan, banyak kemungkinan.",
      href: "produk.html?kategori=essentials",
      alt: "Sneakers suede putih, kemeja oatmeal terlipat, dan tas kulit cokelat pada plinth walnut.",
      crop: "84% center",
    },
  ];

  const content = await storeContentReady;
  const slides = content?.campaigns || defaults;
  if (!slides.length) {
    carousel.classList.add("campaign-no-photo");
    carousel.dataset.campaignIndex = "-1";
    return;
  }
  carousel.querySelector(".campaign-selectors").innerHTML = slides.map((slide,index) => `<button type="button" data-campaign="${index}" aria-label="Lihat kampanye ${h(slide.name)}"${index === 0 ? ' aria-current="true"' : ''}></button>`).join("");
  document.getElementById("campaign-total").textContent = String(slides.length).padStart(2,"0");
  const photo = carousel.querySelector(".campaign-photo");
  const image = document.getElementById("campaign-image");
  const outgoing = carousel.querySelector(".campaign-image-outgoing");
  const title = document.getElementById("campaign-title");
  const description = document.getElementById("campaign-description");
  const link = document.getElementById("campaign-shop-link");
  const status = document.getElementById("campaign-status");
  const selectors = [...carousel.querySelectorAll("[data-campaign]")];
  const reducedMotion = matchMedia("(prefers-reduced-motion: reduce)");
  const loaded = new Map();
  let current = 0, requested = 0, serial = 0, fadeTimer, touch;

  function load(slide) {
    if (!loaded.has(slide.image)) {
      const promise = new Promise((resolve, reject) => {
        const preload = new Image();
        preload.onload = () => preload.decode().then(() => resolve(preload)).catch(() => {
          loaded.delete(slide.image);
          reject(new Error("image"));
        });
        preload.onerror = () => { loaded.delete(slide.image); reject(new Error("image")); };
        preload.src = slide.image;
      });
      loaded.set(slide.image, promise);
    }
    return loaded.get(slide.image);
  }

  async function show(index) {
    requested = (index + slides.length) % slides.length;
    const destination = requested, request = ++serial;
    if (destination === current) {
      photo.removeAttribute("aria-busy");
      return;
    }
    photo.setAttribute("aria-busy", "true");
    const slide = slides[destination];
    try {
      const ready = await load(slide);
      if (request !== serial) return;
      clearTimeout(fadeTimer);
      const previous = image.currentSrc || image.src;
      outgoing.style.backgroundImage = `url("${previous}")`;
      outgoing.style.backgroundPosition = getComputedStyle(image).objectPosition;
      image.classList.add("campaign-image-loading");
      image.src = slide.image;
      image.width = ready.naturalWidth;
      image.height = ready.naturalHeight;
      image.alt = slide.alt;
      image.style.objectPosition = slide.crop;
      // Force the starting frame before the opacity transition, without timers delaying navigation.
      void image.offsetWidth;
      image.classList.remove("campaign-image-loading");
      title.replaceChildren(document.createTextNode(slide.heading[0]), document.createElement("br"), document.createTextNode(slide.heading[1]));
      description.textContent = slide.description;
      link.href = slide.href;
      current = destination;
      document.getElementById("campaign-current").textContent = String(current + 1).padStart(2, "0");
      selectors.forEach((button, i) => {
        if (i === current) button.setAttribute("aria-current", "true");
        else button.removeAttribute("aria-current");
      });
      status.textContent = `Foto ${current + 1} dari ${slides.length}: ${slide.name}.`;
      carousel.dataset.campaignIndex = String(current);
      fadeTimer = setTimeout(() => { outgoing.style.backgroundImage = ""; }, reducedMotion.matches ? 0 : 550);
      [current + 1, current - 1].forEach((i) => load(slides[(i + slides.length) % slides.length]).catch(() => {}));
    } catch {
      if (request !== serial) return;
      requested = current;
      status.textContent = "Foto belum bisa dimuat. Silakan coba lagi.";
      if (typeof tampilToast === "function") tampilToast(status.textContent, "error");
    } finally {
      if (request === serial) photo.removeAttribute("aria-busy");
    }
  }

  carousel.querySelector(".campaign-previous").addEventListener("click", () => show(requested - 1));
  carousel.querySelector(".campaign-next").addEventListener("click", () => show(requested + 1));
  selectors.forEach((button) => button.addEventListener("click", () => show(Number(button.dataset.campaign))));
  carousel.addEventListener("keydown", (event) => {
    if (event.altKey || event.ctrlKey || event.metaKey || event.shiftKey) return;
    if (event.key === "ArrowLeft" || event.key === "ArrowRight") {
      event.preventDefault();
      show(requested + (event.key === "ArrowRight" ? 1 : -1));
    }
  });
  photo.addEventListener("pointerdown", (event) => {
    if (event.pointerType === "mouse" || event.target.closest("button, a")) return;
    touch = {id: event.pointerId, x: event.clientX, y: event.clientY};
    photo.setPointerCapture(event.pointerId);
  });
  photo.addEventListener("pointerup", (event) => {
    if (!touch || touch.id !== event.pointerId) return;
    const dx = event.clientX - touch.x, dy = event.clientY - touch.y;
    touch = null;
    if (Math.abs(dx) > 50 && Math.abs(dx) > Math.abs(dy) * 1.5) show(requested + (dx < 0 ? 1 : -1));
  });
  photo.addEventListener("pointercancel", () => { touch = null; });

  carousel.dataset.campaignIndex = "0";
  carousel.classList.add("campaign-ready");
  carousel.querySelector(".campaign-arrows").hidden = slides.length < 2;
  carousel.querySelector(".campaign-pagination").hidden = slides.length < 2;
  const preloadNext = () => { if (slides[1]) load(slides[1]).catch(() => {}); };
  if ("requestIdleCallback" in window) requestIdleCallback(preloadNext, {timeout: 2000});
  else setTimeout(preloadNext, 1200);
})();
