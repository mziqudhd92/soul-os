"""OpenRouter (OpenAI-compatible) inference backend.

Chat always goes to OpenRouter. Embeddings use OpenRouter when
``OPENROUTER_EMBED_MODEL`` is set; otherwise a deterministic local
vector (same shape as the mock backend) so hybrid sidecar stacks can
keep a stable ``EMBEDDING_DIMENSION`` without a second provider.
"""

from __future__ import annotations

import hashlib
import json
import os
from collections.abc import AsyncIterator

import httpx

from backends.base import InferenceBackend


class OpenRouterBackend(InferenceBackend):
    def __init__(self) -> None:
        self.api_key = os.getenv("OPENROUTER_API_KEY", "").strip()
        if not self.api_key:
            raise ValueError("OPENROUTER_API_KEY is required when BRIDGE_MODE=openrouter")
        self.base_url = os.getenv(
            "OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"
        ).rstrip("/")
        self.chat_model = os.getenv(
            "OPENROUTER_CHAT_MODEL", "openai/gpt-4o-mini"
        )
        self.embed_model = os.getenv("OPENROUTER_EMBED_MODEL", "").strip()
        self.dimension = int(os.getenv("EMBEDDING_DIMENSION", "768"))
        self.http_referer = os.getenv(
            "OPENROUTER_HTTP_REFERER", "https://github.com/mziqudhd92/soul-os"
        )
        self.app_title = os.getenv("OPENROUTER_APP_TITLE", "SoulOS")
        self._timeout = float(os.getenv("OPENROUTER_TIMEOUT_S", "120"))

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": self.http_referer,
            "X-Title": self.app_title,
        }

    def _local_embed(self, text: str, model: str) -> list[float]:
        digest = hashlib.sha256(f"{model}:{text}".encode()).digest()
        return [(digest[i % len(digest)] / 255.0) * 0.1 for i in range(self.dimension)]

    async def embed(self, text: str, model: str) -> list[float]:
        model_id = model or self.embed_model
        if not model_id:
            return self._local_embed(text, model or "local-hash")
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.post(
                f"{self.base_url}/embeddings",
                headers=self._headers(),
                json={"model": model_id, "input": text},
            )
            resp.raise_for_status()
            data = resp.json()
        items = data.get("data") or []
        if not items or "embedding" not in items[0]:
            raise RuntimeError(f"Unexpected OpenRouter embed response: {data}")
        return items[0]["embedding"]

    async def generate_stream(self, prompt: str, model: str) -> AsyncIterator[str]:
        model_id = model or self.chat_model
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            async with client.stream(
                "POST",
                f"{self.base_url}/chat/completions",
                headers=self._headers(),
                json={
                    "model": model_id,
                    "stream": True,
                    "messages": [{"role": "user", "content": prompt}],
                },
            ) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if not line or not line.startswith("data:"):
                        continue
                    payload = line[5:].strip()
                    if payload == "[DONE]":
                        break
                    try:
                        chunk = json.loads(payload)
                    except json.JSONDecodeError:
                        continue
                    choices = chunk.get("choices") or []
                    if not choices:
                        continue
                    delta = choices[0].get("delta") or {}
                    text = delta.get("content")
                    if text:
                        yield text

    async def generate(self, prompt: str, model: str, format_json: bool = False) -> str:
        model_id = model or self.chat_model
        body: dict = {
            "model": model_id,
            "stream": False,
            "messages": [{"role": "user", "content": prompt}],
        }
        if format_json:
            body["response_format"] = {"type": "json_object"}
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.post(
                f"{self.base_url}/chat/completions",
                headers=self._headers(),
                json=body,
            )
            resp.raise_for_status()
            data = resp.json()
        choices = data.get("choices") or []
        if not choices:
            raise RuntimeError(f"Unexpected OpenRouter chat response: {data}")
        message = choices[0].get("message") or {}
        return message.get("content") or ""
