/**
 * SoulOS tutorials — static site (GitHub Pages). Loads pre-built JSON, no FastAPI.
 */

const THEME_KEY = "soulos-studio-theme";

const $ = (id) => document.getElementById(id);

function assetUrl(rel) {
  const base = (window.STUDIO_BASE || "./").replace(/\/?$/, "/");
  const path = rel.replace(/^\//, "");
  return `${base}${path}`;
}

function escapeHtml(str) {
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function isDarkTheme() {
  return document.documentElement.dataset.theme === "dark";
}

function initTheme() {
  const saved = localStorage.getItem(THEME_KEY);
  const theme = saved === "dark" ? "dark" : "light";
  document.documentElement.dataset.theme = theme;
  updateThemeButton();
}

function toggleTheme() {
  const next = isDarkTheme() ? "light" : "dark";
  document.documentElement.dataset.theme = next;
  localStorage.setItem(THEME_KEY, next);
  updateThemeButton();
}

function updateThemeButton() {
  const btn = $("btn-theme");
  if (!btn) return;
  btn.textContent = isDarkTheme() ? "☀" : "☾";
  btn.title = isDarkTheme() ? "Switch to light theme" : "Switch to dark theme";
}

function enhanceProseTutorial(root) {
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

function closeTutorialDetail() {
  $("tutorial-list-view").classList.remove("hidden");
  $("tutorial-detail-view").classList.add("hidden");
  history.replaceState(null, "", location.pathname);
}

function tutorialDeepLinkId() {
  const params = new URLSearchParams(location.search);
  const q = params.get("tutorial");
  if (q) return q;
  const hash = location.hash.replace(/^#/, "");
  if (hash.startsWith("tutorial/")) return decodeURIComponent(hash.slice("tutorial/".length));
  return null;
}

function setTutorialDeepLink(id) {
  const basePath = location.pathname.replace(/\/$/, "") || "/";
  const url = `${basePath}?tutorial=${encodeURIComponent(id)}`;
  history.replaceState(null, "", url);
}

async function loadTutorials() {
  const grid = $("tutorial-grid");
  grid.innerHTML = "<p class='hint'>Loading…</p>";
  try {
    const res = await fetch(assetUrl("data/tutorials.json"));
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "load failed");
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

async function openTutorial(id) {
  $("tutorial-list-view").classList.add("hidden");
  $("tutorial-detail-view").classList.remove("hidden");
  $("tutorial-meta").innerHTML = "<p class='hint'>Loading…</p>";
  $("tutorial-content").innerHTML = "";
  $("tutorial-content").className = "prose";
  setTutorialDeepLink(id);
  try {
    const res = await fetch(assetUrl(`data/tutorials/${encodeURIComponent(id)}.json`));
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "load failed");
    $("tutorial-meta").innerHTML = `
      <h2>${escapeHtml(data.title)}</h2>
      <div class="tutorial-card-meta">
        <span>${escapeHtml(data.category || "")}</span>
        <span>${escapeHtml(data.duration || "")}</span>
        ${data.format === "interactive" || data.format === "interactive_terminal" ? "<span class='it-badge'>Interactive</span>" : ""}
      </div>
    `;
    const contentEl = $("tutorial-content");
    if (typeof isInteractiveTutorial === "function" && isInteractiveTutorial(data) && typeof mountInteractiveTutorial === "function") {
      contentEl.className = "";
      mountInteractiveTutorial(contentEl, data, {
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

async function init() {
  initTheme();
  $("btn-theme").addEventListener("click", toggleTheme);
  $("tutorial-back").addEventListener("click", closeTutorialDetail);

  await loadTutorials();

  const deepId = tutorialDeepLinkId();
  if (deepId) {
    openTutorial(deepId);
  }
}

init();
