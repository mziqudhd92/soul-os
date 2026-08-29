"""Unit tests for turn_session TTL purge helpers."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

import runtime.turn_session as turn_mod
from runtime.turn_session import get_turn_session, purge_expired_turn_sessions


@pytest.mark.asyncio
async def test_purge_turn_sessions_noop_when_ttl_disabled(monkeypatch):
    monkeypatch.setattr(turn_mod, "MEMORY_SESSION_TTL_SECONDS", 0)
    db = AsyncMock()
    assert await purge_expired_turn_sessions(db) == 0
    db.execute.assert_not_called()


@pytest.mark.asyncio
async def test_purge_turn_sessions_deletes(monkeypatch):
    monkeypatch.setattr(turn_mod, "MEMORY_SESSION_TTL_SECONDS", 60)
    monkeypatch.setattr(
        turn_mod,
        "session_ttl_cutoff",
        lambda: datetime.now(timezone.utc) - timedelta(seconds=60),
    )
    db = AsyncMock()
    result = MagicMock()
    result.rowcount = 3
    db.execute = AsyncMock(return_value=result)
    deleted = await purge_expired_turn_sessions(db, bot_id="bot-1")
    assert deleted == 3
    db.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_turn_session_lazy_expires(monkeypatch):
    monkeypatch.setattr(
        turn_mod,
        "session_ttl_cutoff",
        lambda: datetime.now(timezone.utc),
    )
    old = datetime.now(timezone.utc) - timedelta(hours=2)
    row = MagicMock()
    row.current_step = "collect_dates"
    row.slots = {}
    row.turn_version = 1
    row.last_idempotency_key = None
    row.last_success_response = None
    row.updated_at = old

    result = MagicMock()
    result.fetchone = MagicMock(return_value=row)
    db = AsyncMock()
    db.execute = AsyncMock(return_value=result)

    deleted = AsyncMock(return_value=1)
    monkeypatch.setattr(turn_mod, "delete_turn_session", deleted)

    out = await get_turn_session(db, "bot-1", "sess-1")
    assert out is None
    deleted.assert_awaited_once()


@pytest.mark.asyncio
async def test_ensure_turn_session_conflict_does_not_reset(monkeypatch):
    """Second insert must DO NOTHING and re-read the advanced row."""
    calls = {"n": 0}
    advanced = {
        "current_step": "confirm",
        "slots": {"check_in": "2026-09-01"},
        "turn_version": 2,
        "last_idempotency_key": None,
        "last_success_response": None,
    }

    async def fake_get(db, bot_id, session_id):
        calls["n"] += 1
        if calls["n"] == 1:
            return None
        return dict(advanced)

    monkeypatch.setattr(turn_mod, "get_turn_session", fake_get)
    db = AsyncMock()
    db.execute = AsyncMock(return_value=MagicMock())
    out = await turn_mod.ensure_turn_session(
        db, bot_id="bot-1", session_id="s1", initial_step="collect_dates"
    )
    assert out["turn_version"] == 2
    assert out["current_step"] == "confirm"
    sql = str(db.execute.await_args.args[0])
    assert "DO NOTHING" in sql
