"""Curated tutorials for SoulOS Studio."""

from __future__ import annotations

from typing import Any

TUTORIALS: list[dict[str, Any]] = [
    {
        "id": "first-soul",
        "title": "Build your first soul",
        "description": "Use the Wizard to create a validated .soul.json from scratch.",
        "duration": "5 min",
        "category": "Studio",
        "source": {"type": "tutorial", "path": "first-soul-wizard.md"},
    },
    {
        "id": "deploy-chat",
        "title": "Deploy and test chat",
        "description": "Register with the kernel, stream responses, and watch HEXACO drift.",
        "duration": "8 min",
        "category": "Studio",
        "source": {"type": "tutorial", "path": "deploy-and-chat.md"},
    },
    {
        "id": "quickstart",
        "title": "15-minute quickstart",
        "description": "Support agent vs dev twin — same kernel, different souls.",
        "duration": "15 min",
        "category": "Getting started",
        "source": {"type": "docs", "path": "getting-started/quickstart.md"},
    },
    {
        "id": "soul-builder",
        "title": "Soul Builder deep dive",
        "description": "Import, export, sliders, and kernel deploy from Studio.",
        "duration": "10 min",
        "category": "Getting started",
        "source": {"type": "docs", "path": "getting-started/soul-builder.md"},
    },
    {
        "id": "python-bot",
        "title": "Python bot integration",
        "description": "Migrate from static system prompts to SoulOS in Python.",
        "duration": "20 min",
        "category": "Guides",
        "source": {"type": "docs", "path": "guides/python-bot.md"},
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
