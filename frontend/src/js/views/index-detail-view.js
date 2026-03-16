import { ROUTE_PATHS } from "../router.js";

const CANDLE_SIZE_OPTIONS = [
  { key: "1d", label: "1D" },
  { key: "1w", label: "1W" },
  { key: "1m", label: "1M" },
];

const CHART_MODES = [
  { key: "candles", label: "Candles" },
  { key: "line", label: "Line" },
];

const INDICATOR_LINE_STYLES = [
  { value: 0, label: "Solid" },
  { value: 1, label: "Dotted" },
  { value: 2, label: "Dashed" },
];

const INDICATOR_SOURCE_OPTIONS = [
  { value: "close", label: "Close" },
  { value: "open", label: "Open" },
  { value: "high", label: "High" },
  { value: "low", label: "Low" },
  { value: "hl2", label: "HL2 (High + Low) / 2" },
  { value: "hlc3", label: "HLC3 (High + Low + Close) / 3" },
  { value: "ohlc4", label: "OHLC4 (Open + High + Low + Close) / 4" },
];

const BOLLINGER_BASIS_OPTIONS = [
  { value: "sma", label: "SMA Basis" },
  { value: "ema", label: "EMA Basis" },
];

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

function buildDescription(description) {
  const normalized = String(description || "").trim();
  return normalized || "No description.";
}

function formatPercent(value) {
  const numeric = Number(value);
  const sign = numeric > 0 ? "+" : "";
  return `${sign}${numeric.toFixed(2)}%`;
}

function normalizePoints(points) {
  if (!Array.isArray(points)) {
    return [];
  }

  return points
    .map((point) => ({
      date: String(point.date || ""),
      value: Number(point.value),
    }))
    .filter((point) => point.date && Number.isFinite(point.value))
    .sort((left, right) => new Date(left.date).getTime() - new Date(right.date).getTime());
}

function normalizeTimeKey(value) {
  if (!value) {
    return null;
  }

  if (typeof value === "string") {
    return value;
  }

  if (typeof value === "number") {
    return new Date(value * 1000).toISOString().slice(0, 10);
  }

  if (
    typeof value === "object" &&
    Number.isFinite(value.year) &&
    Number.isFinite(value.month) &&
    Number.isFinite(value.day)
  ) {
    const month = String(value.month).padStart(2, "0");
    const day = String(value.day).padStart(2, "0");
    return `${value.year}-${month}-${day}`;
  }

  return null;
}

function toChartCandles(points) {
  return points.map((point, index) => {
    const close = Number(point.value);
    const open = index === 0 ? close : Number(points[index - 1].value);
    const deltaRatio = open === 0 ? 0 : Math.abs(close - open) / open;
    const spreadRatio = Math.min(0.015, Math.max(0.0025, deltaRatio * 0.65));
    const high = Math.max(open, close) * (1 + spreadRatio);
    const low = Math.max(0, Math.min(open, close) * (1 - spreadRatio));

    return {
      time: point.date,
      open,
      high,
      low,
      close,
      changePct: open === 0 ? 0 : ((close / open) - 1) * 100,
      volumeProxy: Math.abs(close - open),
    };
  });
}

function toIsoWeekKey(dateString) {
  const date = new Date(dateString);
  if (Number.isNaN(date.getTime())) {
    return "invalid";
  }
  const utcDate = new Date(Date.UTC(date.getFullYear(), date.getMonth(), date.getDate()));
  const day = utcDate.getUTCDay() || 7;
  utcDate.setUTCDate(utcDate.getUTCDate() + 4 - day);
  const yearStart = new Date(Date.UTC(utcDate.getUTCFullYear(), 0, 1));
  const weekNo = Math.ceil((((utcDate - yearStart) / 86400000) + 1) / 7);
  return `${utcDate.getUTCFullYear()}-W${String(weekNo).padStart(2, "0")}`;
}

function aggregateCandles(candles, getBucketKey) {
  const buckets = [];
  let activeBucket = null;

  candles.forEach((candle) => {
    const bucketKey = getBucketKey(candle.time);
    if (!activeBucket || activeBucket.bucketKey !== bucketKey) {
      activeBucket = {
        bucketKey,
        time: candle.time,
        open: candle.open,
        high: candle.high,
        low: candle.low,
        close: candle.close,
        volumeProxy: candle.volumeProxy,
      };
      buckets.push(activeBucket);
      return;
    }

    activeBucket.time = candle.time;
    activeBucket.high = Math.max(activeBucket.high, candle.high);
    activeBucket.low = Math.min(activeBucket.low, candle.low);
    activeBucket.close = candle.close;
    activeBucket.volumeProxy += candle.volumeProxy;
  });

  return buckets.map((bucket) => ({
    time: bucket.time,
    open: bucket.open,
    high: bucket.high,
    low: bucket.low,
    close: bucket.close,
    changePct: bucket.open === 0 ? 0 : ((bucket.close / bucket.open) - 1) * 100,
    volumeProxy: bucket.volumeProxy,
  }));
}

function buildCandlesForSize(rawPoints, candleSizeKey) {
  const dailyCandles = toChartCandles(rawPoints);
  if (!dailyCandles.length) {
    return [];
  }

  if (candleSizeKey === "1w") {
    return aggregateCandles(dailyCandles, (time) => toIsoWeekKey(time));
  }

  if (candleSizeKey === "1m") {
    return aggregateCandles(dailyCandles, (time) => String(time).slice(0, 7));
  }

  // Daily source data is used for non-aggregated mode (1D).
  return dailyCandles;
}

function buildLineData(candles) {
  return candles.map((candle) => ({ time: candle.time, value: candle.close }));
}

function getIndicatorSourceValue(candle, sourceKey = "close") {
  if (sourceKey === "open") {
    return candle.open;
  }
  if (sourceKey === "high") {
    return candle.high;
  }
  if (sourceKey === "low") {
    return candle.low;
  }
  if (sourceKey === "hl2") {
    return (candle.high + candle.low) / 2;
  }
  if (sourceKey === "hlc3") {
    return (candle.high + candle.low + candle.close) / 3;
  }
  if (sourceKey === "ohlc4") {
    return (candle.open + candle.high + candle.low + candle.close) / 4;
  }
  return candle.close;
}

function computeSma(candles, length, sourceKey = "close") {
  const result = [];
  for (let index = 0; index < candles.length; index += 1) {
    if (index + 1 < length) {
      continue;
    }

    let total = 0;
    for (let rolling = index - length + 1; rolling <= index; rolling += 1) {
      total += getIndicatorSourceValue(candles[rolling], sourceKey);
    }
    result.push({
      time: candles[index].time,
      value: total / length,
    });
  }
  return result;
}

