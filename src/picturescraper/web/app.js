const form = document.getElementById("search-form");
const queryInput = document.getElementById("query");
const limitInput = document.getElementById("limit");
const orientationInput = document.getElementById("orientation");
const licenseInput = document.getElementById("license");
const sourceInput = document.getElementById("source");
const button = document.getElementById("search-button");
const reasoning = document.getElementById("reasoning");
const statusBox = document.getElementById("status");
const gallery = document.getElementById("gallery");
const template = document.getElementById("card-template");
const sentinel = document.getElementById("scroll-sentinel");
const resetFiltersBtn = document.getElementById("reset-filters");
const exportJsonBtn = document.getElementById("export-json");
const exportCsvBtn = document.getElementById("export-csv");
const saveCollectionBtn = document.getElementById("save-collection");
const collectionsList = document.getElementById("collections-list");

let abortController = null;
let state = {
  query: "",
  limit: 12,
  page: 1,
  hasMore: false,
  loading: false,
  results: [],
  filters: {
    orientation: "",
    license: "",
    source: "",
  },
};

function setStatus(message, isError = false) {
  statusBox.textContent = message;
  statusBox.classList.toggle("error", isError);
}

function clearResults() {
  gallery.innerHTML = "";
  reasoning.textContent = "";
  reasoning.classList.add("hidden");
  state.results = [];
}

function chip(text) {
  return `<span class="chip">${escapeHtml(text)}</span>`;
}

function escapeHtml(raw) {
  return String(raw)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function renderCards(results, append = false) {
  if (!append) {
    gallery.innerHTML = "";
  }

  const offset = append ? gallery.children.length : 0;
  for (const [index, item] of results.entries()) {
    const node = template.content.firstElementChild.cloneNode(true);
    const imgLink = node.querySelector(".image-link");
    const img = node.querySelector(".thumb");
    const title = node.querySelector(".title");
    const chipsWrap = node.querySelector(".chips");
    const sourceLink = node.querySelector(".source-link");
    const downloadLink = node.querySelector(".download-link");

    imgLink.href = item.image_url;
    img.src = item.image_url;
    img.alt = item.title_or_alt || "Image result";

    title.textContent = item.title_or_alt || "Untitled";

    const tags = [
      item.source_name ? chip(item.source_name) : "",
      item.license ? chip(item.license) : "",
      item.date_if_available ? chip(item.date_if_available) : "",
      item.width && item.height ? chip(`${item.width}x${item.height}`) : "",
    ]
      .filter(Boolean)
      .join(" ");
    chipsWrap.innerHTML = tags || chip("metadata unavailable");

    sourceLink.href = item.page_url;
    downloadLink.href = item.image_url;
    downloadLink.setAttribute("download", "");

    node.style.animationDelay = `${Math.min((offset + index) * 35, 400)}ms`;
    gallery.appendChild(node);
  }
}

function updateSentinel() {
  sentinel.textContent = state.hasMore
    ? "Scroll to load more"
    : state.results.length > 0
      ? "No more results"
      : "";
}

function hasActiveFilters() {
  return Boolean(state.filters.orientation || state.filters.license || state.filters.source);
}

function clearFilterInputs() {
  orientationInput.value = "";
  licenseInput.value = "";
  sourceInput.value = "";
  state.filters.orientation = "";
  state.filters.license = "";
  state.filters.source = "";
}

function buildSearchUrl() {
  const params = new URLSearchParams();
  params.set("q", state.query);
  params.set("limit", String(state.limit));
  params.set("page", String(state.page));

  if (state.filters.orientation) {
    params.set("orientation", state.filters.orientation);
  }
  if (state.filters.license) {
    params.set("license", state.filters.license);
  }
  if (state.filters.source) {
    params.set("source", state.filters.source);
  }

  return `/search?${params.toString()}`;
}

async function performSearch({ append, allowUnfilteredRetry = false }) {
  if (state.loading) {
    return;
  }

  if (abortController && !append) {
    abortController.abort();
  }
  abortController = new AbortController();

  state.loading = true;
  button.disabled = true;
  setStatus(append ? "Loading more results..." : "Searching Openverse image index...");

  try {
    const response = await fetch(buildSearchUrl(), {
      signal: abortController.signal,
      headers: { Accept: "application/json" },
    });

    if (!response.ok) {
      throw new Error(`Search failed (${response.status})`);
    }

    const data = await response.json();
    reasoning.textContent = data.reasoning_steps || "";
    reasoning.classList.remove("hidden");

    if (!Array.isArray(data.results)) {
      if (!append) {
        clearResults();
      }
      if (!append && allowUnfilteredRetry && hasActiveFilters()) {
        clearFilterInputs();
        setStatus("No hits with active filters. Retrying without filters...");
        await performSearch({ append: false, allowUnfilteredRetry: false });
        return;
      }
      state.hasMore = false;
      updateSentinel();
      setStatus("No results found for that query.");
      return;
    }

    if (append) {
      state.results.push(...data.results);
    } else {
      state.results = [...data.results];
    }

    renderCards(data.results, append);
    state.hasMore = Boolean(data.has_more);
    updateSentinel();

    setStatus(
      `${state.results.length} shown of ${data.total_results ?? state.results.length} total result(s).`
    );
  } catch (error) {
    if (error.name === "AbortError") {
      return;
    }
    if (!append) {
      clearResults();
    }
    state.hasMore = false;
    updateSentinel();
    setStatus(error.message || "Unknown error", true);
  } finally {
    state.loading = false;
    button.disabled = false;
  }
}

function exportResults(format) {
  if (state.results.length === 0) {
    setStatus("Run a search before exporting.", true);
    return;
  }

  let content = "";
  let mime = "application/json;charset=utf-8";
  let extension = "json";

  if (format === "json") {
    content = JSON.stringify(
      {
        query: state.query,
        filters: state.filters,
        exported_at: new Date().toISOString(),
        count: state.results.length,
        results: state.results,
      },
      null,
      2
    );
  } else {
    mime = "text/csv;charset=utf-8";
    extension = "csv";
    const headers = [
      "image_url",
      "page_url",
      "title_or_alt",
      "source_name",
      "date_if_available",
      "license",
      "width",
      "height",
    ];
    const rows = state.results.map((item) =>
      headers
        .map((key) => {
          const value = item[key] ?? "";
          const text = String(value).replaceAll('"', '""');
          return `"${text}"`;
        })
        .join(",")
    );
    content = `${headers.join(",")}\n${rows.join("\n")}`;
  }

  const blob = new Blob([content], { type: mime });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = `picturescraper-${Date.now()}.${extension}`;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);
  setStatus(`Exported ${state.results.length} result(s) as ${extension.toUpperCase()}.`);
}

