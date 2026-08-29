import { state, $ } from "./modules/state.js";
import {
  initTheme,
  toggleTheme,
  buildSliders,
  writeFormToDom,
  refreshSoul,
  setPreviewMode,
  copyJson,
  onPreviewResize,
  exportSoul,
  exportSoulMarkdown,
  importFile,
  buildPrepareCurl,
  setPersonaMode,
} from "./modules/form.js";
import {
  copyMcpConfig,
  deploy,
  sendChat,
} from "./modules/chat.js";
import {
  openWizard,
  closeWizard,
  wizardNext,
  wizardBack,
} from "./modules/wizard.js";
import { switchView } from "./modules/views.js";
import { loadSoulPacksCatalog } from "./modules/soulpacks.js";
import {
  closeTutorialDetail,
} from "./modules/docs-tutorials.js";
import { setSoulpacksLoaded } from "./modules/ui-state.js";

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

  const spSearch = $("soulpacks-search");
  const spRefresh = $("soulpacks-refresh");
  if (spSearch) {
    spSearch.addEventListener("keydown", (e) => {
      if (e.key === "Enter") {
        setSoulpacksLoaded(false);
        loadSoulPacksCatalog(spSearch.value);
      }
    });
  }
  if (spRefresh) {
    spRefresh.addEventListener("click", () => {
      setSoulpacksLoaded(false);
      loadSoulPacksCatalog(spSearch?.value || "");
    });
  }

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
  setPersonaMode(state.form.persona_mode || "simple");

  ["name", "role", "description", "inner_monologue"].forEach((id) => {
    $(id).addEventListener("input", () => refreshSoul());
  });
  $("attachment_style").addEventListener("change", () => refreshSoul());
  $("epistemic_uncertainty").addEventListener("input", (e) => {
    $("uncertainty-val").textContent = parseFloat(e.target.value).toFixed(2);
    refreshSoul();
  });

  $("btn-theme").addEventListener("click", toggleTheme);
  document.querySelectorAll(".view-toggle-btn[data-preview]").forEach((btn) => {
    btn.addEventListener("click", () => setPreviewMode(btn.dataset.preview));
  });
  $("tab-simple")?.addEventListener("click", () => {
    state.form.persona_mode = "simple";
    setPersonaMode("simple");
    refreshSoul();
  });
  $("tab-advanced")?.addEventListener("click", () => {
    state.form.persona_mode = "advanced";
    setPersonaMode("advanced");
    refreshSoul();
  });
  $("btn-inspector-copy-json")?.addEventListener("click", async () => {
    if (state.lastPrepare) await navigator.clipboard.writeText(JSON.stringify(state.lastPrepare, null, 2));
  });
  $("btn-inspector-copy-curl")?.addEventListener("click", async () => {
    if (state.lastPrepare) await navigator.clipboard.writeText(buildPrepareCurl(state.lastPrepare));
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
