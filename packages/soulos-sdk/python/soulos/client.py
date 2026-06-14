"""Thin Python client for the SoulOS kernel API."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, AsyncIterator

import httpx

DEFAULT_CLOUD_URL = "https://api.soulos.dev"


class SoulOSClient:
    def __init__(self, base_url: str | None = None, api_key: str | None = None) -> None:
        if base_url:
            self.base_url = base_url.rstrip("/")
            self.api_key = api_key
        elif api_key:
            self.base_url = DEFAULT_CLOUD_URL
            self.api_key = api_key
        else:
            self.base_url = "http://localhost:8000"
            self.api_key = None

    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    async def register_avatar(self, soul_path_or_dict: str | Path | dict[str, Any]) -> dict[str, Any]:
        async with httpx.AsyncClient() as client:
            if isinstance(soul_path_or_dict, (str, Path)):
                path = Path(soul_path_or_dict)
                if path.suffix.lower() == ".soul":
                    headers = self._headers()
                    headers["Content-Type"] = "text/markdown"
                    headers["X-Filename"] = path.name
                    res = await client.post(
                        f"{self.base_url}/v1/avatars",
                        headers=headers,
                        content=path.read_bytes(),
                        timeout=30.0,
                    )
                else:
                    payload = json.loads(path.read_text(encoding="utf-8"))
                    res = await client.post(
                        f"{self.base_url}/v1/avatars",
                        headers=self._headers(),
                        json=payload,
                        timeout=30.0,
                    )
            else:
                res = await client.post(
                    f"{self.base_url}/v1/avatars",
                    headers=self._headers(),
                    json=soul_path_or_dict,
                    timeout=30.0,
                )
            body = res.json()
            if res.status_code != 200:
                raise ValueError(body.get("detail") or f"register_avatar failed ({res.status_code})")
            return body

    async def ingest_memory(self, avatar_id: str, content: str) -> None:
        async with httpx.AsyncClient() as client:
            res = await client.post(
                f"{self.base_url}/memory/ingest",
                headers=self._headers(),
                json={"bot_id": avatar_id, "content": content},
                timeout=30.0,
            )
            if res.status_code != 200:
                raise RuntimeError(f"ingest_memory failed ({res.status_code})")

    async def get_identity(self, avatar_id: str) -> dict[str, Any]:
        async with httpx.AsyncClient() as client:
            res = await client.get(
                f"{self.base_url}/bot/{avatar_id}/identity",
                headers=self._headers(),
                timeout=30.0,
            )
            if res.status_code != 200:
                raise RuntimeError(f"get_identity failed ({res.status_code})")
            return res.json()

    async def update_state(self, avatar_id: str, new_msv: dict[str, Any]) -> None:
        async with httpx.AsyncClient() as client:
            res = await client.post(
                f"{self.base_url}/state/update",
                headers=self._headers(),
                json={"bot_id": avatar_id, "new_msv": new_msv},
                timeout=30.0,
            )
            if res.status_code != 200:
                raise RuntimeError(f"update_state failed ({res.status_code})")

    async def send_message(self, avatar_id: str, message: str) -> AsyncIterator[dict[str, Any]]:
        async with httpx.AsyncClient() as client:
            async with client.stream(
                "POST",
                f"{self.base_url}/chat/generate",
                headers=self._headers(),
                json={"bot_id": avatar_id, "message": message},
                timeout=120.0,
            ) as response:
                if response.status_code != 200:
                    yield {"type": "error", "message": f"send_message failed ({response.status_code})"}
                    return

                buffer = ""
                async for chunk in response.aiter_text():
                    buffer += chunk
                    blocks = buffer.split("\n\n")
                    buffer = blocks.pop() or ""

                    for block in blocks:
                        event_line = next(
                            (l for l in block.split("\n") if l.startswith("event: ")), None
                        )
                        data_line = next(
                            (l for l in block.split("\n") if l.startswith("data: ")), None
                        )
                        if not event_line or not data_line:
                            continue

                        event = event_line[7:].strip()
                        data = json.loads(data_line[6:])

                        if event == "message" and "text" in data:
                            yield {"type": "message", "text": data["text"]}
                        elif event == "msv_update":
                            yield {"type": "msv_update", "msv": data}
                        elif event == "cognitive_state":
                            yield {"type": "cognitive_state", "state": data}
                        elif event == "error":
                            yield {"type": "error", "message": str(data)}