async function refreshCollections() {
  try {
    const response = await fetch("/collections", { headers: { Accept: "application/json" } });
    if (!response.ok) {
      throw new Error("Could not load collections");
    }
    const data = await response.json();
    renderCollections(data.collections || []);
  } catch (_error) {
    collectionsList.innerHTML = "<li>Unable to load collections.</li>";
  }
}

function renderCollections(collections) {
  if (collections.length === 0) {
    collectionsList.innerHTML = "<li>No saved collections yet.</li>";
    return;
  }

  collectionsList.innerHTML = "";
  for (const item of collections) {
    const li = document.createElement("li");
    const created = item.created_at ? new Date(item.created_at).toLocaleString() : "";
    li.innerHTML = `
      <span class="collection-name">${escapeHtml(item.name)}</span>
      <span class="collection-meta">${escapeHtml(item.query)} • ${item.result_count} images • ${escapeHtml(created)}</span>
      <button type="button" class="collection-load" data-id="${escapeHtml(item.id)}">Load</button>
    `;
    collectionsList.appendChild(li);
  }
}

async function saveCollection() {
  if (state.results.length === 0) {
    setStatus("Search before saving a collection.", true);
    return;
  }

  const name = window.prompt("Collection name:", state.query);
  if (!name || !name.trim()) {
    return;
  }

  const payload = {
    name: name.trim(),
    query: state.query,
    filters: state.filters,
    results: state.results,
  };

  const response = await fetch("/collections", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: "application/json",
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    setStatus("Failed to save collection.", true);
    return;
  }

  setStatus("Collection saved.");
  await refreshCollections();
}

async function loadCollection(collectionId) {
  const response = await fetch(`/collections/${encodeURIComponent(collectionId)}`);
  if (!response.ok) {
    setStatus("Failed to load collection.", true);
    return;
  }

  const data = await response.json();
  queryInput.value = data.query || "";
  state.query = data.query || "";

  const loadedFilters = data.filters || {};
  state.filters.orientation = loadedFilters.orientation || "";
  state.filters.license = loadedFilters.license || "";
  state.filters.source = loadedFilters.source || "";
  orientationInput.value = state.filters.orientation;
  licenseInput.value = state.filters.license;
  sourceInput.value = state.filters.source;

  state.page = 1;
  state.hasMore = false;
  state.results = Array.isArray(data.results) ? data.results : [];

  reasoning.textContent = `Loaded collection: ${data.name}`;
  reasoning.classList.remove("hidden");
  renderCards(state.results, false);
  updateSentinel();
  setStatus(`Loaded ${state.results.length} saved image(s).`);
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();

  const query = queryInput.value.trim();
  const limit = Number(limitInput.value || 12);

  if (query.length < 2) {
    setStatus("Write at least 2 characters in the query.", true);
    return;
  }

  state.query = query;
  state.limit = Math.min(Math.max(limit, 1), 50);
  state.page = 1;
  state.filters.orientation = orientationInput.value;
  state.filters.license = licenseInput.value.trim();
  state.filters.source = sourceInput.value.trim();

  clearResults();
  updateSentinel();
  await performSearch({ append: false, allowUnfilteredRetry: true });
});

exportJsonBtn.addEventListener("click", () => exportResults("json"));
exportCsvBtn.addEventListener("click", () => exportResults("csv"));
saveCollectionBtn.addEventListener("click", () => {
  saveCollection().catch(() => setStatus("Failed to save collection.", true));
});
resetFiltersBtn.addEventListener("click", () => {
  clearFilterInputs();
  setStatus("Filters reset.");
});

collectionsList.addEventListener("click", (event) => {
  const target = event.target;
  if (!(target instanceof HTMLElement)) {
    return;
  }
  if (target.matches(".collection-load")) {
    const collectionId = target.dataset.id;
    if (collectionId) {
      loadCollection(collectionId).catch(() => setStatus("Failed to load collection.", true));
    }
  }
});

const observer = new IntersectionObserver(
  (entries) => {
    const visible = entries.some((entry) => entry.isIntersecting);
    if (!visible || !state.hasMore || state.loading || !state.query) {
      return;
    }
    state.page += 1;
    performSearch({ append: true }).catch(() => {
      state.page -= 1;
      setStatus("Failed to load next page.", true);
    });
  },
  { rootMargin: "240px" }
);
observer.observe(sentinel);

refreshCollections();
setStatus("Ready. Enter a query and press Find Images.");
updateSentinel();
