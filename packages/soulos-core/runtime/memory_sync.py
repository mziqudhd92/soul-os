"""Hydrate pgvector from `.soul-memory/` ledger files."""

from __future__ import annotations

import hashlib
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

from runtime.embedder import Embedder
from runtime.memory_ledger import iter_episode_lines, memory_root


def line_content_hash(summary: str, episode_hash: str) -> str:
    digest = hashlib.sha256(f"{episode_hash}:{summary}".encode("utf-8")).hexdigest()
    return digest[:32]


async def sync_memory_directory(
    db: AsyncConnection,
    embedder: Embedder,
    bot_id: str,
    workspace_root: Path,
) -> dict[str, int]:
    """Import episode summaries from workspace `.soul-memory/` into pgvector."""
    root = memory_root(workspace_root)
    if not root.is_dir():
        return {"imported": 0, "skipped": 0, "total": 0}

    imported = 0
    skipped = 0
    lines = iter_episode_lines(workspace_root)

    for row in lines:
        summary = str(row.get("summary", "")).strip()
        if not summary:
            skipped += 1
            continue

        episode_hash = str(row.get("hash", ""))
        source_hash = line_content_hash(summary, episode_hash)

        existing = await db.execute(
            text(
                "SELECT 1 FROM episodic_memories "
                "WHERE bot_id = :bot_id AND source_hash = :source_hash LIMIT 1"
            ),
            {"bot_id": bot_id, "source_hash": source_hash},
        )
        if existing.fetchone():
            skipped += 1
            continue

        embedding = await embedder.get_embedding(summary)
        await db.execute(
            text("""
                INSERT INTO episodic_memories (bot_id, content, embedding, source_hash)
                VALUES (:bot_id, :content, :embedding, :source_hash)
            """),
            {
                "bot_id": bot_id,
                "content": summary,
                "embedding": str(embedding),
                "source_hash": source_hash,
            },
        )
        imported += 1

    return {"imported": imported, "skipped": skipped, "total": len(lines)}
