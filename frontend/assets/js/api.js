import { API_BASE_URL, hasApiConfiguration } from "./config.js";

export class ApiError extends Error {
  constructor(message, status = 0, payload = null) {
    super(message);
    this.status = status;
    this.payload = payload;
  }
}

export async function api(path, options = {}) {
  if (!hasApiConfiguration()) throw new ApiError("The website service is not configured.");
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 12000);
  try {
    const response = await fetch(`${API_BASE_URL}${path}`, {
      ...options,
      signal: controller.signal,
      headers: { "Content-Type": "application/json", ...(options.headers || {}) }
    });
    const payload = await response.json().catch(() => null);
    if (!response.ok || !payload?.ok) {
      throw new ApiError(payload?.error?.message || "The request could not be completed.", response.status, payload);
    }
    return payload;
  } catch (error) {
    if (error.name === "AbortError") throw new ApiError("The request took too long. Please try again.");
    throw error;
  } finally {
    clearTimeout(timeout);
  }
}