function computeEma(candles, length, sourceKey = "close", smoothing = 1) {
  if (!Number.isFinite(length) || length <= 1 || candles.length < length) {
    return [];
  }

  const normalizedSmoothing = Number.isFinite(smoothing)
    ? Math.max(0.2, Math.min(3, smoothing))
    : 1;
  const smoothingFactor = Math.max(
    0.01,
    Math.min(1, (2 / (length + 1)) * normalizedSmoothing)
  );
  const result = [];

  let seedTotal = 0;
  for (let index = 0; index < length; index += 1) {
    seedTotal += getIndicatorSourceValue(candles[index], sourceKey);
  }
  let previousEma = seedTotal / length;
  result.push({
    time: candles[length - 1].time,
    value: previousEma,
  });

  for (let index = length; index < candles.length; index += 1) {
    const currentValue = getIndicatorSourceValue(candles[index], sourceKey);
    previousEma = (currentValue - previousEma) * smoothingFactor + previousEma;
    result.push({
      time: candles[index].time,
      value: previousEma,
    });
  }

  return result;
}

function computeBollinger(
  candles,
  length = 20,
  stdDevMultiplier = 2,
  sourceKey = "close",
  basisType = "sma",
  basisSmoothing = 1
) {
  if (!Number.isFinite(length) || length <= 1 || candles.length < length) {
    return { upper: [], lower: [] };
  }

  const basisSeries =
    basisType === "ema"
      ? computeEma(candles, length, sourceKey, basisSmoothing)
      : computeSma(candles, length, sourceKey);
  const basisByTime = new Map(
    basisSeries.map((point) => [point.time, point.value])
  );

  const upper = [];
  const lower = [];

  for (let index = length - 1; index < candles.length; index += 1) {
    const window = candles.slice(index - length + 1, index + 1);
    const mean = basisByTime.get(candles[index].time);
    if (!Number.isFinite(mean)) {
      continue;
    }

    const sourceValues = window.map((candle) =>
      getIndicatorSourceValue(candle, sourceKey)
    );
    const variance =
      sourceValues.reduce((sum, value) => sum + (value - mean) ** 2, 0) / length;
    const standardDeviation = Math.sqrt(variance);
    const offset = standardDeviation * stdDevMultiplier;

    upper.push({
      time: candles[index].time,
      value: mean + offset,
    });
    lower.push({
      time: candles[index].time,
      value: mean - offset,
    });
  }

  return { upper, lower };
}

function normalizeIndicatorLength(rawValue, fallback) {
  const parsed = Number(rawValue);
  if (!Number.isFinite(parsed)) {
    return fallback;
  }
  return Math.max(2, Math.min(365, Math.round(parsed)));
}

function normalizeIndicatorMultiplier(rawValue, fallback) {
  const parsed = Number(rawValue);
  if (!Number.isFinite(parsed)) {
    return fallback;
  }
  return Math.max(0.5, Math.min(5, Number(parsed.toFixed(2))));
}

function normalizeIndicatorSource(rawValue, fallback) {
  if (typeof rawValue !== "string") {
    return fallback;
  }
  const normalized = rawValue.trim().toLowerCase();
  const isAllowed = INDICATOR_SOURCE_OPTIONS.some(
    (option) => option.value === normalized
  );
  return isAllowed ? normalized : fallback;
}

function normalizeIndicatorSmoothing(rawValue, fallback) {
  const parsed = Number(rawValue);
  if (!Number.isFinite(parsed)) {
    return fallback;
  }
  return Math.max(0.2, Math.min(3, Number(parsed.toFixed(2))));
}

function normalizeBollingerBasisType(rawValue, fallback) {
  if (typeof rawValue !== "string") {
    return fallback;
  }
  const normalized = rawValue.trim().toLowerCase();
  const isAllowed = BOLLINGER_BASIS_OPTIONS.some(
    (option) => option.value === normalized
  );
  return isAllowed ? normalized : fallback;
}

function normalizeIndicatorColor(rawValue, fallback) {
  if (typeof rawValue !== "string") {
    return fallback;
  }

  const normalized = rawValue.trim();
  if (/^#[0-9a-fA-F]{6}$/.test(normalized)) {
    return normalized.toLowerCase();
  }
  return fallback;
}

function normalizeIndicatorLineWidth(rawValue, fallback) {
  const parsed = Number(rawValue);
  if (!Number.isFinite(parsed)) {
    return fallback;
  }
  return Math.max(1, Math.min(5, Math.round(parsed)));
}

function normalizeIndicatorLineStyle(rawValue, fallback) {
  const parsed = Number(rawValue);
  if (!Number.isFinite(parsed)) {
    return fallback;
  }
  if (parsed !== 0 && parsed !== 1 && parsed !== 2) {
    return fallback;
  }
  return parsed;
}

function computeWindowStats(candles) {
  const firstOpen = candles[0]?.open ?? 0;
  const lastClose = candles[candles.length - 1]?.close ?? 0;
  const totalReturn = firstOpen === 0 ? 0 : ((lastClose / firstOpen) - 1) * 100;
  const high = Math.max(...candles.map((candle) => candle.high));
  const low = Math.min(...candles.map((candle) => candle.low));

  const closes = candles.map((candle) => candle.close);
  const returns = [];
  for (let index = 1; index < closes.length; index += 1) {
    const prev = closes[index - 1];
    const current = closes[index];
    if (prev > 0) {
      returns.push((current / prev) - 1);
    }
  }
  const avgReturn = returns.length
    ? returns.reduce((sum, current) => sum + current, 0) / returns.length
    : 0;
  const variance = returns.length
    ? returns.reduce((sum, current) => sum + (current - avgReturn) ** 2, 0) / returns.length
    : 0;
  const volatility = Math.sqrt(variance) * 100;

  let peak = closes[0] || 0;
  let maxDrawdown = 0;
  closes.forEach((closeValue) => {
    if (closeValue > peak) {
      peak = closeValue;
      return;
    }
    if (peak > 0) {
      const drawdown = ((closeValue - peak) / peak) * 100;
      if (drawdown < maxDrawdown) {
        maxDrawdown = drawdown;
      }
    }
  });

  return {
    start: firstOpen,
    end: lastClose,
    totalReturn,
    high,
    low,
    volatility,
    maxDrawdown,
    points: candles.length,
  };
}

