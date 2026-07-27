#!/usr/bin/env python3
"""LangChain-shaped hybrid turn using SoulHybridClient (mock LLM if LC missing)."""

from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SDK = ROOT / "packages" / "soulos-sdk" / "python"
if str(SDK) not in sys.path:
    sys.path.insert(0, str(SDK))

from soulos.hybrid import SoulHybridClient  # noqa: E402


async def mock_generate(system_prompt: str, user_query: str) -> str:
    try:
        from langchain_core.messages import HumanMessage, SystemMessage
        from langchain_core.prompts import ChatPromptTemplate

        # Structural use of LangChain prompt objects; reply is deterministic for CI.
        _ = ChatPromptTemplate.from_messages(
            [
                ("system", "{system}"),
                ("human", "{query}"),
            ]
        ).format_messages(system=system_prompt[:200], query=user_query)
        _ = SystemMessage(content=system_prompt[:200])
        _ = HumanMessage(content=user_query)
    except ImportError:
        pass
    return (
        "Based on my persona and memory context, I can help with that. "
        f"(mock reply to: {user_query[:80]})"
    )


async def main() -> int:
    kernel = os.getenv("SOULOS_KERNEL_URL", "http://localhost:8000")
    bot_id = os.getenv("SOULOS_BOT_ID", "").strip() or None
    client = SoulHybridClient(base_url=kernel, bot_id=bot_id, enabled=True)
    query = "What is our refund policy?"
    try:
        if not bot_id:
            print(
                json.dumps(
                    {
                        "ok": False,
                        "hint": "Set SOULOS_BOT_ID or ensure an avatar first",
                        "pattern": "prepare → LangChain LLM → complete",
                    },
                    indent=2,
                )
            )
            # Still demonstrate prepare when bot exists via dry structure
            return 0
        prepared = await client.prepare_turn(query)
        if not prepared:
            print(json.dumps({"ok": False, "error": "prepare failed"}, indent=2))
            return 1
        reply = await mock_generate(prepared["system_prompt"], query)
        completed = await client.complete_turn(
            summary=reply[:500],
            user_message=query,
            reflect=False,
        )
        print(
            json.dumps(
                {
                    "ok": True,
                    "reply": reply,
                    "memories": len(prepared.get("memories") or []),
                    "complete": completed,
                },
                indent=2,
            )
        )
        return 0
    finally:
        await client.close()


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
