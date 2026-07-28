export function initNavigation() {
  const header = document.querySelector("[data-header]");
  const toggle = document.querySelector("[data-menu-toggle]");
  const nav = document.querySelector("[data-nav]");
  const syncHeader = () => header?.classList.toggle("scrolled", window.scrollY > 20);
  syncHeader();
  addEventListener("scroll", syncHeader, { passive: true });
  if (!toggle || !nav) return;
  const close = () => { nav.classList.remove("open"); toggle.setAttribute("aria-expanded", "false"); };
  toggle.addEventListener("click", () => {
    const open = nav.classList.toggle("open");
    toggle.setAttribute("aria-expanded", String(open));
    toggle.querySelector(".sr-only").textContent = `${open ? "Close" : "Open"} navigation`;
  });
  nav.addEventListener("click", (event) => { if (event.target.matches("a")) close(); });
  addEventListener("keydown", (event) => { if (event.key === "Escape") { close(); toggle.focus(); } });
  addEventListener("resize", () => { if (innerWidth > 1024) close(); }, { passive: true });
}

export function showFeature(name, enabled) {
  document.querySelectorAll(`[data-feature-nav="${name}"]`).forEach((item) => { item.hidden = !enabled; });
  const section = document.querySelector(`[data-feature-section="${name}"]`);
  if (section) section.hidden = !enabled;
}

