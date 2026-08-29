import { state, $ } from "./state.js";
import { refreshSoul, writeFormToDom, buildSliders, setPersonaMode } from "./form.js";
import { escapeHtml } from "./dom-utils.js";
import { setSoulpacksLoaded } from "./ui-state.js";

export async function loadSoulPacksCatalog(query = "") {
  const grid = $("soulpacks-grid");
  const status = $("soulpacks-status");
  if (!grid) return;
  grid.innerHTML = "<p class='hint'>Loading SoulPacks…</p>";
  status.textContent = "";
  const params = new URLSearchParams();
  if (query.trim()) params.set("q", query.trim());
  try {
    const res = await fetch(`/api/soulpacks?${params}`);
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "load failed");
    const packs = data.packs || [];
    grid.innerHTML = "";
    if (!packs.length) {
      grid.innerHTML = "<p class='hint'>No SoulPacks matched your search.</p>";
      return;
    }
    packs.forEach((p) => {
      const card = document.createElement("div");
      card.className = "tutorial-card soulpacks-card";
      const packId = p.id || "";
      card.innerHTML = `
        <h3>${escapeHtml(p.name || packId)}</h3>
        <p class="hint">MIT · v${escapeHtml(String(p.version || ""))}</p>
        <div class="tutorial-card-meta">
          <span class="mono">${escapeHtml(packId)}</span>
          <span>${escapeHtml((p.tags || []).slice(0, 3).join(", "))}</span>
        </div>
        <div class="soulpacks-card-actions">
          <button type="button" class="btn ghost sm" data-action="studio">Open in Studio</button>
          <button type="button" class="btn primary sm" data-action="deploy">Deploy to kernel</button>
        </div>
      `;
      card.querySelector("[data-action=studio]").addEventListener("click", () =>
        importSoulPack(packId, false)
      );
      card.querySelector("[data-action=deploy]").addEventListener("click", () =>
        importSoulPack(packId, true)
      );
      grid.appendChild(card);
    });
    status.textContent = `${data.total ?? packs.length} SoulPacks · first-party MIT`;
    setSoulpacksLoaded(true);
  } catch (e) {
    grid.innerHTML = `<p class='hint'>${escapeHtml(e.message)}</p>`;
  }
}

export async function importSoulPack(packId, register) {
  const status = $("soulpacks-status");
  status.textContent = `Importing ${packId}…`;
  const { switchView } = await import("./views.js");
  try {
    const res = await fetch("/api/soulpacks/import", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ pack_id: packId, persist: register }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "import failed");

    if (register) {
      state.avatarId = data.id;
      $("avatar-id").textContent = `Avatar ID: ${data.id}`;
      $("chat-send").disabled = false;
      status.textContent = `Deployed ${data.name || packId} (${data.id})`;
      if (data.warnings?.length) {
        status.textContent += ` — ${data.warnings.join("; ")}`;
      }
      switchView("studio");
      return;
    }

    const soul = data.soul;
    if (!soul?.baseline_msv) throw new Error("Invalid soul payload from kernel");
    state.form = {
      name: soul.name,
      role: soul.role,
      description: soul.description,
      attachment_style: soul.attachment_style,
      hexaco: { ...soul.baseline_msv.hexaco },
      moral_foundations: { ...soul.baseline_msv.moral_foundations },
      drives: { ...soul.baseline_msv.drives },
      epistemic_uncertainty: soul.baseline_msv.epistemic_uncertainty,
      inner_monologue: soul.baseline_msv.inner_monologue || "",
      persona_mode: "advanced",
    };
    writeFormToDom();
    buildSliders();
    setPersonaMode("advanced");
    await refreshSoul();
    status.textContent =
      (data.warnings || []).join("; ") || `Loaded ${soul.name} into Studio`;
    switchView("studio");
  } catch (e) {
    status.textContent = String(e.message);
  }
}
