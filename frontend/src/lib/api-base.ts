export function getApiBaseUrl(): string {
  const raw = process.env.NEXT_PUBLIC_API_URL?.trim();
  // Single-origin mode: call /api on the current host (behind a reverse proxy).
  // Domain-agnostic, so the production build isn't tied to a baked hostname.
  if (raw && raw.toLowerCase() === "same-origin") {
    return typeof window !== "undefined" ? window.location.origin : "";
  }
  if (raw && raw.toLowerCase() !== "auto") {
    const normalized = raw.replace(/\/+$/, "");
    if (!normalized) {
      throw new Error("NEXT_PUBLIC_API_URL is invalid.");
    }
    return normalized;
  }

  if (typeof window !== "undefined") {
    const protocol = window.location.protocol === "https:" ? "https" : "http";
    const host = window.location.hostname;
    if (host) {
      return `${protocol}://${host}:8000`;
    }
  }

  throw new Error(
    "NEXT_PUBLIC_API_URL is not set and cannot be auto-resolved outside the browser.",
  );
}
