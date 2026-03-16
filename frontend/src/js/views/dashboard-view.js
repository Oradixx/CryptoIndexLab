import { ROUTE_PATHS } from "../router.js";

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function buildDescription(description) {
  const normalized = String(description || "").trim();
  return normalized || "No description.";
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
            `<span class="asset-chip">${escapeHtml(asset.symbol)}: ${Number(asset.weight).toFixed(2)}%</span>`
        )
        .join("");
      return `
        <li>
          <article
            class="index-item index-item-clickable"
            data-open-index="${escapeHtml(indexObj.id)}"
            role="button"
            tabindex="0"
            aria-label="Open ${escapeHtml(indexObj.name)}"
          >
            <h3 class="index-item-title">${escapeHtml(indexObj.name)}</h3>
            <p class="muted">${escapeHtml(buildDescription(indexObj.description))}</p>
            <p class="muted">Total weight: ${Number(indexObj.total_weight).toFixed(2)}%</p>
            <div class="asset-chip-list">${chips}</div>
          </article>
        </li>
      `;
    })
    .join("");

  return `<ul class="index-list">${items}</ul>`;
}

export async function mountDashboardView(root, { currentUser, onNavigate, onOpenIndex, loadIndexes }) {
  const displayName = escapeHtml(currentUser.name || currentUser.email);

  root.innerHTML = `
    <section class="panel stack">
      <div>
        <h2 class="page-title">Dashboard</h2>
        <p class="page-subtitle">Welcome ${displayName}.</p>
      </div>
      <div class="button-row">
        <button class="button button-primary" type="button" data-create-index>Create new index</button>
        <button class="button button-secondary" type="button" data-view-indexes>View saved indexes</button>
      </div>
      <div class="stack">
        <h3>Saved Indexes</h3>
        <p class="muted">Tip: click an index card to open detail instantly.</p>
        <p class="loading" data-loading>Loading indexes...</p>
        <div class="alert alert-error" data-error hidden></div>
        <div data-list></div>
      </div>
    </section>
  `;

  root.querySelector("[data-create-index]").addEventListener("click", () => {
    onNavigate(ROUTE_PATHS.createIndex);
  });
  root.querySelector("[data-view-indexes]").addEventListener("click", () => {
    onNavigate(ROUTE_PATHS.indexList);
  });

  const loading = root.querySelector("[data-loading]");
  const errorBox = root.querySelector("[data-error]");
  const listContainer = root.querySelector("[data-list]");

  try {
    const indexes = await loadIndexes();
    listContainer.innerHTML = renderIndexList(indexes);
    const openCards = listContainer.querySelectorAll("[data-open-index]");
    openCards.forEach((card) => {
      const open = () => {
        const indexId = card.getAttribute("data-open-index");
        if (indexId) {
          onOpenIndex(indexId);
        }
      };
      card.addEventListener("click", open);
      card.addEventListener("keydown", (event) => {
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          open();
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
