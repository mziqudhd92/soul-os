"""Unit tests for session memory TTL helpers."""

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

import pytest

import runtime.memory as memory_mod
from runtime.memory import (
    purge_expired_session_memories,
    session_ttl_cutoff,
)


def test_session_ttl_cutoff_disabled(monkeypatch):
    monkeypatch.setattr(memory_mod, "MEMORY_SESSION_TTL_SECONDS", 0)
    assert session_ttl_cutoff() is None


def test_session_ttl_cutoff_enabled(monkeypatch):
    monkeypatch.setattr(memory_mod, "MEMORY_SESSION_TTL_SECONDS", 3600)
    cutoff = session_ttl_cutoff()
    assert cutoff is not None
    assert cutoff < datetime.now(timezone.utc)
    assert cutoff > datetime.now(timezone.utc) - timedelta(hours=2)


@pytest.mark.asyncio
async def test_purge_expired_noop_when_ttl_disabled(monkeypatch):
    monkeypatch.setattr(memory_mod, "MEMORY_SESSION_TTL_SECONDS", 0)
    db = MagicMock()
    assert await purge_expired_session_memories(db) == 0
    db.execute.assert_not_called()


@pytest.mark.asyncio
async def test_purge_expired_deletes_session_rows(monkeypatch):
    monkeypatch.setattr(memory_mod, "MEMORY_SESSION_TTL_SECONDS", 60)
    db = MagicMock()

    async def fake_execute(query, params=None):
        return type("R", (), {"rowcount": 4})()

    db.execute = fake_execute
    deleted = await purge_expired_session_memories(db, bot_id="bot-1")
    assert deleted == 4
