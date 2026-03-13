import { ROUTE_PATHS } from "../router.js";

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function renderIndexList(indexes) {
  if (!indexes.length) {
    return `<p class="muted">No indexes yet. Start by creating your first one.</p>`;
  }

  const items = indexes
    .map((indexObj) => {
      const chips = indexObj.assets
        .map(
          (asset) =>
            `<span class="asset-chip">${escapeHtml(asset.symbol)}: ${asset.weight.toFixed(2)}%</span>`
        )
        .join("");
      return `
        <li class="index-item">
          <h3 class="index-item-title">${escapeHtml(indexObj.name)}</h3>
          <p class="muted">Total weight: ${indexObj.total_weight.toFixed(2)}%</p>
          <div class="asset-chip-list">${chips}</div>
        </li>
      `;
    })
    .join("");

  return `<ul class="index-list">${items}</ul>`;
}

export async function mountDashboardView(root, { currentUser, onNavigate, loadIndexes }) {
  const displayName = escapeHtml(currentUser.name || currentUser.email);

  root.innerHTML = `
    <section class="panel stack">
      <div>
        <h2 class="page-title">Dashboard</h2>
        <p class="page-subtitle">Welcome ${displayName}.</p>
      </div>
      <div class="button-row">
        <button class="button button-primary" type="button" data-create-index>Create new index</button>
      </div>
      <div class="stack">
        <h3>Saved Indexes</h3>
        <p class="loading" data-loading>Loading indexes...</p>
        <div class="alert alert-error" data-error hidden></div>
        <div data-list></div>
      </div>
    </section>
  `;

  root.querySelector("[data-create-index]").addEventListener("click", () => {
    onNavigate(ROUTE_PATHS.createIndex);
  });

  const loading = root.querySelector("[data-loading]");
  const errorBox = root.querySelector("[data-error]");
  const listContainer = root.querySelector("[data-list]");

  try {
    const indexes = await loadIndexes();
    listContainer.innerHTML = renderIndexList(indexes);
  } catch (error) {
    errorBox.textContent = error instanceof Error ? error.message : "Failed to load indexes.";
    errorBox.hidden = false;
  } finally {
    loading.hidden = true;
  }
}