function renderAssetComposition(assets) {
  if (!Array.isArray(assets) || !assets.length) {
    return `<p class="muted">No assets found in this index.</p>`;
  }

  const totalWeight = assets.reduce((sum, asset) => {
    const numericWeight = Number(asset.weight);
    return Number.isFinite(numericWeight) ? sum + numericWeight : sum;
  }, 0);

  const rows = assets
    .map((asset) => {
      const numericWeight = Number(asset.weight);
      const safeWeight = Number.isFinite(numericWeight) ? numericWeight : 0;
      const clampedWeight = Math.max(0, Math.min(100, safeWeight));

      return `
        <div class="allocation-line">
          <div class="allocation-head">
            <span>${escapeHtml(asset.symbol)} <span class="muted">(${escapeHtml(asset.name)})</span></span>
            <strong>${formatNumber(safeWeight)}%</strong>
          </div>
          <div class="allocation-track">
            <span class="allocation-fill" style="width: ${clampedWeight}%"></span>
          </div>
        </div>
      `;
    })
    .join("");

  return `
    <p class="composition-summary">
      ${assets.length} assets, total weight ${formatNumber(totalWeight)}%
    </p>
    <div class="allocation-list">${rows}</div>
  `;
}

function renderCandleSizeButtons(activeCandleSizeKey) {
  return CANDLE_SIZE_OPTIONS.map(
    (option) => `
      <button
        class="button button-secondary timeline-button ${option.key === activeCandleSizeKey ? "active" : ""}"
        type="button"
        data-candle-size-key="${option.key}"
      >
        ${option.label}
      </button>
    `
  ).join("");
}

function renderChartModeButtons(activeModeKey) {
  return CHART_MODES.map(
    (mode) => `
      <button
        class="button button-secondary chart-mode-button ${mode.key === activeModeKey ? "active" : ""}"
        type="button"
        data-chart-mode="${mode.key}"
      >
        ${mode.label}
      </button>
    `
  ).join("");
}

function renderIndicatorList(indicators, selectedKey) {
  const entries = Object.entries(indicators);
  if (!entries.length) {
    return `<p class="muted">No indicator available.</p>`;
  }

  return entries
    .map(([key, indicator]) => {
      const selectedClass = key === selectedKey ? "active" : "";
      const enabledClass = indicator.enabled ? "enabled" : "";
      return `
        <div class="indicator-list-item ${selectedClass} ${enabledClass}">
          <button
            class="indicator-toggle-button"
            type="button"
            data-indicator-toggle="${key}"
            aria-pressed="${indicator.enabled ? "true" : "false"}"
          >
            <span>${escapeHtml(indicator.label)}</span>
            <span class="indicator-list-state">${indicator.enabled ? "On" : "Off"}</span>
          </button>
          <button
            class="indicator-config-button"
            type="button"
            data-indicator-config="${key}"
            aria-label="Open ${escapeHtml(indicator.label)} settings"
            title="Settings"
          >
            ⚙
          </button>
        </div>
      `;
    })
    .join("");
}

function renderIndicatorDetail(indicatorKey, indicator) {
  if (!indicatorKey || !indicator) {
    return `<p class="muted">Select an indicator to edit its parameters.</p>`;
  }

  const lineStyleOptions = INDICATOR_LINE_STYLES.map(
    (option) => `
      <option value="${option.value}" ${option.value === indicator.lineStyle ? "selected" : ""}>
        ${option.label}
      </option>
    `
  ).join("");

  const sourceOptions = INDICATOR_SOURCE_OPTIONS.map(
    (option) => `
      <option value="${option.value}" ${option.value === indicator.source ? "selected" : ""}>
        ${option.label}
      </option>
    `
  ).join("");

  const bollingerBasisOptions = BOLLINGER_BASIS_OPTIONS.map(
    (option) => `
      <option value="${option.value}" ${option.value === indicator.basisType ? "selected" : ""}>
        ${option.label}
      </option>
    `
  ).join("");

  return `
    <article class="indicator-detail-window">
      <header class="indicator-detail-head" data-indicator-drag-handle>
        <div>
          <h6>${escapeHtml(indicator.label)}</h6>
          <p class="indicator-detail-subtitle">Customize style and calculation parameters.</p>
        </div>
        <button class="indicator-detail-close" type="button" data-indicator-detail-close>Close</button>
      </header>
      <div class="indicator-detail-grid">
        <div class="indicator-switch-row indicator-param-full">
          <button
            class="indicator-enable-button ${indicator.enabled ? "active" : ""}"
            type="button"
            data-indicator-enable="${indicatorKey}"
          >
            ${indicator.enabled ? "Enabled" : "Disabled"}
          </button>
          <p class="indicator-switch-hint">Toggle visibility on chart.</p>
        </div>
        <label class="indicator-param">
          <span class="indicator-param-label">Length</span>
          <input
            type="number"
            min="2"
            max="365"
            step="1"
            value="${indicator.length}"
            data-indicator-key="${indicatorKey}"
            data-indicator-field="length"
          >
        </label>
        <label class="indicator-param">
          <span class="indicator-param-label">Source</span>
          <select
            data-indicator-key="${indicatorKey}"
            data-indicator-field="source"
          >
            ${sourceOptions}
          </select>
        </label>
        ${
          indicator.type === "ema"
            ? `
              <label class="indicator-param">
                <span class="indicator-param-label">Smoothing</span>
                <input
                  type="number"
                  min="0.2"
                  max="3"
                  step="0.1"
                  value="${indicator.smoothing}"
                  data-indicator-key="${indicatorKey}"
                  data-indicator-field="smoothing"
                >
              </label>
            `
            : ""
        }
        ${
          indicator.type === "bb"
            ? `
              <label class="indicator-param">
                <span class="indicator-param-label">StdDev</span>
                <input
                  type="number"
                  min="0.5"
                  max="5"
                  step="0.1"
                  value="${indicator.multiplier}"
                  data-indicator-key="${indicatorKey}"
                  data-indicator-field="multiplier"
                >
              </label>
              <label class="indicator-param">
                <span class="indicator-param-label">Basis</span>
                <select
                  data-indicator-key="${indicatorKey}"
                  data-indicator-field="basisType"
                >
                  ${bollingerBasisOptions}
                </select>
              </label>
              <label class="indicator-param">
                <span class="indicator-param-label">Basis EMA Smooth</span>
                <input
                  type="number"
                  min="0.2"
                  max="3"
                  step="0.1"
                  value="${indicator.basisSmoothing}"
                  data-indicator-key="${indicatorKey}"
                  data-indicator-field="basisSmoothing"
                  ${indicator.basisType === "ema" ? "" : "disabled"}
                >
              </label>
            `
            : ""
        }
        <label class="indicator-param">
          <span class="indicator-param-label">Color</span>
          <input
            type="color"
            value="${indicator.color}"
            data-indicator-key="${indicatorKey}"
            data-indicator-field="color"
          >
        </label>
        <label class="indicator-param">
          <span class="indicator-param-label">Line Width</span>
          <div class="indicator-inline-field">
            <input
              type="range"
              min="1"
              max="5"
              step="1"
              value="${indicator.lineWidth}"
              data-indicator-key="${indicatorKey}"
              data-indicator-field="lineWidth"
            >
            <span class="indicator-inline-value">${indicator.lineWidth}px</span>
          </div>
        </label>
        <label class="indicator-param indicator-param-full">
          <span class="indicator-param-label">Line Style</span>
          <select
            data-indicator-key="${indicatorKey}"
            data-indicator-field="lineStyle"
          >
            ${lineStyleOptions}
          </select>
        </label>
      </div>
    </article>
  `;
}

