"""Unit tests for Bedrock, Vertex, registry, and remaining OpenRouter paths."""

from __future__ import annotations

import io
import json
import sys
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Bedrock
# ---------------------------------------------------------------------------


@pytest.fixture
def bedrock_backend(monkeypatch):
    monkeypatch.setenv("AWS_REGION", "us-west-2")
    monkeypatch.setenv("BEDROCK_CHAT_MODEL_ID", "amazon.nova-lite-v1:0")
    monkeypatch.setenv("BEDROCK_EMBED_MODEL_ID", "amazon.titan-embed-text-v2:0")
    mock_client = MagicMock()
    with patch("backends.bedrock.boto3") as mock_boto3:
        mock_boto3.client.return_value = mock_client
        from backends.bedrock import BedrockBackend

        backend = BedrockBackend()
    backend.client = mock_client
    return backend, mock_client


def test_bedrock_init_uses_env(monkeypatch):
    monkeypatch.setenv("AWS_REGION", "eu-west-1")
    monkeypatch.setenv("BEDROCK_CHAT_MODEL_ID", "chat-model")
    monkeypatch.setenv("BEDROCK_EMBED_MODEL_ID", "embed-model")
    with patch("backends.bedrock.boto3") as mock_boto3:
        mock_boto3.client.return_value = MagicMock()
        from backends.bedrock import BedrockBackend

        backend = BedrockBackend()
    mock_boto3.client.assert_called_once_with("bedrock-runtime", region_name="eu-west-1")
    assert backend.chat_model == "chat-model"
    assert backend.embed_model == "embed-model"


@pytest.mark.asyncio
async def test_bedrock_embed_embedding_shape(bedrock_backend):
    backend, client = bedrock_backend
    payload = {"embedding": [0.1, 0.2, 0.3]}
    client.invoke_model.return_value = {
        "body": io.BytesIO(json.dumps(payload).encode()),
    }
    vec = await backend.embed("hello", "")
    assert vec == [0.1, 0.2, 0.3]
    assert client.invoke_model.call_args.kwargs["modelId"] == backend.embed_model


@pytest.mark.asyncio
async def test_bedrock_embed_embeddings_list_shape(bedrock_backend):
    backend, client = bedrock_backend
    payload = {"embeddings": [{"embedding": [0.4, 0.5]}]}
    client.invoke_model.return_value = {
        "body": io.BytesIO(json.dumps(payload).encode()),
    }
    vec = await backend.embed("hi", "custom-embed")
    assert vec == [0.4, 0.5]
    assert client.invoke_model.call_args.kwargs["modelId"] == "custom-embed"


@pytest.mark.asyncio
async def test_bedrock_embed_unexpected_raises(bedrock_backend):
    backend, client = bedrock_backend
    client.invoke_model.return_value = {
        "body": io.BytesIO(json.dumps({"unexpected": True}).encode()),
    }
    with pytest.raises(RuntimeError, match="Unexpected Bedrock embed"):
        await backend.embed("x", "")


@pytest.mark.asyncio
async def test_bedrock_generate_stream_with_deltas(bedrock_backend):
    backend, client = bedrock_backend
    client.converse_stream.return_value = {
        "stream": [
            {"contentBlockDelta": {"delta": {"text": "Hello"}}},
            {"contentBlockDelta": {"delta": {"text": " world"}}},
            {"messageStop": {}},
            {"contentBlockDelta": {"delta": {}}},
        ]
    }
    chunks = [c async for c in backend.generate_stream("hi", "")]
    assert chunks == ["Hello", " world"]


@pytest.mark.asyncio
async def test_bedrock_generate_stream_without_stream(bedrock_backend):
    backend, client = bedrock_backend
    client.converse_stream.return_value = {}
    chunks = [c async for c in backend.generate_stream("hi", "m")]
    assert chunks == [""]


@pytest.mark.asyncio
async def test_bedrock_generate(bedrock_backend):
    backend, client = bedrock_backend
    client.converse.return_value = {
        "output": {
            "message": {
                "content": [{"text": "alpha"}, {"image": "x"}, {"text": "beta"}],
            }
        }
    }
    text = await backend.generate("prompt", "")
    assert text == "alphabeta"


# ---------------------------------------------------------------------------
# Vertex
# ---------------------------------------------------------------------------


