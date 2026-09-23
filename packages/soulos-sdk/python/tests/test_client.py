"""Tests for SoulOSClient (REST + SSE)."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from soulos.client import DEFAULT_CLOUD_URL, SoulOSClient


def test_defaults_to_localhost():
    c = SoulOSClient()
    assert c.base_url == "http://localhost:8000"
    assert c.api_key is None


def test_api_key_alone_uses_cloud_url():
    c = SoulOSClient(api_key="sk_x")
    assert c.base_url == DEFAULT_CLOUD_URL
    assert c._headers()["Authorization"] == "Bearer sk_x"


def test_base_url_strips_slash():
    c = SoulOSClient(base_url="http://k.test/")
    assert c.base_url == "http://k.test"


class _FakeAsyncClient:
    """Minimal async context manager wrapping a mock client."""

    def __init__(self, mock: AsyncMock):
        self.mock = mock

    async def __aenter__(self):
        return self.mock

    async def __aexit__(self, *args):
        return False


@pytest.mark.asyncio
async def test_register_avatar_dict():
    mock = AsyncMock()
    mock.post = AsyncMock(
        return_value=httpx.Response(200, json={"id": "b1", "name": "Bot"})
    )
    with patch("soulos.client.httpx.AsyncClient", return_value=_FakeAsyncClient(mock)):
        out = await SoulOSClient(base_url="http://k").register_avatar({"name": "Bot"})
    assert out["id"] == "b1"
    mock.post.assert_awaited_once()


@pytest.mark.asyncio
async def test_register_avatar_json_file(tmp_path: Path):
    soul = tmp_path / "bot.soul.json"
    soul.write_text(json.dumps({"name": "FileBot"}), encoding="utf-8")
    mock = AsyncMock()
    mock.post = AsyncMock(return_value=httpx.Response(200, json={"id": "f1"}))
    with patch("soulos.client.httpx.AsyncClient", return_value=_FakeAsyncClient(mock)):
        out = await SoulOSClient(base_url="http://k").register_avatar(soul)
    assert out["id"] == "f1"
    assert mock.post.await_args.kwargs["json"]["name"] == "FileBot"


@pytest.mark.asyncio
async def test_register_avatar_soul_markdown(tmp_path: Path):
    soul = tmp_path / "bot.soul"
    soul.write_bytes(b"---\nname: MD\n---\nbody")
    mock = AsyncMock()
    mock.post = AsyncMock(return_value=httpx.Response(200, json={"id": "m1"}))
    with patch("soulos.client.httpx.AsyncClient", return_value=_FakeAsyncClient(mock)):
        out = await SoulOSClient(base_url="http://k").register_avatar(soul)
    assert out["id"] == "m1"
    headers = mock.post.await_args.kwargs["headers"]
    assert headers["Content-Type"] == "text/markdown"
    assert headers["X-Filename"] == "bot.soul"


@pytest.mark.asyncio
async def test_register_avatar_error():
    mock = AsyncMock()
    mock.post = AsyncMock(
        return_value=httpx.Response(422, json={"detail": "SOUL_INVALID"})
    )
    with patch("soulos.client.httpx.AsyncClient", return_value=_FakeAsyncClient(mock)):
        with pytest.raises(ValueError, match="SOUL_INVALID"):
            await SoulOSClient(base_url="http://k").register_avatar({})


@pytest.mark.asyncio
async def test_ingest_memory_ok_and_fail():
    mock = AsyncMock()
    mock.post = AsyncMock(return_value=httpx.Response(200, json={"status": "ok"}))
    with patch("soulos.client.httpx.AsyncClient", return_value=_FakeAsyncClient(mock)):
        await SoulOSClient(base_url="http://k", api_key="sk").ingest_memory("b", "fact")
    assert mock.post.await_args.kwargs["headers"]["Authorization"] == "Bearer sk"

    mock.post = AsyncMock(return_value=httpx.Response(500, json={}))
    with patch("soulos.client.httpx.AsyncClient", return_value=_FakeAsyncClient(mock)):
        with pytest.raises(RuntimeError, match="ingest_memory"):
            await SoulOSClient(base_url="http://k").ingest_memory("b", "fact")


@pytest.mark.asyncio
async def test_sync_memory_ok_and_fail():
    mock = AsyncMock()
    mock.post = AsyncMock(
        return_value=httpx.Response(200, json={"imported": 2, "status": "success"})
    )
    with patch("soulos.client.httpx.AsyncClient", return_value=_FakeAsyncClient(mock)):
        out = await SoulOSClient(base_url="http://k").sync_memory("b", "/ws")
    assert out["imported"] == 2

    mock.post = AsyncMock(
        return_value=httpx.Response(422, json={"detail": "bad path"})
    )
    with patch("soulos.client.httpx.AsyncClient", return_value=_FakeAsyncClient(mock)):
        with pytest.raises(RuntimeError, match="bad path"):
            await SoulOSClient(base_url="http://k").sync_memory("b", "/ws")


@pytest.mark.asyncio
async def test_get_identity_ok_and_fail():
    mock = AsyncMock()
    mock.get = AsyncMock(return_value=httpx.Response(200, json={"name": "Bot"}))
    with patch("soulos.client.httpx.AsyncClient", return_value=_FakeAsyncClient(mock)):
        out = await SoulOSClient(base_url="http://k").get_identity("b")
    assert out["name"] == "Bot"

    mock.get = AsyncMock(return_value=httpx.Response(404, json={}))
    with patch("soulos.client.httpx.AsyncClient", return_value=_FakeAsyncClient(mock)):
        with pytest.raises(RuntimeError, match="get_identity"):
            await SoulOSClient(base_url="http://k").get_identity("b")


@pytest.mark.asyncio
async def test_update_state_ok_and_fail():
    mock = AsyncMock()
    mock.post = AsyncMock(return_value=httpx.Response(200, json={}))
    with patch("soulos.client.httpx.AsyncClient", return_value=_FakeAsyncClient(mock)):
        await SoulOSClient(base_url="http://k").update_state("b", {"hexaco": {}})

    mock.post = AsyncMock(return_value=httpx.Response(400, json={}))
    with patch("soulos.client.httpx.AsyncClient", return_value=_FakeAsyncClient(mock)):
        with pytest.raises(RuntimeError, match="update_state"):
            await SoulOSClient(base_url="http://k").update_state("b", {})


@pytest.mark.asyncio
async def test_send_message_parses_sse_events():
    sse = (
        'event: message\ndata: {"text":"Hi"}\n\n'
        'event: msv_update\ndata: {"hexaco":{"H":0.9}}\n\n'
        'event: cognitive_state\ndata: {"current_path":"s1"}\n\n'
        'event: error\ndata: {"msg":"x"}\n\n'
        "event: other\ndata: {}\n\n"
    )

    class _StreamCM:
        def __init__(self, response):
            self.response = response

        async def __aenter__(self):
            return self.response

        async def __aexit__(self, *a):
            return False

    response = MagicMock()
    response.status_code = 200

    async def aiter_text():
        yield sse

    response.aiter_text = aiter_text

    mock = AsyncMock()
    mock.stream = MagicMock(return_value=_StreamCM(response))

    with patch("soulos.client.httpx.AsyncClient", return_value=_FakeAsyncClient(mock)):
        events = [
            e
            async for e in SoulOSClient(base_url="http://k").send_message("b", "hi")
        ]
    types = [e["type"] for e in events]
    assert types == ["message", "msv_update", "cognitive_state", "error"]
    assert events[0]["text"] == "Hi"


@pytest.mark.asyncio
async def test_send_message_error_status():
    class _StreamCM:
        async def __aenter__(self):
            r = MagicMock()
            r.status_code = 502
            return r

        async def __aexit__(self, *a):
            return False

    mock = AsyncMock()
    mock.stream = MagicMock(return_value=_StreamCM())
    with patch("soulos.client.httpx.AsyncClient", return_value=_FakeAsyncClient(mock)):
        events = [
            e
            async for e in SoulOSClient(base_url="http://k").send_message("b", "hi")
        ]
    assert events[0]["type"] == "error"
