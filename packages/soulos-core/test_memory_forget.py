"""Unit tests for memory forget and session delete helpers."""

import pytest

from runtime.memory import delete_session_memories, forget_memory


class MemoryDeleteConnection:
    """Tracks DELETE calls and returns configurable rowcount."""

    rowcount = 2

    def __init__(self) -> None:
        self.deletes: list[tuple[str, dict | None]] = []

    async def execute(self, query, params=None):
        q = str(query)
        if "DELETE FROM episodic_memories" in q:
            self.deletes.append((q, params))
            return type("DeleteResult", (), {"rowcount": self.rowcount})()
        raise AssertionError(f"unexpected query: {q}")


@pytest.mark.asyncio
async def test_forget_memory_uses_ilike_pattern():
    conn = MemoryDeleteConnection()
    conn.rowcount = 3
    deleted = await forget_memory(conn, "bot-1", "refund")
    assert deleted == 3
    assert len(conn.deletes) == 1
    assert conn.deletes[0][1]["pattern"] == "%refund%"
    assert conn.deletes[0][1]["bot_id"] == "bot-1"


@pytest.mark.asyncio
async def test_forget_memory_zero_rows():
    conn = MemoryDeleteConnection()
    conn.rowcount = 0
    deleted = await forget_memory(conn, "bot-1", "missing")
    assert deleted == 0


@pytest.mark.asyncio
async def test_delete_session_memories():
    conn = MemoryDeleteConnection()
    conn.rowcount = 5
    deleted = await delete_session_memories(conn, "bot-1", "sess-abc")
    assert deleted == 5
    assert conn.deletes[0][1]["session_id"] == "sess-abc"
    assert conn.deletes[0][1]["bot_id"] == "bot-1"