def _install_vertex_stubs():
    """Install fake vertexai / google.cloud modules so VertexBackend can import."""
    vertexai = MagicMock()
    generative_models = MagicMock()
    language_models = MagicMock()
    google_cloud = MagicMock()
    aiplatform = MagicMock()
    google_cloud.aiplatform = aiplatform

    stubs = {
        "vertexai": vertexai,
        "vertexai.generative_models": generative_models,
        "vertexai.language_models": language_models,
        "google": MagicMock(),
        "google.cloud": google_cloud,
        "google.cloud.aiplatform": aiplatform,
    }
    return stubs, vertexai, aiplatform, generative_models, language_models


@pytest.fixture
def vertex_modules():
    stubs, vertexai, aiplatform, generative_models, language_models = _install_vertex_stubs()
    with patch.dict(sys.modules, stubs):
        # Ensure a clean import of backends.vertex each time.
        sys.modules.pop("backends.vertex", None)
        yield {
            "vertexai": vertexai,
            "aiplatform": aiplatform,
            "GenerativeModel": generative_models.GenerativeModel,
            "TextEmbeddingModel": language_models.TextEmbeddingModel,
        }
    sys.modules.pop("backends.vertex", None)


def test_vertex_init_missing_project_raises(monkeypatch, vertex_modules):
    monkeypatch.delenv("VERTEX_PROJECT_ID", raising=False)
    from backends.vertex import VertexBackend

    with pytest.raises(ValueError, match="VERTEX_PROJECT_ID"):
        VertexBackend()


def test_vertex_init_ok(monkeypatch, vertex_modules):
    monkeypatch.setenv("VERTEX_PROJECT_ID", "proj-1")
    monkeypatch.setenv("VERTEX_LOCATION", "europe-west1")
    monkeypatch.setenv("VERTEX_CHAT_MODEL", "gemini-test")
    monkeypatch.setenv("VERTEX_EMBED_MODEL", "embed-test")
    from backends.vertex import VertexBackend

    backend = VertexBackend()
    vertex_modules["aiplatform"].init.assert_called_once_with(
        project="proj-1", location="europe-west1"
    )
    vertex_modules["vertexai"].init.assert_called_once_with(
        project="proj-1", location="europe-west1"
    )
    assert backend.chat_model == "gemini-test"
    assert backend.embed_model == "embed-test"


@pytest.mark.asyncio
async def test_vertex_embed(monkeypatch, vertex_modules):
    monkeypatch.setenv("VERTEX_PROJECT_ID", "proj-1")
    from backends.vertex import VertexBackend

    backend = VertexBackend()
    emb = SimpleNamespace(values=[0.1, 0.2])
    model = MagicMock()
    model.get_embeddings.return_value = [emb]
    vertex_modules["TextEmbeddingModel"].from_pretrained.return_value = model

    vec = await backend.embed("hello", "")
    assert vec == [0.1, 0.2]
    vertex_modules["TextEmbeddingModel"].from_pretrained.assert_called_with(
        backend.embed_model
    )


@pytest.mark.asyncio
async def test_vertex_generate_stream(monkeypatch, vertex_modules):
    monkeypatch.setenv("VERTEX_PROJECT_ID", "proj-1")
    from backends.vertex import VertexBackend

    backend = VertexBackend()
    generative = MagicMock()
    generative.generate_content.return_value = [
        SimpleNamespace(text="Hi"),
        SimpleNamespace(text=" there"),
        SimpleNamespace(text=""),
    ]
    vertex_modules["GenerativeModel"].return_value = generative

    chunks = [c async for c in backend.generate_stream("prompt", "custom")]
    assert chunks == ["Hi", " there"]
    vertex_modules["GenerativeModel"].assert_called_with("custom")


@pytest.mark.asyncio
async def test_vertex_generate(monkeypatch, vertex_modules):
    monkeypatch.setenv("VERTEX_PROJECT_ID", "proj-1")
    from backends.vertex import VertexBackend

    backend = VertexBackend()
    generative = MagicMock()
    generative.generate_content.return_value = SimpleNamespace(text="full reply")
    vertex_modules["GenerativeModel"].return_value = generative

    text = await backend.generate("prompt", "")
    assert text == "full reply"


