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
          <div class="index-card-actions">
            <button class="button button-secondary button-sm" type="button" data-open-index="${escapeHtml(indexObj.id)}">
              Open
            </button>
            <button class="button button-secondary button-sm" type="button" data-edit-index="${escapeHtml(indexObj.id)}">
              Edit
            </button>
            <button
              class="button button-danger button-sm"
              type="button"
              data-delete-index="${escapeHtml(indexObj.id)}"
              data-index-name="${escapeHtml(indexObj.name)}"
            >
              Delete
            </button>
          </div>
        </article>
      `;
    })
    .join("");
}

export async function mountIndexListView(
  root,
  { loadIndexes, onOpenIndex, onNavigate, onEditIndex, onDeleteIndex }
) {
  root.innerHTML = `
    <section class="panel stack">
      <div>
        <h2 class="page-title">Saved Indexes</h2>
        <p class="page-subtitle">Open, edit, delete, or create indexes from this page.</p>
      </div>
      <div class="button-row">
        <button class="button button-primary" type="button" data-create-index>Create new index</button>
      </div>
      <div class="alert alert-success" data-success hidden></div>
      <div class="alert alert-error" data-error hidden></div>
      <p class="loading" data-loading>Loading indexes...</p>
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
  const successBox = root.querySelector("[data-success]");
  const errorBox = root.querySelector("[data-error]");
  const emptyState = root.querySelector("[data-empty]");
  const grid = root.querySelector("[data-grid]");
  let indexes = [];

  function clearMessages() {
    successBox.hidden = true;
    errorBox.hidden = true;
  }

  function renderGrid() {
    if (!indexes.length) {
      grid.hidden = true;
      emptyState.hidden = false;
      grid.innerHTML = "";
      return;
    }

    emptyState.hidden = true;
    grid.innerHTML = renderIndexCards(indexes);
    grid.hidden = false;
  }

  grid.addEventListener("click", async (event) => {
    const openButton = event.target.closest("[data-open-index]");
    if (openButton) {
      const indexId = openButton.getAttribute("data-open-index");
      if (indexId && typeof onOpenIndex === "function") {
        onOpenIndex(indexId);
      }
      return;
    }

    const editButton = event.target.closest("[data-edit-index]");
    if (editButton) {
      const indexId = editButton.getAttribute("data-edit-index");
      if (indexId && typeof onEditIndex === "function") {
        onEditIndex(indexId);
      }
      return;
    }

    const deleteButton = event.target.closest("[data-delete-index]");
    if (!deleteButton) {
      return;
    }
    clearMessages();

    const indexId = deleteButton.getAttribute("data-delete-index");
    const indexName = deleteButton.getAttribute("data-index-name") || "this index";
    if (!indexId || typeof onDeleteIndex !== "function") {
      return;
    }

    if (!window.confirm(`Delete "${indexName}" permanently?`)) {
      return;
    }

    deleteButton.disabled = true;
    try {
      await onDeleteIndex(indexId);
      indexes = indexes.filter((item) => item.id !== indexId);
      renderGrid();
      successBox.textContent = `Index "${indexName}" deleted.`;
      successBox.hidden = false;
    } catch (error) {
      errorBox.textContent = error instanceof Error ? error.message : "Failed to delete index.";
      errorBox.hidden = false;
    } finally {
      if (deleteButton.isConnected) {
        deleteButton.disabled = false;
      }
    }
  });

  try {
    indexes = await loadIndexes();
    renderGrid();
  } catch (error) {
    errorBox.textContent = error instanceof Error ? error.message : "Failed to load indexes.";
    errorBox.hidden = false;
  } finally {
    loading.hidden = true;
  }
}
