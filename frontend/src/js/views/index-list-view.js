import { ROUTE_PATHS } from "../router.js";

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function formatDate(rawDate) {
  if (!rawDate) {
    return "n/a";
  }
  const parsedDate = new Date(rawDate);
  if (Number.isNaN(parsedDate.getTime())) {
    return "n/a";
  }
  return parsedDate.toLocaleDateString();
}

function buildAssetSummary(assets) {
  if (!Array.isArray(assets) || !assets.length) {
    return "No assets";
  }
  const preview = assets
    .slice(0, 3)
    .map((asset) => `${asset.symbol} ${Number(asset.weight).toFixed(2)}%`)
    .join(", ");
  if (assets.length <= 3) {
    return preview;
  }
  return `${preview}, +${assets.length - 3} more`;
}

function renderIndexCards(indexes) {
  return indexes
    .map((indexObj) => {
      const assetSummary = buildAssetSummary(indexObj.assets);
      return `
        <article class="index-card">
          <h3 class="index-card-title">${escapeHtml(indexObj.name)}</h3>
          <p class="muted">Created: ${formatDate(indexObj.created_at)}</p>
          <p class="muted">Assets: ${escapeHtml(assetSummary)}</p>
          <div class="button-row">
            <button class="button button-secondary" type="button" data-open-index="${escapeHtml(indexObj.id)}">
              Open detail
            </button>
          </div>
        </article>
      `;
    })
    .join("");
}

export async function mountIndexListView(root, { loadIndexes, onOpenIndex, onNavigate }) {
  root.innerHTML = `
    <section class="panel stack">
      <div>
        <h2 class="page-title">Saved Indexes</h2>
        <p class="page-subtitle">Browse all created indexes and open one in detail.</p>
      </div>
      <div class="button-row">
        <button class="button button-primary" type="button" data-create-index>Create new index</button>
      </div>
      <p class="loading" data-loading>Loading indexes...</p>
      <div class="alert alert-error" data-error hidden></div>
      <div data-empty hidden>
        <p class="muted">No index has been created yet.</p>
      </div>
      <section class="index-grid" data-grid hidden></section>
    </section>
  `;

  root.querySelector("[data-create-index]").addEventListener("click", () => {
    onNavigate(ROUTE_PATHS.createIndex);
  });

  const loading = root.querySelector("[data-loading]");
  const errorBox = root.querySelector("[data-error]");
  const emptyState = root.querySelector("[data-empty]");
  const grid = root.querySelector("[data-grid]");

  try {
    const indexes = await loadIndexes();
    if (!indexes.length) {
      emptyState.hidden = false;
      return;
    }

    grid.innerHTML = renderIndexCards(indexes);
    grid.hidden = false;
    const openButtons = grid.querySelectorAll("[data-open-index]");
    openButtons.forEach((button) => {
      button.addEventListener("click", () => {
        const indexId = button.getAttribute("data-open-index");
        if (indexId) {
          onOpenIndex(indexId);
        }
      });
    });
  } catch (error) {
    errorBox.textContent = error instanceof Error ? error.message : "Failed to load indexes.";
    errorBox.hidden = false;
  } finally {
    loading.hidden = true;
  }
}
