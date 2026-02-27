const form = document.getElementById("search-form");
const queryInput = document.getElementById("query");
const limitInput = document.getElementById("limit");
const button = document.getElementById("search-button");
const reasoning = document.getElementById("reasoning");
const statusBox = document.getElementById("status");
const gallery = document.getElementById("gallery");
const template = document.getElementById("card-template");

let abortController = null;

function setStatus(message, isError = false) {
  statusBox.textContent = message;
  statusBox.classList.toggle("error", isError);
}

function clearResults() {
  gallery.innerHTML = "";
  reasoning.textContent = "";
  reasoning.classList.add("hidden");
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

function renderCards(results) {
  gallery.innerHTML = "";
  for (const [index, item] of results.entries()) {
    const node = template.content.firstElementChild.cloneNode(true);
    const imgLink = node.querySelector(".image-link");
    const img = node.querySelector(".thumb");
    const title = node.querySelector(".title");
    const chipsWrap = node.querySelector(".chips");
    const sourceLink = node.querySelector(".source-link");

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
    node.style.animationDelay = `${Math.min(index * 40, 360)}ms`;
    gallery.appendChild(node);
  }
}

async function performSearch(query, limit) {
  if (abortController) {
    abortController.abort();
  }
  abortController = new AbortController();

  button.disabled = true;
  setStatus("Searching Openverse image index...");

  try {
    const response = await fetch(
      `/search?q=${encodeURIComponent(query)}&limit=${encodeURIComponent(limit)}`,
      {
        signal: abortController.signal,
        headers: { Accept: "application/json" },
      }
    );

    if (!response.ok) {
      throw new Error(`Search failed (${response.status})`);
    }

    const data = await response.json();
    reasoning.textContent = data.reasoning_steps || "";
    reasoning.classList.remove("hidden");

    if (!Array.isArray(data.results)) {
      gallery.innerHTML = "";
      setStatus("No results found for that query.");
      return;
    }

    renderCards(data.results);
    setStatus(`Found ${data.results.length} image(s).`);
  } catch (error) {
    if (error.name === "AbortError") {
      return;
    }
    clearResults();
    setStatus(error.message || "Unknown error", true);
  } finally {
    button.disabled = false;
  }
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();

  const query = queryInput.value.trim();
  const limit = Number(limitInput.value || 12);

  if (query.length < 2) {
    setStatus("Write at least 2 characters in the query.", true);
    return;
  }

  clearResults();
  await performSearch(query, limit);
});

setStatus("Ready. Enter a query and press Find Images.");
