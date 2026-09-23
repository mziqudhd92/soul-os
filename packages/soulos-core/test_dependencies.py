"""Unit tests for FastAPI dependencies."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import dependencies
from runtime.embedder import Embedder
from runtime.pipeline import ChatPipeline


@pytest.mark.asyncio
async def test_get_db_commits_on_success():
    conn = AsyncMock()
    conn.commit = AsyncMock()
    conn.rollback = AsyncMock()
    connect_cm = MagicMock()
    connect_cm.__aenter__ = AsyncMock(return_value=conn)
    connect_cm.__aexit__ = AsyncMock(return_value=False)

    with patch.object(dependencies, "engine") as engine:
        engine.connect.return_value = connect_cm
        gen = dependencies.get_db()
        yielded = await gen.__anext__()
        assert yielded is conn
        try:
            await gen.__anext__()
        except StopAsyncIteration:
            pass

    conn.commit.assert_awaited_once()
    conn.rollback.assert_not_awaited()


@pytest.mark.asyncio
async def test_get_db_rollbacks_on_error():
    conn = AsyncMock()
    conn.commit = AsyncMock()
    conn.rollback = AsyncMock()
    connect_cm = MagicMock()
    connect_cm.__aenter__ = AsyncMock(return_value=conn)
    connect_cm.__aexit__ = AsyncMock(return_value=False)

    with patch.object(dependencies, "engine") as engine:
        engine.connect.return_value = connect_cm
        gen = dependencies.get_db()
        await gen.__anext__()
        with pytest.raises(RuntimeError, match="boom"):
            await gen.athrow(RuntimeError("boom"))

    conn.rollback.assert_awaited_once()


def test_get_embedder_and_pipeline():
    assert isinstance(dependencies.get_embedder(), Embedder)
    assert isinstance(dependencies.get_pipeline(), ChatPipeline)
    assert isinstance(dependencies.get_llm_service(), ChatPipeline)