@pytest.mark.asyncio
async def test_vertex_generate_empty_text(monkeypatch, vertex_modules):
    monkeypatch.setenv("VERTEX_PROJECT_ID", "proj-1")
    from backends.vertex import VertexBackend

    backend = VertexBackend()
    generative = MagicMock()
    generative.generate_content.return_value = SimpleNamespace(text=None)
    vertex_modules["GenerativeModel"].return_value = generative
    assert await backend.generate("p", "m") == ""


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------


def test_registry_mock(monkeypatch):
    monkeypatch.setenv("BRIDGE_MODE", "mock")
    from backends.registry import get_backend

    assert get_backend().__class__.__name__ == "MockBackend"


def test_registry_bedrock(monkeypatch):
    monkeypatch.setenv("BRIDGE_MODE", "bedrock")
    with patch("backends.registry.BedrockBackend") as mock_cls:
        mock_cls.return_value = MagicMock(name="bedrock")
        from backends.registry import get_backend

        backend = get_backend()
    mock_cls.assert_called_once()
    assert backend is mock_cls.return_value


def test_registry_vertex(monkeypatch, vertex_modules):
    monkeypatch.setenv("BRIDGE_MODE", "vertex")
    monkeypatch.setenv("VERTEX_PROJECT_ID", "proj-1")
    from backends.registry import get_backend

    backend = get_backend()
    assert backend.__class__.__name__ == "VertexBackend"


def test_registry_unknown_mode(monkeypatch):
    monkeypatch.setenv("BRIDGE_MODE", "nope")
    from backends.registry import get_backend

    with pytest.raises(ValueError, match="Unknown BRIDGE_MODE"):
        get_backend()


# ---------------------------------------------------------------------------
# OpenRouter remaining paths
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_openrouter_aclose(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-test")
    from backends.openrouter import OpenRouterBackend

    backend = OpenRouterBackend()
    mock_http = AsyncMock()
    backend._http = mock_http
    await backend.aclose()
    mock_http.aclose.assert_awaited_once()
    assert backend._http is None
    await backend.aclose()  # no-op when already closed


@pytest.mark.asyncio
async def test_openrouter_embed_unexpected_response(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-test")
    monkeypatch.setenv("OPENROUTER_EMBED_MODEL", "openai/text-embedding-3-small")
    from backends.openrouter import OpenRouterBackend

    backend = OpenRouterBackend()
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = {"data": [{}]}
    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=mock_resp)
    with patch.object(backend, "_client", return_value=mock_client):
        with pytest.raises(RuntimeError, match="Unexpected OpenRouter embed"):
            await backend.embed("hi", "")


@pytest.mark.asyncio
async def test_openrouter_generate_empty_choices(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-test")
    from backends.openrouter import OpenRouterBackend

    backend = OpenRouterBackend()
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = {"choices": []}
    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=mock_resp)
    with patch.object(backend, "_client", return_value=mock_client):
        with pytest.raises(RuntimeError, match="Unexpected OpenRouter chat"):
            await backend.generate("hi", "")


@pytest.mark.asyncio
async def test_openrouter_generate_stream(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-test")
    from backends.openrouter import OpenRouterBackend

    backend = OpenRouterBackend()

    lines = [
        "",
        ": keepalive",
        'data: {"choices":[{"delta":{"content":"Hello"}}]}',
        "data: not-json",
        'data: {"choices":[]}',
        'data: {"choices":[{"delta":{}}]}',
        "data: [DONE]",
        'data: {"choices":[{"delta":{"content":"skip"}}]}',
    ]

    async def aiter_lines():
        for line in lines:
            yield line

    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.aiter_lines = aiter_lines
    mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
    mock_resp.__aexit__ = AsyncMock(return_value=None)

    mock_client = MagicMock()
    mock_client.stream = MagicMock(return_value=mock_resp)

    with patch.object(backend, "_client", return_value=mock_client):
        chunks = [c async for c in backend.generate_stream("hi", "openai/gpt-4o")]
    assert chunks == ["Hello"]


@pytest.mark.asyncio
async def test_mock_generate_format_json(monkeypatch):
    monkeypatch.setenv("EMBEDDING_DIMENSION", "8")
    from backends.mock import MockBackend

    backend = MockBackend()
    text = await backend.generate("x", "m", format_json=True)
    data = json.loads(text)
    assert "hexaco" in data
    assert data["epistemic_uncertainty"] == 0.2