function renderInsightMetric(label, value, toneClass = "") {
  const className = toneClass ? `insight-value ${toneClass}` : "insight-value";
  return `
    <p class="insight-metric">
      <span class="muted">${label}</span>
      <strong class="${className}">${value}</strong>
    </p>
  `;
}

function renderWindowStats(stats) {
  const drawdownTone = stats.maxDrawdown <= 0 ? "metric-value-negative" : "metric-value-positive";
  return `
    <p class="metric-label">Window Snapshot</p>
    <div class="insight-metrics insight-metrics-wide">
      ${renderInsightMetric("Start", formatNumber(stats.start))}
      ${renderInsightMetric("End", formatNumber(stats.end))}
      ${renderInsightMetric(
        "Return",
        formatPercent(stats.totalReturn),
        stats.totalReturn >= 0 ? "metric-value-positive" : "metric-value-negative"
      )}
      ${renderInsightMetric("High", formatNumber(stats.high))}
      ${renderInsightMetric("Low", formatNumber(stats.low))}
      ${renderInsightMetric("Volatility", formatPercent(stats.volatility))}
      ${renderInsightMetric("Max Drawdown", formatPercent(stats.maxDrawdown), drawdownTone)}
      ${renderInsightMetric("Candles", String(stats.points))}
    </div>
  `;
}

function renderCandleDetails(candle) {
  if (!candle) {
    return `
      <p class="metric-label">Selected Candle</p>
      <p class="muted">Move your cursor over the chart to inspect OHLC values.</p>
    `;
  }

  return `
    <p class="metric-label">Selected Candle: ${formatDate(candle.time)}</p>
    <div class="insight-metrics">
      ${renderInsightMetric("Open", formatNumber(candle.open))}
      ${renderInsightMetric("High", formatNumber(candle.high))}
      ${renderInsightMetric("Low", formatNumber(candle.low))}
      ${renderInsightMetric("Close", formatNumber(candle.close))}
      ${renderInsightMetric(
        "Change",
        formatPercent(candle.changePct),
        candle.changePct >= 0 ? "metric-value-positive" : "metric-value-negative"
      )}
    </div>
  `;
}

