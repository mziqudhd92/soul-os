"""Thin SoulOS adapter — prefer SoulHybridClient from soulos-sdk for production."""

from __future__ import annotations

import os
from typing import Any

import httpx


class SoulClient:
    """REST wrapper; use prepare_turn / complete_turn when available."""

    def __init__(
        self,
        base_url: str | None = None,
        timeout: float = 60.0,
        enabled: bool | None = None,
    ) -> None:
        self.base_url = (
            base_url or os.getenv("SOULOS_KERNEL_URL", "http://localhost:8000")
        ).rstrip("/")
        self.timeout = timeout
        if enabled is None:
            self.enabled = os.getenv("SOULOS_ENABLED", "1").lower() not in (
                "0",
                "false",
                "no",
            )
        else:
            self.enabled = enabled
        self._client: httpx.AsyncClient | None = None

    async def _client_get(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=self.timeout)
        return self._client

    async def is_ready(self) -> bool:
        if not self.enabled:
            return False
        try:
            client = await self._client_get()
            resp = await client.get(f"{self.base_url}/ready")
            return resp.status_code == 200 and resp.json().get("status") == "ok"
        except httpx.HTTPError:
            return False

    async def prepare_turn(
        self, bot_id: str, query: str, session_id: str | None = None, top_k: int = 5
    ) -> dict[str, Any] | None:
        if not self.enabled:
            return None
        client = await self._client_get()
        resp = await client.post(
            f"{self.base_url}/hybrid/prepare",
            json={
                "bot_id": bot_id,
                "query": query,
                "session_id": session_id,
                "top_k": top_k,
            },
        )
        resp.raise_for_status()
        return resp.json()

    async def complete_turn(
        self,
        bot_id: str,
        summary: str,
        user_message: str | None = None,
        session_id: str | None = None,
        reflect_async: bool = True,
    ) -> dict[str, Any] | None:
        if not self.enabled:
            return None
        client = await self._client_get()
        resp = await client.post(
            f"{self.base_url}/hybrid/complete",
            json={
                "bot_id": bot_id,
                "summary": summary,
                "user_message": user_message,
                "session_id": session_id,
                "reflect": bool(user_message),
                "reflect_async": reflect_async,
            },
        )
        resp.raise_for_status()
        return resp.json()

    def build_system_prompt(self, prepare_payload: dict[str, Any]) -> str:
        return prepare_payload.get("system_prompt", "")
