import { $ } from "./state.js";
import { escapeHtml } from "./dom-utils.js";
import {
  docsCatalog,
  activeDocPath,
  setDocsCatalog,
  setActiveDocPath,
} from "./ui-state.js";

export async function loadDocsCatalog() {
  const nav = $("docs-nav");
  nav.innerHTML = "<p class='hint'>Loading…</p>";
  try {
    const res = await fetch("/api/docs/catalog");
    const catalog = await res.json();
    setDocsCatalog(catalog);
    if (!docsCatalog.sections?.length) {
      nav.innerHTML = "<p class='hint'>No docs found. Set SOULOS_DOCS_ROOT or run from the monorepo.</p>";
      return;
    }
    nav.innerHTML = "";
    docsCatalog.sections.forEach((section) => {
      const block = document.createElement("div");
      block.className = "docs-section";
      block.innerHTML = `<p class="docs-section-title">${section.title}</p>`;
      section.items.forEach((item) => {
        const btn = document.createElement("button");
        btn.type = "button";
        btn.className = "docs-link";
        btn.dataset.path = item.path;
        btn.textContent = item.title;
        btn.title = item.description || item.title;
        btn.addEventListener("click", () => loadDoc(item.path));
        block.appendChild(btn);
      });
      nav.appendChild(block);
    });
    const first = docsCatalog.sections[0]?.items[0];
    if (first && !activeDocPath) loadDoc(first.path);
  } catch (e) {
    nav.innerHTML = `<p class='hint'>Failed to load docs: ${e.message}</p>`;
  }
}

export async function loadDoc(path) {
  setActiveDocPath(path);
  document.querySelectorAll(".docs-link").forEach((btn) => {
    btn.classList.toggle("active", btn.dataset.path === path);
  });

  const content = $("docs-content");
  content.innerHTML = "<p class='hint'>Loading…</p>";
  try {
    const res = await fetch(`/api/docs/content?path=${encodeURIComponent(path)}`);
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "load failed");
    content.innerHTML = data.html;
  } catch (e) {
    content.innerHTML = `<p class='hint'>${e.message}</p>`;
  }
}

export async function loadTutorials() {
  const grid = $("tutorial-grid");
  grid.innerHTML = "<p class='hint'>Loading…</p>";
  try {
    const res = await fetch("/api/tutorials");
    const data = await res.json();
    grid.innerHTML = "";
    data.tutorials.forEach((t) => {
      const card = document.createElement("button");
      card.type = "button";
      card.className = "tutorial-card";
      card.innerHTML = `
        <h3>${escapeHtml(t.title)}</h3>
        <p>${escapeHtml(t.description)}</p>
        <div class="tutorial-card-meta">
          <span>${escapeHtml(t.category)}</span>
          <span>${escapeHtml(t.duration)}</span>
          ${t.interactive ? "<span class='it-badge'>Interactive</span>" : ""}
        </div>
      `;
      card.addEventListener("click", () => openTutorial(t.id));
      grid.appendChild(card);
    });
  } catch (e) {
    grid.innerHTML = `<p class='hint'>${e.message}</p>`;
  }
}

export async function openTutorial(id) {
  const { switchView } = await import("./views.js");
  $("tutorial-list-view").classList.add("hidden");
  $("tutorial-detail-view").classList.remove("hidden");
  $("tutorial-meta").innerHTML = "<p class='hint'>Loading…</p>";
  $("tutorial-content").innerHTML = "";
  $("tutorial-content").className = "prose";
  try {
    const res = await fetch(`/api/tutorials/${encodeURIComponent(id)}`);
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "load failed");
    $("tutorial-meta").innerHTML = `
      <h2>${escapeHtml(data.title)}</h2>
      <div class="tutorial-card-meta">
        <span>${escapeHtml(data.category || "")}</span>
        <span>${escapeHtml(data.duration || "")}</span>
        ${data.format === "interactive" || data.format === "interactive_terminal" || data.format === "interactive_studio" ? "<span class='it-badge'>Interactive</span>" : ""}
      </div>
    `;
    const contentEl = $("tutorial-content");
    if (isInteractiveTutorial(data) && typeof mountInteractiveTutorial === "function") {
      contentEl.className = "";
      mountInteractiveTutorial(contentEl, data, {
        switchView,
        closeTutorialDetail,
      });
    } else {
      contentEl.className = "prose";
      contentEl.innerHTML = data.html;
      enhanceProseTutorial(contentEl);
    }
  } catch (e) {
    $("tutorial-meta").innerHTML = `<p class='hint'>${e.message}</p>`;
  }
}

export function closeTutorialDetail() {
  $("tutorial-list-view").classList.remove("hidden");
  $("tutorial-detail-view").classList.add("hidden");
}

export function enhanceProseTutorial(root) {
  root.querySelectorAll("pre").forEach((pre) => {
    if (pre.parentElement?.classList.contains("it-code-wrap")) return;
    const wrap = document.createElement("div");
    wrap.className = "it-code-wrap";
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "btn ghost sm it-copy";
    btn.textContent = "Copy";
    btn.addEventListener("click", async () => {
      const text = pre.textContent || "";
      try {
        await navigator.clipboard.writeText(text);
        btn.textContent = "Copied!";
        setTimeout(() => { btn.textContent = "Copy"; }, 1500);
      } catch (_) {
        btn.textContent = "Failed";
      }
    });
    pre.parentNode.insertBefore(wrap, pre);
    wrap.append(pre, btn);
  });
}

function isInteractiveTutorial(data) {
  return (
    data.format === "interactive" ||
    data.format === "interactive_terminal" ||
    data.format === "interactive_studio"
  );
}
