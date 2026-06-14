"""Hybrid sidecar client for SoulOS kernel."""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class SoulHybridClient:
    """Identity + memory + hybrid prepare/complete with graceful fallback."""

    def __init__(
        self,
        base_url: str | None = None,
        bot_id: str | None = None,
        enabled: bool | None = None,
        timeout: float = 60.0,
    ) -> None:
        self.base_url = (
            base_url or os.getenv("SOULOS_KERNEL_URL", "http://localhost:8000")
        ).rstrip("/")
        self.bot_id = bot_id or os.getenv("SOULOS_BOT_ID", "").strip() or None
        if enabled is None:
            self.enabled = os.getenv("SOULOS_ENABLED", "1").lower() not in (
                "0",
                "false",
                "no",
            )
        else:
            self.enabled = enabled
        self.timeout = timeout
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=self.timeout)
        return self._client

    async def close(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def is_ready(self) -> bool:
        if not self.enabled:
            return False
        try:
            client = await self._get_client()
            resp = await client.get(f"{self.base_url}/ready")
            if resp.status_code != 200:
                return False
            data = resp.json()
            return data.get("status") == "ok"
        except httpx.HTTPError:
            return False

    async def ensure_avatar(
        self,
        external_key: str,
        soul_path_or_dict: str | Path | dict[str, Any],
        runtime_config: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if isinstance(soul_path_or_dict, (str, Path)):
            path = Path(soul_path_or_dict)
            soul = json.loads(path.read_text(encoding="utf-8"))
        else:
            soul = soul_path_or_dict
        client = await self._get_client()
        resp = await client.post(
            f"{self.base_url}/v1/avatars/ensure",
            json={
                "external_key": external_key,
                "soul": soul,
                "runtime_config": runtime_config,
            },
        )
        resp.raise_for_status()
        record = resp.json()
        self.bot_id = record.get("id") or record.get("bot_id") or self.bot_id
        return record

    async def prepare_turn(
        self,
        query: str,
        bot_id: str | None = None,
        session_id: str | None = None,
        top_k: int = 5,
    ) -> dict[str, Any] | None:
        if not self.enabled:
            return None
        bid = bot_id or self.bot_id
        if not bid:
            return None
        try:
            client = await self._get_client()
            resp = await client.post(
                f"{self.base_url}/hybrid/prepare",
                json={
                    "bot_id": bid,
                    "query": query,
                    "top_k": top_k,
                    "session_id": session_id,
                },
            )
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPError as e:
            logger.warning("SoulOS prepare_turn failed: %s", e)
            return None

    async def complete_turn(
        self,
        summary: str,
        user_message: str | None = None,
        bot_id: str | None = None,
        session_id: str | None = None,
        reflect: bool = True,
        reflect_async: bool = True,
    ) -> dict[str, Any] | None:
        if not self.enabled:
            return None
        bid = bot_id or self.bot_id
        if not bid:
            return None
        try:
            client = await self._get_client()
            resp = await client.post(
                f"{self.base_url}/hybrid/complete",
                json={
                    "bot_id": bid,
                    "summary": summary,
                    "user_message": user_message,
                    "session_id": session_id,
                    "reflect": reflect,
                    "reflect_async": reflect_async,
                },
            )
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPError as e:
            logger.warning("SoulOS complete_turn failed: %s", e)
            return None
