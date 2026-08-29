import { state, $, THEME_KEY } from "./state.js";

export function isDarkTheme() {
  return document.documentElement.dataset.theme === "dark";
}

export function initTheme() {
  const saved = localStorage.getItem(THEME_KEY);
  const theme = saved === "dark" ? "dark" : "light";
  document.documentElement.dataset.theme = theme;
  updateThemeButton();
}

export function toggleTheme() {
  const next = isDarkTheme() ? "light" : "dark";
  document.documentElement.dataset.theme = next;
  localStorage.setItem(THEME_KEY, next);
  updateThemeButton();
  if (state.form?.hexaco) drawRadar(state.form.hexaco);
}

export function updateThemeButton() {
  const btn = $("btn-theme");
  if (!btn) return;
  btn.textContent = isDarkTheme() ? "☀" : "☾";
  btn.title = isDarkTheme() ? "Switch to light theme" : "Switch to dark theme";
}

export function sliderRow(key, label, value, onChange, prefix = "val") {
  const row = document.createElement("div");
  row.className = "slider-row";
  const valId = `${prefix}-${key}`;
  row.innerHTML = `
    <label><span>${label}</span><span id="${valId}">${value.toFixed(2)}</span></label>
    <input type="range" min="0" max="1" step="0.01" value="${value}" data-key="${key}" />
  `;
  row.querySelector("input").addEventListener("input", (e) => {
    const v = parseFloat(e.target.value);
    document.getElementById(valId).textContent = v.toFixed(2);
    onChange(key, v);
  });
  return row;
}

export function hexacoSliderRow(key, label, value, onChange) {
  return sliderRow(key, label, value, onChange, "hex");
}

export function readFormFromDom() {
  state.form.name = $("name").value;
  state.form.role = $("role").value;
  state.form.description = $("description").value;
  state.form.attachment_style = $("attachment_style").value;
  state.form.inner_monologue = $("inner_monologue").value;
  state.form.epistemic_uncertainty = parseFloat($("epistemic_uncertainty").value);
}

export function writeFormToDom() {
  $("name").value = state.form.name;
  $("role").value = state.form.role;
  $("description").value = state.form.description;
  $("attachment_style").value = state.form.attachment_style;
  $("inner_monologue").value = state.form.inner_monologue;
  $("epistemic_uncertainty").value = state.form.epistemic_uncertainty;
  $("uncertainty-val").textContent = state.form.epistemic_uncertainty.toFixed(2);
}

export function buildSliders() {
  const simple = $("simple-sliders");
  if (simple && state.form.simple_persona) {
    simple.innerHTML = "";
    const labels = { warmth: "Warmth", rigor: "Rigor", caution: "Caution" };
    for (const [key, label] of Object.entries(labels)) {
      simple.appendChild(
        sliderRow(key, label, state.form.simple_persona[key] ?? 0.5, (k, v) => {
          state.form.simple_persona[k] = v;
          refreshSoul();
        }, "simp")
      );
    }
  }

  const hex = $("hexaco-sliders");
  hex.innerHTML = "";
  for (const [key, label] of Object.entries(state.meta.hexaco_labels)) {
    hex.appendChild(
      hexacoSliderRow(key, label, state.form.hexaco[key], (k, v) => {
        state.form.hexaco[k] = v;
        refreshSoul();
      })
    );
  }

  const moral = $("moral-sliders");
  moral.innerHTML = "";
  state.meta.moral_meta.forEach(({ key, label }) => {
    moral.appendChild(
      sliderRow(key, label, state.form.moral_foundations[key], (k, v) => {
        state.form.moral_foundations[k] = v;
        refreshSoul();
      })
    );
  });

  const drives = $("drive-sliders");
  drives.innerHTML = "";
  state.meta.drive_meta.forEach(({ key, label }) => {
    drives.appendChild(
      sliderRow(key, label, state.form.drives[key], (k, v) => {
        state.form.drives[k] = v;
        refreshSoul();
      })
    );
  });
}

