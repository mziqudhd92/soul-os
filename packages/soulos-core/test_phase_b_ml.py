"""HTTP + unit coverage for Phase B routes and ML helpers."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from dependencies import get_db, get_embedder, get_llm_service
from main import app
from runtime.capability_query import (
    invalidate_capability_cache,
    list_avatars_by_capability,
)
from runtime.conversation_memory import normalize_conversation_id, parse_tenant_uuid
from runtime.dual_process import (
    DualProcessFeatures,
    decide_reflect,
    estimate_query_complex,
    log_router_decision_async,
    should_run_system_2,
    system2_max_loops,
    uncertainty_trigger,
)
from runtime.hybrid import apply_memory_budgets
from runtime.memory_consolidate import consolidate_memories, extractive_summary
from runtime.memory_rank import MemoryHit, hit_contents
from runtime.trait_directives import compile_trait_directives
from soul_validation import default_msv_dict

BOT_A = "123e4567-e89b-12d3-a456-426614174000"
BOT_B = "123e4567-e89b-12d3-a456-426614174001"


class _Conn:
    async def execute(self, query, params=None):
        class _R:
            def fetchone(self):
                return None

            def fetchall(self):
                return []

        return _R()

    async def commit(self):
        pass


async def _db():
    yield _Conn()


class _Embedder:
    async def get_embedding(self, text: str):
        return [0.1] * 8


@pytest.fixture(autouse=True)
def _overrides():
    app.dependency_overrides[get_db] = _db
    app.dependency_overrides[get_embedder] = _Embedder
    app.dependency_overrides[get_llm_service] = lambda: object()
    yield


def test_normalize_conversation_id():
    assert normalize_conversation_id("t1") == "conv:t1"
    assert normalize_conversation_id("conv:t1") == "conv:t1"
    with pytest.raises(ValueError):
        normalize_conversation_id("  ")


def test_parse_tenant_uuid():
    assert parse_tenant_uuid(None) is None
    assert parse_tenant_uuid("not-a-uuid") is None
    assert parse_tenant_uuid(BOT_A) == BOT_A


def test_apply_memory_budgets_fills_top_k():
    out = apply_memory_budgets(
        ["e1", "e2", "e3"],
        ["s1", "s2"],
        ["m1"],
        top_k=5,
        budget_episodic=0.4,
        budget_shared=0.4,
        budget_semantic=0.2,
    )
    assert len(out) == 5
    assert apply_memory_budgets([], [], [], top_k=3) == []
    assert apply_memory_budgets(["a"], [], [], top_k=0) == []


def test_extractive_summary_and_hit_contents():
    text = extractive_summary(["a", "b" * 2000], max_chars=80)
    assert text.startswith("[SoulOS semantic summary]")
    assert text.endswith("…")
    assert hit_contents([MemoryHit(content="x")]) == ["x"]


def test_estimate_query_complex_and_triggers():
    assert estimate_query_complex("x" * 200) is True
    assert estimate_query_complex("a? b?") is True
    assert estimate_query_complex("a, b, c, d") is True
    assert estimate_query_complex("short") is False
    assert uncertainty_trigger({"dual_process": {"uncertainty_trigger": 0.55}}) == 0.55
    assert uncertainty_trigger({"dual_process": {"uncertainty_trigger": "bad"}}) > 0
    assert system2_max_loops({"dual_process": {"system2_max_loops": 5}}) == 5
    assert system2_max_loops({"dual_process": {"system2_max_loops": "x"}}) == 3
    assert system2_max_loops({}) == 3


def test_decide_reflect_and_async_log(tmp_path, monkeypatch):
    log_path = tmp_path / "router.jsonl"
    import runtime.dual_process as dp

    monkeypatch.setattr(dp, "SOULOS_ROUTER_LOG_PATH", str(log_path))
    monkeypatch.setattr(dp, "_router_queue", None)
    monkeypatch.setattr(dp, "_router_worker_started", False)

    msv = default_msv_dict()
    msv["epistemic_uncertainty"] = 0.85
    run, features = decide_reflect(msv, {}, query="hello?", bot_id="b1")
    assert run is True
    assert isinstance(features, DualProcessFeatures)
    log_router_decision_async(features, run_system_2=True, threshold=0.35, bot_id="b1")
    assert should_run_system_2(
        DualProcessFeatures(confidence=0.2, contract_incomplete=True),
        threshold=0.9,
    )


def test_compile_trait_directives_handles_bad_values():
    out = compile_trait_directives({"hexaco": {"H": "bad"}, "epistemic_uncertainty": "x"})
    assert "-" in out
    assert compile_trait_directives(None) == ""


@pytest.mark.asyncio
async def test_capability_query_cache():
    invalidate_capability_cache()

    class _Row:
        def __init__(self):
            self.id = "1"
            self.name = "A"
            self.role = "r"
            self.capabilities = ["billing"]

    class _Result:
        def fetchall(self):
            return [_Row()]

    class _Db:
        async def execute(self, *a, **k):
            return _Result()

    rows = await list_avatars_by_capability(_Db(), "Billing", tenant_id=None)
    assert rows[0]["name"] == "A"
    rows2 = await list_avatars_by_capability(_Db(), "billing", tenant_id=None)
    assert rows2 == rows
    assert await list_avatars_by_capability(_Db(), "  ", tenant_id=None) == []
    invalidate_capability_cache()


@pytest.mark.asyncio
async def test_conversation_memory_and_handoff_routes():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        with patch(
            "routes.conversations.ingest_conversation_memory",
            new_callable=AsyncMock,
            return_value="mem-1",
        ):
            r = await ac.post(
                "/v1/conversations/thread-9/memory",
                json={"content": "shared fact", "importance": 0.7},
            )
        assert r.status_code == 200
        assert r.json()["id"] == "mem-1"

        with patch(
            "routes.conversations.retrieve_conversation_memories",
            new_callable=AsyncMock,
            return_value=["shared fact"],
        ):
            r2 = await ac.post(
                "/v1/conversations/thread-9/memory/retrieve",
                json={"query": "fact", "top_k": 3},
            )
        assert r2.status_code == 200
        assert r2.json()["memories"] == ["shared fact"]

        with patch(
            "routes.conversations.retrieve_conversation_memory_hits",
            new_callable=AsyncMock,
            return_value=[MemoryHit(content="scored", id="1", rrf_score=0.5)],
        ):
            r3 = await ac.post(
                "/v1/conversations/thread-9/memory/retrieve",
                json={"query": "fact", "include_scores": True},
            )
        assert r3.status_code == 200
        assert "hits" in r3.json()

        with (
            patch("routes.handoffs.verify_bot_access", new_callable=AsyncMock),
            patch(
                "routes.handoffs.ingest_memory_record", new_callable=AsyncMock
            ),
            patch(
                "routes.handoffs.ingest_conversation_memory",
                new_callable=AsyncMock,
                return_value="shared-1",
            ),
            patch(
                "routes.handoffs._load_idempotent",
                new_callable=AsyncMock,
                return_value=None,
            ),
            patch(
                "routes.handoffs._store_idempotent", new_callable=AsyncMock
            ),
        ):
            h = await ac.post(
                "/v1/handoffs",
                json={
                    "from_bot_id": BOT_A,
                    "to_bot_id": BOT_B,
                    "from_role": "customer",
                    "to_role": "inventory",
                    "conversation_id": "thread-9",
                    "reason": "stock",
                    "summary": "SKU-1",
                    "idempotency_key": "k1",
                    "user_message": "need stock",
                    "payload": {"sku": "1"},
                },
            )
        assert h.status_code == 200
        body = h.json()
        assert body["shared_memory_id"] == "shared-1"
        assert body["session_id"].startswith("conv:")


@pytest.mark.asyncio
async def test_handoff_idempotent_replay():
    cached = {"status": "success", "session_id": "conv:t", "note": "n"}
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        with (
            patch("routes.handoffs.verify_bot_access", new_callable=AsyncMock),
            patch(
                "routes.handoffs._load_idempotent",
                new_callable=AsyncMock,
                return_value=cached,
            ),
        ):
            h = await ac.post(
                "/v1/handoffs",
                json={
                    "from_bot_id": BOT_A,
                    "to_bot_id": BOT_B,
                    "from_role": "a",
                    "to_role": "b",
                    "conversation_id": "t",
                    "reason": "r",
                    "summary": "s",
                    "idempotency_key": "same",
                },
            )
    assert h.status_code == 200
    assert h.json() == cached


@pytest.mark.asyncio
async def test_capability_and_consolidate_routes():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        with patch(
            "routes.avatars.list_avatars_by_capability",
            new_callable=AsyncMock,
            return_value=[
                {"id": "1", "name": "Bot", "role": "r", "capabilities": ["x"]}
            ],
        ):
            r = await ac.get("/v1/avatars/by-capability/x")
        assert r.status_code == 200
        assert r.json()["total"] == 1

        with (
            patch("routes.memory.verify_bot_access", new_callable=AsyncMock),
            patch(
                "routes.memory.consolidate_memories",
                new_callable=AsyncMock,
                return_value={
                    "status": "success",
                    "semantic_id": "s1",
                    "source_memory_ids": ["a", "b"],
                    "consolidated": 2,
                    "time_range_start": datetime.now(UTC).isoformat(),
                    "time_range_end": datetime.now(UTC).isoformat(),
                },
            ),
        ):
            c = await ac.post(
                "/memory/consolidate",
                json={"bot_id": BOT_A, "limit": 4},
            )
        assert c.status_code == 200
        assert c.json()["consolidated"] == 2


@pytest.mark.asyncio
async def test_retrieve_include_scores():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        with (
            patch("routes.memory.verify_bot_access", new_callable=AsyncMock),
            patch(
                "routes.memory.retrieve_memory_hits",
                new_callable=AsyncMock,
                return_value=[
                    MemoryHit(
                        content="m", id="1", dense_distance=0.1, rrf_score=0.2
                    )
                ],
            ),
        ):
            r = await ac.post(
                "/memory/retrieve",
                json={
                    "bot_id": BOT_A,
                    "query": "q",
                    "include_scores": True,
                },
            )
        assert r.status_code == 200
        assert r.json()["hits"][0]["content"] == "m"


@pytest.mark.asyncio
async def test_consolidate_memories_logic():
    class Row:
        def __init__(self, i):
            self.id = f"00000000-0000-0000-0000-00000000000{i}"
            self.content = f"fact {i}"
            self.created_at = datetime(2026, 1, i, tzinfo=UTC)
            self.importance = 0.2

    class Result:
        def __init__(self, rows=None, one=None):
            self._rows = rows or []
            self._one = one

        def fetchall(self):
            return self._rows

        def fetchone(self):
            return self._one

    class Conn:
        async def execute(self, query, params=None):
            q = str(query)
            if "FOR UPDATE" in q:
                return Result(rows=[Row(1), Row(2)])
            if "RETURNING" in q:
                return Result(one=type("R", (), {"id": "sem-1"})())
            return Result()

    emb = AsyncMock()
    emb.get_embedding = AsyncMock(return_value=[0.1] * 8)
    out = await consolidate_memories(Conn(), emb, "bot-1", limit=4)
    assert out["status"] == "success"
    assert out["semantic_id"] == "sem-1"
    assert len(out["source_memory_ids"]) == 2

    class ConnEmpty:
        async def execute(self, query, params=None):
            return Result(rows=[Row(1)])

    empty = await consolidate_memories(ConnEmpty(), emb, "bot-1", limit=4)
    assert empty["status"] == "noop"


@pytest.mark.asyncio
async def test_conversation_memory_ingest_and_retrieve():
    from runtime.conversation_memory import (
        _parse_embedding,
        ingest_conversation_memory,
        retrieve_conversation_memories,
        retrieve_conversation_memory_hits,
    )

    assert _parse_embedding(None) is None
    assert _parse_embedding([1, 2]) == [1.0, 2.0]
    assert _parse_embedding("[0.1, 0.2]") == [0.1, 0.2]
    assert _parse_embedding("[]") is None
    assert _parse_embedding("nope") is None
    assert _parse_embedding(123) is None

    class Row:
        def __init__(self):
            self.id = "m1"
            self.content = "shared note"
            self.distance = 0.05
            self.importance = 0.8
            self.embedding_text = "[0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8]"
            self.rank = 0.9

    class Conn:
        def __init__(self):
            self.calls = 0

        async def execute(self, query, params=None):
            self.calls += 1
            q = str(query)

            class R:
                def fetchone(self_inner):
                    return type("X", (), {"id": "new-id"})()

                def fetchall(self_inner):
                    if "ts_rank" in q:
                        return [Row()]
                    if "<->" in q or "distance" in q.lower() or "ORDER BY distance" in q:
                        return [Row()]
                    return [Row()]

            return R()

    emb = AsyncMock()
    emb.get_embedding = AsyncMock(return_value=[0.1] * 8)

    mid = await ingest_conversation_memory(
        Conn(), emb, "t1", "hello", tenant_id=BOT_A, source_bot_id=BOT_B
    )
    assert mid == "new-id"
    mid2 = await ingest_conversation_memory(
        Conn(), emb, "t1", "hello", source_bot_id=BOT_B
    )
    assert mid2 == "new-id"
    mid3 = await ingest_conversation_memory(Conn(), emb, "t1", "hello")
    assert mid3 == "new-id"

    hits = await retrieve_conversation_memory_hits(
        Conn(), emb, "t1", "shared note query", top_k=3, tenant_id=BOT_A
    )
    assert hits
    mems = await retrieve_conversation_memories(Conn(), emb, "t1", "shared", top_k=2)
    assert isinstance(mems, list)


@pytest.mark.asyncio
async def test_handoff_idempotency_helpers():
    import json

    from routes.handoffs import _load_idempotent, _store_idempotent, format_handoff_note

    note = format_handoff_note(
        from_role="a",
        to_role="b",
        conversation_id="conv:t",
        reason="r",
        summary="s",
        payload={"x": 1},
    )
    assert "SoulOS handoff" in note
    assert "payload:" in note

    class Conn:
        def __init__(self, row=None):
            self.row = row
            self.stored = None

        async def execute(self, query, params=None):
            self.stored = params

            class R:
                def __init__(self, row):
                    self._row = row

                def fetchone(self_inner):
                    return self_inner._row

            return R(self.row)

    assert await _load_idempotent(Conn(), None, "k") is None
    cached = await _load_idempotent(
        Conn(row=type("R", (), {"response": {"ok": True}})()),
        None,
        "k",
    )
    assert cached == {"ok": True}
    cached2 = await _load_idempotent(
        Conn(row=type("R", (), {"response": json.dumps({"a": 1})})()),
        BOT_A,
        "k",
    )
    assert cached2 == {"a": 1}
    await _store_idempotent(Conn(), None, "k", {"status": "ok"})
    await _store_idempotent(Conn(), BOT_A, "k", {"status": "ok"})


@pytest.mark.asyncio
async def test_dual_process_router_worker(tmp_path, monkeypatch):
    import asyncio

    import runtime.dual_process as dp
    from runtime.dual_process import DualProcessFeatures, score_system1

    assert score_system1(
        DualProcessFeatures(
            confidence=0.8,
            retrieval_weak=True,
            query_complex=True,
            contract_incomplete=True,
        )
    ) < 0.8

    log_path = tmp_path / "subdir" / "router.jsonl"
    monkeypatch.setattr(dp, "SOULOS_ROUTER_LOG_PATH", str(log_path))
    monkeypatch.setattr(dp, "_router_queue", None)
    monkeypatch.setattr(dp, "_router_worker_started", False)

    q = dp._ensure_router_worker()
    assert q is not None
    features = DualProcessFeatures(confidence=0.5)
    dp.log_router_decision_async(
        features, run_system_2=False, threshold=0.3, bot_id="b", extra={"x": 1}
    )
    await asyncio.sleep(0.15)
    assert log_path.exists()
