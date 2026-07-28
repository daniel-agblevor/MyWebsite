export function initTheme() {
  const button = document.querySelector("[data-theme-toggle]");
  if (!button) return;
  const update = () => {
    const dark = document.documentElement.dataset.theme === "dark";
    button.setAttribute("aria-label", `Switch to ${dark ? "light" : "dark"} theme`);
    button.setAttribute("aria-pressed", String(dark));
  };
  button.addEventListener("click", () => {
    const next = document.documentElement.dataset.theme === "dark" ? "light" : "dark";
    document.documentElement.dataset.theme = next;
    try { localStorage.setItem("site-theme", next); } catch (_error) {}
    update();
  });
  update();
}

