/* SoulOS Studio — vanilla JS, no build step */

const state = {
  meta: null,
  form: null,
  soul: null,
  avatarId: null,
  valid: true,
};

const wizard = {
  step: 0,
  form: null,
  steps: [],
};

const ATTACHMENT_HINTS = {
  Secure: "Warm and consistent — connects without anxiety or avoidance.",
  "Anxious-Preoccupied": "Sensitive to rejection — seeks reassurance in relationships.",
  "Dismissive-Avoidant": "Values independence — may appear emotionally distant.",
};

const THEME_KEY = "soulos-studio-theme";

const $ = (id) => document.getElementById(id);

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
  if (state.form?.hexaco) drawRadar(state.form.hexaco);
}

function updateThemeButton() {
  const btn = $("btn-theme");
  if (!btn) return;
  btn.textContent = isDarkTheme() ? "☀" : "☾";
  btn.title = isDarkTheme() ? "Switch to light theme" : "Switch to dark theme";
}

function sliderRow(key, label, value, onChange, prefix = "val") {
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

function hexacoSliderRow(key, label, value, onChange) {
  return sliderRow(key, label, value, onChange, "hex");
}

function readFormFromDom() {
  state.form.name = $("name").value;
  state.form.role = $("role").value;
  state.form.description = $("description").value;
  state.form.attachment_style = $("attachment_style").value;
  state.form.inner_monologue = $("inner_monologue").value;
  state.form.epistemic_uncertainty = parseFloat($("epistemic_uncertainty").value);
}

function writeFormToDom() {
  $("name").value = state.form.name;
  $("role").value = state.form.role;
  $("description").value = state.form.description;
  $("attachment_style").value = state.form.attachment_style;
  $("inner_monologue").value = state.form.inner_monologue;
  $("epistemic_uncertainty").value = state.form.epistemic_uncertainty;
  $("uncertainty-val").textContent = state.form.epistemic_uncertainty.toFixed(2);
}

function buildSliders() {
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

async function refreshSoul() {
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

function updateHexacoChips(hexaco) {
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

function sizeRadarCanvas() {
  const canvas = $("radar");
  const wrap = canvas?.parentElement;
  if (!canvas || !wrap) return { size: 0, dpr: 1 };
  const dpr = window.devicePixelRatio || 1;
  const size = wrap.clientWidth || 260;
  canvas.width = Math.floor(size * dpr);
  canvas.height = Math.floor(size * dpr);
  return { size, dpr };
}

function drawRadar(hexaco) {
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

function setPreviewMode(mode) {
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

function copyJson() {
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
function onPreviewResize() {
  clearTimeout(resizeTimer);
  resizeTimer = setTimeout(() => {
    if (state.form?.hexaco) drawRadar(state.form.hexaco);
  }, 120);
}

function logChat(text, role = "sys") {
  const div = document.createElement("div");
  div.className = `chat-line ${role}`;
  div.textContent = text;
  $("chat-log").appendChild(div);
  $("chat-log").scrollTop = $("chat-log").scrollHeight;
}

function buildMcpConfig() {
  const kernelUrl = (state.meta?.kernel_url || "http://localhost:8000").replace(/\/$/, "");
  return {
    mcpServers: {
      soulos: {
        url: `${kernelUrl}/mcp/sse`,
      },
    },
  };
}

function showMcpConnect(botId, name) {
  const panel = $("mcp-connect");
  const kernelUrl = (state.meta?.kernel_url || "http://localhost:8000").replace(/\/$/, "");
  $("mcp-bot-id").textContent = `bot_id: ${botId} (${name}) · MCP: ${kernelUrl}/mcp/sse`;
  $("mcp-config").textContent = JSON.stringify(buildMcpConfig(), null, 2);
  panel.classList.remove("hidden");
}

async function copyMcpConfig() {
  if (!state.avatarId) return;
  const text = $("mcp-config").textContent;
  try {
    await navigator.clipboard.writeText(text);
    const btn = $("btn-copy-mcp");
    const prev = btn.textContent;
    btn.textContent = "Copied!";
    setTimeout(() => {
      btn.textContent = prev;
    }, 1500);
  } catch {
    logChat("Could not copy MCP config — select the JSON and copy manually.", "sys");
  }
}

async function deploy() {
  await refreshSoul();
  if (!state.soul) return;
  $("btn-deploy").disabled = true;
  try {
    const res = await fetch("/api/register", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ soul: state.soul }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "deploy failed");
    state.avatarId = data.id;
    $("avatar-id").textContent = `Avatar: ${data.name} (${data.id})`;
    $("chat-input").disabled = false;
    $("chat-send").disabled = false;
    showMcpConnect(data.id, data.name);
    logChat(`Deployed ${data.name}`, "sys");
  } catch (e) {
    logChat(`Deploy failed: ${e.message}`, "sys");
  }
  $("btn-deploy").disabled = false;
}

async function sendChat(message) {
  if (!state.avatarId) return;
  logChat(message, "user");
  const res = await fetch("/api/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ avatar_id: state.avatarId, message }),
  });
  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let botLine = document.createElement("div");
  botLine.className = "chat-line bot";
  $("chat-log").appendChild(botLine);
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const blocks = buffer.split("\n\n");
    buffer = blocks.pop() || "";
    for (const block of blocks) {
      const event = block.match(/event: (.*)/)?.[1]?.trim();
      const dataLine = block.match(/data: (.*)/)?.[1];
      if (!event || !dataLine) continue;
      try {
        const data = JSON.parse(dataLine);
        if (event === "message" && data.text) {
          botLine.textContent += data.text;
        } else if (event === "msv_update" && data.hexaco) {
          state.form.hexaco = { ...state.form.hexaco, ...data.hexaco };
          writeFormToDom();
          buildSliders();
          refreshSoul();
          logChat("MSV updated (HEXACO drift)", "sys");
        }
      } catch (_) {}
    }
    $("chat-log").scrollTop = $("chat-log").scrollHeight;
  }
}

function exportSoul() {
  if (!state.soul) return;
  const blob = new Blob([JSON.stringify(state.soul, null, 2)], { type: "application/json" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  const slug = state.soul.name.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "") || "my-bot";
  a.download = `${slug}.soul.json`;
  a.click();
}

async function exportSoulMarkdown() {
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

async function importFile(file) {
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

function cloneForm(form) {
  return JSON.parse(JSON.stringify(form));
}

function defineWizardSteps() {
  wizard.steps = [
    { id: "welcome", title: "Welcome", subtitle: "Let's build your avatar's soul file." },
    { id: "identity", title: "Identity", subtitle: "Who is this avatar?" },
    { id: "attachment", title: "Attachment", subtitle: "How they relate to others." },
    { id: "hexaco", title: "HEXACO", subtitle: "Core personality traits (0–1)." },
    { id: "moral", title: "Moral foundations", subtitle: "What they value in ethics." },
    { id: "drives", title: "Drives", subtitle: "Motivation and uncertainty." },
    { id: "mind", title: "Inner voice", subtitle: "Default internal state." },
    { id: "review", title: "Review", subtitle: "Confirm and create your soul." },
  ];
}

function renderWizardProgress() {
  const el = $("wizard-progress");
  el.innerHTML = "";
  wizard.steps.forEach((s, i) => {
    const dot = document.createElement("div");
    dot.className = "wizard-dot";
    if (i < wizard.step) dot.classList.add("done");
    if (i === wizard.step) dot.classList.add("active");
    dot.title = s.title;
    el.appendChild(dot);
  });
}

function renderWizardSliders(container, items, values, onChange, prefix) {
  container.innerHTML = "";
  items.forEach(({ key, label }) => {
    container.appendChild(sliderRow(key, label, values[key], onChange, prefix));
  });
}

function renderWizardStep() {
  const step = wizard.steps[wizard.step];
  const body = $("wizard-body");
  const f = wizard.form;

  $("wizard-title").textContent = step.title;
  $("wizard-subtitle").textContent = step.subtitle;

  body.innerHTML = "";

  if (step.id === "welcome") {
    body.innerHTML = `
      <p class="wizard-lead">Every SoulOS avatar starts with a validated <code>.soul.json</code>. This wizard walks you through each field — you can fine-tune later in the main editor.</p>
      <label class="field">
        <span>Avatar name</span>
        <input id="w-name" type="text" value="${escapeAttr(f.name)}" placeholder="e.g. Site Support" />
      </label>
    `;
    body.querySelector("#w-name").addEventListener("input", (e) => {
      wizard.form.name = e.target.value;
    });
  } else if (step.id === "identity") {
    body.innerHTML = `
      <p class="wizard-step-title">Step 2 of ${wizard.steps.length}</p>
      <p class="wizard-lead">Define their job and how they should behave.</p>
      <label class="field">
        <span>Role</span>
        <input id="w-role" type="text" value="${escapeAttr(f.role)}" placeholder="e.g. Customer Support Agent" />
      </label>
      <label class="field">
        <span>Description (system prompt)</span>
        <textarea id="w-description" rows="4" placeholder="How should they act? What boundaries matter?">${escapeHtml(f.description)}</textarea>
      </label>
    `;
    body.querySelector("#w-role").addEventListener("input", (e) => {
      wizard.form.role = e.target.value;
    });
    body.querySelector("#w-description").addEventListener("input", (e) => {
      wizard.form.description = e.target.value;
    });
  } else if (step.id === "attachment") {
    const cards = document.createElement("div");
    cards.className = "attachment-cards";
    state.meta.attachment_styles.forEach((style) => {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "attachment-card" + (f.attachment_style === style ? " selected" : "");
      btn.innerHTML = `<strong>${style}</strong><span>${ATTACHMENT_HINTS[style] || ""}</span>`;
      btn.addEventListener("click", () => {
        wizard.form.attachment_style = style;
        cards.querySelectorAll(".attachment-card").forEach((c) => c.classList.remove("selected"));
        btn.classList.add("selected");
      });
      cards.appendChild(btn);
    });
    body.innerHTML = `<p class="wizard-lead">Attachment style shapes how your avatar bonds and responds under stress.</p>`;
    body.appendChild(cards);
  } else if (step.id === "hexaco") {
    body.innerHTML = `<p class="wizard-lead">HEXACO traits define baseline personality. Higher = stronger expression.</p>`;
    const wrap = document.createElement("div");
    wrap.className = "sliders";
    for (const [key, label] of Object.entries(state.meta.hexaco_labels)) {
      wrap.appendChild(
        hexacoSliderRow(key, label, f.hexaco[key], (k, v) => {
          wizard.form.hexaco[k] = v;
        })
      );
    }
    body.appendChild(wrap);
  } else if (step.id === "moral") {
    body.innerHTML = `<p class="wizard-lead">Moral foundations guide ethical decisions in ambiguous situations.</p>`;
    const wrap = document.createElement("div");
    wrap.className = "sliders";
    renderWizardSliders(
      wrap,
      state.meta.moral_meta,
      f.moral_foundations,
      (k, v) => { wizard.form.moral_foundations[k] = v; },
      "wm"
    );
    body.appendChild(wrap);
  } else if (step.id === "drives") {
    body.innerHTML = `<p class="wizard-lead">Drives motivate behavior. Epistemic uncertainty controls how often they admit not knowing.</p>`;
    const wrap = document.createElement("div");
    wrap.className = "sliders";
    renderWizardSliders(
      wrap,
      state.meta.drive_meta,
      f.drives,
      (k, v) => { wizard.form.drives[k] = v; },
      "wd"
    );
    const uncRow = document.createElement("label");
    uncRow.className = "field";
    uncRow.innerHTML = `
      <span>Epistemic uncertainty</span>
      <input id="w-uncertainty" type="range" min="0" max="1" step="0.01" value="${f.epistemic_uncertainty}" />
      <span id="w-uncertainty-val" class="mono">${f.epistemic_uncertainty.toFixed(2)}</span>
    `;
    uncRow.querySelector("#w-uncertainty").addEventListener("input", (e) => {
      const v = parseFloat(e.target.value);
      wizard.form.epistemic_uncertainty = v;
      document.getElementById("w-uncertainty-val").textContent = v.toFixed(2);
    });
    body.appendChild(wrap);
    body.appendChild(uncRow);
  } else if (step.id === "mind") {
    body.innerHTML = `
      <p class="wizard-lead">Inner monologue is the avatar's default private thought — shown in telemetry, not always to users.</p>
      <label class="field">
        <span>Inner monologue</span>
        <input id="w-monologue" type="text" value="${escapeAttr(f.inner_monologue)}" placeholder="e.g. Ready to help with clarity and care." />
      </label>
    `;
    body.querySelector("#w-monologue").addEventListener("input", (e) => {
      wizard.form.inner_monologue = e.target.value;
    });
  } else if (step.id === "review") {
    const hexSummary = Object.entries(f.hexaco)
      .map(([k, v]) => `${state.meta.hexaco_labels[k]}: ${v.toFixed(2)}`)
      .join(", ");
    body.innerHTML = `
      <p class="wizard-lead">Your soul is ready. Click <strong>Create soul</strong> to load it into the editor.</p>
      <dl class="wizard-review">
        <dt>Name</dt><dd>${escapeHtml(f.name || "—")}</dd>
        <dt>Role</dt><dd>${escapeHtml(f.role || "—")}</dd>
        <dt>Description</dt><dd>${escapeHtml(f.description || "—")}</dd>
        <dt>Attachment</dt><dd>${escapeHtml(f.attachment_style)}</dd>
        <dt>HEXACO</dt><dd>${escapeHtml(hexSummary)}</dd>
        <dt>Inner monologue</dt><dd>${escapeHtml(f.inner_monologue || "—")}</dd>
      </dl>
    `;
  }

  renderWizardProgress();
  updateWizardNav();
}

function updateWizardNav() {
  const back = $("wizard-back");
  const next = $("wizard-next");
  const isFirst = wizard.step === 0;
  const isLast = wizard.step === wizard.steps.length - 1;

  back.classList.toggle("hidden", isFirst);
  next.textContent = isLast ? "Create soul" : "Next";
}

function escapeHtml(str) {
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function escapeAttr(str) {
  return escapeHtml(str).replace(/'/g, "&#39;");
}

function openWizard() {
  wizard.form = cloneForm(state.form);
  wizard.step = 0;
  defineWizardSteps();
  renderWizardStep();
  $("wizard-overlay").classList.add("open");
  document.body.style.overflow = "hidden";
}

function closeWizard() {
  $("wizard-overlay").classList.remove("open");
  document.body.style.overflow = "";
}

function wizardValidateStep() {
  const step = wizard.steps[wizard.step];
  if (step.id === "welcome" && !wizard.form.name.trim()) {
    alert("Please enter a name for your avatar.");
    return false;
  }
  if (step.id === "identity" && !wizard.form.description.trim()) {
    alert("Please add a short description (system prompt).");
    return false;
  }
  return true;
}

async function finishWizard() {
  state.form = cloneForm(wizard.form);
  writeFormToDom();
  buildSliders();
  await refreshSoul();
  closeWizard();
}

function wizardNext() {
  if (!wizardValidateStep()) return;
  if (wizard.step >= wizard.steps.length - 1) {
    finishWizard();
    return;
  }
  wizard.step += 1;
  renderWizardStep();
}

function wizardBack() {
  if (wizard.step <= 0) return;
  wizard.step -= 1;
  renderWizardStep();
}

let activeTab = "studio";
let docsCatalog = null;
let activeDocPath = null;

function switchView(view) {
  activeTab = view;
  document.querySelectorAll(".btn.nav").forEach((el) => {
    const match = el.dataset.view === view;
    el.classList.toggle("active", match);
    if (el.id === "nav-studio") {
      el.classList.toggle("primary", view !== "studio");
    }
  });
  document.querySelectorAll(".view").forEach((el) => {
    const id = el.id.replace("view-", "");
    el.classList.toggle("view-active", id === view);
    el.classList.toggle("hidden", id !== view);
  });

  const studioToolbar = $("studio-toolbar");
  const toolbarDivider = $("toolbar-divider");
  const onStudio = view === "studio";
  if (studioToolbar) studioToolbar.classList.toggle("hidden", !onStudio);
  if (toolbarDivider) toolbarDivider.classList.toggle("hidden", !onStudio);

  if (view === "docs" && !docsCatalog) loadDocsCatalog();
  if (view === "tutorial" && !document.getElementById("tutorial-grid").children.length) loadTutorials();
}

async function loadDocsCatalog() {
  const nav = $("docs-nav");
  nav.innerHTML = "<p class='hint'>Loading…</p>";
  try {
    const res = await fetch("/api/docs/catalog");
    docsCatalog = await res.json();
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

async function loadDoc(path) {
  activeDocPath = path;
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

async function loadTutorials() {
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
  try {
    const res = await fetch(`/api/tutorials/${encodeURIComponent(id)}`);
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "load failed");
    $("tutorial-meta").innerHTML = `
      <h2>${escapeHtml(data.title)}</h2>
      <div class="tutorial-card-meta">
        <span>${escapeHtml(data.category || "")}</span>
        <span>${escapeHtml(data.duration || "")}</span>
      </div>
    `;
    $("tutorial-content").innerHTML = data.html;
  } catch (e) {
    $("tutorial-meta").innerHTML = `<p class='hint'>${e.message}</p>`;
  }
}

function closeTutorialDetail() {
  $("tutorial-list-view").classList.remove("hidden");
  $("tutorial-detail-view").classList.add("hidden");
}

async function init() {
  initTheme();

  const goStudio = () => {
    switchView("studio");
    closeTutorialDetail();
  };
  $("btn-home").addEventListener("click", goStudio);
  $("nav-studio").addEventListener("click", goStudio);
  document.querySelectorAll(".btn.nav").forEach((btn) => {
    if (btn.id === "nav-studio") return;
    btn.addEventListener("click", () => switchView(btn.dataset.view));
  });
  $("tutorial-back").addEventListener("click", closeTutorialDetail);

  const metaRes = await fetch("/api/meta");
  state.meta = await metaRes.json();

  const defRes = await fetch("/api/defaults");
  state.form = await defRes.json();

  const sel = $("attachment_style");
  state.meta.attachment_styles.forEach((s) => {
    const o = document.createElement("option");
    o.value = s;
    o.textContent = s;
    sel.appendChild(o);
  });

  writeFormToDom();
  buildSliders();

  ["name", "role", "description", "inner_monologue"].forEach((id) => {
    $(id).addEventListener("input", () => refreshSoul());
  });
  $("attachment_style").addEventListener("change", () => refreshSoul());
  $("epistemic_uncertainty").addEventListener("input", (e) => {
    $("uncertainty-val").textContent = parseFloat(e.target.value).toFixed(2);
    refreshSoul();
  });

  $("btn-theme").addEventListener("click", toggleTheme);
  document.querySelectorAll(".view-toggle-btn").forEach((btn) => {
    btn.addEventListener("click", () => setPreviewMode(btn.dataset.preview));
  });
  $("btn-copy-json").addEventListener("click", copyJson);
  window.addEventListener("resize", onPreviewResize);
  $("btn-wizard").addEventListener("click", openWizard);
  $("wizard-cancel").addEventListener("click", closeWizard);
  $("wizard-next").addEventListener("click", wizardNext);
  $("wizard-back").addEventListener("click", wizardBack);
  $("wizard-overlay").addEventListener("click", (e) => {
    if (e.target === $("wizard-overlay")) closeWizard();
  });

  $("btn-deploy").addEventListener("click", deploy);
  $("btn-copy-mcp").addEventListener("click", copyMcpConfig);
  $("btn-export").addEventListener("click", exportSoul);
  $("btn-export-soul").addEventListener("click", async () => {
    try { await exportSoulMarkdown(); } catch (err) { alert(err.message); }
  });
  $("btn-reset").addEventListener("click", async () => {
    const res = await fetch("/api/defaults");
    state.form = await res.json();
    writeFormToDom();
    buildSliders();
    await refreshSoul();
  });
  $("btn-import").addEventListener("click", () => $("file-input").click());
  $("file-input").addEventListener("change", async (e) => {
    const f = e.target.files?.[0];
    e.target.value = "";
    if (f) try { await importFile(f); } catch (err) { alert(err.message); }
  });

  $("chat-form").addEventListener("submit", (e) => {
    e.preventDefault();
    const msg = $("chat-input").value.trim();
    if (!msg) return;
    $("chat-input").value = "";
    sendChat(msg);
  });

  switchView("studio");
  await refreshSoul();
}

init();
