"""RECALL + persist: episodic memory via pgvector."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

from config import EMBEDDING_DIMENSION, MEMORY_SESSION_TTL_SECONDS
from runtime.embedder import Embedder


def session_ttl_cutoff() -> datetime | None:
    """UTC cutoff for session-scoped rows when MEMORY_SESSION_TTL_SECONDS > 0."""
    if MEMORY_SESSION_TTL_SECONDS <= 0:
        return None
    return datetime.now(timezone.utc) - timedelta(seconds=MEMORY_SESSION_TTL_SECONDS)


def _session_filter_sql(session_id: str | None, *, ttl_cutoff: datetime | None) -> str:
    parts: list[str] = []
    if session_id:
        parts.append("AND (session_id IS NULL OR session_id = :session_id)")
    if ttl_cutoff is not None:
        # Global (session_id IS NULL) rows never expire via session TTL.
        parts.append(
            "AND (session_id IS NULL OR created_at IS NULL OR created_at >= :ttl_cutoff)"
        )
    return " ".join(parts)


async def ingest_memory(
    db: AsyncConnection,
    embedder: Embedder,
    bot_id: str,
    content: str,
    session_id: str | None = None,
) -> None:
    embedding = await embedder.get_embedding(content)
    await db.execute(
        text("""
            INSERT INTO episodic_memories (bot_id, content, embedding, session_id)
            VALUES (:bot_id, :content, :embedding, :session_id)
        """),
        {
            "bot_id": bot_id,
            "content": content,
            "embedding": str(embedding),
            "session_id": session_id,
        },
    )


async def retrieve_memories(
    db: AsyncConnection,
    embedder: Embedder,
    bot_id: str,
    query: str,
    top_k: int = 5,
    session_id: str | None = None,
) -> list[str]:
    embedding = await embedder.get_embedding(query)
    ttl_cutoff = session_ttl_cutoff()
    session_clause = _session_filter_sql(session_id, ttl_cutoff=ttl_cutoff)
    result = await db.execute(
        text(f"""
            SELECT content, embedding <-> CAST(:embedding AS vector({EMBEDDING_DIMENSION})) AS distance
            FROM episodic_memories
            WHERE bot_id = :bot_id
            {session_clause}
            ORDER BY distance
            LIMIT :top_k
        """),
        {
            "bot_id": bot_id,
            "embedding": str(embedding),
            "top_k": top_k,
            "session_id": session_id,
            "ttl_cutoff": ttl_cutoff,
        },
    )
    return [row.content for row in result.fetchall()]


async def list_memories(
    db: AsyncConnection,
    bot_id: str,
    limit: int = 50,
    session_id: str | None = None,
) -> list[str]:
    ttl_cutoff = session_ttl_cutoff()
    params: dict = {"bot_id": bot_id, "limit": limit, "ttl_cutoff": ttl_cutoff}
    clauses = ["bot_id = :bot_id"]
    if session_id:
        clauses.append("session_id = :session_id")
        params["session_id"] = session_id
    if ttl_cutoff is not None:
        clauses.append(
            "(session_id IS NULL OR created_at IS NULL OR created_at >= :ttl_cutoff)"
        )
    where = " AND ".join(clauses)
    result = await db.execute(
        text(
            f"SELECT content FROM episodic_memories "
            f"WHERE {where} "
            f"ORDER BY id DESC LIMIT :limit"
        ),
        params,
    )
    return [row.content for row in result.fetchall()]


async def forget_memory(
    db: AsyncConnection,
    bot_id: str,
    content_match: str,
) -> int:
    result = await db.execute(
        text(
            "DELETE FROM episodic_memories "
            "WHERE bot_id = :bot_id AND content ILIKE :pattern"
        ),
        {"bot_id": bot_id, "pattern": f"%{content_match}%"},
    )
    return int(result.rowcount or 0)


async def delete_session_memories(
    db: AsyncConnection,
    bot_id: str,
    session_id: str,
) -> int:
    result = await db.execute(
        text(
            "DELETE FROM episodic_memories "
            "WHERE bot_id = :bot_id AND session_id = :session_id"
        ),
        {"bot_id": bot_id, "session_id": session_id},
    )
    return int(result.rowcount or 0)


async def purge_expired_session_memories(
    db: AsyncConnection,
    bot_id: str | None = None,
) -> int:
    """Delete session-scoped rows past MEMORY_SESSION_TTL_SECONDS.

    Global memories (session_id IS NULL) are never purged by this path.
    Returns 0 when TTL is disabled.
    """
    ttl_cutoff = session_ttl_cutoff()
    if ttl_cutoff is None:
        return 0
    if bot_id:
        result = await db.execute(
            text(
                "DELETE FROM episodic_memories "
                "WHERE session_id IS NOT NULL "
                "AND created_at IS NOT NULL "
                "AND created_at < :ttl_cutoff "
                "AND bot_id = :bot_id"
            ),
            {"ttl_cutoff": ttl_cutoff, "bot_id": bot_id},
        )
    else:
        result = await db.execute(
            text(
                "DELETE FROM episodic_memories "
                "WHERE session_id IS NOT NULL "
                "AND created_at IS NOT NULL "
                "AND created_at < :ttl_cutoff"
            ),
            {"ttl_cutoff": ttl_cutoff},
        )
    return int(result.rowcount or 0)
