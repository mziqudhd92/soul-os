/**
 * Interactive Soul Builder tutorial — Studio mock, HEXACO dials, export + wire panels.
 */

function soulBuilderStorageKey() {
  return "soulos-tutorial-soul-builder-step";
}

function mountSoulBuilderTutorial(container, data, ctx) {
  const steps = data.steps || [];
  let stepIndex = Number(localStorage.getItem(soulBuilderStorageKey()) || 0);
  if (stepIndex >= steps.length) stepIndex = 0;
  let nerdMode = localStorage.getItem("soulos-tutorial-terminal-nerd") === "1";

  container.className = "interactive-tutorial interactive-studio";
  container.innerHTML = `
    <div class="it-topbar">
      <div class="it-progress" role="tablist"></div>
      <button type="button" class="btn ghost sm it-nerd-toggle" title="Toggle nerd details">
        <span class="it-nerd-label">Nerd mode</span>
        <span class="it-nerd-pill"></span>
      </button>
    </div>
    <div class="it-progress-bar" aria-hidden="true"><span class="it-progress-fill"></span></div>
    <p class="it-nerd-fact mono hidden" id="it-sb-nerd-fact"></p>
    <div class="it-step-head sb-head"></div>
    <div class="sb-panel"></div>
    <div class="it-footer">
      <button type="button" class="btn ghost sm" id="it-prev" disabled>Back</button>
      <span class="it-step-count mono"></span>
      <button type="button" class="btn primary sm" id="it-next">Next</button>
    </div>
  `;

  const progressEl = container.querySelector(".it-progress");
  const progressFill = container.querySelector(".it-progress-fill");
  const nerdFactEl = container.querySelector("#it-sb-nerd-fact");
  const headEl = container.querySelector(".sb-head");
  const panelEl = container.querySelector(".sb-panel");
  const prevBtn = container.querySelector("#it-prev");
  const nextBtn = container.querySelector("#it-next");
  const countEl = container.querySelector(".it-step-count");
  const nerdToggle = container.querySelector(".it-nerd-toggle");

  steps.forEach((step, i) => {
    const tab = document.createElement("button");
    tab.type = "button";
    tab.className = "it-progress-pill";
    tab.role = "tab";
    tab.title = step.title;
    tab.innerHTML = `<span class="it-pill-num">${i + 1}</span><span class="it-pill-label">${escapeHtml(step.label || String(i + 1))}</span>`;
    tab.addEventListener("click", () => goTo(i));
    progressEl.appendChild(tab);
  });

  function setNerdMode(on) {
    nerdMode = on;
    localStorage.setItem("soulos-tutorial-terminal-nerd", on ? "1" : "0");
    container.classList.toggle("it-nerd-on", on);
    nerdToggle.classList.toggle("active", on);
    updateNerdFact();
  }

  nerdToggle.addEventListener("click", () => setNerdMode(!nerdMode));
  setNerdMode(nerdMode);

  function updateNerdFact() {
    const step = steps[stepIndex];
    const fact = step?.nerd_fact || data.nerd_fact_default;
    if (!fact || !nerdMode) {
      nerdFactEl.classList.add("hidden");
      return;
    }
    nerdFactEl.classList.remove("hidden");
    nerdFactEl.textContent = `// ${fact}`;
  }

  function updateProgress() {
    progressEl.querySelectorAll(".it-progress-pill").forEach((pill, i) => {
      pill.classList.toggle("done", i < stepIndex);
      pill.classList.toggle("active", i === stepIndex);
    });
    const pct = steps.length <= 1 ? 100 : (stepIndex / (steps.length - 1)) * 100;
    progressFill.style.width = `${pct}%`;
    countEl.textContent = `Step ${stepIndex + 1} of ${steps.length}`;
    prevBtn.disabled = stepIndex === 0;
    nextBtn.textContent = stepIndex === steps.length - 1 ? "Finish" : "Next";
    localStorage.setItem(soulBuilderStorageKey(), String(stepIndex));
    updateNerdFact();
  }

  function addCopyButton(parent, text) {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "btn ghost sm it-copy";
    btn.textContent = "Copy";
    btn.addEventListener("click", async () => {
      try {
        await navigator.clipboard.writeText(text);
        btn.textContent = "Copied!";
        setTimeout(() => { btn.textContent = "Copy"; }, 1500);
      } catch (_) {
        btn.textContent = "Failed";
      }
    });
    parent.appendChild(btn);
  }

  function renderPaths(step) {
    const grid = document.createElement("div");
    grid.className = "sb-path-grid";
    grid.innerHTML = `
      <button type="button" class="sb-path-card vibe" data-path="vibe">
        <span class="sb-path-emoji">⚡</span>
        <h4>Vibe coder</h4>
        <p>Wizard → tweak 2 sliders → Export .soul → paste into Cursor / bot. ~8 min.</p>
        <ul><li>No JSON hand-editing</li><li>Ship personality before prompts</li><li>MCP optional</li></ul>
      </button>
      <button type="button" class="sb-path-card dev" data-path="dev">
        <span class="sb-path-emoji">🛠</span>
        <h4>Developer</h4>
        <p>Validate schema → deploy to kernel → curl register → SDK in CI. ~15 min.</p>
        <ul><li>spec/soul.schema.json</li><li>Deploy + cognitive_state SSE</li><li>.soul-memory/ sync</li></ul>
      </button>
    `;
    grid.querySelectorAll(".sb-path-card").forEach((card) => {
      card.addEventListener("click", () => {
        grid.querySelectorAll(".sb-path-card").forEach((c) => c.classList.remove("active"));
        card.classList.add("active");
      });
    });
    panelEl.appendChild(grid);
  }

  function renderChecklist(step) {
    const list = document.createElement("div");
    list.className = "sb-checklist";
    step.items.forEach((item) => {
      const row = document.createElement("div");
      row.className = "sb-check-item";
      row.innerHTML = `<h4>${escapeHtml(item.title)}</h4>`;
      if (item.note) row.innerHTML += `<p class="hint">${escapeHtml(item.note)}</p>`;
      const wrap = document.createElement("div");
      wrap.className = "it-code-wrap";
      const pre = document.createElement("pre");
      pre.className = "it-code mono";
      pre.textContent = item.cmd;
      wrap.appendChild(pre);
      addCopyButton(wrap, item.cmd);
      row.appendChild(wrap);
      list.appendChild(row);
    });
    panelEl.appendChild(list);
  }

  function renderStudioForm(step) {
    const d = step.defaults || {};
    const wrap = document.createElement("div");
    wrap.className = "sb-mock-studio";
    wrap.innerHTML = `
      <div class="sb-mock-form">
        <label><span>Name</span><input type="text" id="sb-name" value="${escapeHtml(d.name || "")}" /></label>
        <label><span>Role</span><input type="text" id="sb-role" value="${escapeHtml(d.role || "")}" /></label>
        <label><span>Description</span><textarea id="sb-desc" rows="3">${escapeHtml(d.description || "")}</textarea></label>
      </div>
      <div class="sb-mock-preview">
        <p class="sb-preview-label mono">Live preview (.soul front matter)</p>
        <pre class="it-code mono" id="sb-preview"></pre>
      </div>
    `;
    const preview = wrap.querySelector("#sb-preview");
    const sync = () => {
      const name = wrap.querySelector("#sb-name").value;
      const role = wrap.querySelector("#sb-role").value;
      const desc = wrap.querySelector("#sb-desc").value;
      preview.textContent = `---\nname: ${name}\nrole: ${role}\nattachment_style: Secure\n---\n\n${desc}`;
    };
    wrap.querySelectorAll("input, textarea").forEach((el) => el.addEventListener("input", sync));
    sync();
    panelEl.appendChild(wrap);
  }

  function renderHexacoDials(step) {
    const wrap = document.createElement("div");
    wrap.className = "sb-hexaco";
    step.traits.forEach((t) => {
      const row = document.createElement("div");
      row.className = "sb-hex-row";
      row.innerHTML = `
        <div class="sb-hex-label"><span>${escapeHtml(t.label)}</span><span class="mono sb-hex-val">${t.value.toFixed(2)}</span></div>
        <input type="range" min="0" max="1" step="0.01" value="${t.value}" data-key="${t.key}" />
        <div class="sb-hex-bar"><span style="width:${t.value * 100}%"></span></div>
        <p class="sb-hex-hint hint">${escapeHtml(t.hint)}</p>
      `;
      const input = row.querySelector("input");
      const bar = row.querySelector(".sb-hex-bar span");
      const val = row.querySelector(".sb-hex-val");
      input.addEventListener("input", () => {
        const v = parseFloat(input.value);
        val.textContent = v.toFixed(2);
        bar.style.width = `${v * 100}%`;
      });
      wrap.appendChild(row);
    });
    panelEl.appendChild(wrap);
  }

  function renderExportPanel(step) {
    const wrap = document.createElement("div");
    wrap.className = "sb-export";
    const tabs = document.createElement("div");
    tabs.className = "sb-export-tabs";
    tabs.innerHTML = `
      <button type="button" class="active" data-tab="soul">.soul</button>
      <button type="button" data-tab="json">.soul.json</button>
    `;
    const body = document.createElement("div");
    body.className = "sb-export-body";
    const pre = document.createElement("pre");
    pre.className = "it-code mono";
    pre.textContent = step.soul;
    body.appendChild(pre);
    addCopyButton(body, step.soul);
    tabs.querySelectorAll("button").forEach((btn) => {
      btn.addEventListener("click", () => {
        tabs.querySelectorAll("button").forEach((b) => b.classList.remove("active"));
        btn.classList.add("active");
        const isSoul = btn.dataset.tab === "soul";
        pre.textContent = isSoul ? step.soul : step.json;
        body.querySelector(".it-copy").onclick = async () => {
          await navigator.clipboard.writeText(pre.textContent);
        };
      });
    });
    wrap.append(tabs, body);
    const tip = document.createElement("p");
    tip.className = "hint sb-export-tip";
    tip.textContent = "Vibe tip: commit .soul to repo — Studio Import reloads it in one click.";
    wrap.appendChild(tip);
    panelEl.appendChild(wrap);
  }

  function renderChatDemo() {
    const wrap = document.createElement("div");
    wrap.className = "sb-chat-demo";
    wrap.innerHTML = `
      <div class="it-chat-bubble user">How do I register an avatar?</div>
      <div class="it-cognitive-rail">
        <div class="it-path it-path-s1 active"><span class="it-path-label">System 1</span><span class="it-path-meta mono">38ms</span></div>
        <div class="it-path it-path-s2"><span class="it-path-label">System 2</span><span class="it-path-meta mono">idle</span></div>
      </div>
      <div class="it-chat-bubble bot" id="sb-bot-reply"></div>
      <button type="button" class="btn primary sm" id="sb-run-chat">▶ Simulate deploy chat</button>
    `;
    const reply = wrap.querySelector("#sb-bot-reply");
    wrap.querySelector("#sb-run-chat").addEventListener("click", () => {
      reply.textContent = "";
      const chunks = ["POST /v1/avatars ", "accepts .soul bodies. ", "Returns id for send_message."];
      let i = 0;
      const tick = () => {
        if (i >= chunks.length) return;
        reply.textContent += chunks[i];
        i += 1;
        setTimeout(tick, prefersReducedMotion() ? 0 : 400);
      };
      tick();
      wrap.querySelector(".it-path-s2").classList.add("active");
    });
    panelEl.appendChild(wrap);
  }

  function renderWirePanel(step) {
    const wrap = document.createElement("div");
    wrap.className = "sb-wire";
    [
      { title: "curl register", code: step.curl },
      { title: "Python SDK", code: step.python },
      { title: "Cursor MCP", code: step.mcp },
    ].forEach((block) => {
      const sec = document.createElement("div");
      sec.className = "sb-wire-block";
      sec.innerHTML = `<h4>${escapeHtml(block.title)}</h4>`;
      const cw = document.createElement("div");
      cw.className = "it-code-wrap";
      const pre = document.createElement("pre");
      pre.className = "it-code mono";
      pre.textContent = block.code;
      cw.appendChild(pre);
      addCopyButton(cw, block.code);
      sec.appendChild(cw);
      wrap.appendChild(sec);
    });
    if (window.STUDIO_STATIC) {
      const link = document.createElement("a");
      link.className = "btn ghost sm";
      link.href = "http://localhost:8765";
      link.target = "_blank";
      link.rel = "noopener";
      link.textContent = "Open full Soul Studio";
      wrap.appendChild(link);
    } else if (ctx.switchView) {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "btn primary sm";
      btn.textContent = "Open Soul Builder";
      btn.addEventListener("click", () => {
        ctx.switchView("studio");
        if (ctx.closeTutorialDetail) ctx.closeTutorialDetail();
      });
      wrap.appendChild(btn);
    }
    panelEl.appendChild(wrap);
  }

  function renderStep() {
    const step = steps[stepIndex];
    headEl.innerHTML = `<h3>${escapeHtml(step.title)}</h3><p>${escapeHtml(step.subtitle || "")}</p>`;
    panelEl.innerHTML = "";
    panelEl.classList.remove("it-animate-in");
    if (!prefersReducedMotion()) requestAnimationFrame(() => panelEl.classList.add("it-animate-in"));

    if (step.kind === "paths") renderPaths(step);
    if (step.kind === "checklist") renderChecklist(step);
    if (step.kind === "studio_form") renderStudioForm(step);
    if (step.kind === "hexaco_dials") renderHexacoDials(step);
    if (step.kind === "export_panel") renderExportPanel(step);
    if (step.kind === "chat_demo") renderChatDemo();
    if (step.kind === "wire_panel") renderWirePanel(step);

    updateProgress();
  }

  function goTo(index) {
    stepIndex = index;
    renderStep();
  }

  prevBtn.addEventListener("click", () => { if (stepIndex > 0) goTo(stepIndex - 1); });
  nextBtn.addEventListener("click", () => {
    if (stepIndex < steps.length - 1) goTo(stepIndex + 1);
    else {
      localStorage.setItem(soulBuilderStorageKey(), String(steps.length));
      nextBtn.textContent = "Done ✓";
      container.classList.add("it-tutorial-done");
    }
  });

  renderStep();
}
