import { ROUTE_PATHS, buildIndexDetailPath } from "../router.js";

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function buildAssetOptions(assets) {
  const options = ['<option value="">Select asset</option>'];
  for (const asset of assets) {
    const symbol = escapeHtml(asset.symbol);
    const name = escapeHtml(asset.name);
    options.push(`<option value="${symbol}">${symbol} - ${name}</option>`);
  }
  return options.join("");
}

function parseWeight(rawValue) {
  const normalized = rawValue.replace(",", ".");
  const parsed = Number(normalized);
  return Number.isFinite(parsed) ? parsed : NaN;
}

export async function mountEditIndexView(
  root,
  { indexId, loadAssets, loadIndexDetail, onUpdateIndex, onNavigate }
) {
  root.innerHTML = `
    <section class="panel stack">
      <h2 class="page-title">Edit Index</h2>
      <p class="page-subtitle">Update index name and composition.</p>

      <div class="alert alert-success" data-success hidden></div>
      <div class="alert alert-error" data-error hidden></div>
      <p class="loading" data-loading>Loading index data...</p>

      <form class="stack" data-form hidden>
        <div class="field">
          <label for="index-name">Index Name</label>
          <input id="index-name" name="name" type="text" maxlength="100" required>
        </div>

        <div class="stack">
          <h3>Assets and Weights</h3>
          <div class="stack" data-assets-container></div>
          <p class="weight-hint" data-total-weight>Total weight: 0.00%</p>
          <div class="button-row">
            <button class="button button-secondary" type="button" data-add-asset>Add asset</button>
          </div>
        </div>

        <div class="button-row">
          <button class="button button-primary" type="submit" data-submit>Save changes</button>
          <button class="button button-secondary" type="button" data-cancel>Cancel</button>
        </div>
      </form>
    </section>
  `;

  const loading = root.querySelector("[data-loading]");
  const form = root.querySelector("[data-form]");
  const errorBox = root.querySelector("[data-error]");
  const successBox = root.querySelector("[data-success]");
  const submitButton = root.querySelector("[data-submit]");
  const addAssetButton = root.querySelector("[data-add-asset]");
  const cancelButton = root.querySelector("[data-cancel]");
  const assetsContainer = root.querySelector("[data-assets-container]");
  const totalWeightLabel = root.querySelector("[data-total-weight]");
  const nameInput = root.querySelector("#index-name");

  let availableAssets = [];

  cancelButton.addEventListener("click", () => {
    onNavigate(buildIndexDetailPath(indexId));
  });

  function setError(message) {
    errorBox.textContent = message;
    errorBox.hidden = false;
  }

  function clearMessages() {
    errorBox.hidden = true;
    successBox.hidden = true;
  }

  function updateTotalWeight() {
    const rows = Array.from(assetsContainer.querySelectorAll("[data-asset-row]"));
    const total = rows.reduce((accumulator, row) => {
      const weightInput = row.querySelector("[data-weight]");
      const value = parseWeight(String(weightInput.value || ""));
      return Number.isFinite(value) ? accumulator + value : accumulator;
    }, 0);
    totalWeightLabel.textContent = `Total weight: ${total.toFixed(2)}%`;
  }

  function addAssetRow(initialSymbol = "", initialWeight = "") {
    const optionsMarkup = buildAssetOptions(availableAssets);
    const rowElement = document.createElement("div");
    rowElement.className = "form-row";
    rowElement.dataset.assetRow = "true";
    rowElement.innerHTML = `
      <div class="field">
        <label>Asset</label>
        <select data-symbol>${optionsMarkup}</select>
      </div>
      <div class="field">
        <label>Weight (%)</label>
        <input data-weight type="number" min="0" max="100" step="0.01" placeholder="e.g. 35">
      </div>
      <div class="button-row">
        <button class="button button-danger" type="button" data-remove>Remove</button>
      </div>
    `;

    const symbolSelect = rowElement.querySelector("[data-symbol]");
    const weightInput = rowElement.querySelector("[data-weight]");
    symbolSelect.value = initialSymbol;
    weightInput.value = initialWeight;

    rowElement.querySelector("[data-remove]").addEventListener("click", () => {
      rowElement.remove();
      updateTotalWeight();
    });
    weightInput.addEventListener("input", updateTotalWeight);

    assetsContainer.appendChild(rowElement);
    updateTotalWeight();
  }

  addAssetButton.addEventListener("click", () => {
    addAssetRow();
  });

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    clearMessages();

    const indexName = String(new FormData(form).get("name") || "").trim();
    if (!indexName) {
      setError("Index name is required.");
      return;
    }

    const rows = Array.from(assetsContainer.querySelectorAll("[data-asset-row]"));
    if (!rows.length) {
      setError("Add at least one asset.");
      return;
    }

    const symbolsSeen = new Set();
    const assets = [];
    let totalWeight = 0;

    for (const row of rows) {
      const symbol = String(row.querySelector("[data-symbol]").value || "").trim();
      const weightValue = String(row.querySelector("[data-weight]").value || "").trim();
      const weight = parseWeight(weightValue);

      if (!symbol) {
        setError("Each row must have an asset selected.");
        return;
      }
      if (symbolsSeen.has(symbol)) {
        setError("Asset symbols must be unique.");
        return;
      }
      if (!Number.isFinite(weight) || weight <= 0 || weight > 100) {
        setError("Each weight must be a valid number between 0 and 100.");
        return;
      }

      symbolsSeen.add(symbol);
      totalWeight += weight;
      assets.push({ symbol, weight });
    }

    if (totalWeight > 100) {
      setError("Total asset weight must be less than or equal to 100.");
      return;
    }

    submitButton.disabled = true;
    try {
      await onUpdateIndex(indexId, { name: indexName, assets });
      successBox.textContent = "Index updated successfully.";
      successBox.hidden = false;
      setTimeout(() => {
        onNavigate(buildIndexDetailPath(indexId));
      }, 500);
    } catch (error) {
      setError(error instanceof Error ? error.message : "Failed to update index.");
    } finally {
      submitButton.disabled = false;
      updateTotalWeight();
    }
  });

  try {
    const [assets, indexDetail] = await Promise.all([loadAssets(), loadIndexDetail(indexId)]);
    availableAssets = assets;
    if (!availableAssets.length) {
      throw new Error("No available assets were returned by api2.");
    }

    nameInput.value = indexDetail.name || "";
    const existingAssets = Array.isArray(indexDetail.assets) ? indexDetail.assets : [];
    assetsContainer.innerHTML = "";
    if (existingAssets.length) {
      for (const asset of existingAssets) {
        addAssetRow(asset.symbol, String(asset.weight));
      }
    } else {
      addAssetRow();
    }

    form.hidden = false;
  } catch (error) {
    const statusCode = error && typeof error === "object" ? error.statusCode : null;
    const message =
      statusCode === 404
        ? "This index does not exist."
        : statusCode === 403
          ? "You are not allowed to edit this index."
          : error instanceof Error
            ? error.message
            : "Failed to load index for editing.";
    setError(message);
    root.insertAdjacentHTML(
      "beforeend",
      `
        <div class="button-row">
          <button class="button button-secondary" type="button" data-back-indexes>Back to indexes</button>
        </div>
      `
    );
    root.querySelector("[data-back-indexes]").addEventListener("click", () => {
      onNavigate(ROUTE_PATHS.indexList);
    });
  } finally {
    loading.hidden = true;
    updateTotalWeight();
  }
}
