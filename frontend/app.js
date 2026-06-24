
const API_BASE = "";
let allElements = [];
let activeTab = "url";
let paginationState = {
  totalAvailable: 0,
  currentOffset: 0,
  limit: 100,
  currentRequest: null,
  isLoading: false
};
let filterDebounceTimer = null;

/* ─── Tab switching ─── */
function switchTab(tab, event) {
  activeTab = tab;
  document.querySelectorAll(".tab").forEach(t => t.classList.remove("active"));
  document.querySelectorAll(".tab-panel").forEach(p => p.classList.add("hidden"));
  if (event && event.target) event.target.classList.add("active");
  document.getElementById(`${tab}-panel`).classList.remove("hidden");
}

/* ─── Copy the console command ─── */
function copyCommand() {
  const cmd = document.getElementById("console-cmd").textContent;
  navigator.clipboard.writeText(cmd).then(() => {
    const btn = document.querySelector(".copy-cmd-btn");
    btn.textContent = "✅ Copied!";
    setTimeout(() => btn.textContent = "📋 Copy", 1800);
  });
}

/* ─── Main analyze ─── */
async function analyzePage() {
  const loading = document.getElementById("loading");
  const results = document.getElementById("results");
  results.classList.add("hidden");
  loading.classList.remove("hidden");

  try {
    let body;
    if (activeTab === "url") {
      const url = document.getElementById("url-input").value.trim();
      const tag = document.getElementById("tag-filter").value;
      if (!url) { alert("Please enter a URL"); return; }
      body = { input_type: "url", content: url, filter_tag: tag || null, limit: 100, offset: 0 };
    } else {
      const html = document.getElementById("html-input").value.trim();
      if (!html) { alert("Please paste HTML into the text area"); return; }
      body = { input_type: "html", content: html, limit: 100, offset: 0 };
    }

    paginationState.currentRequest = body;
    paginationState.currentOffset = 0;

    const res = await fetch(`${API_BASE}/analyze/`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body)
    });

    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || "API error");
    }

    const data = await res.json();
    allElements = data.elements;
    paginationState.totalAvailable = data.total_available;
    paginationState.currentOffset = data.offset + data.total_elements;
    renderResults(data);
  } catch (err) {
    alert(`Error: ${err.message}`);
  } finally {
    loading.classList.add("hidden");
  }
}

/* ─── Load more elements ─── */
async function loadMoreElements() {
  if (paginationState.isLoading || paginationState.currentOffset >= paginationState.totalAvailable) {
    return;
  }

  paginationState.isLoading = true;
  const loadMoreBtn = document.getElementById("load-more-btn");
  if (loadMoreBtn) loadMoreBtn.disabled = true;

  try {
    const body = { ...paginationState.currentRequest, offset: paginationState.currentOffset };

    const res = await fetch(`${API_BASE}/analyze/`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body)
    });

    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || "API error");
    }

    const data = await res.json();
    allElements = [...allElements, ...data.elements];
    paginationState.currentOffset = data.offset + data.total_elements;
    updatePaginationUI();
  } catch (err) {
    alert(`Error loading more: ${err.message}`);
  } finally {
    paginationState.isLoading = false;
    const loadMoreBtn = document.getElementById("load-more-btn");
    if (loadMoreBtn) loadMoreBtn.disabled = false;
  }
}

/* ─── Update pagination UI ─── */
function updatePaginationUI() {
  const hasMore = paginationState.currentOffset < paginationState.totalAvailable;
  const container = document.getElementById("pagination-container");

  if (container) {
    if (hasMore) {
      container.classList.remove("hidden");
      const btn = document.getElementById("load-more-btn");
      if (btn) {
        btn.textContent = `📥 Load More (${paginationState.totalAvailable - paginationState.currentOffset} remaining)`;
      }
    } else {
      container.classList.add("hidden");
    }
  }

  // Render current set (already loaded / filtered) into the grid
  document.getElementById("no-results").classList.toggle("hidden", allElements.length > 0);
  document.getElementById("total-count").textContent =
    `📊 ${allElements.length} element${allElements.length === 1 ? "" : "s"} shown${paginationState.totalAvailable > allElements.length ? ` of ${paginationState.totalAvailable}` : ""}`;
  renderGrid(allElements);
}

/* ─── Render results ─── */
function renderResults(data) {
  document.getElementById("total-count").textContent =
    `📊 ${data.total_elements} elements loaded${data.total_available > data.total_elements ? ` (${data.total_available} total available)` : ""}${data.page_title ? ` on "${data.page_title}"` : ""}`;
  allElements = data.elements;
  paginationState.totalAvailable = data.total_available;
  document.getElementById("search-box").value = "";
  document.getElementById("reliability-filter").value = "";
  updatePaginationUI();
  document.getElementById("results").classList.remove("hidden");
}

