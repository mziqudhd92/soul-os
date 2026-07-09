"""Tests for Embedder error paths (RFC 7807)."""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from config import EMBEDDING_DIMENSION
from runtime.embedder import Embedder
from runtime.errors import INFERENCE_DOWN, MEMORY_DIM_MISMATCH, SoulOSProblem


@pytest.mark.asyncio
async def test_embedder_inference_down():
    embedder = Embedder()
    mock_resp = MagicMock()
    mock_resp.status_code = 503
    mock_resp.text = "service unavailable"

    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=mock_resp)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    with patch("runtime.embedder.httpx.AsyncClient", return_value=mock_client):
        with pytest.raises(SoulOSProblem) as exc:
            await embedder.get_embedding("hello")
    assert exc.value.code == INFERENCE_DOWN
    assert exc.value.status == 503


@pytest.mark.asyncio
async def test_embedder_dimension_mismatch():
    embedder = Embedder()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"embedding": [0.1] * (EMBEDDING_DIMENSION - 1)}

    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=mock_resp)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    with patch("runtime.embedder.httpx.AsyncClient", return_value=mock_client):
        with pytest.raises(SoulOSProblem) as exc:
            await embedder.get_embedding("hello")
    assert exc.value.code == MEMORY_DIM_MISMATCH
    assert exc.value.status == 422
    assert exc.value.extra["expected"] == EMBEDDING_DIMENSION


@pytest.mark.asyncio
async def test_embedder_success():
    embedder = Embedder()
    vec = [0.2] * EMBEDDING_DIMENSION
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"embedding": vec}

    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=mock_resp)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    with patch("runtime.embedder.httpx.AsyncClient", return_value=mock_client):
        result = await embedder.get_embedding("hello")
    assert result == vec
