export const ROUTE_PATHS = {
  login: "/login",
  register: "/register",
  dashboard: "/dashboard",
  createIndex: "/indexes/create",
};

const PROTECTED_PATHS = new Set([ROUTE_PATHS.dashboard, ROUTE_PATHS.createIndex]);
const AUTH_PATHS = new Set([ROUTE_PATHS.login, ROUTE_PATHS.register]);
const KNOWN_PATHS = new Set(Object.values(ROUTE_PATHS));

export function getCurrentPath() {
  const rawHash = window.location.hash.replace(/^#/, "").trim();
  if (!rawHash) {
    return ROUTE_PATHS.login;
  }

  const normalizedPath = rawHash.startsWith("/") ? rawHash : `/${rawHash}`;
  return KNOWN_PATHS.has(normalizedPath) ? normalizedPath : ROUTE_PATHS.login;
}

export function navigate(path) {
  window.location.hash = `#${path}`;
}

export function isProtectedPath(path) {
  return PROTECTED_PATHS.has(path);
}

export function isAuthPath(path) {
  return AUTH_PATHS.has(path);
}
