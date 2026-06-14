import os

import pytest
from httpx import ASGITransport, AsyncClient

os.environ["BRIDGE_MODE"] = "mock"
os.environ["EMBEDDING_DIMENSION"] = "768"

from main import app  # noqa: E402


@pytest.mark.asyncio
async def test_health():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/")
    assert resp.status_code == 200
    assert resp.json()["service"] == "soulos-inference-bridge"


@pytest.mark.asyncio
async def test_pull_noop():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/api/pull", json={"name": "llama3"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "success"


@pytest.mark.asyncio
async def test_embeddings_shape():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/api/embeddings",
            json={"model": "test-embed", "prompt": "hello soul"},
        )
    assert resp.status_code == 200
    embedding = resp.json()["embedding"]
    assert len(embedding) == 768


@pytest.mark.asyncio
async def test_generate_stream_lines():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/api/generate",
            json={"model": "test-chat", "prompt": "Say hi", "stream": True},
        )
    assert resp.status_code == 200
    lines = [line for line in resp.text.split("\n") if line.strip()]
    assert lines
    assert "response" in lines[0]


@pytest.mark.asyncio
async def test_generate_non_stream():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/api/generate",
            json={"model": "test-chat", "prompt": "Reflect", "stream": False},
        )
    assert resp.status_code == 200
    assert "response" in resp.json()