function renderGrid(elements) {
  const grid = document.getElementById("elements-grid");
  grid.innerHTML = "";
  elements.forEach((el) => {
    const card = document.createElement("div");
    card.className = "element-card";
    const best = el.best_locator;
    const pct = Math.round(best.score * 100);
    const xpathForBest = (best.locator_type === 'css') ? cssAttrToXPath(best.value) : (best.value && (best.value.trim().startsWith('/') ? best.value : '//' + best.value));

    card.innerHTML = `
      <div class="card-header">
        <span class="tag-badge">&lt;${el.tag}&gt;</span>
        <span class="reliability-badge ${best.reliability}">${best.reliability.toUpperCase()}</span>
      </div>
      <div class="element-text">${el.text ? truncate(el.text, 60) : "<em>no text</em>"}</div>
      <div class="best-locator">
        <span class="loc-type">${best.locator_type.toUpperCase()}</span>
        <div style="display:block;">
          <div class="locator-css"><strong>CSS:</strong> <code>${truncate(best.value, 60)}</code></div>
          <div class="locator-xpath" style="margin-top:.25rem;"><strong>XPath:</strong> <code>${truncate(xpathForBest, 80)}</code></div>
        </div>
        <div style="display:inline-block;margin-left:.6rem">
          <button onclick="copyLocator('${escapeHtml(best.value)}', event)">📋 Copy</button>
          <button onclick="copyAsXPath('${escapeHtml(best.value)}','${escapeHtml(best.locator_type)}', event)">🔁 Copy XPath</button>
        </div>
      </div>
      <div class="score-wrap">
        <div class="score-track"><div class="score-fill" style="width:${pct}%"></div></div>
        <span class="score-pct">${pct}%</span>
      </div>
      <div class="card-actions">
        <button onclick="copyLocator('${escapeHtml(best.value)}', event)">📋 Copy</button>
        <button onclick="showDetails(${el.element_index})">🔎 Details</button>
        <button class="validate-btn" data-validate-index="${el.element_index}" onclick="validateLocator(${el.element_index})">✅ Validate</button>
      </div>
      <div id="validate-status-${el.element_index}" class="validate-card-status hidden">Validating locator… please wait</div>`;
    grid.appendChild(card);
  });
}

