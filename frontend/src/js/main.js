import { AuthService } from "./services/auth-service.js";
import { IndexService } from "./services/index-service.js";
import {
  ROUTE_PATHS,
  buildIndexEditPath,
  buildIndexDetailPath,
  getCurrentRoute,
  isAuthRoute,
  isProtectedRoute,
  navigate,
} from "./router.js";
import { mountCreateIndexView } from "./views/create-index-view.js";
import { mountDashboardView } from "./views/dashboard-view.js";
import { mountEditIndexView } from "./views/edit-index-view.js";
import { mountIndexDetailView } from "./views/index-detail-view.js";
import { mountIndexListView } from "./views/index-list-view.js";
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
const indexService = new IndexService(config.api2BaseUrl, () => authService.getToken());

function setFlashMessage(type, message) {
  state.flashMessage = { type, message };
}

function consumeFlashMessage() {
  const current = state.flashMessage;
  state.flashMessage = null;
  return current;
}

function renderTopbar(route) {
  const loggedIn = Boolean(state.currentUser);
  const showBackToList = route.name === "indexDetail" || route.name === "indexEdit";

  const authLinks = `
    <a class="nav-link ${route.name === "login" ? "active" : ""}" href="#${ROUTE_PATHS.login}">Login</a>
    <a class="nav-link ${route.name === "register" ? "active" : ""}" href="#${ROUTE_PATHS.register}">Register</a>
  `;

  const appLinks = `
    ${showBackToList
      ? `<a class="nav-link" href="#${ROUTE_PATHS.indexList}">Back to list</a>`
      : ""}
    <a class="nav-link ${route.name === "dashboard" ? "active" : ""}" href="#${ROUTE_PATHS.dashboard}">Dashboard</a>
    <button type="button" class="nav-button" data-logout>Logout</button>
  `;

  return `
    <header class="topbar">
      <div class="brand">
        <h1 class="brand-title">CryptoIndexLab</h1>
      </div>
      <nav class="nav-links">
        ${loggedIn ? appLinks : authLinks}
      </nav>
    </header>
  `;
}

function renderShell(route) {
  appElement.innerHTML = `
    <div class="app-shell">
      ${renderTopbar(route)}
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

async function loadUserIndexes() {
  return runProtectedApiCall(() => indexService.listIndexes());
}

function normalizeApiError(error) {
  if (error && typeof error === "object" && "statusCode" in error) {
    return error;
  }
  return null;
}

async function runProtectedApiCall(operation) {
  try {
    return await operation();
  } catch (error) {
    const apiError = normalizeApiError(error);
    if (apiError && apiError.statusCode === 401) {
      authService.clearSession();
      state.currentUser = null;
      setFlashMessage("error", "Your session expired. Please login again.");
      navigate(ROUTE_PATHS.login);
      throw new Error("Unauthorized.");
    }
    throw error;
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
  const route = getCurrentRoute();

  if (route.name === "unknown") {
    navigate(state.currentUser ? ROUTE_PATHS.dashboard : ROUTE_PATHS.login);
    return;
  }

  if (!state.currentUser && isProtectedRoute(route)) {
    navigate(ROUTE_PATHS.login);
    return;
  }
  if (state.currentUser && isAuthRoute(route)) {
    navigate(ROUTE_PATHS.dashboard);
    return;
  }

  renderShell(route);
  const pageRoot = appElement.querySelector("#page-root");

  if (route.name === "login") {
    mountLoginView(pageRoot, {
      onLogin: handleLogin,
      onNavigate: navigate,
    });
    return;
  }

  if (route.name === "register") {
    mountRegisterView(pageRoot, {
      onRegister: handleRegister,
      onNavigate: navigate,
    });
    return;
  }

  if (route.name === "dashboard") {
    await mountDashboardView(pageRoot, {
      currentUser: state.currentUser,
      onNavigate: navigate,
      onOpenIndex: (indexId) => navigate(buildIndexDetailPath(indexId)),
      loadIndexes: loadUserIndexes,
    });
    return;
  }

  if (route.name === "indexList") {
    await mountIndexListView(pageRoot, {
      loadIndexes: loadUserIndexes,
      onNavigate: navigate,
      onOpenIndex: (indexId) => navigate(buildIndexDetailPath(indexId)),
      onEditIndex: (indexId) => navigate(buildIndexEditPath(indexId)),
      onDeleteIndex: (indexId) =>
        runProtectedApiCall(() => indexService.deleteIndex(indexId)),
    });
    return;
  }

  if (route.name === "indexDetail") {
    await mountIndexDetailView(pageRoot, {
      indexId: route.params.indexId,
      onNavigate: navigate,
      loadIndexDetail: (indexId) =>
        runProtectedApiCall(() => indexService.getIndex(indexId)),
      loadPerformance: (indexId) =>
        runProtectedApiCall(() => indexService.getIndexPerformance(indexId)),
      loadIndexes: loadUserIndexes,
      loadMarketHistory: (symbol) =>
        runProtectedApiCall(() => indexService.getMarketHistory(symbol)),
    });
    return;
  }

  if (route.name === "indexEdit") {
    await mountEditIndexView(pageRoot, {
      indexId: route.params.indexId,
      onNavigate: navigate,
      loadAssets: () => indexService.listAvailableAssets(),
      loadIndexDetail: (indexId) =>
        runProtectedApiCall(() => indexService.getIndex(indexId)),
      onUpdateIndex: (indexId, payload) =>
        runProtectedApiCall(() => indexService.updateIndex(indexId, payload)),
    });
    return;
  }

  if (route.name === "createIndex") {
    await mountCreateIndexView(pageRoot, {
      loadAssets: () => indexService.listAvailableAssets(),
      onCreateIndex: ({ name, description, assets }) =>
        runProtectedApiCall(() =>
          indexService.createIndex({
            name,
            description,
            assets,
          })
        ),
      onCreated: (createdIndex) => {
        setFlashMessage("success", `Index "${createdIndex.name}" created.`);
        navigate(ROUTE_PATHS.dashboard);
      },
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
