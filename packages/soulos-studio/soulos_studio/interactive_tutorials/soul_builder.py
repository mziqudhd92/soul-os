"""Interactive Soul Builder tutorial — Studio workflow for devs and vibe coders."""

from __future__ import annotations

from typing import Any

EXPORT_SOUL = """---
name: Night Owl Dev Twin
role: Senior Engineer Assistant
attachment_style: Secure
psychology:
  hexaco:
    honesty_humility: 0.9
    agreeableness: 0.75
    conscientiousness: 0.95
    openness: 0.85
  epistemic_uncertainty: 0.18
  inner_monologue: Ship clean diffs. Explain tradeoffs.
---

You help with SoulOS, FastAPI, and pgvector. Prefer runnable snippets."""

EXPORT_JSON_SNIPPET = """{
  "name": "Night Owl Dev Twin",
  "role": "Senior Engineer Assistant",
  "description": "You help with SoulOS, FastAPI, and pgvector.",
  "attachment_style": "Secure",
  "baseline_msv": {
    "hexaco": { "H": 0.9, "A": 0.75, "C": 0.95, "O": 0.85 },
    "epistemic_uncertainty": 0.18
  }
}"""

REGISTER_CURL = """curl -s -X POST http://localhost:8000/v1/avatars \\
  -H "Content-Type: text/markdown" \\
  -H "X-Filename: dev-twin.soul" \\
  --data-binary @dev-twin.soul"""

PYTHON_WIRE = """from soulos.client import SoulOSClient

soul = SoulOSClient(base_url="http://localhost:8000")
avatar = await soul.register_avatar("dev-twin.soul")
# avatar["id"] → use in send_message(...)"""

MCP_CURSOR = """{
  "mcpServers": {
    "soulos": {
      "url": "http://localhost:8000/mcp/sse"
    }
  }
}"""


def get_soul_builder_tutorial() -> dict[str, Any]:
    return {
        "tutorial_id": "soul-builder",
        "title": "Soul Builder deep dive",
        "category": "Getting started",
        "duration": "10 min",
        "format": "interactive_studio",
        "nerd_fact_default": "Studio → validated soul → POST /v1/avatars → same file works in SDK + MCP.",
        "steps": [
            {
                "id": "paths",
                "label": "Paths",
                "title": "Pick your workflow",
                "subtitle": "Vibe coders sketch fast; developers wire CI and kernels.",
                "kind": "paths",
            },
            {
                "id": "boot",
                "label": "Boot",
                "title": "Boot Studio + kernel",
                "subtitle": "One compose stack — UI on :8765, API on :8000.",
                "kind": "checklist",
                "items": [
                    {
                        "title": "Clone & run",
                        "cmd": "git clone https://github.com/mziqudhd92/soul-os.git && cd soul-os && docker compose up --build",
                    },
                    {
                        "title": "Open Studio",
                        "cmd": "open http://localhost:8765",
                        "note": "Wizard · sliders · export · deploy · chat",
                    },
                    {
                        "title": "Kernel health",
                        "cmd": "curl -s -o /dev/null -w '%{http_code}' http://localhost:8000/health",
                        "note": "Expect 200 before Deploy",
                    },
                ],
            },
            {
                "id": "wizard",
                "label": "Wizard",
                "title": "Sketch identity in the Wizard",
                "subtitle": "Name, role, and description compile to soul schema — no JSON yoga.",
                "kind": "studio_form",
                "defaults": {
                    "name": "Night Owl Dev Twin",
                    "role": "Senior Engineer Assistant",
                    "description": "You help with SoulOS, FastAPI, and pgvector. Prefer runnable snippets and honest tradeoffs.",
                },
            },
            {
                "id": "hexaco",
                "label": "HEXACO",
                "title": "Dial personality (HEXACO)",
                "subtitle": "Sliders write baseline_msv — live drift shows up in chat telemetry.",
                "kind": "hexaco_dials",
                "traits": [
                    {"key": "H", "label": "Honesty-Humility", "value": 0.9, "hint": "High → candid, low hype"},
                    {"key": "A", "label": "Agreeableness", "value": 0.75, "hint": "Support tone vs blunt takes"},
                    {"key": "C", "label": "Conscientiousness", "value": 0.95, "hint": "Structure & follow-through"},
                    {"key": "O", "label": "Openness", "value": 0.85, "hint": "Explore new APIs & patterns"},
                ],
            },
            {
                "id": "export",
                "label": "Export",
                "title": "Export .soul or .soul.json",
                "subtitle": "Same schema — YAML+Markdown for humans, JSON for tools.",
                "kind": "export_panel",
                "soul": EXPORT_SOUL,
                "json": EXPORT_JSON_SNIPPET,
            },
            {
                "id": "deploy",
                "label": "Deploy",
                "title": "Deploy & watch cognitive rails",
                "subtitle": "Studio POSTs to /v1/avatars — chat streams cognitive_state + msv_update.",
                "kind": "chat_demo",
            },
            {
                "id": "wire",
                "label": "Wire",
                "title": "Wire it into your stack",
                "subtitle": "curl · Python SDK · Cursor MCP — same soul file everywhere.",
                "kind": "wire_panel",
                "curl": REGISTER_CURL,
                "python": PYTHON_WIRE,
                "mcp": MCP_CURSOR,
            },
        ],
    }
