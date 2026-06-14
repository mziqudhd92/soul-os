/**
 * Terminal-style interactive tutorials (quickstart curl walkthrough).
 */

function terminalTutorialStorageKey(tutorialId) {
  return `soulos-tutorial-${tutorialId}-step`;
}

function mountTerminalTutorial(container, data, ctx) {
  const tutorialId = data.tutorial_id || "quickstart";
  const steps = data.steps || [];
  let stepIndex = Number(localStorage.getItem(terminalTutorialStorageKey(tutorialId)) || 0);
  if (stepIndex >= steps.length) stepIndex = 0;

  container.className = "interactive-tutorial interactive-terminal";
  container.innerHTML = `
    <div class="it-topbar">
      <div class="it-progress" role="tablist"></div>
      <button type="button" class="btn ghost sm it-nerd-toggle" title="Toggle nerd details">
        <span class="it-nerd-label">Nerd mode</span>
        <span class="it-nerd-pill"></span>
      </button>
    </div>
    <div class="it-progress-bar" aria-hidden="true"><span class="it-progress-fill"></span></div>
    <p class="it-nerd-fact mono hidden" id="it-term-nerd-fact"></p>
    <div class="it-step-head it-term-head"></div>
    <div class="term-wrap">
      <div class="term-toolbar">
        <span class="term-dots" aria-hidden="true"><span></span><span></span><span></span></span>
        <span class="term-title mono">soulos — zsh — 80×24</span>
        <span class="term-sim-badge mono">simulated</span>
      </div>
      <div class="term-screen mono" aria-live="polite"></div>
      <div class="term-actions">
        <button type="button" class="btn primary sm" id="term-run">▶ Run step</button>
        <button type="button" class="btn ghost sm" id="term-copy">Copy commands</button>
      </div>
    </div>
    <div class="it-footer">
      <button type="button" class="btn ghost sm" id="it-prev" disabled>Back</button>
      <span class="it-step-count mono"></span>
      <button type="button" class="btn primary sm" id="it-next">Next</button>
    </div>
  `;

  const progressEl = container.querySelector(".it-progress");
  const progressFill = container.querySelector(".it-progress-fill");
  const nerdFactEl = container.querySelector("#it-term-nerd-fact");
  const headEl = container.querySelector(".it-term-head");
  const screenEl = container.querySelector(".term-screen");
  const runBtn = container.querySelector("#term-run");
  const copyBtn = container.querySelector("#term-copy");
  const prevBtn = container.querySelector("#it-prev");
  const nextBtn = container.querySelector("#it-next");
  const countEl = container.querySelector(".it-step-count");
  const nerdToggle = container.querySelector(".it-nerd-toggle");

  let nerdMode = localStorage.getItem("soulos-tutorial-terminal-nerd") === "1";
  let running = false;

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
    localStorage.setItem(terminalTutorialStorageKey(tutorialId), String(stepIndex));
    updateNerdFact();
  }

  function sleep(ms) {
    return new Promise((r) => setTimeout(r, ms));
  }

  function appendLine(className, text) {
    const line = document.createElement("div");
    line.className = `term-line ${className}`;
    line.textContent = text;
    screenEl.appendChild(line);
    screenEl.scrollTop = screenEl.scrollHeight;
    return line;
  }

  async function typeCommand(cmd) {
    const row = document.createElement("div");
    row.className = "term-line term-cmd-row";
    const prompt = document.createElement("span");
    prompt.className = "term-prompt";
    prompt.textContent = "$ ";
    const typed = document.createElement("span");
    typed.className = "term-cmd";
    row.append(prompt, typed);
    screenEl.appendChild(row);
    screenEl.scrollTop = screenEl.scrollHeight;

    const flat = cmd.replace(/\\n/g, "\n");
    if (prefersReducedMotion()) {
      typed.textContent = flat;
      return;
    }
    for (let i = 0; i < flat.length; i += 1) {
      typed.textContent += flat[i];
      await sleep(12 + Math.random() * 18);
    }
  }

  async function runScript(script, instant) {
    for (const block of script) {
      if (block.type === "comment") {
        appendLine("term-comment", block.text);
        if (!instant) await sleep(120);
        continue;
      }
      if (block.type === "run") {
        if (instant) {
          appendLine("term-cmd-row", `$ ${block.cmd.replace(/\\n/g, " ")}`);
        } else {
          await typeCommand(block.cmd);
          await sleep(200);
        }
        for (const out of block.output || []) {
          if (!instant) await sleep(80);
          appendLine(out ? "term-out" : "term-blank", out);
        }
        if (!instant) await sleep(280);
      }
    }
  }

  async function renderHistoryThrough(currentExclusive) {
    screenEl.innerHTML = "";
    for (let s = 0; s < currentExclusive; s += 1) {
      await runScript(steps[s].script || [], true);
    }
  }

  async function runCurrentStep() {
    if (running) return;
    running = true;
    runBtn.disabled = true;
    runBtn.textContent = "Running…";
    await renderHistoryThrough(stepIndex);
    await runScript(steps[stepIndex].script || [], prefersReducedMotion());
    runBtn.disabled = false;
    runBtn.textContent = "▶ Run again";
    running = false;
  }

  function renderStep() {
    const step = steps[stepIndex];
    const pathBadge = step.path ? `<span class="it-badge term-path">Path ${step.path}</span>` : "";
    headEl.innerHTML = `
      <h3>${escapeHtml(step.title)} ${pathBadge}</h3>
      <p>${escapeHtml(step.subtitle || "")}</p>
    `;
    screenEl.innerHTML = "";
    runBtn.textContent = "▶ Run step";
    updateProgress();
    if (!prefersReducedMotion()) {
      setTimeout(() => runCurrentStep(), 180);
    }
  }

  function goTo(index) {
    stepIndex = index;
    renderStep();
  }

  runBtn.addEventListener("click", () => runCurrentStep());

  copyBtn.addEventListener("click", async () => {
    const cmds = (steps[stepIndex].script || [])
      .filter((b) => b.type === "run")
      .map((b) => b.cmd.replace(/\\n/g, "\n"))
      .join("\n\n");
    try {
      await navigator.clipboard.writeText(cmds);
      copyBtn.textContent = "Copied!";
      setTimeout(() => { copyBtn.textContent = "Copy commands"; }, 1500);
    } catch (_) {
      copyBtn.textContent = "Failed";
    }
  });

  prevBtn.addEventListener("click", () => {
    if (stepIndex > 0) goTo(stepIndex - 1);
  });

  nextBtn.addEventListener("click", () => {
    if (stepIndex < steps.length - 1) goTo(stepIndex + 1);
    else {
      localStorage.setItem(terminalTutorialStorageKey(tutorialId), String(steps.length));
      nextBtn.textContent = "Done ✓";
      container.classList.add("it-tutorial-done");
    }
  });

  renderStep();
}

function mountInteractiveTutorial(contentEl, data, ctx) {
  if (data.format === "interactive_terminal") {
    mountTerminalTutorial(contentEl, data, ctx);
  } else {
    mountPythonBotTutorial(contentEl, data, ctx);
  }
}

function isInteractiveTutorial(data) {
  return data.format === "interactive" || data.format === "interactive_terminal";
}
