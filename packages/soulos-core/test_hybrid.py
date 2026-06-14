"""Tests for hybrid sidecar API."""

import pytest
from httpx import AsyncClient, ASGITransport

from dependencies import get_db, get_embedder, get_llm_service
from main import app
from test_main import MockEmbedder, MockLLMService, VALID_SOUL, mock_get_db

app.dependency_overrides[get_db] = mock_get_db
app.dependency_overrides[get_embedder] = MockEmbedder
app.dependency_overrides[get_llm_service] = lambda: MockLLMService()


@pytest.mark.asyncio
async def test_ready_endpoint():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/ready")
    assert response.status_code in (200, 503)
    body = response.json()
    assert "checks" in body
    assert "embedding_dimension" in body


"""Tests for hybrid sidecar API."""

from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient, ASGITransport

from dependencies import get_db, get_embedder, get_llm_service
from main import app
from test_main import MockEmbedder, MockLLMService, VALID_SOUL, mock_get_db

app.dependency_overrides[get_db] = mock_get_db
app.dependency_overrides[get_embedder] = MockEmbedder
app.dependency_overrides[get_llm_service] = lambda: MockLLMService()


@pytest.mark.asyncio
async def test_ensure_avatar():
    record = {
        "id": "123e4567-e89b-12d3-a456-426614174000",
        "name": "Test Avatar",
        "role": "Tester",
        "baseline_msv": VALID_SOUL["baseline_msv"],
        "current_msv": VALID_SOUL["baseline_msv"],
    }
    with patch("main.ensure_avatar_record", new_callable=AsyncMock) as mock_ensure:
        mock_ensure.return_value = record
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            response = await ac.post(
                "/v1/avatars/ensure",
                json={"external_key": "test-planner", "soul": VALID_SOUL},
            )
        assert response.status_code == 200
        assert response.json()["id"] == record["id"]
        mock_ensure.assert_awaited_once()


@pytest.mark.asyncio
async def test_hybrid_prepare():
    bot_id = "123e4567-e89b-12d3-a456-426614174000"
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post(
            "/hybrid/prepare",
            json={
                "bot_id": bot_id,
                "query": "refund policy",
                "session_id": "sess-1",
                "top_k": 3,
            },
        )
    assert response.status_code == 200
    body = response.json()
    assert "system_prompt" in body
    assert "memories" in body
    assert "inner_monologue" in body


@pytest.mark.asyncio
async def test_hybrid_complete():
    bot_id = "123e4567-e89b-12d3-a456-426614174000"
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post(
            "/hybrid/complete",
            json={
                "bot_id": bot_id,
                "summary": "User asked about refunds",
                "user_message": "Can I get a refund?",
                "session_id": "sess-1",
                "reflect": False,
            },
        )
    assert response.status_code == 200
    assert response.json()["ingested"] is True


@pytest.mark.asyncio
async def test_memory_ingest_with_session_id():
    payload = {
        "bot_id": "123e4567-e89b-12d3-a456-426614174000",
        "content": "Prefers beach destinations",
        "session_id": "trip-abc",
    }
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post("/memory/ingest", json=payload)
    assert response.status_code == 200
