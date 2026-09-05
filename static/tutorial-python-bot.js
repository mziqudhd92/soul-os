/**
 * Interactive Python bot tutorial — animations, arch flow, dual SSE playground, nerd mode.
 */

function pythonBotTutorialStorageKey() {
  return "soulos-tutorial-python-bot-step";
}

function pythonBotNerdModeKey() {
  return "soulos-tutorial-python-bot-nerd";
}

function escapeHtml(str) {
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function prefersReducedMotion() {
  return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}

const ARCH_META = {
  bot: { label: "Your bot", icon: "🤖", tip: "Discord · Telegram · FastAPI · REPL" },
  sdk: { label: "soulos-sdk", icon: "⚡", tip: "Python client · async SSE iterator" },
  kernel: { label: "Kernel :8000", icon: "🧠", tip: "FastAPI · dual-process · MSV pipeline" },
  db: { label: "Postgres + LLM", icon: "🗄", tip: "pgvector recall · Ollama/OpenAI" },
};

const DEFAULT_ARCH_FOCUS = ["bot", "sdk", "kernel", "db"];

function mountPythonBotTutorial(container, data, ctx) {
  const steps = data.steps || [];
  let stepIndex = Number(localStorage.getItem(pythonBotTutorialStorageKey()) || 0);
  if (stepIndex >= steps.length) stepIndex = 0;
  let nerdMode = localStorage.getItem(pythonBotNerdModeKey()) === "1";

  container.className = "interactive-tutorial";
  container.innerHTML = `
    <div class="it-topbar">
      <div class="it-progress" role="tablist" aria-label="Tutorial steps"></div>
      <button type="button" class="btn ghost sm it-nerd-toggle" title="Toggle nerd details">
        <span class="it-nerd-label">Nerd mode</span>
        <span class="it-nerd-pill"></span>
      </button>
    </div>
    <div class="it-progress-bar" aria-hidden="true"><span class="it-progress-fill"></span></div>
    <div class="it-body">
      <div class="it-arch-wrap">
        <div class="it-arch" aria-hidden="true"></div>
        <p class="it-nerd-fact mono hidden" id="it-nerd-fact"></p>
      </div>
      <div class="it-step-panel"></div>
    </div>
    <div class="it-footer">
      <button type="button" class="btn ghost sm" id="it-prev" disabled>Back</button>
      <span class="it-step-count mono"></span>
      <button type="button" class="btn primary sm" id="it-next">Next</button>
    </div>
  `;

  const progressEl = container.querySelector(".it-progress");
  const progressFill = container.querySelector(".it-progress-fill");
  const archEl = container.querySelector(".it-arch");
  const nerdFactEl = container.querySelector("#it-nerd-fact");
  const nerdToggle = container.querySelector(".it-nerd-toggle");
  const panelEl = container.querySelector(".it-step-panel");
  const prevBtn = container.querySelector("#it-prev");
  const nextBtn = container.querySelector("#it-next");
  const countEl = container.querySelector(".it-step-count");

  buildArchDiagram(archEl);

  steps.forEach((step, i) => {
    const tab = document.createElement("button");
    tab.type = "button";
    tab.className = "it-progress-pill";
    tab.role = "tab";
    tab.title = step.title;
    tab.innerHTML = `<span class="it-pill-num">${i + 1}</span><span class="it-pill-label">${escapeHtml(step.label || step.title.split(" ")[0])}</span>`;
    tab.setAttribute("aria-selected", i === stepIndex ? "true" : "false");
    tab.addEventListener("click", () => goTo(i));
    progressEl.appendChild(tab);
  });

  function setNerdMode(on) {
    nerdMode = on;
    localStorage.setItem(pythonBotNerdModeKey(), on ? "1" : "0");
    container.classList.toggle("it-nerd-on", on);
    nerdToggle.classList.toggle("active", on);
    updateNerdFact();
  }

  nerdToggle.addEventListener("click", () => setNerdMode(!nerdMode));
  setNerdMode(nerdMode);

  function buildArchDiagram(root) {
    const order = ["bot", "sdk", "kernel", "db"];
    order.forEach((key, i) => {
      const meta = ARCH_META[key];
      const node = document.createElement("button");
      node.type = "button";
      node.className = `it-arch-node it-arch-${key}`;
      node.dataset.node = key;
      node.innerHTML = `
        <span class="it-arch-icon">${meta.icon}</span>
        <span class="it-arch-label">${escapeHtml(meta.label)}</span>
        <span class="it-arch-tip mono">${escapeHtml(meta.tip)}</span>
      `;
      node.addEventListener("click", () => {
        node.classList.add("it-arch-ping");
        setTimeout(() => node.classList.remove("it-arch-ping"), 600);
      });
      root.appendChild(node);
      if (i < order.length - 1) {
        const line = document.createElement("div");
        line.className = `it-arch-line it-arch-line-${i + 1}`;
        line.dataset.from = key;
        line.dataset.to = order[i + 1];
        line.innerHTML = `<span class="it-packet-track"><span class="it-packet"></span><span class="it-packet it-packet-2"></span></span>`;
        root.appendChild(line);
      }
    });
  }

  function updateArchFocus(step) {
    const focus = step.arch_focus || DEFAULT_ARCH_FOCUS;
    archEl.querySelectorAll(".it-arch-node").forEach((n) => {
      const active = focus.includes(n.dataset.node);
      n.classList.toggle("active", active);
      n.classList.toggle("dim", !active && focus.length < 4);
    });
    archEl.querySelectorAll(".it-arch-line").forEach((line) => {
      const from = line.dataset.from;
      const to = line.dataset.to;
      const flowing = focus.includes(from) && focus.includes(to);
      line.classList.toggle("flowing", flowing);
    });
  }

  function updateNerdFact() {
    const step = steps[stepIndex];
    if (!step?.nerd_fact || !nerdMode) {
      nerdFactEl.classList.add("hidden");
      nerdFactEl.textContent = "";
      return;
    }
    nerdFactEl.classList.remove("hidden");
    nerdFactEl.textContent = `// ${step.nerd_fact}`;
  }

  function updateProgress() {
    progressEl.querySelectorAll(".it-progress-pill").forEach((pill, i) => {
      pill.classList.toggle("done", i < stepIndex);
      pill.classList.toggle("active", i === stepIndex);
      pill.setAttribute("aria-selected", i === stepIndex ? "true" : "false");
    });
    const pct = steps.length <= 1 ? 100 : (stepIndex / (steps.length - 1)) * 100;
    progressFill.style.width = `${pct}%`;
    countEl.textContent = `Step ${stepIndex + 1} of ${steps.length}`;
    prevBtn.disabled = stepIndex === 0;
    nextBtn.textContent = stepIndex === steps.length - 1 ? "Finish" : "Next";
    nextBtn.classList.toggle("it-finish-ready", stepIndex === steps.length - 1);
    localStorage.setItem(pythonBotTutorialStorageKey(), String(stepIndex));
    updateArchFocus(steps[stepIndex]);
    updateNerdFact();
  }

  function animatePanelIn() {
    panelEl.classList.remove("it-animate-in");
    if (!prefersReducedMotion()) {
      requestAnimationFrame(() => panelEl.classList.add("it-animate-in"));
    }
  }

  function renderIntro(step) {
    const wrap = document.createElement("div");
    wrap.className = "it-intro";
    wrap.innerHTML = `
      <div class="it-morph-wrap">
        <input type="range" class="it-morph-slider" min="0" max="100" value="55" aria-label="Compare without vs with SoulOS" />
        <div class="it-morph-labels">
          <span>Without SoulOS</span>
          <span>With SoulOS</span>
        </div>
        <div class="it-morph-stage">
          <div class="it-morph-col bad">
            <h4>Fragile stack</h4>
            <ul class="it-stagger-list">
              <li>Static system prompt</li>
              <li>Manual context stuffing</li>
              <li>Unstable tone across sessions</li>
              <li>No telemetry</li>
            </ul>
          </div>
          <div class="it-morph-col good">
            <h4>SoulOS stack</h4>
            <ul class="it-stagger-list">
              <li>Validated HEXACO soul file</li>
              <li>pgvector episodic recall</li>
              <li>Live MSV + cognitive telemetry</li>
              <li>Dual-process routing</li>
            </ul>
          </div>
          <div class="it-morph-shimmer" aria-hidden="true"></div>
        </div>
      </div>
      <div class="it-stat-row">
        <div class="it-stat"><span class="it-stat-val" data-target="47">0</span><span class="it-stat-label">% prompt drift (typical)</span></div>
        <div class="it-stat"><span class="it-stat-val" data-target="0.12">0</span><span class="it-stat-label">ε after recall</span></div>
        <div class="it-stat"><span class="it-stat-val" data-target="42">0</span><span class="it-stat-label">ms System-1 path</span></div>
      </div>
    `;
    const slider = wrap.querySelector(".it-morph-slider");
    const stage = wrap.querySelector(".it-morph-stage");
    stage.style.setProperty("--morph", slider.value);
    slider.addEventListener("input", () => {
      stage.style.setProperty("--morph", slider.value);
    });
    panelEl.appendChild(wrap);
    if (!prefersReducedMotion()) {
      wrap.querySelectorAll(".it-stat-val").forEach((el) => {
        const target = parseFloat(el.dataset.target);
        const isFloat = String(target).includes(".");
        const duration = 900;
        const start = performance.now();
        const tick = (now) => {
          const t = Math.min(1, (now - start) / duration);
          const eased = 1 - (1 - t) ** 3;
          const val = target * eased;
          el.textContent = isFloat ? val.toFixed(2) : Math.round(val);
          if (t < 1) requestAnimationFrame(tick);
        };
        requestAnimationFrame(tick);
      });
    } else {
      wrap.querySelectorAll(".it-stat-val").forEach((el) => {
        el.textContent = el.dataset.target;
      });
    }
  }

  function renderCodeBlock(step) {
    const wrap = document.createElement("div");
    wrap.className = "it-code-wrap";
    const pre = document.createElement("pre");
    pre.className = "it-code mono";
    const code = document.createElement("code");
    pre.appendChild(code);
    const copyBtn = document.createElement("button");
    copyBtn.type = "button";
    copyBtn.className = "btn ghost sm it-copy";
    copyBtn.textContent = "Copy";
    copyBtn.addEventListener("click", async () => {
      try {
        await navigator.clipboard.writeText(step.code);
        copyBtn.textContent = "Copied!";
        setTimeout(() => { copyBtn.textContent = "Copy"; }, 1500);
      } catch (_) {
        copyBtn.textContent = "Copy failed";
      }
    });
    const actions = document.createElement("div");
    actions.className = "it-code-actions";
    const typeBtn = document.createElement("button");
    typeBtn.type = "button";
    typeBtn.className = "btn ghost sm";
    typeBtn.textContent = prefersReducedMotion() ? "Show code" : "Type it out";
    wrap.append(pre, copyBtn, actions);
    actions.append(typeBtn);
    panelEl.appendChild(wrap);

    function showCodeInstant() {
      code.textContent = step.code;
      code.classList.add("it-code-revealed");
    }

    if (prefersReducedMotion()) {
      showCodeInstant();
      typeBtn.addEventListener("click", showCodeInstant);
    } else {
      typeBtn.addEventListener("click", () => {
        code.textContent = "";
        code.classList.remove("it-code-revealed");
        const lines = step.code.split("\n");
        let li = 0;
        const typeLine = () => {
          if (li >= lines.length) {
            code.classList.add("it-code-revealed");
            return;
          }
          const line = document.createElement("span");
          line.className = "it-code-line";
          line.textContent = lines[li] + (li < lines.length - 1 ? "\n" : "");
          code.appendChild(line);
          requestAnimationFrame(() => line.classList.add("visible"));
          li += 1;
          setTimeout(typeLine, 28);
        };
        typeLine();
      });
      setTimeout(() => typeBtn.click(), 120);
    }

    if (step.action === "open_studio") {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "btn primary sm it-action";
      if (window.STUDIO_STATIC) {
        btn.textContent = "Run Soul Builder locally";
        btn.addEventListener("click", () => window.open("http://localhost:8765", "_blank", "noopener"));
      } else {
        btn.textContent = "Open Soul Builder";
        btn.addEventListener("click", () => {
          if (ctx.switchView) ctx.switchView("studio");
          if (ctx.closeTutorialDetail) ctx.closeTutorialDetail();
        });
      }
      panelEl.appendChild(btn);
    }

    if (step.action === "check_kernel") {
      const status = document.createElement("p");
      status.className = "it-status mono hint";
      panelEl.appendChild(status);
      if (window.STUDIO_STATIC) {
        status.textContent =
          "Kernel runs on your machine — docker compose up, then open http://localhost:8765 for health checks.";
      } else {
        status.textContent = "Checking kernel…";
        fetch("/api/kernel-health")
          .then((r) => r.json())
          .then((j) => {
            if (j.ok) {
              status.textContent = `✓ Kernel healthy at ${j.url}`;
              status.classList.add("ok");
            } else {
              status.textContent = `✗ ${j.detail || "Kernel unreachable"} — run docker compose up`;
              status.classList.add("err");
            }
          })
          .catch(() => {
            status.textContent = "✗ Could not reach kernel health endpoint";
            status.classList.add("err");
          });
      }
    }

    if (step.action === "complete") {
      const done = document.createElement("div");
      done.className = "it-complete-burst";
      done.innerHTML = `
        <div class="it-confetti" aria-hidden="true"></div>
        <p class="it-complete">Ship it — paste into Discord, FastAPI, or your REPL.</p>
        <div class="it-complete-badges">
          <span class="it-badge">avatar_id persisted</span>
          <span class="it-badge">SSE wired</span>
          <span class="it-badge">MSV live</span>
        </div>
      `;
      panelEl.appendChild(done);
      if (!prefersReducedMotion()) {
        done.querySelector(".it-confetti").innerHTML = Array.from({ length: 24 }, (_, i) =>
          `<span class="it-confetti-bit" style="--i:${i}"></span>`
        ).join("");
      }
    }
  }

  function renderMemoryPlayground(step) {
    const pg = document.createElement("div");
    pg.className = "it-memory-playground";
    pg.innerHTML = `
      <div class="it-memory-viz">
        <div class="it-memory-input">
          <input type="text" class="it-memory-field" placeholder="Type a fact to ingest…" value="Refunds within 30 days." />
          <button type="button" class="btn primary sm it-memory-send">Ingest</button>
        </div>
        <div class="it-vector-grid" aria-hidden="true">
          ${Array.from({ length: 16 }, (_, i) => `<span class="it-vector-cell" style="--d:${i * 0.05}s"></span>`).join("")}
        </div>
        <p class="it-memory-status mono hint">pgvector · cosine similarity recall</p>
      </div>
    `;
    const field = pg.querySelector(".it-memory-field");
    const grid = pg.querySelector(".it-vector-grid");
    const status = pg.querySelector(".it-memory-status");
    pg.querySelector(".it-memory-send").addEventListener("click", () => {
      const text = field.value.trim() || "Refunds within 30 days.";
      status.textContent = "embedding…";
      grid.classList.add("it-vector-pulse");
      setTimeout(() => {
        status.textContent = `recalled: "${text}" · similarity 0.94`;
        status.classList.add("ok");
      }, prefersReducedMotion() ? 0 : 650);
      setTimeout(() => grid.classList.remove("it-vector-pulse"), 1200);
    });
    panelEl.appendChild(pg);

    if (step.code) {
      const mini = document.createElement("div");
      mini.className = "it-code-wrap it-code-mini";
      mini.innerHTML = `<pre class="it-code mono"><code>${escapeHtml(step.code)}</code></pre>`;
      const copy = document.createElement("button");
      copy.type = "button";
      copy.className = "btn ghost sm it-copy";
      copy.textContent = "Copy";
      copy.addEventListener("click", () => navigator.clipboard.writeText(step.code));
      mini.append(copy);
      panelEl.appendChild(mini);
    }
  }

  function renderSsePlayground() {
    const pg = document.createElement("div");
    pg.className = "it-sse-playground";
    pg.innerHTML = `
      <div class="it-sse-controls">
        <button type="button" class="btn primary sm it-run-sse">▶ Run demo stream</button>
        <label class="it-speed-label mono">
          Speed
          <select class="it-speed-select">
            <option value="1">1×</option>
            <option value="0.5">0.5×</option>
            <option value="2">2× nerd</option>
          </select>
        </label>
      </div>
      <div class="it-sse-dual">
        <div class="it-sse-human">
          <p class="it-sse-panel-title">Human view</p>
          <div class="it-chat-bubble user">Can I get a refund?</div>
          <div class="it-cognitive-rail">
            <div class="it-path it-path-s1 active" data-path="s1">
              <span class="it-path-label">System 1</span>
              <span class="it-path-meta mono">42ms · conf 0.82</span>
            </div>
            <div class="it-path it-path-s2" data-path="s2">
              <span class="it-path-label">System 2</span>
              <span class="it-path-meta mono">890ms · 128 tokens</span>
            </div>
          </div>
          <div class="it-chat-bubble bot it-bot-stream"></div>
          <div class="it-msv-gauge">
            <span class="mono">ε uncertainty</span>
            <div class="it-msv-track"><div class="it-msv-fill" style="width:15%"></div></div>
            <span class="it-msv-val mono">0.15</span>
          </div>
          <p class="it-inner-mono mono hint it-inner-text">inner_monologue: …</p>
        </div>
        <div class="it-sse-nerd">
          <p class="it-sse-panel-title mono">Wire log</p>
          <div class="it-sse-log mono" aria-live="polite"></div>
        </div>
      </div>
    `;

    const events = [
      { event: "cognitive_state", data: { current_path: "system_1_heuristic", system_1: { confidence_score: 0.82, latency_ms: 42 } }, delay: 1 },
      { event: "message", data: { text: "Refunds are available within " }, delay: 1 },
      { event: "message", data: { text: "30 days of purchase." }, delay: 1 },
      { event: "cognitive_state", data: { current_path: "system_2_deliberation", system_2: { loop_count: 1, reasoning_tokens: 128, latency_ms: 890 } }, delay: 1.2 },
      { event: "msv_update", data: { epistemic_uncertainty: 0.12, inner_monologue: "Policy recall succeeded." }, delay: 1 },
    ];

    const log = pg.querySelector(".it-sse-log");
    const botStream = pg.querySelector(".it-bot-stream");
    const pathS1 = pg.querySelector(".it-path-s1");
    const pathS2 = pg.querySelector(".it-path-s2");
    const msvFill = pg.querySelector(".it-msv-fill");
    const msvVal = pg.querySelector(".it-msv-val");
    const innerText = pg.querySelector(".it-inner-text");
    const runBtn = pg.querySelector(".it-run-sse");
    const speedSelect = pg.querySelector(".it-speed-select");

    pg.querySelector(".it-run-sse").addEventListener("click", () => {
      if (runBtn.disabled) return;
      runBtn.disabled = true;
      runBtn.textContent = "Streaming…";
      log.innerHTML = "";
      botStream.textContent = "";
      pathS1.classList.add("active");
      pathS2.classList.remove("active");
      msvFill.style.width = "15%";
      msvVal.textContent = "0.15";
      innerText.textContent = "inner_monologue: …";

      const speed = parseFloat(speedSelect.value) || 1;
      const baseMs = prefersReducedMotion() ? 0 : 700 / speed;
      let i = 0;

      const tick = () => {
        if (i >= events.length) {
          runBtn.disabled = false;
          runBtn.textContent = "▶ Run again";
          return;
        }
        const { event, data } = events[i];
        const line = document.createElement("div");
        line.className = `it-sse-line event-${event} it-sse-line-in`;
        const ts = (performance.now() % 10000).toFixed(1);
        line.innerHTML = `<span class="it-sse-ts">+${ts}ms</span> event: ${event}<br>data: ${escapeHtml(JSON.stringify(data))}`;
        log.appendChild(line);
        log.scrollTop = log.scrollHeight;

        if (event === "message") {
          botStream.textContent += data.text;
          botStream.classList.add("it-typing");
        }
        if (event === "cognitive_state" && data.current_path?.includes("system_2")) {
          pathS1.classList.remove("active");
          pathS2.classList.add("active");
        }
        if (event === "msv_update") {
          const eps = data.epistemic_uncertainty;
          msvFill.style.width = `${eps * 100}%`;
          msvVal.textContent = eps.toFixed(2);
          innerText.textContent = `inner_monologue: ${data.inner_monologue}`;
        }

        i += 1;
        setTimeout(tick, baseMs);
      };
      tick();
    });

    panelEl.appendChild(pg);
  }

  function renderStep() {
    const step = steps[stepIndex];
    panelEl.innerHTML = "";
    animatePanelIn();

    const head = document.createElement("header");
    head.className = "it-step-head";
    head.innerHTML = `<h3>${escapeHtml(step.title)}</h3><p>${escapeHtml(step.subtitle || "")}</p>`;
    panelEl.appendChild(head);

    if (step.kind === "intro") renderIntro(step);
    if (step.kind === "code" && step.code) renderCodeBlock(step);
    if (step.kind === "memory_playground") renderMemoryPlayground(step);
    if (step.kind === "sse_playground") renderSsePlayground();

    updateProgress();
  }

  function goTo(index) {
    stepIndex = index;
    renderStep();
  }

  prevBtn.addEventListener("click", () => {
    if (stepIndex > 0) goTo(stepIndex - 1);
  });
  nextBtn.addEventListener("click", () => {
    if (stepIndex < steps.length - 1) goTo(stepIndex + 1);
    else {
      localStorage.setItem(pythonBotTutorialStorageKey(), String(steps.length));
      nextBtn.textContent = "Done ✓";
      container.classList.add("it-tutorial-done");
    }
  });

  renderStep();
}
