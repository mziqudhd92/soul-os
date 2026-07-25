"""Hybrid sidecar client for SoulOS kernel."""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any, Callable, Awaitable

import httpx

logger = logging.getLogger(__name__)

PROBLEM_CONTENT_TYPE = "application/problem+json"


class SoulOSError(Exception):
    """Raised when kernel returns RFC 7807 Problem Details."""

    def __init__(self, code: str, status: int, detail: str, body: dict[str, Any]):
        self.code = code
        self.status = status
        self.detail = detail
        self.body = body
        super().__init__(f"{code}: {detail}")


def _parse_problem(resp: httpx.Response) -> SoulOSError:
    try:
        body = resp.json()
    except json.JSONDecodeError:
        body = {"detail": resp.text}
    code = body.get("code", "UNKNOWN")
    detail = body.get("detail") or body.get("title") or resp.text
    return SoulOSError(code, resp.status_code, detail, body)


class SoulHybridClient:
    """Identity + memory + hybrid prepare/complete with graceful fallback."""

    def __init__(
        self,
        base_url: str | None = None,
        bot_id: str | None = None,
        enabled: bool | None = None,
        timeout: float = 60.0,
        gateway_secret: str | None = None,
        account_id: str | None = None,
        max_retries: int = 2,
    ) -> None:
        self.base_url = (
            base_url or os.getenv("SOULOS_KERNEL_URL", "http://localhost:8000")
        ).rstrip("/")
        self.bot_id = bot_id or os.getenv("SOULOS_BOT_ID", "").strip() or None
        self.gateway_secret = gateway_secret or os.getenv("SOULOS_GATEWAY_SECRET", "").strip() or None
        self.account_id = account_id or os.getenv("SOULOS_ACCOUNT_ID", "").strip() or None
        if enabled is None:
            self.enabled = os.getenv("SOULOS_ENABLED", "1").lower() not in (
                "0",
                "false",
                "no",
            )
        else:
            self.enabled = enabled
        self.timeout = timeout
        self.max_retries = max_retries
        self._client: httpx.AsyncClient | None = None

    def _request_headers(self) -> dict[str, str]:
        headers: dict[str, str] = {}
        if self.gateway_secret:
            headers["X-SoulOS-Gateway-Secret"] = self.gateway_secret
        if self.account_id:
            headers["X-SoulOS-Account-Id"] = self.account_id
        return headers

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=self.timeout, headers=self._request_headers())
        return self._client

    async def close(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def _request(
        self,
        method: str,
        path: str,
        *,
        json_body: dict[str, Any] | None = None,
    ) -> httpx.Response:
        client = await self._get_client()
        url = f"{self.base_url}{path}"
        last_exc: Exception | None = None
        for attempt in range(self.max_retries + 1):
            try:
                resp = await client.request(method, url, json=json_body)
                if resp.status_code >= 500 and attempt < self.max_retries:
                    continue
                if not resp.is_success:
                    ct = resp.headers.get("content-type", "")
                    if PROBLEM_CONTENT_TYPE in ct or resp.status_code >= 400:
                        raise _parse_problem(resp)
                return resp
            except httpx.HTTPError as e:
                last_exc = e
                if attempt >= self.max_retries:
                    raise
        if last_exc:
            raise last_exc
        raise RuntimeError("request failed")

    async def is_ready(self) -> bool:
        if not self.enabled:
            return False
        try:
            resp = await self._request("GET", "/ready")
            if resp.status_code != 200:
                return False
            data = resp.json()
            return data.get("status") == "ok"
        except (httpx.HTTPError, SoulOSError):
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
        resp = await self._request(
            "POST",
            "/v1/avatars/ensure",
            json_body={
                "external_key": external_key,
                "soul": soul,
                "runtime_config": runtime_config,
            },
        )
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
            resp = await self._request(
                "POST",
                "/hybrid/prepare",
                json_body={
                    "bot_id": bid,
                    "query": query,
                    "top_k": top_k,
                    "session_id": session_id,
                },
            )
            return resp.json()
        except (httpx.HTTPError, SoulOSError) as e:
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
            resp = await self._request(
                "POST",
                "/hybrid/complete",
                json_body={
                    "bot_id": bid,
                    "summary": summary,
                    "user_message": user_message,
                    "session_id": session_id,
                    "reflect": reflect,
                    "reflect_async": reflect_async,
                },
            )
            return resp.json()
        except (httpx.HTTPError, SoulOSError) as e:
            logger.warning("SoulOS complete_turn failed: %s", e)
            return None

    async def ingest_memory(
        self,
        content: str,
        bot_id: str | None = None,
        session_id: str | None = None,
    ) -> dict[str, Any] | None:
        """POST /memory/ingest — seed facts (e.g. Phase A handoff notes)."""
        if not self.enabled:
            return None
        bid = bot_id or self.bot_id
        if not bid:
            return None
        try:
            body: dict[str, Any] = {"bot_id": bid, "content": content}
            if session_id is not None:
                body["session_id"] = session_id
            resp = await self._request("POST", "/memory/ingest", json_body=body)
            return resp.json()
        except (httpx.HTTPError, SoulOSError) as e:
            logger.warning("SoulOS ingest_memory failed: %s", e)
            return None

    async def run_turn(
        self,
        query: str,
        generate: Callable[[str, dict[str, Any]], Awaitable[str]],
        *,
        external_key: str | None = None,
        soul: str | Path | dict[str, Any] | None = None,
        session_id: str | None = None,
        top_k: int = 5,
        reflect: bool = True,
    ) -> dict[str, Any]:
        """Optional ensure → prepare → caller generate → complete."""
        if external_key and soul is not None:
            await self.ensure_avatar(external_key, soul)
        prepared = await self.prepare_turn(query, session_id=session_id, top_k=top_k)
        if not prepared:
            raise SoulOSError("PREPARE_FAILED", 0, "prepare_turn returned no context", {})
        system_prompt = prepared["system_prompt"]
        reply = await generate(system_prompt, prepared)
        completed = await self.complete_turn(
            summary=reply[:2000],
            user_message=query,
            session_id=session_id,
            reflect=reflect,
        )
        return {
            "query": query,
            "system_prompt": system_prompt,
            "reply": reply,
            "prepare": prepared,
            "complete": completed,
        }
