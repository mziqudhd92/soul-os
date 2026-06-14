"""Thin SoulOS adapter for hybrid orchestrator integrations."""

from __future__ import annotations

import os
from typing import Any

import httpx


class SoulClient:
    """REST wrapper for identity + episodic memory + MSV reflect."""

    def __init__(
        self,
        base_url: str | None = None,
        timeout: float = 60.0,
    ) -> None:
        self.base_url = (base_url or os.getenv("SOULOS_KERNEL_URL", "http://localhost:8000")).rstrip(
            "/"
        )
        self.timeout = timeout

    async def get_identity(self, bot_id: str) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.get(f"{self.base_url}/bot/{bot_id}/identity")
            resp.raise_for_status()
            return resp.json()

    async def retrieve_memory(
        self, bot_id: str, query: str, top_k: int = 5
    ) -> list[str]:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(
                f"{self.base_url}/memory/retrieve",
                json={"bot_id": bot_id, "query": query, "top_k": top_k},
            )
            resp.raise_for_status()
            return resp.json().get("memories", [])

    async def ingest_memory(self, bot_id: str, content: str) -> None:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(
                f"{self.base_url}/memory/ingest",
                json={"bot_id": bot_id, "content": content},
            )
            resp.raise_for_status()

    async def reflect(self, bot_id: str, message: str) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(
                f"{self.base_url}/state/reflect",
                json={"bot_id": bot_id, "message": message},
            )
            resp.raise_for_status()
            return resp.json()

    async def get_context(
        self, bot_id: str, query: str, top_k: int = 5
    ) -> dict[str, Any]:
        identity = await self.get_identity(bot_id)
        memories = await self.retrieve_memory(bot_id, query, top_k=top_k)
        return {"identity": identity, "memories": memories}

    def build_system_prompt(self, context: dict[str, Any]) -> str:
        identity = context["identity"]
        msv = identity.get("current_msv", {})
        monologue = msv.get("inner_monologue", "")
        memories = context.get("memories", [])
        memory_block = "\n".join(f"- {m}" for m in memories) if memories else "(none)"
        return (
            f"You are {identity.get('name')}, {identity.get('role')}.\n"
            f"{identity.get('description', '')}\n"
            f"Inner state: {monologue}\n"
            f"Recalled memories:\n{memory_block}"
        )

    async def persist_turn(
        self, bot_id: str, session_id: str, summary: str
    ) -> None:
        await self.ingest_memory(bot_id, f"[session:{session_id}] {summary}")
