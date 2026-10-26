// Progressive adaptation of the supplied layered parallax component.
// The server and carousel still own the photos, copy and shopping controls.
(() => {
  const campaign = document.getElementById("campaign-carousel");
  const photo = campaign?.querySelector(".campaign-photo");
  const image = document.getElementById("campaign-image");
  if (!campaign || !photo || !image || image.hidden || campaign.classList.contains("campaign-no-photo")) return;

  const motion = matchMedia(
    "(min-width: 761px) and (min-height: 600px) and (prefers-reduced-motion: no-preference)",
  );
  let enabled = false;
  let visible = true;
  let frame = 0;
  let photoTop = 0;
  let photoHeight = 0;

  function paint() {
    frame = 0;
    if (!enabled) return;
    const distance = Math.min(photoHeight, Math.max(0, window.scrollY - photoTop));
    // No zoom or overscan: at the top, the approved original crop is exact.
    // Both crossfade images move together; arrows remain in their own layer.
    campaign.style.setProperty("--campaign-photo-shift", `${(distance * 0.28).toFixed(2)}px`);
    campaign.style.setProperty("--campaign-copy-shift", `${Math.min(32, distance * 0.08).toFixed(2)}px`);
  }

  function schedule() {
    if (enabled && visible && !frame && !document.hidden) frame = requestAnimationFrame(paint);
  }

  function measure() {
    if (!enabled) return;
    const bounds = photo.getBoundingClientRect();
    photoTop = bounds.top + window.scrollY;
    photoHeight = bounds.height;
    schedule();
  }

  function configure() {
    enabled = motion.matches;
    cancelAnimationFrame(frame);
    frame = 0;
    campaign.classList.toggle("campaign-parallax", enabled);
    window.removeEventListener("scroll", schedule);
    if (enabled) {
      window.addEventListener("scroll", schedule, { passive: true });
      measure();
      // Also restore the correct frame after back/forward scroll restoration.
      cancelAnimationFrame(frame);
      paint();
    } else {
      campaign.style.removeProperty("--campaign-photo-shift");
      campaign.style.removeProperty("--campaign-copy-shift");
    }
  }

  if ("IntersectionObserver" in window) {
    const observer = new IntersectionObserver(([entry]) => {
      visible = entry.isIntersecting;
      campaign.classList.toggle("campaign-parallax-visible", visible);
      if (visible) schedule();
      else {
        cancelAnimationFrame(frame);
        frame = 0;
      }
    });
    observer.observe(photo);
  }
  if ("ResizeObserver" in window) new ResizeObserver(measure).observe(photo);
  motion.addEventListener("change", configure);
  window.addEventListener("resize", measure, { passive: true });
  window.addEventListener("pageshow", configure);
  window.addEventListener("pagehide", () => {
    cancelAnimationFrame(frame);
    frame = 0;
  });
  document.addEventListener("visibilitychange", () => {
    if (document.hidden) {
      cancelAnimationFrame(frame);
      frame = 0;
    } else measure();
  });
  configure();
})();