function mountPerformanceExplorer(performanceRoot, performance) {
  const LightweightCharts = window.LightweightCharts;
  if (!LightweightCharts || typeof LightweightCharts.createChart !== "function") {
    performanceRoot.innerHTML = `
      <div class="alert alert-error">
        Chart library failed to load. Rebuild frontend and hard refresh browser cache.
      </div>
    `;
    return;
  }

  const rawPoints = normalizePoints(performance?.points || []);
  if (rawPoints.length < 2) {
    performanceRoot.innerHTML = `<p class="muted">Not enough performance points to render chart data.</p>`;
    return;
  }

  const state = {
    candleSizeKey: "1d",
    chartMode: "candles",
    indicators: {
      sma20: {
        label: "SMA 20",
        type: "sma",
        enabled: true,
        length: 20,
        source: "close",
        color: "#ffd166",
        lineWidth: 2,
        lineStyle: 2,
      },
      sma50: {
        label: "SMA 50",
        type: "sma",
        enabled: false,
        length: 50,
        source: "close",
        color: "#e88cff",
        lineWidth: 2,
        lineStyle: 0,
      },
      sma100: {
        label: "SMA 100",
        type: "sma",
        enabled: false,
        length: 100,
        source: "close",
        color: "#8aa4ff",
        lineWidth: 2,
        lineStyle: 2,
      },
      ema20: {
        label: "EMA 20",
        type: "ema",
        enabled: false,
        length: 20,
        source: "close",
        smoothing: 1,
        color: "#ffb86b",
        lineWidth: 2,
        lineStyle: 0,
      },
      ema50: {
        label: "EMA 50",
        type: "ema",
        enabled: false,
        length: 50,
        source: "close",
        smoothing: 1,
        color: "#b295ff",
        lineWidth: 2,
        lineStyle: 2,
      },
      bb20: {
        label: "BB 20",
        type: "bb",
        enabled: false,
        length: 20,
        multiplier: 2,
        source: "close",
        basisType: "sma",
        basisSmoothing: 1,
        color: "#78d6ff",
        lineWidth: 1,
        lineStyle: 1,
      },
    },
    selectedIndicatorKey: "sma20",
    candles: [],
    candleByTime: new Map(),
    lastCandle: null,
  };
  const modalState = {
    position: null,
    pointerId: null,
    offsetX: 0,
    offsetY: 0,
  };

  performanceRoot.innerHTML = `
    <section class="performance-explorer stack">
      <div class="chart-panel">
        <div class="chart-controls">
          <div class="control-cluster">
            <p class="control-label">Candle Size</p>
            <div class="control-buttons" data-candle-size-row></div>
          </div>
          <div class="control-cluster">
            <p class="control-label">Style</p>
            <div class="control-buttons" data-chart-mode-row></div>
          </div>
          <div class="control-cluster control-cluster-indicators">
            <p class="control-label">Indicators</p>
            <button class="indicator-open-button" type="button" data-indicator-open>
              Indicators
              <span class="indicator-open-count" data-indicator-count></span>
            </button>
            <section class="indicator-panel" data-indicator-panel hidden>
              <div class="indicator-panel-head">
                <h5>Indicators</h5>
                <button class="indicator-close-button" type="button" data-indicator-close>Close</button>
              </div>
              <div class="indicator-panel-body">
                <div class="indicator-list" data-indicator-list></div>
              </div>
            </section>
          </div>
        </div>
        <div class="indicator-detail-modal" data-indicator-modal hidden>
          <div class="indicator-detail-container" data-indicator-detail></div>
        </div>
        <div class="chart-head">
          <h4 class="chart-title">Market Context</h4>
          <p class="chart-legend" data-chart-legend></p>
        </div>
        <div class="tv-chart-host" data-chart-host></div>
      </div>
      <div class="insight-strip">
        <article class="insight-inline" data-candle-details></article>
        <article class="insight-inline" data-window-stats></article>
      </div>
    </section>
  `;

  const candleSizeRow = performanceRoot.querySelector("[data-candle-size-row]");
  const modeRow = performanceRoot.querySelector("[data-chart-mode-row]");
  const legendNode = performanceRoot.querySelector("[data-chart-legend]");
  const chartHost = performanceRoot.querySelector("[data-chart-host]");
  const candleDetailsNode = performanceRoot.querySelector("[data-candle-details]");
  const windowStatsNode = performanceRoot.querySelector("[data-window-stats]");
  const indicatorPanel = performanceRoot.querySelector("[data-indicator-panel]");
  const indicatorOpenButton = performanceRoot.querySelector("[data-indicator-open]");
  const indicatorCloseButton = performanceRoot.querySelector("[data-indicator-close]");
  const indicatorCountNode = performanceRoot.querySelector("[data-indicator-count]");
  const indicatorListNode = performanceRoot.querySelector("[data-indicator-list]");
  const indicatorModal = performanceRoot.querySelector("[data-indicator-modal]");
  const indicatorDetailNode = performanceRoot.querySelector("[data-indicator-detail]");

  function getIndicatorDetailWindow() {
    return indicatorDetailNode.querySelector(".indicator-detail-window");
  }

  function clampIndicatorModalPosition(x, y, detailWindow) {
    const margin = 12;
    const maxX = Math.max(
      margin,
      indicatorModal.clientWidth - detailWindow.offsetWidth - margin
    );
    const maxY = Math.max(
      margin,
      indicatorModal.clientHeight - detailWindow.offsetHeight - margin
    );

    return {
      x: Math.max(margin, Math.min(maxX, Math.round(x))),
      y: Math.max(margin, Math.min(maxY, Math.round(y))),
    };
  }

  function applyIndicatorModalPosition(reset = false) {
    const detailWindow = getIndicatorDetailWindow();
    if (!detailWindow) {
      return;
    }

    if (reset || !modalState.position) {
      const centeredX = (indicatorModal.clientWidth - detailWindow.offsetWidth) / 2;
      const centeredY = (indicatorModal.clientHeight - detailWindow.offsetHeight) / 2;
      modalState.position = clampIndicatorModalPosition(centeredX, centeredY, detailWindow);
    } else {
      modalState.position = clampIndicatorModalPosition(
        modalState.position.x,
        modalState.position.y,
        detailWindow
      );
    }

    detailWindow.style.left = `${modalState.position.x}px`;
    detailWindow.style.top = `${modalState.position.y}px`;
  }

  candleSizeRow.innerHTML = renderCandleSizeButtons(state.candleSizeKey);
  modeRow.innerHTML = renderChartModeButtons(state.chartMode);

  const chart = LightweightCharts.createChart(chartHost, {
    width: chartHost.clientWidth || 960,
    height: chartHost.clientHeight || 620,
    layout: {
      background: {
        type: "solid",
        color: "#0b1523",
      },
      textColor: "#9cb0c7",
      fontFamily: "Space Grotesk, IBM Plex Sans, sans-serif",
      attributionLogo: false,
    },
    watermark: {
      visible: false,
    },
    grid: {
      vertLines: {
        color: "rgba(80, 104, 132, 0.25)",
      },
      horzLines: {
        color: "rgba(80, 104, 132, 0.25)",
      },
    },
    rightPriceScale: {
      borderColor: "rgba(87, 111, 142, 0.4)",
      scaleMargins: {
        top: 0.08,
        bottom: 0.08,
      },
    },
    timeScale: {
      borderColor: "rgba(87, 111, 142, 0.4)",
      timeVisible: true,
      secondsVisible: false,
    },
    crosshair: {
      mode: LightweightCharts.CrosshairMode.Normal,
      vertLine: {
        color: "rgba(176, 202, 234, 0.45)",
        width: 1,
        style: 2,
      },
      horzLine: {
        color: "rgba(176, 202, 234, 0.45)",
        width: 1,
        style: 2,
      },
    },
    handleScroll: {
      mouseWheel: true,
      pressedMouseMove: true,
      vertTouchDrag: true,
      horzTouchDrag: true,
    },
    handleScale: {
      axisPressedMouseMove: true,
      axisDoubleClickReset: true,
      mouseWheel: true,
      pinch: true,
    },
  });

  const candleSeries = chart.addCandlestickSeries({
    upColor: "#2adf8f",
    downColor: "#ff6b7a",
    wickUpColor: "#2adf8f",
    wickDownColor: "#ff6b7a",
    borderVisible: false,
    priceLineVisible: false,
  });

  const lineSeries = chart.addLineSeries({
    color: "#67b6ff",
    lineWidth: 2,
    priceLineVisible: false,
    crosshairMarkerVisible: true,
  });

  const sma20Series = chart.addLineSeries({
    color: state.indicators.sma20.color,
    lineWidth: state.indicators.sma20.lineWidth,
    lineStyle: state.indicators.sma20.lineStyle,
    priceLineVisible: false,
  });

  const sma50Series = chart.addLineSeries({
    color: state.indicators.sma50.color,
    lineWidth: state.indicators.sma50.lineWidth,
    lineStyle: state.indicators.sma50.lineStyle,
    priceLineVisible: false,
  });

  const sma100Series = chart.addLineSeries({
    color: state.indicators.sma100.color,
    lineWidth: state.indicators.sma100.lineWidth,
    lineStyle: state.indicators.sma100.lineStyle,
    priceLineVisible: false,
  });

  const ema20Series = chart.addLineSeries({
    color: state.indicators.ema20.color,
    lineWidth: state.indicators.ema20.lineWidth,
    lineStyle: state.indicators.ema20.lineStyle,
    priceLineVisible: false,
  });

  const ema50Series = chart.addLineSeries({
    color: state.indicators.ema50.color,
    lineWidth: state.indicators.ema50.lineWidth,
    lineStyle: state.indicators.ema50.lineStyle,
    priceLineVisible: false,
  });

  const bbUpperSeries = chart.addLineSeries({
    color: state.indicators.bb20.color,
    lineWidth: state.indicators.bb20.lineWidth,
    lineStyle: state.indicators.bb20.lineStyle,
    priceLineVisible: false,
  });

  const bbLowerSeries = chart.addLineSeries({
    color: state.indicators.bb20.color,
    lineWidth: state.indicators.bb20.lineWidth,
    lineStyle: state.indicators.bb20.lineStyle,
    priceLineVisible: false,
  });

  const volumeSeries = chart.addHistogramSeries({
    color: "rgba(88, 122, 157, 0.75)",
    priceFormat: {
      type: "volume",
    },
    priceScaleId: "",
  });
  volumeSeries.priceScale().applyOptions({
    scaleMargins: {
      top: 0.95,
      bottom: 0,
    },
  });

  const indicatorSeriesMap = {
    sma20: [sma20Series],
    sma50: [sma50Series],
    sma100: [sma100Series],
    ema20: [ema20Series],
    ema50: [ema50Series],
    bb20: [bbUpperSeries, bbLowerSeries],
  };

  function updateLegend(candle) {
    if (!candle) {
      legendNode.textContent = "No candle selected.";
      return;
    }

    legendNode.innerHTML = `
      <span>${formatDate(candle.time)}</span>
      <span>O ${formatNumber(candle.open)}</span>
      <span>H ${formatNumber(candle.high)}</span>
      <span>L ${formatNumber(candle.low)}</span>
      <span>C ${formatNumber(candle.close)}</span>
      <span class="${candle.changePct >= 0 ? "metric-value-positive" : "metric-value-negative"}">${formatPercent(candle.changePct)}</span>
    `;
  }

  function updateSelectedCandle(candle) {
    state.lastCandle = candle || null;
    candleDetailsNode.innerHTML = renderCandleDetails(candle);
    updateLegend(candle);
  }

  function applySeriesVisibility() {
    const isCandleMode = state.chartMode === "candles";
    candleSeries.applyOptions({ visible: isCandleMode });
    lineSeries.applyOptions({ visible: !isCandleMode });
    sma20Series.applyOptions({ visible: state.indicators.sma20.enabled });
    sma50Series.applyOptions({ visible: state.indicators.sma50.enabled });
    sma100Series.applyOptions({ visible: state.indicators.sma100.enabled });
    ema20Series.applyOptions({ visible: state.indicators.ema20.enabled });
    ema50Series.applyOptions({ visible: state.indicators.ema50.enabled });
    bbUpperSeries.applyOptions({ visible: state.indicators.bb20.enabled });
    bbLowerSeries.applyOptions({ visible: state.indicators.bb20.enabled });
  }

  function applyIndicatorStyles() {
    Object.entries(indicatorSeriesMap).forEach(([key, seriesList]) => {
      const indicator = state.indicators[key];
      if (!indicator) {
        return;
      }
      const options = {
        color: indicator.color,
        lineWidth: indicator.lineWidth,
        lineStyle: indicator.lineStyle,
      };
      seriesList.forEach((series) => {
        series.applyOptions(options);
      });
    });
  }

  function computeCurrentCandles() {
    return buildCandlesForSize(rawPoints, state.candleSizeKey);
  }

  function renderStats(candles) {
    const stats = computeWindowStats(candles);
    windowStatsNode.innerHTML = renderWindowStats(stats);
  }

  function updateIndicatorPanelState() {
    indicatorListNode.innerHTML = renderIndicatorList(
      state.indicators,
      state.selectedIndicatorKey
    );

    let enabledCount = 0;
    Object.values(state.indicators).forEach((indicator) => {
      if (indicator.enabled) {
        enabledCount += 1;
      }
    });

    indicatorCountNode.textContent = `${enabledCount} active`;
  }

  function closeIndicatorModal() {
    indicatorModal.hidden = true;
    indicatorDetailNode.innerHTML = "";
    state.selectedIndicatorKey = null;
    modalState.pointerId = null;
    updateIndicatorPanelState();
  }

  function refreshIndicatorModal() {
    if (!state.selectedIndicatorKey) {
      return;
    }
    const indicator = state.indicators[state.selectedIndicatorKey];
    if (!indicator) {
      return;
    }
    indicatorDetailNode.innerHTML = renderIndicatorDetail(
      state.selectedIndicatorKey,
      indicator
    );
    if (!indicatorModal.hidden) {
      applyIndicatorModalPosition();
    }
  }

  function openIndicatorModal(indicatorKey) {
    const indicator = state.indicators[indicatorKey];
    if (!indicator) {
      return;
    }
    state.selectedIndicatorKey = indicatorKey;
    refreshIndicatorModal();
    indicatorModal.hidden = false;
    applyIndicatorModalPosition(!modalState.position);
    updateIndicatorPanelState();
  }

  function updateToolbarVisualState() {
    const sizeButtons = candleSizeRow.querySelectorAll("[data-candle-size-key]");
    sizeButtons.forEach((button) => {
      const isActive = button.getAttribute("data-candle-size-key") === state.candleSizeKey;
      button.classList.toggle("active", isActive);
    });

    const modeButtons = modeRow.querySelectorAll("[data-chart-mode]");
    modeButtons.forEach((button) => {
      const isActive = button.getAttribute("data-chart-mode") === state.chartMode;
      button.classList.toggle("active", isActive);
    });

    updateIndicatorPanelState();
  }

  function rebuildData() {
    const candles = computeCurrentCandles();
    state.candles = candles;
    state.candleByTime = new Map(candles.map((candle) => [candle.time, candle]));

    if (candles.length < 2) {
      chartHost.innerHTML = `<div class="alert alert-error">Not enough points for chart rendering.</div>`;
      return;
    }

    const lineData = buildLineData(candles);
    const sma20 = computeSma(
      candles,
      state.indicators.sma20.length,
      state.indicators.sma20.source
    );
    const sma50 = computeSma(
      candles,
      state.indicators.sma50.length,
      state.indicators.sma50.source
    );
    const sma100 = computeSma(
      candles,
      state.indicators.sma100.length,
      state.indicators.sma100.source
    );
    const ema20 = computeEma(
      candles,
      state.indicators.ema20.length,
      state.indicators.ema20.source,
      state.indicators.ema20.smoothing
    );
    const ema50 = computeEma(
      candles,
      state.indicators.ema50.length,
      state.indicators.ema50.source,
      state.indicators.ema50.smoothing
    );
    const bollinger = computeBollinger(
      candles,
      state.indicators.bb20.length,
      state.indicators.bb20.multiplier,
      state.indicators.bb20.source,
      state.indicators.bb20.basisType,
      state.indicators.bb20.basisSmoothing
    );
    const volume = candles.map((candle) => ({
      time: candle.time,
      value: candle.volumeProxy * 100,
      color: candle.close >= candle.open ? "rgba(42, 223, 143, 0.35)" : "rgba(255, 107, 122, 0.35)",
    }));

    candleSeries.setData(candles);
    lineSeries.setData(lineData);
    sma20Series.setData(sma20);
    sma50Series.setData(sma50);
    sma100Series.setData(sma100);
    ema20Series.setData(ema20);
    ema50Series.setData(ema50);
    bbUpperSeries.setData(bollinger.upper);
    bbLowerSeries.setData(bollinger.lower);
    volumeSeries.setData(volume);
    applySeriesVisibility();
    chart.timeScale().fitContent();
    renderStats(candles);
    updateSelectedCandle(candles[candles.length - 1]);
    updateToolbarVisualState();
  }

  chart.subscribeCrosshairMove((param) => {
    if (!param?.time) {
      if (state.lastCandle) {
        updateSelectedCandle(state.lastCandle);
      }
      return;
    }

    const key = normalizeTimeKey(param.time);
    const candle = key ? state.candleByTime.get(key) : null;
    if (candle) {
      updateSelectedCandle(candle);
    }
  });

  const resizeObserver = new ResizeObserver(() => {
    const width = chartHost.clientWidth || 960;
    const height = chartHost.clientHeight || 620;
    chart.applyOptions({ width, height });
    if (!indicatorModal.hidden) {
      applyIndicatorModalPosition();
    }
  });
  resizeObserver.observe(chartHost);

  const onCandleSizeClick = (event) => {
    const button = event.target.closest("[data-candle-size-key]");
    if (!button) {
      return;
    }
    const candleSizeKey = button.getAttribute("data-candle-size-key");
    if (!candleSizeKey || candleSizeKey === state.candleSizeKey) {
      return;
    }
    state.candleSizeKey = candleSizeKey;
    rebuildData();
  };

  const onModeClick = (event) => {
    const button = event.target.closest("[data-chart-mode]");
    if (!button) {
      return;
    }
    const modeKey = button.getAttribute("data-chart-mode");
    if (!modeKey || modeKey === state.chartMode) {
      return;
    }
    state.chartMode = modeKey;
    applySeriesVisibility();
    updateToolbarVisualState();
  };

  candleSizeRow.addEventListener("click", onCandleSizeClick);
  modeRow.addEventListener("click", onModeClick);

  const closeIndicatorPanel = () => {
    indicatorPanel.hidden = true;
    closeIndicatorModal();
    indicatorOpenButton.classList.remove("active");
  };

  const onIndicatorOpen = () => {
    const nextHidden = !indicatorPanel.hidden;
    indicatorPanel.hidden = nextHidden;
    indicatorOpenButton.classList.toggle("active", !nextHidden);
    if (!nextHidden) {
      updateIndicatorPanelState();
    } else {
      closeIndicatorModal();
    }
  };

  const onIndicatorClose = () => {
    closeIndicatorPanel();
  };

  const onOutsidePointerDown = (event) => {
    const target = event.target;
    const detailWindow = getIndicatorDetailWindow();

    if (!indicatorModal.hidden && detailWindow && !detailWindow.contains(target)) {
      closeIndicatorModal();
    }

    if (indicatorPanel.hidden) {
      return;
    }
    if (
      indicatorPanel.contains(target) ||
      indicatorOpenButton.contains(target) ||
      indicatorModal.contains(target)
    ) {
      return;
    }
    closeIndicatorPanel();
  };

  const onEscapeKey = (event) => {
    if (event.key === "Escape") {
      if (!indicatorModal.hidden) {
        closeIndicatorModal();
        return;
      }
      closeIndicatorPanel();
    }
  };

  const onIndicatorListClick = (event) => {
    const toggleButton = event.target.closest("[data-indicator-toggle]");
    if (toggleButton) {
      const indicatorKey = toggleButton.getAttribute("data-indicator-toggle");
      const indicator = indicatorKey ? state.indicators[indicatorKey] : null;
      if (!indicator) {
        return;
      }
      indicator.enabled = !indicator.enabled;
      applySeriesVisibility();
      updateToolbarVisualState();
      if (state.selectedIndicatorKey === indicatorKey && !indicatorModal.hidden) {
        refreshIndicatorModal();
      }
      return;
    }

    const configButton = event.target.closest("[data-indicator-config]");
    if (!configButton) {
      return;
    }
    const indicatorKey = configButton.getAttribute("data-indicator-config");
    if (!indicatorKey) {
      return;
    }
    openIndicatorModal(indicatorKey);
  };

  const onIndicatorModalClick = (event) => {
    const closeButton = event.target.closest("[data-indicator-detail-close]");
    if (closeButton) {
      closeIndicatorModal();
      return;
    }

    const enableButton = event.target.closest("[data-indicator-enable]");
    if (!enableButton) {
      return;
    }
    const indicatorKey = enableButton.getAttribute("data-indicator-enable");
    const indicator = indicatorKey ? state.indicators[indicatorKey] : null;
    if (!indicator) {
      return;
    }

    indicator.enabled = !indicator.enabled;
    applySeriesVisibility();
    updateToolbarVisualState();
    refreshIndicatorModal();
  };

  const onIndicatorModalInput = (event) => {
    const fieldNode = event.target.closest("[data-indicator-field]");
    if (!fieldNode) {
      return;
    }

    const indicatorKey = fieldNode.getAttribute("data-indicator-key");
    const fieldName = fieldNode.getAttribute("data-indicator-field");
    const indicator = indicatorKey ? state.indicators[indicatorKey] : null;
    if (!indicator || !fieldName) {
      return;
    }

    if (fieldName === "length") {
      indicator.length = normalizeIndicatorLength(fieldNode.value, indicator.length);
      rebuildData();
      refreshIndicatorModal();
      return;
    }

    if (fieldName === "source") {
      indicator.source = normalizeIndicatorSource(fieldNode.value, indicator.source);
      rebuildData();
      refreshIndicatorModal();
      return;
    }

    if (fieldName === "smoothing") {
      indicator.smoothing = normalizeIndicatorSmoothing(
        fieldNode.value,
        indicator.smoothing || 1
      );
      rebuildData();
      refreshIndicatorModal();
      return;
    }

    if (fieldName === "multiplier") {
      indicator.multiplier = normalizeIndicatorMultiplier(
        fieldNode.value,
        indicator.multiplier || 2
      );
      rebuildData();
      refreshIndicatorModal();
      return;
    }

    if (fieldName === "basisType") {
      indicator.basisType = normalizeBollingerBasisType(
        fieldNode.value,
        indicator.basisType || "sma"
      );
      rebuildData();
      refreshIndicatorModal();
      return;
    }

    if (fieldName === "basisSmoothing") {
      indicator.basisSmoothing = normalizeIndicatorSmoothing(
        fieldNode.value,
        indicator.basisSmoothing || 1
      );
      rebuildData();
      refreshIndicatorModal();
      return;
    }

    if (fieldName === "color") {
      indicator.color = normalizeIndicatorColor(fieldNode.value, indicator.color);
      applyIndicatorStyles();
      refreshIndicatorModal();
      return;
    }

    if (fieldName === "lineWidth") {
      indicator.lineWidth = normalizeIndicatorLineWidth(
        fieldNode.value,
        indicator.lineWidth
      );
      applyIndicatorStyles();
      refreshIndicatorModal();
      return;
    }

    if (fieldName === "lineStyle") {
      indicator.lineStyle = normalizeIndicatorLineStyle(
        fieldNode.value,
        indicator.lineStyle
      );
      applyIndicatorStyles();
      refreshIndicatorModal();
    }
  };

  const stopIndicatorModalDrag = () => {
    if (modalState.pointerId === null) {
      return;
    }
    modalState.pointerId = null;
    const detailWindow = getIndicatorDetailWindow();
    if (detailWindow) {
      detailWindow.classList.remove("dragging");
    }
  };

  const onIndicatorModalPointerDown = (event) => {
    const dragHandle = event.target.closest("[data-indicator-drag-handle]");
    if (!dragHandle || !indicatorDetailNode.contains(dragHandle)) {
      return;
    }
    if (event.target.closest("[data-indicator-detail-close]")) {
      return;
    }

    const detailWindow = getIndicatorDetailWindow();
    if (!detailWindow) {
      return;
    }

    const detailRect = detailWindow.getBoundingClientRect();
    modalState.pointerId = event.pointerId;
    modalState.offsetX = event.clientX - detailRect.left;
    modalState.offsetY = event.clientY - detailRect.top;
    detailWindow.classList.add("dragging");
    event.preventDefault();
  };

  const onWindowPointerMove = (event) => {
    if (modalState.pointerId === null || event.pointerId !== modalState.pointerId) {
      return;
    }

    const detailWindow = getIndicatorDetailWindow();
    if (!detailWindow) {
      stopIndicatorModalDrag();
      return;
    }

    const modalRect = indicatorModal.getBoundingClientRect();
    const nextX = event.clientX - modalRect.left - modalState.offsetX;
    const nextY = event.clientY - modalRect.top - modalState.offsetY;
    modalState.position = clampIndicatorModalPosition(nextX, nextY, detailWindow);
    detailWindow.style.left = `${modalState.position.x}px`;
    detailWindow.style.top = `${modalState.position.y}px`;
  };

  const onWindowPointerUp = (event) => {
    if (modalState.pointerId === null || event.pointerId !== modalState.pointerId) {
      return;
    }
    stopIndicatorModalDrag();
  };

  indicatorOpenButton.addEventListener("click", onIndicatorOpen);
  indicatorCloseButton.addEventListener("click", onIndicatorClose);
  indicatorListNode.addEventListener("click", onIndicatorListClick);
  indicatorDetailNode.addEventListener("pointerdown", onIndicatorModalPointerDown);
  indicatorDetailNode.addEventListener("click", onIndicatorModalClick);
  indicatorDetailNode.addEventListener("change", onIndicatorModalInput);
  document.addEventListener("pointerdown", onOutsidePointerDown);
  window.addEventListener("keydown", onEscapeKey);
  window.addEventListener("pointermove", onWindowPointerMove);
  window.addEventListener("pointerup", onWindowPointerUp);
  window.addEventListener("pointercancel", onWindowPointerUp);
  window.addEventListener("blur", stopIndicatorModalDrag);

  rebuildData();

  const onCleanup = () => {
    resizeObserver.disconnect();
    candleSizeRow.removeEventListener("click", onCandleSizeClick);
    modeRow.removeEventListener("click", onModeClick);
    indicatorOpenButton.removeEventListener("click", onIndicatorOpen);
    indicatorCloseButton.removeEventListener("click", onIndicatorClose);
    indicatorListNode.removeEventListener("click", onIndicatorListClick);
    indicatorDetailNode.removeEventListener("pointerdown", onIndicatorModalPointerDown);
    indicatorDetailNode.removeEventListener("click", onIndicatorModalClick);
    indicatorDetailNode.removeEventListener("change", onIndicatorModalInput);
    document.removeEventListener("pointerdown", onOutsidePointerDown);
    window.removeEventListener("keydown", onEscapeKey);
    window.removeEventListener("pointermove", onWindowPointerMove);
    window.removeEventListener("pointerup", onWindowPointerUp);
    window.removeEventListener("pointercancel", onWindowPointerUp);
    window.removeEventListener("blur", stopIndicatorModalDrag);
    chart.remove();
    window.removeEventListener("hashchange", onCleanup);
  };
  window.addEventListener("hashchange", onCleanup);
}

