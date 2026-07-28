const runtime = window.__SITE_CONFIG__ || {};
const isLocal = ["localhost", "127.0.0.1"].includes(window.location.hostname);

export const API_BASE_URL = String(runtime.API_BASE_URL || (isLocal ? "http://localhost:5000" : "")).replace(/\/$/, "");

export function hasApiConfiguration() {
  return Boolean(API_BASE_URL);
}

