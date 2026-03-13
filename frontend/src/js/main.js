import { AuthService } from "./services/auth-service.js";
import { IndexService } from "./services/index-service.js";
import {
  ROUTE_PATHS,
  getCurrentPath,
  isAuthPath,
  isProtectedPath,
  navigate,
} from "./router.js";
import { mountCreateIndexView } from "./views/create-index-view.js";
import { mountDashboardView } from "./views/dashboard-view.js";
import { mountLoginView } from "./views/login-view.js";
import { mountRegisterView } from "./views/register-view.js";

const appElement = document.querySelector("#app");

const state = {
  currentUser: null,
  flashMessage: null,
};

function normalizeBaseUrl(value, fallback) {
  if (typeof value !== "string") {
    return fallback;
  }
  const normalized = value.trim();
  if (!normalized) {
    return fallback;
  }
  return normalized.endsWith("/") ? normalized.slice(0, -1) : normalized;
}

function loadConfig() {
  const runtimeConfig = window.__CRYPTO_INDEX_LAB_CONFIG__ || {};
  return {
    api1BaseUrl: normalizeBaseUrl(runtimeConfig.api1BaseUrl, "/api1"),
    api2BaseUrl: normalizeBaseUrl(runtimeConfig.api2BaseUrl, "/api2"),
  };
}

const config = loadConfig();
const authService = new AuthService(config.api1BaseUrl);
const indexService = new IndexService(config.api2BaseUrl);

function setFlashMessage(type, message) {
  state.flashMessage = { type, message };
}

function consumeFlashMessage() {
  const current = state.flashMessage;
  state.flashMessage = null;
  return current;
}

function renderTopbar(activePath) {
  const loggedIn = Boolean(state.currentUser);

  const authLinks = `
    <a class="nav-link ${activePath === ROUTE_PATHS.login ? "active" : ""}" href="#${ROUTE_PATHS.login}">Login</a>
    <a class="nav-link ${activePath === ROUTE_PATHS.register ? "active" : ""}" href="#${ROUTE_PATHS.register}">Register</a>
  `;

  const appLinks = `
    <a class="nav-link ${activePath === ROUTE_PATHS.dashboard ? "active" : ""}" href="#${ROUTE_PATHS.dashboard}">Dashboard</a>
    <a class="nav-link ${activePath === ROUTE_PATHS.createIndex ? "active" : ""}" href="#${ROUTE_PATHS.createIndex}">Create Index</a>
    <button type="button" class="nav-button" data-logout>Logout</button>
  `;

  return `
    <header class="topbar">
      <div class="brand">
        <h1 class="brand-title">CryptoIndexLab</h1>
        <p class="brand-subtitle">MVP interface for auth and custom index creation</p>
      </div>
      <nav class="nav-links">
        ${loggedIn ? appLinks : authLinks}
      </nav>
    </header>
  `;
}

function renderShell(activePath) {
  appElement.innerHTML = `
    <div class="app-shell">
      ${renderTopbar(activePath)}
      <section id="flash-anchor"></section>
      <main id="page-root"></main>
    </div>
  `;

  const logoutButton = appElement.querySelector("[data-logout]");
  if (logoutButton) {
    logoutButton.addEventListener("click", () => {
      authService.clearSession();
      state.currentUser = null;
      setFlashMessage("info", "You are now logged out.");
      navigate(ROUTE_PATHS.login);
    });
  }

  const flashMessage = consumeFlashMessage();
  if (flashMessage) {
    const flashAnchor = appElement.querySelector("#flash-anchor");
    const alert = document.createElement("div");
    alert.className = `alert alert-${flashMessage.type}`;
    alert.textContent = flashMessage.message;
    flashAnchor.appendChild(alert);
  }
}

function renderLoadingState() {
  appElement.innerHTML = `
    <div class="app-shell">
      <section class="panel">
        <p class="loading">Loading application...</p>
      </section>
    </div>
  `;
}

async function restoreSession() {
  const token = authService.getToken();
  if (!token) {
    return;
  }

  try {
    state.currentUser = await authService.getCurrentUser(token);
  } catch {
    authService.clearSession();
    state.currentUser = null;
    setFlashMessage("error", "Your session is invalid or expired. Please login again.");
  }
}

async function handleLogin({ email, password }) {
  const tokenResponse = await authService.login({ email, password });
  authService.storeToken(tokenResponse.access_token);
  state.currentUser = await authService.getCurrentUser(tokenResponse.access_token);
  setFlashMessage("success", "Login successful.");
  navigate(ROUTE_PATHS.dashboard);
}

async function handleRegister({ name, email, password }) {
  await authService.register({ name, email, password });
  await handleLogin({ email, password });
  setFlashMessage("success", "Account created and logged in.");
}

async function renderCurrentRoute() {
  const currentPath = getCurrentPath();

  if (!state.currentUser && isProtectedPath(currentPath)) {
    navigate(ROUTE_PATHS.login);
    return;
  }
  if (state.currentUser && isAuthPath(currentPath)) {
    navigate(ROUTE_PATHS.dashboard);
    return;
  }

  renderShell(currentPath);
  const pageRoot = appElement.querySelector("#page-root");

  if (currentPath === ROUTE_PATHS.login) {
    mountLoginView(pageRoot, {
      onLogin: handleLogin,
      onNavigate: navigate,
    });
    return;
  }

  if (currentPath === ROUTE_PATHS.register) {
    mountRegisterView(pageRoot, {
      onRegister: handleRegister,
      onNavigate: navigate,
    });
    return;
  }

  if (currentPath === ROUTE_PATHS.dashboard) {
    await mountDashboardView(pageRoot, {
      currentUser: state.currentUser,
      onNavigate: navigate,
      loadIndexes: async () => {
        const indexes = await indexService.listIndexes();
        return indexes.filter((indexObj) => {
          return !indexObj.user_id || indexObj.user_id === state.currentUser?.id;
        });
      },
    });
    return;
  }

  if (currentPath === ROUTE_PATHS.createIndex) {
    await mountCreateIndexView(pageRoot, {
      loadAssets: () => indexService.listAvailableAssets(),
      onCreateIndex: ({ name, assets }) =>
        indexService.createIndex({
          name,
          assets,
          userId: state.currentUser?.id || null,
        }),
    });
  }
}

async function bootstrap() {
  renderLoadingState();
  await restoreSession();

  if (!window.location.hash) {
    navigate(state.currentUser ? ROUTE_PATHS.dashboard : ROUTE_PATHS.login);
  } else {
    await renderCurrentRoute();
  }
}

window.addEventListener("hashchange", () => {
  void renderCurrentRoute();
});

void bootstrap();