export async function mountIndexDetailView(
  root,
  {
    indexId,
    loadIndexDetail,
    loadPerformance,
    onNavigate,
  }
) {
  root.innerHTML = `
    <section class="panel panel-flat stack">
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
        : statusCode === 403
          ? "You are not allowed to access this index."
          : error instanceof Error
            ? error.message
            : "Failed to load index detail.";

    root.innerHTML = `
      <section class="panel panel-flat stack">
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
      <div>
        <h2 class="page-title">${escapeHtml(indexDetail.name)}</h2>
        <p class="page-subtitle">${escapeHtml(buildDescription(indexDetail.description))}</p>
        <p class="page-subtitle">
          Created: ${formatDate(indexDetail.created_at)}
        </p>
      </div>
      <section class="stack">
        <h3 class="section-title">Allocation</h3>
        ${renderAssetComposition(indexDetail.assets)}
      </section>
      <section class="stack" data-performance-section>
        <h3 class="section-title">Market Context</h3>
        <p class="section-description">
          Use this chart to validate behavior after adjusting the index composition.
        </p>
        <p class="loading" data-loading-performance>Loading performance...</p>
      </section>
    </div>
  `;

  loadingDetail.hidden = true;

  const performanceSection = content.querySelector("[data-performance-section]");
  const loadingPerformance = content.querySelector("[data-loading-performance]");

  try {
    const performance = await loadPerformance(indexId);
    performanceSection.innerHTML = `
      <h3 class="section-title">Market Context</h3>
      <div data-performance-root></div>
    `;
    const performanceRoot = performanceSection.querySelector("[data-performance-root]");
    mountPerformanceExplorer(performanceRoot, performance);
  } catch (error) {
    const statusCode = error && typeof error === "object" ? error.statusCode : null;
    const message =
      statusCode === 403
        ? "You are not allowed to access this index performance."
        : error instanceof Error
          ? error.message
          : "Failed to load performance data.";
    performanceSection.innerHTML = `
      <h3 class="section-title">Market Context</h3>
      <div class="alert alert-error">Performance fetch failed: ${escapeHtml(message)}</div>
    `;
  } finally {
    if (loadingPerformance) {
      loadingPerformance.hidden = true;
    }
  }
}
