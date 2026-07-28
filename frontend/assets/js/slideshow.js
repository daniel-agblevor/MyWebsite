export function initSlideshow(images) {
  const root = document.querySelector("[data-slideshow]");
  const section = document.querySelector("[data-slideshow-section]");
  if (!root || !section || !images?.length) return;
  section.hidden = false;
  const viewport = root.querySelector("[data-slide-viewport]");
  const dots = root.querySelector("[data-slide-dots]");
  const caption = root.querySelector("[data-slide-caption]");
  const position = root.querySelector("[data-slide-position]");
  let index = 0, timer = null, startX = 0;
  const slides = images.slice(0, 15).map((item, itemIndex) => {
    const slide = document.createElement("div"); slide.className = "slide"; slide.setAttribute("aria-hidden", "true");
    const image = document.createElement("img"); image.src = item.image_url; image.alt = item.alt_text; image.loading = itemIndex ? "lazy" : "eager"; image.decoding = "async";
    slide.append(image); viewport.append(slide);
    const dot = document.createElement("button"); dot.type = "button"; dot.className = "slide-dot"; dot.setAttribute("aria-label", `Go to slide ${itemIndex + 1}`); dot.addEventListener("click", () => go(itemIndex, true)); dots.append(dot);
    return { slide, dot, item };
  });
  const reduced = matchMedia("(prefers-reduced-motion: reduce)").matches;
  const stop = () => { clearInterval(timer); timer = null; };
  const start = () => { if (!reduced && !timer && !document.hidden) timer = setInterval(() => go(index + 1), 6500); };
  function go(next, user = false) {
    index = (next + slides.length) % slides.length;
    slides.forEach(({ slide, dot }, itemIndex) => { const active = itemIndex === index; slide.classList.toggle("active", active); slide.setAttribute("aria-hidden", String(!active)); dot.classList.toggle("active", active); });
    caption.textContent = slides[index].item.caption;
    position.textContent = `${index + 1} / ${slides.length}`;
    if (user) { stop(); start(); }
  }
  root.querySelector("[data-slide-prev]").addEventListener("click", () => go(index - 1, true));
  root.querySelector("[data-slide-next]").addEventListener("click", () => go(index + 1, true));
  root.addEventListener("keydown", (event) => { if (event.key === "ArrowLeft") go(index - 1, true); if (event.key === "ArrowRight") go(index + 1, true); });
  root.addEventListener("pointerdown", (event) => { startX = event.clientX; stop(); });
  root.addEventListener("pointerup", (event) => { if (Math.abs(event.clientX - startX) > 50) go(index + (event.clientX < startX ? 1 : -1), true); else start(); });
  root.addEventListener("mouseenter", stop); root.addEventListener("mouseleave", start); root.addEventListener("focusin", stop); root.addEventListener("focusout", start);
  document.addEventListener("visibilitychange", () => document.hidden ? stop() : start());
  go(0); start();
}

