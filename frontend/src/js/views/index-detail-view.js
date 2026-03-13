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
  const parsed = new Date(rawDate);
  if (Number.isNaN(parsed.getTime())) {
    return "n/a";
  }
  return parsed.toLocaleDateString();
}

function formatNumber(value) {
  return Number(value).toLocaleString(undefined, {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

function formatPercent(value) {
  const numeric = Number(value);
  const sign = numeric > 0 ? "+" : "";
  return `${sign}${numeric.toFixed(2)}%`;
}

function renderAssetComposition(assets) {
  if (!Array.isArray(assets) || !assets.length) {
    return `<p class="muted">No assets found in this index.</p>`;
  }

  const rows = assets
    .map(
      (asset) => `
        <div class="composition-row">
          <span>${escapeHtml(asset.symbol)} (${escapeHtml(asset.name)})</span>
          <strong>${formatNumber(asset.weight)}%</strong>
        </div>
      `
    )
    .join("");

  return `<div class="composition-list">${rows}</div>`;
}

function buildLineChart(points) {
  if (!Array.isArray(points) || points.length < 2) {
    return `<p class="muted">Not enough points to draw a chart.</p>`;
  }

  const width = 900;
  const height = 280;
  const padding = 28;

  const values = points.map((point) => Number(point.value));
  const minValue = Math.min(...values);
  const maxValue = Math.max(...values);
  const range = maxValue - minValue || 1;
  const innerWidth = width - padding * 2;
  const innerHeight = height - padding * 2;

  const polyline = points
    .map((point, index) => {
      const x = padding + (innerWidth * index) / (points.length - 1);
      const y =
        height -
        padding -
        ((Number(point.value) - minValue) / range) * innerHeight;
      return `${x.toFixed(2)},${y.toFixed(2)}`;
    })
    .join(" ");

  return `
    <div class="chart-shell">
      <svg class="chart-svg" viewBox="0 0 ${width} ${height}" role="img" aria-label="Index performance chart">
        <rect x="${padding}" y="${padding}" width="${innerWidth}" height="${innerHeight}" fill="#ffffff"></rect>
        <line x1="${padding}" y1="${height - padding}" x2="${width - padding}" y2="${height - padding}" stroke="#d8dde4"></line>
        <line x1="${padding}" y1="${padding}" x2="${padding}" y2="${height - padding}" stroke="#d8dde4"></line>
        <polyline points="${polyline}" fill="none" stroke="#0b6f59" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"></polyline>
      </svg>
      <div class="chart-foot">
        <span>${formatDate(points[0].date)}</span>
        <span>${formatDate(points[points.length - 1].date)}</span>
      </div>
    </div>
  `;
}

function renderPerformancePanel(performance) {
  if (!performance) {
    return `<p class="muted">No performance data available.</p>`;
  }

  const summary = performance.summary || null;
  const metrics = summary
    ? `
      <div class="metric-grid">
        <article class="metric-card">
          <p class="metric-label">Start value</p>
          <p class="metric-value">${formatNumber(summary.start_value)}</p>
        </article>
        <article class="metric-card">
          <p class="metric-label">End value</p>
          <p class="metric-value">${formatNumber(summary.end_value)}</p>
        </article>
        <article class="metric-card">
          <p class="metric-label">Total return</p>
          <p class="metric-value">${formatPercent(summary.total_return_pct)}</p>
        </article>
      </div>
    `
    : `<p class="muted">Summary metrics were not provided by the backend.</p>`;

  return `
    ${metrics}
    <div class="stack">
      <h3 class="section-title">Historical performance</h3>
      ${buildLineChart(performance.points || [])}
    </div>
  `;
}

export async function mountIndexDetailView(
  root,
  { indexId, loadIndexDetail, loadPerformance, onNavigate }
) {
  root.innerHTML = `
    <section class="panel stack">
      <p class="loading" data-loading-detail>Loading index detail...</p>
      <div data-content hidden></div>
    </section>
  `;

  const loadingDetail = root.querySelector("[data-loading-detail]");
  const content = root.querySelector("[data-content]");

  let indexDetail = null;
  try {
    indexDetail = await loadIndexDetail(indexId);
  } catch (error) {
    const statusCode = error && typeof error === "object" ? error.statusCode : null;
    const message =
      statusCode === 404
        ? "This index does not exist."
        : error instanceof Error
          ? error.message
          : "Failed to load index detail.";

    root.innerHTML = `
      <section class="panel stack">
        <div class="alert alert-error">${escapeHtml(message)}</div>
        <div class="button-row">
          <button class="button button-secondary" type="button" data-back-list>Back to list</button>
        </div>
      </section>
    `;
    root.querySelector("[data-back-list]").addEventListener("click", () => {
      onNavigate(ROUTE_PATHS.indexList);
    });
    return;
  }

  content.hidden = false;
  content.innerHTML = `
    <div class="stack">
      <div class="button-row">
        <button class="button button-secondary" type="button" data-back-list>Back to list</button>
        <button class="button button-secondary" type="button" data-create-index>Create new index</button>
      </div>
      <div>
        <h2 class="page-title">${escapeHtml(indexDetail.name)}</h2>
        <p class="page-subtitle">
          Index ID: ${escapeHtml(indexDetail.id)}<br>
          Created: ${formatDate(indexDetail.created_at)}
        </p>
      </div>
      <section class="stack">
        <h3 class="section-title">Asset composition</h3>
        ${renderAssetComposition(indexDetail.assets)}
      </section>
      <section class="stack" data-performance-section>
        <h3 class="section-title">Performance</h3>
        <p class="loading" data-loading-performance>Loading performance...</p>
      </section>
    </div>
  `;

  loadingDetail.hidden = true;

  content.querySelector("[data-back-list]").addEventListener("click", () => {
    onNavigate(ROUTE_PATHS.indexList);
  });
  content.querySelector("[data-create-index]").addEventListener("click", () => {
    onNavigate(ROUTE_PATHS.createIndex);
  });

  const performanceSection = content.querySelector("[data-performance-section]");
  const loadingPerformance = content.querySelector("[data-loading-performance]");

  try {
    const performance = await loadPerformance(indexId);
    performanceSection.innerHTML = `
      <h3 class="section-title">Performance</h3>
      ${renderPerformancePanel(performance)}
    `;
  } catch (error) {
    const message =
      error instanceof Error
        ? error.message
        : "Failed to load performance data.";
    performanceSection.innerHTML = `
      <h3 class="section-title">Performance</h3>
      <div class="alert alert-error">Performance fetch failed: ${escapeHtml(message)}</div>
    `;
  } finally {
    if (loadingPerformance) {
      loadingPerformance.hidden = true;
    }
  }
}
