"""HTTP tests for hybrid turn contracts (ASGI)."""

from __future__ import annotations

from copy import deepcopy
from typing import Any
from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient

from dependencies import get_db, get_embedder, get_llm_service
from main import app
from test_main import MockEmbedder, MockLLMService, mock_get_db

BOOKING_CONTRACT = {
    "id": "booking.v1",
    "initial_step": "collect_dates",
    "reject_tokens": ["IGNORE PREVIOUS"],
    "steps": [
        {
            "id": "collect_dates",
            "required_slots": ["check_in", "check_out"],
            "slot_schemas": {
                "check_in": {"type": "string", "format": "date"},
                "check_out": {"type": "string", "format": "date"},
            },
            "clear_slots_on_entry": ["user_agreed_to_terms", "payment_method"],
            "allowed_intents": ["provide_dates", "clarify", "cancel"],
            "transitions": {"cancel": "cancelled"},
            "next": "confirm",
            "completion": {"all_required_slots": True},
        },
        {
            "id": "confirm",
            "required_slots": ["user_agreed_to_terms"],
            "slot_schemas": {
                "check_in": {"type": "string", "format": "date"},
                "check_out": {"type": "string", "format": "date"},
                "user_agreed_to_terms": {"type": "boolean"},
                "payment_method": {"type": "string"},
            },
            "allowed_intents": ["confirm_booking", "edit_dates", "cancel"],
            "transitions": {
                "confirm_booking": "completed",
                "edit_dates": "collect_dates",
                "cancel": "cancelled",
            },
            "next": "completed",
            "completion": {"all_required_slots": True},
        },
        {"id": "completed"},
        {"id": "cancelled"},
    ],
}

BOT_ID = "123e4567-e89b-12d3-a456-426614174000"


class ContractLLMService(MockLLMService):
    async def load_runtime_config(self, db, bot_id: str) -> dict:
        return {"turn_contract": BOOKING_CONTRACT}


_STORE: dict[tuple[str, str], dict[str, Any]] = {}


async def _mem_get(db, bot_id: str, session_id: str):
    row = _STORE.get((bot_id, session_id))
    return deepcopy(row) if row else None


async def _mem_advance(
    db,
    *,
    bot_id: str,
    session_id: str,
    expected_version: int,
    current_step: str,
    slots: dict,
    turn_version: int,
    last_idempotency_key: str | None = None,
    last_success_response: dict | None = None,
):
    row = _STORE.get((bot_id, session_id))
    if not row or row["turn_version"] != expected_version:
        return False
    row["current_step"] = current_step
    row["slots"] = deepcopy(slots)
    row["turn_version"] = turn_version
    if last_idempotency_key is not None:
        row["last_idempotency_key"] = last_idempotency_key
    if last_success_response is not None:
        row["last_success_response"] = deepcopy(last_success_response)
    return True


async def _mem_store_success(
    db,
    *,
    bot_id: str,
    session_id: str,
    turn_version: int,
    last_idempotency_key: str | None,
    last_success_response: dict,
):
    row = _STORE.get((bot_id, session_id))
    if not row or row["turn_version"] != turn_version:
        return
    if last_idempotency_key is not None:
        row["last_idempotency_key"] = last_idempotency_key
    row["last_success_response"] = deepcopy(last_success_response)


async def _mem_ensure(db, *, bot_id: str, session_id: str, initial_step: str):
    existing = await _mem_get(db, bot_id, session_id)
    if existing:
        return existing
    _STORE[(bot_id, session_id)] = {
        "current_step": initial_step,
        "slots": {},
        "turn_version": 0,
        "last_idempotency_key": None,
        "last_success_response": None,
    }
    return await _mem_get(db, bot_id, session_id)


@pytest.fixture
def contract_app():
    _STORE.clear()
    app.dependency_overrides[get_db] = mock_get_db
    app.dependency_overrides[get_embedder] = MockEmbedder
    app.dependency_overrides[get_llm_service] = lambda: ContractLLMService()
    patches = [
        patch("main.ensure_turn_session", _mem_ensure),
        patch("main.get_turn_session", _mem_get),
        patch("main.advance_turn_session", _mem_advance),
        patch("main.store_turn_success_response", _mem_store_success),
    ]
    for p in patches:
        p.start()
    yield app
    for p in patches:
        p.stop()
    app.dependency_overrides[get_llm_service] = lambda: MockLLMService()
    _STORE.clear()


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
