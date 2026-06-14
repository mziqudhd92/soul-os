/**
 * Interactive Python bot tutorial — step rail, animations, kernel check, SSE playground.
 */

function pythonBotTutorialStorageKey() {
  return "soulos-tutorial-python-bot-step";
}

function prefersReducedMotion() {
  return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}

function mountPythonBotTutorial(container, data, ctx) {
  const steps = data.steps || [];
  let stepIndex = Number(localStorage.getItem(pythonBotTutorialStorageKey()) || 0);
  if (stepIndex >= steps.length) stepIndex = 0;

  container.className = "interactive-tutorial";
  container.innerHTML = `
    <div class="it-progress" role="tablist" aria-label="Tutorial steps"></div>
    <div class="it-body">
      <div class="it-arch" aria-hidden="true">
        <div class="it-arch-node it-arch-bot">Your bot</div>
        <div class="it-arch-line it-arch-line-1"><span class="it-pulse"></span></div>
        <div class="it-arch-node it-arch-sdk">soulos-sdk</div>
        <div class="it-arch-line it-arch-line-2"><span class="it-pulse"></span></div>
        <div class="it-arch-node it-arch-kernel">Kernel :8000</div>
        <div class="it-arch-line it-arch-line-3"><span class="it-pulse"></span></div>
        <div class="it-arch-node it-arch-db">Postgres + LLM</div>
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
  const panelEl = container.querySelector(".it-step-panel");
  const prevBtn = container.querySelector("#it-prev");
  const nextBtn = container.querySelector("#it-next");
  const countEl = container.querySelector(".it-step-count");

  steps.forEach((step, i) => {
    const tab = document.createElement("button");
    tab.type = "button";
    tab.className = "it-progress-dot";
    tab.role = "tab";
    tab.title = step.title;
    tab.setAttribute("aria-selected", i === stepIndex ? "true" : "false");
    tab.addEventListener("click", () => goTo(i));
    progressEl.appendChild(tab);
  });

  function updateProgress() {
    progressEl.querySelectorAll(".it-progress-dot").forEach((dot, i) => {
      dot.classList.toggle("done", i < stepIndex);
      dot.classList.toggle("active", i === stepIndex);
      dot.setAttribute("aria-selected", i === stepIndex ? "true" : "false");
    });
    countEl.textContent = `Step ${stepIndex + 1} of ${steps.length}`;
    prevBtn.disabled = stepIndex === 0;
    nextBtn.textContent = stepIndex === steps.length - 1 ? "Finish" : "Next";
    localStorage.setItem(pythonBotTutorialStorageKey(), String(stepIndex));
  }

  function renderStep() {
    const step = steps[stepIndex];
    panelEl.innerHTML = "";
    panelEl.classList.remove("it-animate-in");
    if (!prefersReducedMotion()) {
      requestAnimationFrame(() => panelEl.classList.add("it-animate-in"));
    }

    const head = document.createElement("header");
    head.className = "it-step-head";
    head.innerHTML = `<h3>${escapeHtml(step.title)}</h3><p>${escapeHtml(step.subtitle || "")}</p>`;
    panelEl.appendChild(head);

    if (step.kind === "intro") {
      const compare = document.createElement("div");
      compare.className = "it-compare";
      compare.innerHTML = `
        <div class="it-compare-col bad">
          <h4>Without SoulOS</h4>
          <ul>
            <li>Static system prompt</li>
            <li>Manual context stuffing</li>
            <li>Unstable tone across sessions</li>
          </ul>
        </div>
        <div class="it-compare-col good">
          <h4>With SoulOS</h4>
          <ul>
            <li>Validated HEXACO soul file</li>
            <li>pgvector episodic recall</li>
            <li>Live MSV + cognitive telemetry</li>
          </ul>
        </div>
      `;
      panelEl.appendChild(compare);
    }

    if (step.kind === "code" && step.code) {
      const wrap = document.createElement("div");
      wrap.className = "it-code-wrap";
      const pre = document.createElement("pre");
      pre.className = "it-code mono";
      const code = document.createElement("code");
      code.textContent = step.code;
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
      wrap.append(pre, copyBtn);
      panelEl.appendChild(wrap);

      if (step.action === "open_studio") {
        const btn = document.createElement("button");
        btn.type = "button";
        btn.className = "btn primary sm it-action";
        if (window.STUDIO_STATIC) {
          btn.textContent = "Run Soul Builder locally";
          btn.addEventListener("click", () => {
            window.open("http://localhost:8765", "_blank", "noopener");
          });
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
            "Kernel runs on your machine — docker compose up, then open http://localhost:8765 for health checks and live chat.";
          return;
        }
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

      if (step.action === "complete") {
        const done = document.createElement("p");
        done.className = "it-complete";
        done.textContent = "You’re ready to paste this pattern into Discord, FastAPI, or your REPL.";
        panelEl.appendChild(done);
      }
    }

    if (step.kind === "sse_playground") {
      const playground = document.createElement("div");
      playground.className = "it-sse-playground";
      playground.innerHTML = `
        <p class="hint">Simulated SSE stream (same events as <code>send_message</code>):</p>
        <div class="it-sse-log mono" aria-live="polite"></div>
        <button type="button" class="btn primary sm it-run-sse">Run demo stream</button>
      `;
      const log = playground.querySelector(".it-sse-log");
      playground.querySelector(".it-run-sse").addEventListener("click", () => {
        log.innerHTML = "";
        const events = [
          { event: "cognitive_state", data: { current_path: "system_1_heuristic", system_1: { confidence_score: 0.82, latency_ms: 42 } } },
          { event: "message", data: { text: "Refunds are available within " } },
          { event: "message", data: { text: "30 days of purchase." } },
          { event: "cognitive_state", data: { current_path: "system_2_deliberation", system_2: { loop_count: 1, reasoning_tokens: 128, latency_ms: 890 } } },
          { event: "msv_update", data: { epistemic_uncertainty: 0.12, inner_monologue: "Policy recall succeeded." } },
        ];
        let i = 0;
        const tick = () => {
          if (i >= events.length) return;
          const { event, data } = events[i];
          const line = document.createElement("div");
          line.className = `it-sse-line event-${event}`;
          line.textContent = `event: ${event}\ndata: ${JSON.stringify(data)}`;
          log.appendChild(line);
          log.scrollTop = log.scrollHeight;
          i += 1;
          if (!prefersReducedMotion()) setTimeout(tick, 700);
          else tick();
        };
        tick();
      });
      panelEl.appendChild(playground);
    }

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
    }
  });

  renderStep();
}
