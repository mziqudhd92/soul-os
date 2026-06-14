"""Curated tutorials for SoulOS Studio."""

from __future__ import annotations

from typing import Any

TUTORIALS: list[dict[str, Any]] = [
    {
        "id": "python-bot",
        "title": "Python bot integration",
        "description": "Interactive walkthrough — migrate from static system prompts.",
        "duration": "25 min",
        "category": "Guides",
        "interactive": True,
        "source": {"type": "interactive", "path": "guides/python-bot.md"},
    },
    {
        "id": "quickstart",
        "title": "15-minute quickstart",
        "description": "Terminal walkthrough — support agent vs dev twin (curl + SSE).",
        "duration": "15 min",
        "category": "Getting started",
        "interactive": True,
        "source": {"type": "interactive", "path": "getting-started/quickstart.md"},
    },
    {
        "id": "first-soul",
        "title": "Build your first soul",
        "description": "Wizard walkthrough — validated .soul.json without hand-editing JSON.",
        "duration": "15 min",
        "category": "Studio",
        "source": {"type": "tutorial", "path": "first-soul-wizard.md"},
    },
    {
        "id": "deploy-chat",
        "title": "Deploy and test chat",
        "description": "Register with the kernel, stream responses, watch HEXACO drift.",
        "duration": "12 min",
        "category": "Studio",
        "source": {"type": "tutorial", "path": "deploy-and-chat.md"},
    },
    {
        "id": "soul-builder",
        "title": "Soul Builder deep dive",
        "description": "Interactive Studio walkthrough — Wizard, HEXACO, export, deploy, wire to SDK/MCP.",
        "duration": "10 min",
        "category": "Getting started",
        "interactive": True,
        "source": {"type": "interactive", "path": "getting-started/soul-builder.md"},
    },
    {
        "id": "psychometrics",
        "title": "HEXACO psychometrics",
        "description": "What each slider means and how MSV drift works.",
        "duration": "12 min",
        "category": "Guides",
        "source": {"type": "docs", "path": "guides/psychometrics.md"},
    },
    {
        "id": "mcp",
        "title": "MCP with Claude & Cursor",
        "description": "Connect SoulOS to Claude Desktop and Cursor via MCP.",
        "duration": "15 min",
        "category": "Guides",
        "source": {"type": "docs", "path": "guides/mcp.md"},
    },
    {
        "id": "self-hosted",
        "title": "Self-hosted deployment",
        "description": "Docker Compose, env vars, and security notes.",
        "duration": "15 min",
        "category": "Deployment",
        "source": {"type": "docs", "path": "deployment/self-hosted.md"},
    },
    {
        "id": "api-sse",
        "title": "API & SSE streaming",
        "description": "REST endpoints, message events, and msv_update telemetry.",
        "duration": "10 min",
        "category": "Reference",
        "source": {"type": "docs", "path": "reference/api.md"},
    },
    {
        "id": "soul-standard",
        "title": "Soul file anatomy",
        "description": "Field-by-field reference for .soul.json.",
        "duration": "8 min",
        "category": "Reference",
        "source": {"type": "docs", "path": "reference/soul-standard.md"},
    },
]

TUTORIALS_BY_ID = {t["id"]: t for t in TUTORIALS}
