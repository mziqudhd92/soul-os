"""Unit tests for runtime.boot_memory."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from runtime import boot_memory


@pytest.mark.asyncio
async def test_sync_memory_on_boot_skips_when_unset(monkeypatch):
    monkeypatch.setattr(boot_memory, "MEMORY_SYNC_WORKSPACE", "")
    monkeypatch.setattr(boot_memory, "MEMORY_SYNC_BOT_ID", "")
    await boot_memory.sync_memory_on_boot()


@pytest.mark.asyncio
async def test_sync_memory_on_boot_warns_non_directory(monkeypatch, tmp_path: Path):
    missing = tmp_path / "nope"
    monkeypatch.setattr(boot_memory, "MEMORY_SYNC_WORKSPACE", str(missing))
    monkeypatch.setattr(boot_memory, "MEMORY_SYNC_BOT_ID", "bot-1")
    await boot_memory.sync_memory_on_boot()


@pytest.mark.asyncio
async def test_sync_memory_on_boot_success(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(boot_memory, "MEMORY_SYNC_WORKSPACE", str(tmp_path))
    monkeypatch.setattr(boot_memory, "MEMORY_SYNC_BOT_ID", "bot-1")

    mock_conn = AsyncMock()
    begin_cm = MagicMock()
    begin_cm.__aenter__ = AsyncMock(return_value=mock_conn)
    begin_cm.__aexit__ = AsyncMock(return_value=False)
    mock_engine = MagicMock()
    mock_engine.begin.return_value = begin_cm
    monkeypatch.setattr(boot_memory, "engine", mock_engine)

    with (
        patch("runtime.boot_memory.Embedder") as Emb,
        patch(
            "runtime.boot_memory.sync_memory_directory",
            new_callable=AsyncMock,
            return_value={"imported": 1, "skipped": 0, "total": 1},
        ) as sync,
    ):
        Emb.return_value = MagicMock()
        await boot_memory.sync_memory_on_boot()
        sync.assert_awaited_once()


@pytest.mark.asyncio
async def test_sync_memory_on_boot_logs_error(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(boot_memory, "MEMORY_SYNC_WORKSPACE", str(tmp_path))
    monkeypatch.setattr(boot_memory, "MEMORY_SYNC_BOT_ID", "bot-1")

    mock_conn = AsyncMock()
    begin_cm = MagicMock()
    begin_cm.__aenter__ = AsyncMock(return_value=mock_conn)
    begin_cm.__aexit__ = AsyncMock(return_value=False)
    mock_engine = MagicMock()
    mock_engine.begin.return_value = begin_cm
    monkeypatch.setattr(boot_memory, "engine", mock_engine)

    with (
        patch("runtime.boot_memory.Embedder"),
        patch(
            "runtime.boot_memory.sync_memory_directory",
            new_callable=AsyncMock,
            side_effect=RuntimeError("sync blew up"),
        ),
    ):
        await boot_memory.sync_memory_on_boot()
