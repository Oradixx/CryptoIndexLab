export class ApiError extends Error {
  constructor(message, statusCode, details) {
    super(message);
    this.name = "ApiError";
    this.statusCode = statusCode;
    this.details = details;
  }
}

function joinUrl(baseUrl, path) {
  const normalizedBase = (baseUrl || "").replace(/\/$/, "");
  const normalizedPath = path.startsWith("/") ? path : `/${path}`;
  return `${normalizedBase}${normalizedPath}`;
}

function buildErrorMessage(payload, fallback) {
  if (!payload) {
    return fallback;
  }
  if (typeof payload === "string" && payload.trim()) {
    return payload;
  }
  if (typeof payload.detail === "string" && payload.detail.trim()) {
    return payload.detail;
  }
  return fallback;
}

export async function requestJson({
  baseUrl,
  path,
  method = "GET",
  body = null,
  token = null,
}) {
  const headers = {
    Accept: "application/json",
  };
  if (body !== null) {
    headers["Content-Type"] = "application/json";
  }
  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }

  const response = await fetch(joinUrl(baseUrl, path), {
    method,
    headers,
    body: body !== null ? JSON.stringify(body) : undefined,
  });

  const rawText = await response.text();
  let payload = null;
  if (rawText) {
    try {
      payload = JSON.parse(rawText);
    } catch {
      payload = rawText;
    }
  }

  if (!response.ok) {
    const fallbackMessage = `Request failed with status ${response.status}.`;
    throw new ApiError(buildErrorMessage(payload, fallbackMessage), response.status, payload);
  }

  return payload;
}
