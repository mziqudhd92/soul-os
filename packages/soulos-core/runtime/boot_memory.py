"""Optional boot-time hydration of .soul-memory into pgvector."""

from __future__ import annotations

import logging
from pathlib import Path

from config import MEMORY_SYNC_BOT_ID, MEMORY_SYNC_WORKSPACE, engine
from runtime.embedder import Embedder
from runtime.memory_sync import sync_memory_directory

logger = logging.getLogger(__name__)


async def sync_memory_on_boot() -> None:
    if not MEMORY_SYNC_WORKSPACE or not MEMORY_SYNC_BOT_ID:
        return

    workspace = Path(MEMORY_SYNC_WORKSPACE).resolve()
    if not workspace.is_dir():
        logger.warning(
            "SOULOS_MEMORY_SYNC_WORKSPACE is not a directory: %s", workspace
        )
        return

    embedder = Embedder()
    try:
        async with engine.begin() as conn:
            stats = await sync_memory_directory(
                conn, embedder, MEMORY_SYNC_BOT_ID, workspace
            )
        logger.info(
            "Boot memory sync for bot %s: imported=%s skipped=%s total=%s",
            MEMORY_SYNC_BOT_ID,
            stats["imported"],
            stats["skipped"],
            stats["total"],
        )
    except Exception as exc:
        logger.error("Boot memory sync failed: %s", exc)
