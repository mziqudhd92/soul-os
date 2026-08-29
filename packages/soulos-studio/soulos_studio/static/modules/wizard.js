import { state, wizard, ATTACHMENT_HINTS, $ } from "./state.js";
import { sliderRow, hexacoSliderRow, refreshSoul, writeFormToDom, buildSliders } from "./form.js";
import { escapeHtml, escapeAttr } from "./dom-utils.js";

export function cloneForm(form) {
  return JSON.parse(JSON.stringify(form));
}

export function defineWizardSteps() {
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

export function renderWizardProgress() {
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

export function renderWizardSliders(container, items, values, onChange, prefix) {
  container.innerHTML = "";
  items.forEach(({ key, label }) => {
    container.appendChild(sliderRow(key, label, values[key], onChange, prefix));
  });
}

export function renderWizardStep() {
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

export function updateWizardNav() {
  const back = $("wizard-back");
  const next = $("wizard-next");
  const isFirst = wizard.step === 0;
  const isLast = wizard.step === wizard.steps.length - 1;

  back.classList.toggle("hidden", isFirst);
  next.textContent = isLast ? "Create soul" : "Next";
}

export function openWizard() {
  wizard.form = cloneForm(state.form);
  wizard.step = 0;
  defineWizardSteps();
  renderWizardStep();
  $("wizard-overlay").classList.add("open");
  document.body.style.overflow = "hidden";
}

export function closeWizard() {
  $("wizard-overlay").classList.remove("open");
  document.body.style.overflow = "";
}

export function wizardValidateStep() {
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

export async function finishWizard() {
  state.form = cloneForm(wizard.form);
  writeFormToDom();
  buildSliders();
  await refreshSoul();
  closeWizard();
}

export function wizardNext() {
  if (!wizardValidateStep()) return;
  if (wizard.step >= wizard.steps.length - 1) {
    finishWizard();
    return;
  }
  wizard.step += 1;
  renderWizardStep();
}

export function wizardBack() {
  if (wizard.step <= 0) return;
  wizard.step -= 1;
  renderWizardStep();
}