export async function refreshSoul() {
  readFormFromDom();
  try {
    const res = await fetch("/api/build", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(state.form),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "build failed");
    state.soul = data;
    state.valid = true;
    $("validation-badge").textContent = "Valid";
    $("validation-badge").className = "badge ok";
  } catch (e) {
    state.valid = false;
    $("validation-badge").textContent = "Invalid";
    $("validation-badge").className = "badge err";
    state.soul = null;
    $("json-preview").textContent = String(e.message);
    return;
  }
  $("json-preview").textContent = JSON.stringify(state.soul, null, 2);
  updateHexacoChips(state.form.hexaco);
  drawRadar(state.form.hexaco);
}

export function updateHexacoChips(hexaco) {
  const container = $("hexaco-chips");
  if (!container || !state.meta) return;
  container.innerHTML = "";
  for (const [key, label] of Object.entries(state.meta.hexaco_labels)) {
    const v = hexaco[key] ?? 0;
    const chip = document.createElement("div");
    chip.className = "hexaco-chip";
    chip.title = label;
    chip.innerHTML = `
      <div class="hexaco-chip-top">
        <span class="hexaco-chip-key">${key}</span>
        <span class="hexaco-chip-val">${v.toFixed(2)}</span>
      </div>
      <div class="hexaco-chip-bar"><div class="hexaco-chip-fill" style="width:${(v * 100).toFixed(1)}%"></div></div>
    `;
    container.appendChild(chip);
  }
}

export function sizeRadarCanvas() {
  const canvas = $("radar");
  const wrap = canvas?.parentElement;
  if (!canvas || !wrap) return { size: 0, dpr: 1 };
  const dpr = window.devicePixelRatio || 1;
  const size = wrap.clientWidth || 260;
  canvas.width = Math.floor(size * dpr);
  canvas.height = Math.floor(size * dpr);
  return { size, dpr };
}

