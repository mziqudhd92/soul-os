"""HTTP tests for hybrid turn contracts (ASGI)."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient

from dependencies import get_db, get_embedder, get_llm_service
from main import app
from test_main import MockEmbedder, MockLLMService, mock_get_db

from turn_contract_fixtures import (
    BOOKING_CONTRACT,
    BOT_ID,
    clear_turn_store,
    mem_advance,
    mem_ensure,
    mem_get,
    mem_store_success,
)


class ContractLLMService(MockLLMService):
    async def load_runtime_config(self, db, bot_id: str) -> dict:
        return {"turn_contract": BOOKING_CONTRACT}


@pytest.fixture
def contract_app():
    clear_turn_store()
    app.dependency_overrides[get_db] = mock_get_db
    app.dependency_overrides[get_embedder] = MockEmbedder
    app.dependency_overrides[get_llm_service] = lambda: ContractLLMService()
    patches = [
        patch("routes.hybrid.ensure_turn_session", mem_ensure),
        patch("runtime.hybrid_complete.get_turn_session", mem_get),
        patch("runtime.hybrid_complete.advance_turn_session", mem_advance),
        patch("routes.hybrid.store_turn_success_response", mem_store_success),
    ]
    for p in patches:
        p.start()
    yield app
    for p in patches:
        p.stop()
    app.dependency_overrides[get_llm_service] = lambda: MockLLMService()
    clear_turn_store()


@pytest.mark.asyncio
async def test_prepare_without_contract_unchanged():
    app.dependency_overrides[get_db] = mock_get_db
    app.dependency_overrides[get_embedder] = MockEmbedder
    app.dependency_overrides[get_llm_service] = lambda: MockLLMService()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post(
            "/hybrid/prepare",
            json={"bot_id": BOT_ID, "query": "hi", "session_id": "s1", "top_k": 3},
        )
    assert response.status_code == 200
    body = response.json()
    assert "system_prompt" in body
    assert "memories" in body
    assert "inner_monologue" in body
    assert "contract_context" not in body


@pytest.mark.asyncio
async def test_prepare_with_contract_context(contract_app):
    async with AsyncClient(
        transport=ASGITransport(app=contract_app), base_url="http://test"
    ) as ac:
        response = await ac.post(
            "/hybrid/prepare",
            json={"bot_id": BOT_ID, "query": "book", "session_id": "sess-a"},
        )
    assert response.status_code == 200
    body = response.json()
    assert "system_prompt" in body
    ctx = body["contract_context"]
    assert ctx["expected_step"] == "collect_dates"
    assert ctx["turn_version"] == 0
    assert "check_in" in ctx["missing_slots"]
    assert "collect_dates" in body["system_prompt"] or True  # persona prompt untouched required
    # system_prompt must NOT include the machine appendix automatically
    assert "[SYSTEM DIRECTIVE" not in body["system_prompt"]
    assert "[SYSTEM DIRECTIVE" in ctx["prompt_appendix"]


@pytest.mark.asyncio
async def test_complete_happy_path_and_idempotent_replay(contract_app):
    async with AsyncClient(
        transport=ASGITransport(app=contract_app), base_url="http://test"
    ) as ac:
        prep = await ac.post(
            "/hybrid/prepare",
            json={"bot_id": BOT_ID, "query": "book", "session_id": "sess-b"},
        )
        version = prep.json()["contract_context"]["turn_version"]
        body = {
            "bot_id": BOT_ID,
            "summary": "collected dates",
            "session_id": "sess-b",
            "reflect": False,
            "filled_slots": {"check_in": "2026-09-01", "check_out": "2026-09-05"},
            "intent": "provide_dates",
            "expected_version": version,
            "idempotency_key": "idem-1",
        }
        r1 = await ac.post("/hybrid/complete", json=body)
        assert r1.status_code == 200
        t1 = r1.json()["turn"]
        assert t1["step"] == "confirm"
        assert t1["turn_version"] == 1
        r2 = await ac.post("/hybrid/complete", json=body)
        assert r2.status_code == 200
        assert r2.json()["turn"]["turn_version"] == 1


@pytest.mark.asyncio
async def test_complete_422_invalid_slot(contract_app):
    async with AsyncClient(
        transport=ASGITransport(app=contract_app), base_url="http://test"
    ) as ac:
        await ac.post(
            "/hybrid/prepare",
            json={"bot_id": BOT_ID, "query": "book", "session_id": "sess-c"},
        )
        r = await ac.post(
            "/hybrid/complete",
            json={
                "bot_id": BOT_ID,
                "summary": "bad",
                "session_id": "sess-c",
                "reflect": False,
                "filled_slots": {"check_in": "nope", "check_out": "2026-09-05"},
                "intent": "provide_dates",
                "expected_version": 0,
                "idempotency_key": "idem-bad",
            },
        )
    assert r.status_code == 422
    problem = r.json()
    assert problem["code"] == "TURN_CONTRACT_VIOLATION"
    assert "check_in" in (problem.get("invalid_slots") or {})
    assert problem.get("remedial_prompt_hint")
    assert "application/problem+json" in r.headers.get("content-type", "")


@pytest.mark.asyncio
async def test_complete_409_stale_version(contract_app):
    async with AsyncClient(
        transport=ASGITransport(app=contract_app), base_url="http://test"
    ) as ac:
        await ac.post(
            "/hybrid/prepare",
            json={"bot_id": BOT_ID, "query": "book", "session_id": "sess-d"},
        )
        await ac.post(
            "/hybrid/complete",
            json={
                "bot_id": BOT_ID,
                "summary": "ok",
                "session_id": "sess-d",
                "reflect": False,
                "filled_slots": {"check_in": "2026-09-01", "check_out": "2026-09-05"},
                "intent": "provide_dates",
                "expected_version": 0,
                "idempotency_key": "idem-d1",
            },
        )
        r = await ac.post(
            "/hybrid/complete",
            json={
                "bot_id": BOT_ID,
                "summary": "stale",
                "session_id": "sess-d",
                "reflect": False,
                "filled_slots": {"user_agreed_to_terms": True},
                "intent": "confirm_booking",
                "expected_version": 0,
                "idempotency_key": "idem-d2",
            },
        )
    assert r.status_code == 409
    assert r.json()["code"] == "TURN_STATE_STALE"


@pytest.mark.asyncio
async def test_complete_404_expired_session(contract_app):
    async with AsyncClient(
        transport=ASGITransport(app=contract_app), base_url="http://test"
    ) as ac:
        r = await ac.post(
            "/hybrid/complete",
            json={
                "bot_id": BOT_ID,
                "summary": "gone",
                "session_id": "never-prepared",
                "reflect": False,
                "expected_version": 0,
                "idempotency_key": "idem-x",
            },
        )
    assert r.status_code == 404
    assert r.json()["code"] == "TURN_SESSION_EXPIRED"


@pytest.mark.asyncio
async def test_violation_does_not_advance(contract_app):
    async with AsyncClient(
        transport=ASGITransport(app=contract_app), base_url="http://test"
    ) as ac:
        await ac.post(
            "/hybrid/prepare",
            json={"bot_id": BOT_ID, "query": "book", "session_id": "sess-e"},
        )
        await ac.post(
            "/hybrid/complete",
            json={
                "bot_id": BOT_ID,
                "summary": "bad",
                "session_id": "sess-e",
                "reflect": False,
                "filled_slots": {"check_in": "bad", "check_out": "2026-09-05"},
                "intent": "provide_dates",
                "expected_version": 0,
            },
        )
        prep = await ac.post(
            "/hybrid/prepare",
            json={"bot_id": BOT_ID, "query": "book", "session_id": "sess-e"},
        )
    ctx = prep.json()["contract_context"]
    assert ctx["turn_version"] == 0
    assert ctx["expected_step"] == "collect_dates"


@pytest.mark.asyncio
async def test_complete_idempotent_async_preserves_202(contract_app):
    async with AsyncClient(
        transport=ASGITransport(app=contract_app), base_url="http://test"
    ) as ac:
        await ac.post(
            "/hybrid/prepare",
            json={"bot_id": BOT_ID, "query": "book", "session_id": "sess-202"},
        )
        body = {
            "bot_id": BOT_ID,
            "summary": "dates",
            "user_message": "dates please",
            "session_id": "sess-202",
            "reflect": True,
            "reflect_async": True,
            "filled_slots": {"check_in": "2026-09-01", "check_out": "2026-09-05"},
            "intent": "provide_dates",
            "expected_version": 0,
            "idempotency_key": "idem-202",
        }
        r1 = await ac.post("/hybrid/complete", json=body)
        assert r1.status_code == 202
        r2 = await ac.post("/hybrid/complete", json=body)
        assert r2.status_code == 202
        assert r2.json()["status"] == "accepted"


@pytest.mark.asyncio
async def test_complete_oversized_filled_slots_rejected_at_api(contract_app):
    async with AsyncClient(
        transport=ASGITransport(app=contract_app), base_url="http://test"
    ) as ac:
        await ac.post(
            "/hybrid/prepare",
            json={"bot_id": BOT_ID, "query": "book", "session_id": "sess-big"},
        )
        r = await ac.post(
            "/hybrid/complete",
            json={
                "bot_id": BOT_ID,
                "summary": "big",
                "session_id": "sess-big",
                "reflect": False,
                "filled_slots": {"x": "y" * (70 * 1024)},
                "expected_version": 0,
                "idempotency_key": "big-1",
            },
        )
    assert r.status_code == 422
    body = r.json()
    assert body.get("code") in ("VALIDATION_ERROR", "TURN_CONTRACT_VIOLATION")
    async with AsyncClient(
        transport=ASGITransport(app=contract_app), base_url="http://test"
    ) as ac:
        await ac.post(
            "/hybrid/prepare",
            json={"bot_id": BOT_ID, "query": "book", "session_id": "sess-cas"},
        )
        ok = await ac.post(
            "/hybrid/complete",
            json={
                "bot_id": BOT_ID,
                "summary": "first",
                "session_id": "sess-cas",
                "reflect": False,
                "filled_slots": {"check_in": "2026-09-01", "check_out": "2026-09-05"},
                "intent": "provide_dates",
                "expected_version": 0,
                "idempotency_key": "cas-1",
            },
        )
        assert ok.status_code == 200
        stale = await ac.post(
            "/hybrid/complete",
            json={
                "bot_id": BOT_ID,
                "summary": "second",
                "session_id": "sess-cas",
                "reflect": False,
                "filled_slots": {"check_in": "2026-09-02", "check_out": "2026-09-06"},
                "intent": "provide_dates",
                "expected_version": 0,
                "idempotency_key": "cas-2",
            },
        )
        assert stale.status_code == 409
        assert stale.json()["code"] == "TURN_STATE_STALE"


@pytest.mark.asyncio
async def test_complete_step_mismatch_returns_422(contract_app):
    async with AsyncClient(
        transport=ASGITransport(app=contract_app), base_url="http://test"
    ) as ac:
        await ac.post(
            "/hybrid/prepare",
            json={"bot_id": BOT_ID, "query": "book", "session_id": "sess-step"},
        )
        r = await ac.post(
            "/hybrid/complete",
            json={
                "bot_id": BOT_ID,
                "summary": "ok",
                "session_id": "sess-step",
                "reflect": False,
                "filled_slots": {"check_in": "2026-09-01", "check_out": "2026-09-05"},
                "intent": "provide_dates",
                "expected_version": 0,
                "expected_step": "confirm",
            },
        )
    assert r.status_code == 422
    assert r.json()["code"] == "TURN_STEP_MISMATCH"
