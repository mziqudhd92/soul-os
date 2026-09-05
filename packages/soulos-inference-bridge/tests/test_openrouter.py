"""OpenRouter backend unit tests (mocked httpx)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backends.openrouter import OpenRouterBackend


@pytest.fixture
def backend(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-test")
    monkeypatch.setenv("OPENROUTER_CHAT_MODEL", "openai/gpt-4o-mini")
    monkeypatch.delenv("OPENROUTER_EMBED_MODEL", raising=False)
    monkeypatch.setenv("EMBEDDING_DIMENSION", "768")
    return OpenRouterBackend()


def test_headers_include_referer_and_title(backend):
    headers = backend._headers()
    assert headers["Authorization"] == "Bearer sk-or-test"
    assert headers["HTTP-Referer"]
    assert headers["X-Title"] == "SoulOS"


@pytest.mark.asyncio
async def test_embed_local_when_no_embed_model(backend):
    vec = await backend.embed("hello", "")
    assert len(vec) == 768
    again = await backend.embed("hello", "")
    assert vec == again


@pytest.mark.asyncio
async def test_embed_calls_openrouter_when_model_set(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-test")
    monkeypatch.setenv("OPENROUTER_EMBED_MODEL", "openai/text-embedding-3-small")
    backend = OpenRouterBackend()

    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = {"data": [{"embedding": [0.1] * 8}]}

    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None
    mock_client.post = AsyncMock(return_value=mock_resp)

    with patch("backends.openrouter.httpx.AsyncClient", return_value=mock_client):
        vec = await backend.embed("hi", "")

    assert vec == [0.1] * 8
    args, kwargs = mock_client.post.call_args
    assert args[0].endswith("/embeddings")
    assert kwargs["headers"]["Authorization"] == "Bearer sk-or-test"


@pytest.mark.asyncio
async def test_generate_non_stream(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-test")
    backend = OpenRouterBackend()

    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = {
        "choices": [{"message": {"content": '{"ok": true}'}}]
    }

    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None
    mock_client.post = AsyncMock(return_value=mock_resp)

    with patch("backends.openrouter.httpx.AsyncClient", return_value=mock_client):
        text = await backend.generate("reflect", "", format_json=True)

    assert text == '{"ok": true}'
    body = mock_client.post.call_args.kwargs["json"]
    assert body["response_format"] == {"type": "json_object"}
    assert body["model"] == "openai/gpt-4o-mini"


def test_missing_api_key_raises(monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    with pytest.raises(ValueError, match="OPENROUTER_API_KEY"):
        OpenRouterBackend()


def test_registry_openrouter(monkeypatch):
    monkeypatch.setenv("BRIDGE_MODE", "openrouter")
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-test")
    from backends.registry import get_backend

    backend = get_backend()
    assert backend.__class__.__name__ == "OpenRouterBackend"