export function drawRadar(hexaco) {
  const canvas = $("radar");
  if (!canvas) return;
  const ctx = canvas.getContext("2d");
  const { size, dpr } = sizeRadarCanvas();
  if (!size) return;

  ctx.setTransform(1, 0, 0, 1, 0, 0);
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  ctx.scale(dpr, dpr);

  const cx = size / 2;
  const cy = size / 2;
  const r = size * 0.32;
  const labelR = size * 0.44;
  const keys = Object.keys(hexaco);
  const n = keys.length;
  const dark = isDarkTheme();

  ctx.lineWidth = 1;
  ctx.strokeStyle = dark ? "rgba(255,255,255,0.06)" : "rgba(15,23,42,0.06)";
  keys.forEach((_, i) => {
    const a = (Math.PI * 2 * i) / n - Math.PI / 2;
    ctx.beginPath();
    ctx.moveTo(cx, cy);
    ctx.lineTo(cx + r * Math.cos(a), cy + r * Math.sin(a));
    ctx.stroke();
  });

  ctx.strokeStyle = dark ? "rgba(255,255,255,0.1)" : "rgba(15,23,42,0.08)";
  for (let ring = 1; ring <= 4; ring++) {
    ctx.beginPath();
    const rr = (r * ring) / 4;
    for (let i = 0; i <= n; i++) {
      const a = (Math.PI * 2 * i) / n - Math.PI / 2;
      const x = cx + rr * Math.cos(a);
      const y = cy + rr * Math.sin(a);
      if (i === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    }
    ctx.stroke();
  }

  const points = keys.map((k, i) => {
    const a = (Math.PI * 2 * i) / n - Math.PI / 2;
    const v = hexaco[k] ?? 0.5;
    return { x: cx + r * v * Math.cos(a), y: cy + r * v * Math.sin(a) };
  });

  ctx.beginPath();
  points.forEach((p, i) => {
    if (i === 0) ctx.moveTo(p.x, p.y);
    else ctx.lineTo(p.x, p.y);
  });
  ctx.closePath();

  const grad = ctx.createRadialGradient(cx, cy, 0, cx, cy, r);
  grad.addColorStop(0, dark ? "rgba(167,139,250,0.38)" : "rgba(109,40,217,0.28)");
  grad.addColorStop(1, dark ? "rgba(167,139,250,0.06)" : "rgba(109,40,217,0.04)");
  ctx.fillStyle = grad;
  ctx.fill();
  ctx.strokeStyle = dark ? "#a78bfa" : "#6d28d9";
  ctx.lineWidth = 2;
  ctx.stroke();

  points.forEach((p) => {
    ctx.beginPath();
    ctx.arc(p.x, p.y, 4.5, 0, Math.PI * 2);
    ctx.fillStyle = dark ? "#c4b5fd" : "#6d28d9";
    ctx.fill();
    ctx.strokeStyle = dark ? "#18181b" : "#ffffff";
    ctx.lineWidth = 2;
    ctx.stroke();
  });

  ctx.textAlign = "center";
  ctx.textBaseline = "middle";
  keys.forEach((k, i) => {
    const a = (Math.PI * 2 * i) / n - Math.PI / 2;
    const v = hexaco[k] ?? 0;
    const lx = cx + labelR * Math.cos(a);
    const ly = cy + labelR * Math.sin(a);
    ctx.fillStyle = dark ? "#a1a1aa" : "#64748b";
    ctx.font = "600 10px system-ui, sans-serif";
    ctx.fillText(k, lx, ly - 7);
    ctx.fillStyle = dark ? "#f4f4f5" : "#0f172a";
    ctx.font = "600 11px ui-monospace, monospace";
    ctx.fillText(v.toFixed(2), lx, ly + 8);
  });
}

export function setPreviewMode(mode) {
  const body = $("soul-preview-body");
  body.classList.remove("split", "chart-only", "json-only");
  if (mode === "split") body.classList.add("split");
  else if (mode === "chart") body.classList.add("chart-only");
  else body.classList.add("json-only");

  document.querySelectorAll(".view-toggle-btn").forEach((btn) => {
    btn.classList.toggle("active", btn.dataset.preview === mode);
  });

  if (mode !== "json") {
    requestAnimationFrame(() => {
      if (state.form?.hexaco) drawRadar(state.form.hexaco);
    });
  }
}

export function copyJson() {
  if (!state.soul) return;
  const text = JSON.stringify(state.soul, null, 2);
  navigator.clipboard.writeText(text).then(() => {
    const btn = $("btn-copy-json");
    const orig = btn.textContent;
    btn.textContent = "Copied";
    setTimeout(() => { btn.textContent = orig; }, 1500);
  });
}

let resizeTimer;

export function onPreviewResize() {
  clearTimeout(resizeTimer);
  resizeTimer = setTimeout(() => {
    if (state.form?.hexaco) drawRadar(state.form.hexaco);
  }, 120);
}

export function exportSoul() {
  if (!state.soul) return;
  const blob = new Blob([JSON.stringify(state.soul, null, 2)], { type: "application/json" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  const slug = state.soul.name.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "") || "my-bot";
  a.download = `${slug}.soul.json`;
  a.click();
}

export async function exportSoulMarkdown() {
  const res = await fetch("/api/build-soul", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(state.form),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || "export failed");
  const blob = new Blob([data.text], { type: "text/plain" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  const slug = (state.form.name || "my-bot").toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "") || "my-bot";
  a.download = `${slug}.soul`;
  a.click();
}

export async function importFile(file) {
  const text = await file.text();
  const isSoul = file.name.toLowerCase().endsWith(".soul") || text.trimStart().startsWith("---");
  if (isSoul) {
    const res = await fetch("/api/import-text", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "import failed");
    state.form = data.form;
  } else {
    const soul = JSON.parse(text);
    const res = await fetch("/api/import", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ soul }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "import failed");
    state.form = data.form;
  }
  writeFormToDom();
  buildSliders();
  await refreshSoul();
}

export function setPersonaMode(mode) {
  const simplePanel = $("simple-persona-panel");
  const advancedPanel = $("advanced-persona-panel");
  const tabSimple = $("tab-simple");
  const tabAdvanced = $("tab-advanced");
  if (!simplePanel || !advancedPanel) return;
  const isSimple = mode === "simple";
  simplePanel.classList.toggle("hidden", !isSimple);
  advancedPanel.classList.toggle("hidden", isSimple);
  tabSimple?.classList.toggle("active", isSimple);
  tabAdvanced?.classList.toggle("active", !isSimple);
}

export function buildPrepareCurl(payload) {
  const body = JSON.stringify({
    bot_id: payload.bot_id,
    query: payload.query || "user question",
    top_k: 5,
  });
  return `curl -s -X POST ${state.kernelUrl}/hybrid/prepare \\\n  -H "Content-Type: application/json" \\\n  -d '${body.replace(/'/g, "'\\''")}'`;
}
