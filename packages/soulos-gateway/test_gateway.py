import json
import os
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from httpx import ASGITransport, AsyncClient

# Load demo keys before importing app
os.environ["SOULOS_API_KEYS"] = json.dumps(
    {
        "sk_test_demo_key_for_local_dev": {
            "account_id": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
            "tier": "cloud",
            "rate_limit_per_minute": 120,
        }
    }
)

from keys import KEY_STORE, load_key_store

# Refresh store after env set
import keys as keys_module

keys_module.KEY_STORE = load_key_store()

from main import app


@pytest.mark.asyncio
async def test_gateway_health():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/health")
    assert response.status_code == 200
    assert response.json()["service"] == "soulos-gateway"


@pytest.mark.asyncio
async def test_gateway_rejects_missing_key():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/v1/avatars")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_gateway_rejects_invalid_key():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post(
            "/v1/avatars",
            headers={"Authorization": "Bearer sk_invalid"},
            json={"name": "x"},
        )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_gateway_proxies_mcp_sse_as_stream():
    demo_key = "sk_test_demo_key_for_local_dev"
    chunks = [b"event: endpoint\n", b"data: /mcp/messages\n\n"]

    async def aiter_bytes():
        for chunk in chunks:
            yield chunk

    mock_upstream = MagicMock()
    mock_upstream.status_code = 200
    mock_upstream.headers = httpx.Headers({"content-type": "text/event-stream"})
    mock_upstream.aiter_bytes = aiter_bytes
    mock_upstream.aclose = AsyncMock()

    mock_client = MagicMock()
    mock_client.build_request = MagicMock(return_value=MagicMock())
    mock_client.send = AsyncMock(return_value=mock_upstream)
    mock_client.aclose = AsyncMock()

    with patch("main.httpx.AsyncClient", return_value=mock_client):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            response = await ac.get(
                "/mcp/sse",
                headers={"Authorization": f"Bearer {demo_key}"},
            )

    assert response.status_code == 200
    assert "text/event-stream" in response.headers.get("content-type", "")
    body = b"".join([chunk async for chunk in response.aiter_bytes()])
    assert body == b"".join(chunks)
    mock_client.send.assert_awaited_once()
