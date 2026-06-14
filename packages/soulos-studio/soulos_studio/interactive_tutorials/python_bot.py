"""Structured steps for the interactive Python bot tutorial."""

from __future__ import annotations

from typing import Any


def get_python_bot_tutorial() -> dict[str, Any]:
    return {
        "tutorial_id": "python-bot",
        "title": "Python bot integration",
        "category": "Guides",
        "duration": "25 min",
        "format": "interactive",
        "steps": [
            {
                "id": "intro",
                "title": "Why SoulOS?",
                "subtitle": "Replace fragile system prompts with a validated soul + memory.",
                "kind": "intro",
            },
            {
                "id": "soul",
                "title": "Create a soul file",
                "subtitle": "Export `.soul` or `.soul.json` from Studio or copy an example.",
                "kind": "code",
                "code": """---
name: Acme Support
role: Customer Support Agent
attachment_style: Secure
psychology:
  hexaco:
    honesty_humility: 0.9
    agreeableness: 0.9
  epistemic_uncertainty: 0.15
  inner_monologue: Ready to help with clarity.
---

You help with orders and refunds. Be concise and empathetic.""",
                "language": "markdown",
                "action": "open_studio",
            },
            {
                "id": "register",
                "title": "Register once",
                "subtitle": "Persist `avatar_id` — do not register on every message.",
                "kind": "code",
                "code": """import asyncio
from soulos.client import SoulOSClient

async def bootstrap():
    soul = SoulOSClient(base_url="http://localhost:8000")
    avatar = await soul.register_avatar("my-bot.soul")
    print(f"avatar_id={avatar['id']}")
    return avatar["id"]

asyncio.run(bootstrap())""",
                "language": "python",
                "action": "check_kernel",
            },
            {
                "id": "memory",
                "title": "Teach the bot",
                "subtitle": "Ingest facts via API or commit `.soul-memory/` and sync.",
                "kind": "code",
                "code": """await soul.ingest_memory(avatar_id, "Refunds within 30 days.")

# Git ledger (team repos)
# soulos memory-append "Refunds within 30 days."
# await soul.sync_memory(avatar_id, "/path/to/project")""",
                "language": "python",
            },
            {
                "id": "chat",
                "title": "Stream chat + telemetry",
                "subtitle": "Handle `message`, `msv_update`, and `cognitive_state` events.",
                "kind": "sse_playground",
            },
            {
                "id": "wire",
                "title": "Wire your bot loop",
                "subtitle": "Swap your LLM call for `send_message` in Discord, FastAPI, or REPL.",
                "kind": "code",
                "code": """async def handle_user_message(text: str) -> str:
    parts = []
    async for event in soul.send_message(AVATAR_ID, text):
        if event["type"] == "message":
            parts.append(event["text"])
    return "".join(parts)""",
                "language": "python",
                "action": "complete",
            },
        ],
    }
