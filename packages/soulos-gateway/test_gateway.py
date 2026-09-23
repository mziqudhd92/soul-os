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

# Refresh store after env set
import keys as keys_module
from keys import load_key_store

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
async def test_gateway_proxies_memory_sync():
    demo_key = "sk_test_demo_key_for_local_dev"
    mock_upstream = MagicMock()
    mock_upstream.status_code = 200
    mock_upstream.content = json.dumps(
        {"status": "success", "imported": 2, "skipped": 0, "total": 2}
    ).encode()
    mock_upstream.headers = httpx.Headers({"content-type": "application/json"})

    mock_client = MagicMock()
    mock_client.request = AsyncMock(return_value=mock_upstream)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("main.httpx.AsyncClient", return_value=mock_client):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            response = await ac.post(
                "/memory/sync",
                headers={"Authorization": f"Bearer {demo_key}"},
                json={
                    "bot_id": "123e4567-e89b-12d3-a456-426614174000",
                    "workspace_path": "/tmp/project",
                },
            )

    assert response.status_code == 200
    assert response.json()["imported"] == 2
    mock_client.request.assert_awaited_once()


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


def test_hash_api_key_format():
    from keys import hash_api_key

    digest = hash_api_key("sk_test_demo_key_for_local_dev")
    assert digest.startswith("sha256:")
    assert len(digest) == len("sha256:") + 64
    assert hash_api_key("sk_test_demo_key_for_local_dev") == digest


def test_lookup_api_key_hashes_bearer_token():
    from keys import hash_api_key, lookup_api_key

    record = lookup_api_key("sk_test_demo_key_for_local_dev")
    assert record is not None
    assert record.account_id == "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
    assert hash_api_key("sk_test_demo_key_for_local_dev") in keys_module.KEY_STORE
    assert "sk_test_demo_key_for_local_dev" not in keys_module.KEY_STORE
    assert lookup_api_key("sk_invalid") is None


def test_load_key_store_accepts_prehashed_keys(monkeypatch):
    from keys import hash_api_key, load_key_store, lookup_api_key

    plaintext = "sk_prehashed_test"
    hashed = hash_api_key(plaintext)
    monkeypatch.setenv(
        "SOULOS_API_KEYS",
        json.dumps(
            {
                hashed: {
                    "account_id": "11111111-2222-3333-4444-555555555555",
                    "tier": "cloud",
                    "rate_limit_per_minute": 60,
                }
            }
        ),
    )
    monkeypatch.setattr("keys.API_KEYS_JSON", os.environ["SOULOS_API_KEYS"])
    store = load_key_store()
    assert hashed in store
    assert plaintext not in store
    old = keys_module.KEY_STORE
    keys_module.KEY_STORE = store
    try:
        assert lookup_api_key(plaintext) is not None
        assert lookup_api_key(plaintext).account_id == "11111111-2222-3333-4444-555555555555"
    finally:
        keys_module.KEY_STORE = old
