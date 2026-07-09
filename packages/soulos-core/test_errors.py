"""Tests for RFC 7807 Problem Details."""

import pytest
from httpx import AsyncClient, ASGITransport

from dependencies import get_db, get_embedder, get_llm_service
from main import app
from runtime.errors import (
    ACCESS_DENIED,
    BOT_NOT_FOUND,
    CLAWSOULS_IMPORT_DISABLED,
    INFERENCE_DOWN,
    MEMORY_DIM_MISMATCH,
    PROBLEM_CONTENT_TYPE,
    READY_DEGRADED,
    SOUL_INVALID,
    VALIDATION_ERROR,
    INTERNAL_ERROR,
    SoulOSProblem,
    _map_http_detail_to_code,
    problem_body,
    validation_exception_handler,
)
from test_main import MockEmbedder, MockLLMService, VALID_SOUL, mock_get_db

app.dependency_overrides[get_db] = mock_get_db
app.dependency_overrides[get_embedder] = MockEmbedder
app.dependency_overrides[get_llm_service] = lambda: MockLLMService()


def test_problem_body_shape():
    body = problem_body(BOT_NOT_FOUND, 404, "Bot not found")
    assert body["type"].endswith("bot-not-found")
    assert body["title"] == "Bot not found"
    assert body["status"] == 404
    assert body["detail"] == "Bot not found"
    assert body["code"] == BOT_NOT_FOUND


@pytest.mark.asyncio
async def test_hybrid_prepare_bot_not_found_problem():
    from unittest.mock import AsyncMock, patch

    with patch("main.fetch_bot_identity", new_callable=AsyncMock, return_value=None):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            response = await ac.post(
                "/hybrid/prepare",
                json={
                    "bot_id": "00000000-0000-0000-0000-000000000000",
                    "query": "test",
                },
            )
    assert response.status_code == 404
    assert PROBLEM_CONTENT_TYPE in response.headers.get("content-type", "")
    body = response.json()
    assert body["code"] == BOT_NOT_FOUND
    assert "title" in body
    assert "detail" in body


@pytest.mark.asyncio
async def test_invalid_soul_registration_problem():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post(
            "/v1/avatars",
            json={"name": "bad"},
        )
    assert response.status_code == 422
    assert PROBLEM_CONTENT_TYPE in response.headers.get("content-type", "")
    body = response.json()
    assert body["code"] in (SOUL_INVALID, "VALIDATION_ERROR")
    assert "title" in body


@pytest.mark.asyncio
async def test_ready_degraded_problem():
    from unittest.mock import AsyncMock, patch

    with patch(
        "runtime.readiness.check_inference",
        new_callable=AsyncMock,
        return_value=False,
    ):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            response = await ac.get("/ready")
    assert response.status_code == 503
    body = response.json()
    assert body["code"] == READY_DEGRADED
    assert PROBLEM_CONTENT_TYPE in response.headers.get("content-type", "")


@pytest.mark.asyncio
async def test_clawsouls_import_disabled_problem():
    from unittest.mock import patch

    with patch("main.import_enabled", return_value=False):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            response = await ac.post(
                "/v1/avatars/import-clawsouls",
                json={"owner": "test", "name": "bot", "persist": False},
            )
    assert response.status_code == 403
    body = response.json()
    assert body["code"] == CLAWSOULS_IMPORT_DISABLED


def test_soulos_problem_exception_fields():
    exc = SoulOSProblem(ACCESS_DENIED, 403, "Access denied")
    assert exc.code == ACCESS_DENIED
    assert exc.status == 403


def test_map_http_detail_to_code_branches():
    assert _map_http_detail_to_code(404, "Bot not found: x") == BOT_NOT_FOUND
    assert _map_http_detail_to_code(403, "Access denied") == ACCESS_DENIED
    assert _map_http_detail_to_code(403, "ClawSouls import disabled") == CLAWSOULS_IMPORT_DISABLED
    assert _map_http_detail_to_code(422, "Soul validation failed") == SOUL_INVALID
    assert _map_http_detail_to_code(422, "field required") == VALIDATION_ERROR
    assert _map_http_detail_to_code(500, "embedding service down") == INFERENCE_DOWN
    assert _map_http_detail_to_code(401, "Unauthorized") == ACCESS_DENIED
    assert _map_http_detail_to_code(500, "unexpected") == INTERNAL_ERROR


@pytest.mark.asyncio
async def test_validation_exception_handler_shape():
    from fastapi.exceptions import RequestValidationError

    exc = RequestValidationError(
        [{"loc": ("body", "bot_id"), "msg": "field required", "type": "missing"}]
    )
    response = await validation_exception_handler(None, exc)
    assert response.status_code == 422
    body = response.body.decode()
    assert VALIDATION_ERROR in body
    assert PROBLEM_CONTENT_TYPE in response.media_type


@pytest.mark.asyncio
async def test_memory_forget_missing_field_problem():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post(
            "/memory/forget",
            json={"bot_id": "123e4567-e89b-12d3-a456-426614174000"},
        )
    assert response.status_code == 422
    assert PROBLEM_CONTENT_TYPE in response.headers.get("content-type", "")
    assert response.json()["code"] == VALIDATION_ERROR
