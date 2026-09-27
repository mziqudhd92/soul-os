"""Memory consolidation with FOR UPDATE locking and provenance metadata."""

from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

from runtime.embedder import Embedder

logger = logging.getLogger(__name__)


def extractive_summary(contents: list[str], *, max_chars: int = 1200) -> str:
    joined = " | ".join(c.strip() for c in contents if c and c.strip())
    if len(joined) <= max_chars:
        return f"[SoulOS semantic summary] {joined}"
    return f"[SoulOS semantic summary] {joined[: max_chars - 20]}…"


async def consolidate_memories(
    db: AsyncConnection,
    embedder: Embedder,
    bot_id: str,
    *,
    session_id: str | None = None,
    limit: int = 8,
) -> dict[str, Any]:
    """Select old/low-importance episodics, lock, summarize into one semantic row."""
    params: dict[str, Any] = {"bot_id": bot_id, "limit": max(2, limit)}
    session_clause = ""
    if session_id:
        session_clause = "AND session_id = :session_id"
        params["session_id"] = session_id

    result = await db.execute(
        text(f"""
            SELECT id::text AS id, content, created_at, COALESCE(importance, 0.5) AS importance
            FROM episodic_memories
            WHERE bot_id = :bot_id
              AND COALESCE(memory_kind, 'episodic') = 'episodic'
              {session_clause}
            ORDER BY COALESCE(importance, 0.5) ASC, created_at ASC NULLS FIRST
            LIMIT :limit
            FOR UPDATE
        """),
        params,
    )
    rows = result.fetchall()
    if len(rows) < 2:
        return {"status": "noop", "reason": "not_enough_candidates", "consolidated": 0}

    ids = [r.id for r in rows]
    contents = [r.content for r in rows]
    created_ats = [r.created_at for r in rows if r.created_at is not None]
    time_start: datetime | None = min(created_ats) if created_ats else None
    time_end: datetime | None = max(created_ats) if created_ats else None

    await db.execute(
        text(
            "UPDATE episodic_memories SET memory_kind = 'consolidating' "
            "WHERE id = ANY(CAST(:ids AS uuid[]))"
        ),
        {"ids": ids},
    )

    summary = extractive_summary(contents)
    embedding = await embedder.get_embedding(summary)
    avg_importance = sum(float(r.importance) for r in rows) / len(rows)

    insert = await db.execute(
        text("""
            INSERT INTO episodic_memories (
                bot_id, content, embedding, session_id, importance, memory_kind,
                source_memory_ids, time_range_start, time_range_end
            )
            VALUES (
                :bot_id, :content, :embedding, :session_id, :importance, 'semantic',
                CAST(:source_ids AS jsonb), :time_start, :time_end
            )
            RETURNING id::text AS id
        """),
        {
            "bot_id": bot_id,
            "content": summary,
            "embedding": str(embedding),
            "session_id": session_id,
            "importance": min(1.0, avg_importance + 0.15),
            "source_ids": json.dumps(ids),
            "time_start": time_start,
            "time_end": time_end,
        },
    )
    new_row = insert.fetchone()
    new_id = new_row.id if new_row else None

    await db.execute(
        text(
            "UPDATE episodic_memories SET supersedes = CAST(:new_id AS uuid), "
            "memory_kind = 'episodic' "
            "WHERE id = ANY(CAST(:ids AS uuid[]))"
        ),
        {"new_id": new_id, "ids": ids},
    )
    # Soft-delete sources by marking them superseded; remove from default retrieve via kind
    await db.execute(
        text(
            "UPDATE episodic_memories SET memory_kind = 'archived' "
            "WHERE id = ANY(CAST(:ids AS uuid[]))"
        ),
        {"ids": ids},
    )

    return {
        "status": "success",
        "semantic_id": new_id,
        "source_memory_ids": ids,
        "time_range_start": time_start.isoformat() if time_start else None,
        "time_range_end": time_end.isoformat() if time_end else None,
        "consolidated": len(ids),
    }
