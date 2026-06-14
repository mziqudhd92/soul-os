"""Tests for memory sync from .soul-memory to pgvector."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from runtime.memory_ledger import append_episode_line
from runtime.memory_sync import sync_memory_directory
from runtime.soulignore import content_matches_ignore_patterns, validate_memory_content


class MockEmbedder:
    async def get_embedding(self, text: str) -> list[float]:
        return [0.1] * 768


@pytest.mark.asyncio
async def test_sync_memory_directory_imports_episodes(tmp_path: Path):
    append_episode_line(tmp_path, "Team prefers typed Python over untyped scripts.")
    db = AsyncMock()
    db.execute = AsyncMock(
        return_value=MagicMock(fetchone=MagicMock(return_value=None))
    )

    stats = await sync_memory_directory(
        db,
        MockEmbedder(),
        "123e4567-e89b-12d3-a456-426614174000",
        tmp_path,
    )

    assert stats["imported"] == 1
    assert stats["total"] == 1
    assert db.execute.await_count >= 2


@pytest.mark.asyncio
async def test_sync_skips_duplicate_source_hash(tmp_path: Path):
    append_episode_line(tmp_path, "Duplicate line test content.")
    db = AsyncMock()
    db.execute = AsyncMock(
        return_value=MagicMock(fetchone=MagicMock(return_value=(1,)))
    )

    stats = await sync_memory_directory(
        db,
        MockEmbedder(),
        "123e4567-e89b-12d3-a456-426614174000",
        tmp_path,
    )

    assert stats["imported"] == 0
    assert stats["skipped"] == 1


def test_soulignore_blocks_path_pattern_in_content(tmp_path: Path):
    (tmp_path / ".soulignore").write_text(".env\n", encoding="utf-8")
    with pytest.raises(ValueError, match="pattern"):
        validate_memory_content("Loaded secrets from .env file", tmp_path)


def test_content_matches_ignore_patterns():
    assert content_matches_ignore_patterns("see .env for keys", [".env"])
    assert not content_matches_ignore_patterns("safe summary line", [".env"])
