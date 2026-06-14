"""Interactive terminal quickstart — support agent vs dev twin."""

from __future__ import annotations

from typing import Any

FAKE_SUPPORT_ID = "7f3a9c2e-8b1d-4e5f-9a0c-1d2e3f4a5b6c"
FAKE_DEV_ID = "2c8e1f4a-9b3d-5e6f-7a8b-9c0d1e2f3a4b"


def get_quickstart_tutorial() -> dict[str, Any]:
    return {
        "tutorial_id": "quickstart",
        "title": "15-minute quickstart",
        "category": "Getting started",
        "duration": "15 min",
        "format": "interactive_terminal",
        "nerd_fact_default": "One kernel · many souls · POST /v1/avatars compiles .soul on the fly.",
        "steps": [
            {
                "id": "boot",
                "label": "Boot",
                "title": "Start the stack",
                "subtitle": "Kernel + Postgres + Ollama via Docker Compose.",
                "nerd_fact": "soulos-kernel :8000 · Studio optional :8765",
                "script": [
                    {"type": "comment", "text": "# prerequisites: Docker installed"},
                    {
                        "type": "run",
                        "cmd": "git clone https://github.com/mziqudhd92/soul-os.git && cd soul-os",
                        "output": ["Cloning into 'soul-os'... done."],
                    },
                    {
                        "type": "run",
                        "cmd": "docker compose up --build",
                        "output": [
                            "✔ Container senticore-soulos-kernel  Started",
                            "✔ Kernel listening on http://localhost:8000",
                            "✔ Studio optional → http://localhost:8765",
                        ],
                    },
                ],
            },
            {
                "id": "health",
                "label": "Health",
                "title": "Verify kernel",
                "subtitle": "Smoke test before registering souls.",
                "script": [
                    {
                        "type": "run",
                        "cmd": "curl -s -o /dev/null -w '%{http_code}' http://localhost:8000/health",
                        "output": ["200"],
                    },
                ],
            },
            {
                "id": "support-register",
                "label": "Support",
                "title": "Path A — Register support agent",
                "subtitle": "Same API accepts .soul (markdown) or .soul.json.",
                "path": "A",
                "script": [
                    {
                        "type": "run",
                        "cmd": "curl -s -X POST http://localhost:8000/v1/avatars \\n  -H 'Content-Type: application/json' \\n  -d @examples/support-bot/support-bot.soul.json \\n  | tee /tmp/support-register.json",
                        "output": [
                            "{",
                            f'  "id": "{FAKE_SUPPORT_ID}",',
                            '  "name": "Site Support",',
                            '  "role": "Customer Support Agent",',
                            '  "baseline_msv": { "hexaco": { "H": 0.95, "A": 0.92, ... } }',
                            "}",
                        ],
                    },
                    {
                        "type": "run",
                        "cmd": "export SUPPORT_ID=$(python3 -c \"import json; print(json.load(open('/tmp/support-register.json'))['id'])\")",
                        "output": [f"bot_id={FAKE_SUPPORT_ID}"],
                    },
                ],
            },
            {
                "id": "support-memory",
                "label": "Memory",
                "title": "Teach refund policy",
                "subtitle": "Facts live in pgvector — not in a giant system prompt.",
                "path": "A",
                "script": [
                    {
                        "type": "run",
                        "cmd": f"curl -X POST http://localhost:8000/memory/ingest \\n  -H 'Content-Type: application/json' \\n  -d '{{\"bot_id\":\"{FAKE_SUPPORT_ID}\",\"content\":\"Full refunds within 30 days of purchase.\"}}'",
                        "output": ['{"status":"success","memory_id":"mem_01h..."}'],
                    },
                ],
            },
            {
                "id": "support-chat",
                "label": "Chat",
                "title": "Stream SSE chat",
                "subtitle": "Watch message chunks + msv_update + cognitive_state.",
                "path": "A",
                "script": [
                    {
                        "type": "run",
                        "cmd": f"curl -N -X POST http://localhost:8000/chat/generate \\n  -H 'Content-Type: application/json' \\n  -d '{{\"bot_id\":\"{FAKE_SUPPORT_ID}\",\"message\":\"Can I get a refund after 20 days?\"}}'",
                        "output": [
                            "event: cognitive_state",
                            'data: {"current_path":"system_1_heuristic","system_1":{"confidence_score":0.85,"latency_ms":38}}',
                            "",
                            "event: message",
                            'data: {"text":"Yes — refunds are available within "}',
                            "",
                            "event: message",
                            'data: {"text":"30 days of purchase."}',
                            "",
                            "event: msv_update",
                            'data: {"epistemic_uncertainty":0.11,"inner_monologue":"Policy recall succeeded."}',
                        ],
                    },
                ],
            },
            {
                "id": "dev-register",
                "label": "Dev twin",
                "title": "Path B — Register dev twin",
                "subtitle": "Same kernel, different soul file + memory.",
                "path": "B",
                "script": [
                    {
                        "type": "run",
                        "cmd": "curl -s -X POST http://localhost:8000/v1/avatars \\n  -d @examples/dev-twin/dev-twin.soul.json | tee /tmp/dev-register.json",
                        "output": [
                            "{",
                            f'  "id": "{FAKE_DEV_ID}",',
                            '  "name": "Dev Twin",',
                            '  "role": "Senior Engineer Assistant",',
                            "}",
                        ],
                    },
                    {
                        "type": "run",
                        "cmd": f"curl -X POST http://localhost:8000/memory/ingest -d '{{\"bot_id\":\"{FAKE_DEV_ID}\",\"content\":\"POST /v1/avatars registers validated HEXACO souls.\"}}'",
                        "output": ['{"status":"success"}'],
                    },
                    {
                        "type": "run",
                        "cmd": f"curl -N -X POST http://localhost:8000/chat/generate -d '{{\"bot_id\":\"{FAKE_DEV_ID}\",\"message\":\"How do I register an avatar?\"}}'",
                        "output": [
                            "event: message",
                            'data: {"text":"Use POST /v1/avatars with .soul or .soul.json — returns id for chat."}',
                        ],
                    },
                ],
            },
            {
                "id": "done",
                "label": "Done",
                "title": "You proved the model",
                "subtitle": "Two avatars, one kernel — only soul + memory differ.",
                "script": [
                    {"type": "comment", "text": "# Path A  support-bot.soul.json  + FAQ memory  → empathetic refunds"},
                    {"type": "comment", "text": "# Path B  dev-twin.soul.json   + API facts   → technical answers"},
                    {"type": "comment", "text": "# Next: Python bot guide or Soul Studio → Deploy"},
                    {
                        "type": "run",
                        "cmd": "echo 'ready for production wiring'",
                        "output": [
                            "✓ avatar_id persisted",
                            "✓ episodic memory ingested",
                            "✓ SSE telemetry observed",
                            "",
                            "→ https://mziqudhd92.github.io/soul-os/?tutorial=python-bot",
                        ],
                    },
                ],
            },
        ],
    }
