let opener = null;

export function initBlogDialog() {
  const dialog = document.querySelector("[data-blog-dialog]");
  const close = document.querySelector("[data-dialog-close]");
  if (!dialog || !close) return;
  const closeDialog = () => dialog.close();
  close.addEventListener("click", closeDialog);
  dialog.addEventListener("click", (event) => {
    const rect = dialog.getBoundingClientRect();
    const inside = event.clientX >= rect.left && event.clientX <= rect.right && event.clientY >= rect.top && event.clientY <= rect.bottom;
    if (!inside) closeDialog();
  });
  dialog.addEventListener("close", () => { document.body.classList.remove("modal-open"); opener?.focus(); opener = null; });
}

export function openBlogDialog(post, trigger) {
  const dialog = document.querySelector("[data-blog-dialog]");
  if (!dialog) return;
  opener = trigger;
  document.querySelector("[data-dialog-title]").textContent = post.title;
  const body = document.querySelector("[data-dialog-body]");
  body.innerHTML = window.DOMPurify ? window.DOMPurify.sanitize(post.full_content, { USE_PROFILES: { html: true } }) : "";
  const link = document.querySelector("[data-dialog-link]");
  if (post.linkedin_url) { link.href = post.linkedin_url; link.hidden = false; } else { link.hidden = true; link.removeAttribute("href"); }
  document.body.classList.add("modal-open");
  dialog.showModal();
  document.querySelector("[data-dialog-close]").focus();
}

