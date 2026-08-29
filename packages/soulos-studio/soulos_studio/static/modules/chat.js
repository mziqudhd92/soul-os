import { state } from "./state.js";
import { $ } from "./state.js";
import { refreshSoul, writeFormToDom, buildSliders } from "./form.js";

export function logChat(text, role = "sys") {
  const div = document.createElement("div");
  div.className = `chat-line ${role}`;
  div.textContent = text;
  $("chat-log").appendChild(div);
  $("chat-log").scrollTop = $("chat-log").scrollHeight;
}

export function buildMcpConfig() {
  const kernelUrl = (state.meta?.kernel_url || "http://localhost:8000").replace(/\/$/, "");
  return {
    mcpServers: {
      soulos: {
        url: `${kernelUrl}/mcp/sse`,
      },
    },
  };
}

export function showMcpConnect(botId, name) {
  const panel = $("mcp-connect");
  const kernelUrl = (state.meta?.kernel_url || "http://localhost:8000").replace(/\/$/, "");
  $("mcp-bot-id").textContent = `bot_id: ${botId} (${name}) · MCP: ${kernelUrl}/mcp/sse`;
  $("mcp-config").textContent = JSON.stringify(buildMcpConfig(), null, 2);
  panel.classList.remove("hidden");
}

export async function copyMcpConfig() {
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

export async function deploy() {
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

export function showCognitiveRails() {
  const el = $("cognitive-rails");
  if (el) el.classList.remove("hidden");
}

export function updateCognitiveState(data) {
  showCognitiveRails();
  const pathEl = $("cognitive-path");
  if (pathEl) pathEl.textContent = data.current_path || "idle";

  const rail1 = document.querySelector(".cognitive-rail.system-1");
  const rail2 = document.querySelector(".cognitive-rail.system-2");
  const s1 = data.system_1;
  const s2 = data.system_2;

  if (s1 && rail1) {
    rail1.classList.add("active");
    const conf = s1.confidence_score ?? 0;
    const pulse1 = $("pulse-system-1");
    if (pulse1) pulse1.style.width = `${Math.round(conf * 100)}%`;
    const meta1 = $("meta-system-1");
    if (meta1) meta1.textContent = `conf ${conf.toFixed(2)} · ${s1.latency_ms ?? 0}ms`;
  } else if (rail1) {
    rail1.classList.remove("active");
  }

  if (s2 && rail2) {
    rail2.classList.add("active");
    const tokens = s2.reasoning_tokens ?? 0;
    const pulse2 = $("pulse-system-2");
    if (pulse2) pulse2.style.width = `${Math.min(100, Math.round(tokens / 8))}%`;
    const tools = (s2.active_mcp_tools || []).join(", ") || "none";
    const meta2 = $("meta-system-2");
    if (meta2) meta2.textContent = `loop ${s2.loop_count ?? 0} · ${s2.latency_ms ?? 0}ms · ${tools}`;
  } else if (rail2 && data.current_path === "system_2_deliberation") {
    rail2.classList.add("active");
  } else if (rail2) {
    rail2.classList.remove("active");
  }
}

export async function sendChat(message) {
  if (!state.avatarId) return;
  logChat(message, "user");
  try {
    const prepRes = await fetch("/api/hybrid/prepare", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ avatar_id: state.avatarId, query: message }),
    });
    if (prepRes.ok) {
      state.lastPrepare = await prepRes.json();
      showTurnInspector(state.lastPrepare);
    }
  } catch (_) {}
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
        } else if (event === "cognitive_state") {
          updateCognitiveState(data);
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

export function showTurnInspector(payload) {
  const panel = $("turn-inspector");
  const pre = $("inspector-json");
  if (!panel || !pre || !payload) return;
  panel.classList.remove("hidden");
  pre.textContent = JSON.stringify(payload, null, 2);
}
