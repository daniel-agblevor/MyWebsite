import { api, ApiError } from "./api.js";

export function initContactForm() {
  const form = document.querySelector("[data-contact-form]");
  if (!form) return;
  let submissionKey = crypto.randomUUID ? crypto.randomUUID() : `${Date.now()}-${Math.random()}`;
  const status = form.querySelector("[data-form-status]");
  const button = form.querySelector("button[type=submit]");
  const label = form.querySelector("[data-submit-label]");
  const clearErrors = () => form.querySelectorAll("[data-error-for]").forEach((node) => { node.textContent = ""; const input = form.elements[node.dataset.errorFor]; input?.removeAttribute("aria-invalid"); });
  const showErrors = (errors) => Object.entries(errors || {}).forEach(([name, message]) => { const node = form.querySelector(`[data-error-for="${name}"]`); const input = form.elements[name]; if (node) node.textContent = message; if (input) input.setAttribute("aria-invalid", "true"); });
  const setStatus = (message = "", type = "") => { status.textContent = message; status.className = `form-status ${type}`; if (message) status.focus(); };
  document.addEventListener("click", (event) => {
    const link = event.target.closest("[data-service-interest]");
    if (!link) return;
    const select = form.elements.service_interest;
    if ([...select.options].some((option) => option.value === link.dataset.serviceInterest)) select.value = link.dataset.serviceInterest;
  });
  form.addEventListener("submit", async (event) => {
    event.preventDefault(); clearErrors(); setStatus();
    if (!form.checkValidity()) { form.reportValidity(); return; }
    const payload = Object.fromEntries(new FormData(form).entries());
    button.disabled = true; label.textContent = "Sending…"; button.setAttribute("aria-busy", "true");
    try {
      const result = await api("/api/contact", { method: "POST", body: JSON.stringify(payload), headers: { "Idempotency-Key": submissionKey } });
      setStatus(result.data.message, result.data.notification_delayed ? "" : "success");
      form.reset(); submissionKey = crypto.randomUUID ? crypto.randomUUID() : `${Date.now()}-${Math.random()}`;
    } catch (error) {
      if (!navigator.onLine) setStatus("You appear to be offline. Your message is still here; reconnect and try again.", "error");
      else if (error instanceof ApiError && error.status === 422) { showErrors(error.payload?.error?.fields); setStatus("Please correct the highlighted fields.", "error"); }
      else if (error instanceof ApiError && error.status === 429) setStatus("Too many attempts were received. Please wait before trying again.", "error");
      else setStatus("Your inquiry could not be sent. Your message is still here; please try again.", "error");
    } finally { button.disabled = false; label.textContent = "Send inquiry"; button.removeAttribute("aria-busy"); }
  });
}