/* ─── Filter ─── */
function filterElements() {
  const query = document.getElementById("search-box").value.trim();
  const reliability = document.getElementById("reliability-filter").value || null;

  // Debounce server-side filtering to avoid excessive requests
  if (filterDebounceTimer) clearTimeout(filterDebounceTimer);
  filterDebounceTimer = setTimeout(async () => {
    if (!paginationState.currentRequest) return;

    const body = {
      ...paginationState.currentRequest,
      search_query: query || null,
      reliability_filter: reliability || null,
      offset: 0,
      limit: paginationState.limit,
    };

    try {
      const res = await fetch(`${API_BASE}/analyze/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || "Filter API error");
      }

      const data = await res.json();
      allElements = data.elements;
      paginationState.totalAvailable = data.total_available;
      paginationState.currentOffset = data.offset + data.total_elements;

      // Update UI without clearing the search box
      document.getElementById("no-results").classList.toggle("hidden", allElements.length > 0);
      document.getElementById("total-count").textContent =
        `📊 ${allElements.length} element${allElements.length === 1 ? "" : "s"} shown${paginationState.totalAvailable > allElements.length ? ` of ${paginationState.totalAvailable}` : ""}`;
      renderGrid(allElements);
      updatePaginationUI();
    } catch (err) {
      showToast(`Filter error: ${err.message}`);
    }
  }, 300);
}

function exportPOM() {
  if (!allElements.length) {
    showToast("No elements to export. Analyze a page first.");
    return;
  }

  const url = document.getElementById("url-input").value.trim() || null;
  const data = {
    generated_at: new Date().toISOString(),
    source_url: url,
    total_elements: allElements.length,
    elements: allElements
  };

  const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
  const link = document.createElement("a");
  link.href = URL.createObjectURL(blob);
  link.download = "smart_locator_pom.json";
  link.style.display = "none";
  document.body.appendChild(link);
  link.click();
  setTimeout(() => {
    URL.revokeObjectURL(link.href);
    link.remove();
  }, 1000);

  showToast("POM exported successfully.");
}

function showToast(message) {
  const toast = document.getElementById("toast");
  toast.textContent = message;
  toast.classList.remove("hidden");
  toast.classList.add("visible");
  clearTimeout(window.toastTimeout);
  window.toastTimeout = setTimeout(() => {
    toast.classList.remove("visible");
    toast.classList.add("hidden");
  }, 2800);
}

/* ─── Detail modal ─── */
function showDetails(index) {
  const el = allElements.find(e => e.element_index === index);
  if (!el) return;

  document.getElementById("modal-title").textContent =
    `<${el.tag}> — All Locators (${el.locators.length})`;

  let html = `<div class="attr-list"><strong>Attributes:</strong><br>`;
  for (const [k, v] of Object.entries(el.attributes)) {
    html += `<span class="attr-chip">${k}="${escapeHtml(v)}"</span> `;
  }
  html += `</div><div class="locators-list">`;

  el.locators.forEach(loc => {
    const pct = Math.round(loc.score * 100);
    const xpathForLoc = (loc.locator_type === 'css') ? cssAttrToXPath(loc.value) : (loc.value && (loc.value.trim().startsWith('/') ? loc.value : '//' + loc.value));
    html += `
      <div class="locator-row ${loc.reliability}">
        <div class="loc-meta">
          <span class="loc-type">${loc.locator_type.toUpperCase()}</span>
          <span class="strategy-label">${loc.strategy}</span>
          <span class="reliability-badge ${loc.reliability}">${loc.reliability}</span>
          <span class="score-text">${pct}%</span>
        </div>
        <div style="display:block;">
          <div class="locator-css"><strong>CSS:</strong> <code>${escapeHtml(loc.value)}</code></div>
          <div class="locator-xpath" style="margin-top:.25rem;"><strong>XPath:</strong> <code>${escapeHtml(xpathForLoc)}</code></div>
        </div>
        ${loc.notes ? `<div class="loc-notes">💡 ${loc.notes}</div>` : ""}
        <div style="display:flex;gap:.4rem;flex-wrap:wrap;margin-top:.4rem">
          <button class="card-actions" onclick="copyLocator('${escapeHtml(loc.value)}', event)"
            style="font-size:.76rem;padding:3px 9px;border:1px solid var(--border);
                   background:transparent;color:var(--text);border-radius:5px;cursor:pointer">
            📋 Copy
          </button>
          <button class="card-actions" onclick="copyAsXPath('${escapeHtml(loc.value)}','${escapeHtml(loc.locator_type)}', event)"
            style="font-size:.76rem;padding:3px 9px;border:1px solid var(--border);
                   background:transparent;color:var(--text);border-radius:5px;cursor:pointer">
            🔁 Copy XPath
          </button>
          <button onclick="generateCode('${escapeHtml(loc.locator_type)}','${escapeHtml(loc.value)}','selenium','python')"
            style="font-size:.76rem;padding:3px 9px;border:1px solid var(--border);
                   background:transparent;color:var(--text);border-radius:5px;cursor:pointer">
            🐍 Python Code
          </button>
          <button onclick="generateCode('${escapeHtml(loc.locator_type)}','${escapeHtml(loc.value)}','playwright','js')"
            style="font-size:.76rem;padding:3px 9px;border:1px solid var(--border);
                   background:transparent;color:var(--text);border-radius:5px;cursor:pointer">
            🧪 Playwright JS
          </button>
          <button onclick="generateCode('${escapeHtml(loc.locator_type)}','${escapeHtml(loc.value)}','playwright','ts')"
            style="font-size:.76rem;padding:3px 9px;border:1px solid var(--border);
                   background:transparent;color:var(--text);border-radius:5px;cursor:pointer">
            🧪 Playwright TS
          </button>
          <button onclick="generateCode('${escapeHtml(loc.locator_type)}','${escapeHtml(loc.value)}','cypress','js')"
            style="font-size:.76rem;padding:3px 9px;border:1px solid var(--border);
                   background:transparent;color:var(--text);border-radius:5px;cursor:pointer">
            ☂ Cypress
          </button>
        </div>
      </div>`;
  });
  html += `</div>`;

  const modalBody = document.getElementById("modal-body");
  modalBody.innerHTML = html;
  modalBody.scrollTop = 0;
  document.getElementById("modal").classList.remove("hidden");
  document.body.style.overflow = "hidden";
}

/* ─── Live Selenium validation ─── */
async function validateLocator(index) {
  const el = allElements.find(e => e.element_index === index);
  if (!el) {
    alert("Validation error: element data is not available. Refresh the results and try again.");
    return;
  }

  const url = document.getElementById("url-input").value.trim();
  if (!url) {
    alert("URL validation requires a URL in the URL input.");
    return;
  }

  setValidateCardStatus(index, "Validating locator… please wait", true);
  setValidateButtonState(index, true);

  const best = el.best_locator;
  try {
    const res = await fetch(`${API_BASE}/validate/`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url, locator_type: best.locator_type, locator_value: best.value })
    });
    const data = await res.json();
    if (!res.ok) {
      throw new Error(data.detail || data.message || res.statusText || "Validation failed");
    }

    const message = data.message || data.detail || "Validation completed.";
    alert(`${message}\n\nLocator : ${data.locator_value || best.value}\nFound   : ${typeof data.elements_found === 'number' ? data.elements_found : 'unknown'} element(s)\nUnique  : ${data.is_unique ?? 'unknown'}`);
  } catch (e) {
    alert(`Validation error: ${e.message || e}`);
  } finally {
    setValidateCardStatus(index, "", false);
    setValidateButtonState(index, false);
  }
}

/* ─── Generate Code ─── */
async function generateCode(locatorType, locatorValue, target = "selenium", language = "python") {
  const modalBody = document.getElementById("modal-body");
  const url = document.getElementById("url-input").value.trim() || "https://example.com";
  const res = await fetch(`${API_BASE}/validate/generate-code`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      url,
      locator_type: locatorType,
      locator_value: locatorValue,
      target,
      language,
    })
  });
  const data = await res.json();
  if (!res.ok) {
    throw new Error(data.detail || data.message || res.statusText || "Code generation failed");
  }

  const existing = modalBody.querySelector("pre.code-block");
  if (existing) existing.remove();
  modalBody.innerHTML +=
    `<pre class="code-block">${escapeHtml(data.code)}</pre>`;
}

/* ─── Copy locator to clipboard ─── */
function copyLocator(value, event) {
  navigator.clipboard.writeText(value).then(() => {
    if (event && event.target) {
      const btn = event.target;
      btn.textContent = "✅ Copied!";
      setTimeout(() => btn.textContent = "📋 Copy", 1600);
    }
  });
}

/* ─── Modal helpers ─── */
function closeModal() {
  document.getElementById("modal").classList.add("hidden");
  document.body.style.overflow = "auto";
}
function setValidateButtonState(index, disabled) {
  const btn = document.querySelector(`[data-validate-index="${index}"]`);
  if (!btn) return;
  btn.disabled = disabled;
  btn.style.cursor = disabled ? "not-allowed" : "pointer";
  btn.style.opacity = disabled ? "0.6" : "1";
}

function setValidateCardStatus(index, message, visible) {
  const status = document.getElementById(`validate-status-${index}`);
  if (!status) return;
  status.textContent = message;
  status.classList.toggle("hidden", !visible);
}

function handleModalBg(event) {
  if (event.target.id === "modal") closeModal();
}

function initApp() {
  const searchBox = document.getElementById("search-box");
  const reliabilitySelect = document.getElementById("reliability-filter");
  const exportBtn = document.getElementById("export-pom-btn");
  const modal = document.getElementById("modal");

  if (searchBox) searchBox.addEventListener("input", filterElements);
  if (reliabilitySelect) reliabilitySelect.addEventListener("change", filterElements);
  if (exportBtn) exportBtn.addEventListener("click", exportPOM);
  if (modal) modal.addEventListener("click", handleModalBg);
}

if (document.readyState === "loading") {
  window.addEventListener("DOMContentLoaded", initApp);
} else {
  initApp();
}

/* ─── Utilities ─── */
function truncate(str, n) {
  return str.length > n ? str.substring(0, n) + "…" : str;
}
function escapeHtml(str) {
  return String(str)
    .replace(/&/g, "&amp;").replace(/</g, "&lt;")
    .replace(/>/g, "&gt;").replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

/* ─── Copy as XPath helper ─── */
function cssAttrToXPath(sel) {
  // match tag[attr="value"] or tag[attr='value']
  const m = sel.match(/^\s*([a-zA-Z0-9_-]+)\s*\[\s*([^\s=\]]+)\s*=\s*(["'])(.*?)\3\s*\]\s*$/);
  if (m) {
    const tag = m[1], attr = m[2], value = m[4];
    return `//${tag}[@${attr}="${value}"]`;
  }
  // fallback: convert [attr="value"] -> [@attr="value"] and ensure leading //
  const s = sel.replace(/\[([^\]=]+)=(["'])(.*?)\2\]/g, '[@$1="$3"]');
  return s.trim().startsWith('//') ? s : '//' + s;
}

function copyAsXPath(value, locatorType, event) {
  let xpath = value;
  try {
    if (locatorType === 'css') {
      xpath = cssAttrToXPath(value);
    } else if (!value.trim().startsWith('//') && !value.trim().startsWith('/')) {
      xpath = '//' + value;
    }
  } catch (e) {
    xpath = value;
  }
  navigator.clipboard.writeText(xpath).then(() => {
    if (event && event.target) {
      const btn = event.target;
      btn.textContent = '✅ Copied XPath';
      setTimeout(() => btn.textContent = '🔁 Copy XPath', 1600);
    }
  });
}