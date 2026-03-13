export const ROUTE_PATHS = {
  login: "/login",
  register: "/register",
  dashboard: "/dashboard",
  indexList: "/indexes",
  createIndex: "/indexes/create",
};

const PROTECTED_ROUTE_NAMES = new Set([
  "dashboard",
  "indexList",
  "indexDetail",
  "indexEdit",
  "createIndex",
]);
const AUTH_ROUTE_NAMES = new Set(["login", "register"]);

function normalizeHashPath() {
  const rawHash = window.location.hash.replace(/^#/, "").trim();
  if (!rawHash) {
    return ROUTE_PATHS.login;
  }
  return rawHash.startsWith("/") ? rawHash : `/${rawHash}`;
}

export function buildIndexDetailPath(indexId) {
  return `${ROUTE_PATHS.indexList}/${encodeURIComponent(indexId)}`;
}

export function buildIndexEditPath(indexId) {
  return `${buildIndexDetailPath(indexId)}/edit`;
}

export function getCurrentRoute() {
  const path = normalizeHashPath();

  if (path === ROUTE_PATHS.login) {
    return { name: "login", path, params: {} };
  }
  if (path === ROUTE_PATHS.register) {
    return { name: "register", path, params: {} };
  }
  if (path === ROUTE_PATHS.dashboard) {
    return { name: "dashboard", path, params: {} };
  }
  if (path === ROUTE_PATHS.createIndex) {
    return { name: "createIndex", path, params: {} };
  }
  if (path === ROUTE_PATHS.indexList) {
    return { name: "indexList", path, params: {} };
  }

  if (path.startsWith(`${ROUTE_PATHS.indexList}/`)) {
    try {
      const pathSuffix = path.slice(`${ROUTE_PATHS.indexList}/`.length);
      if (pathSuffix.endsWith("/edit")) {
        const indexId = decodeURIComponent(pathSuffix.slice(0, -"/edit".length));
        if (indexId) {
          return {
            name: "indexEdit",
            path,
            params: { indexId },
          };
        }
      }

      const indexId = decodeURIComponent(pathSuffix);
      if (indexId) {
        return {
          name: "indexDetail",
          path,
          params: { indexId },
        };
      }
    } catch {
      return { name: "unknown", path, params: {} };
    }
  }

  return { name: "unknown", path, params: {} };
}

export function navigate(path) {
  window.location.hash = `#${path}`;
}

export function isProtectedRoute(route) {
  return PROTECTED_ROUTE_NAMES.has(route.name);
}

export function isAuthRoute(route) {
  return AUTH_ROUTE_NAMES.has(route.name);
}
