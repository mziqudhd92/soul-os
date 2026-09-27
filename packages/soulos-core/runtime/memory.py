"""RECALL + persist: episodic memory via pgvector + hybrid FTS ranking."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

from config import (
    EMBEDDING_DIMENSION,
    MEMORY_DENSE_CANDIDATE_LIMIT,
    MEMORY_IMPORTANCE_WEIGHT,
    MEMORY_LEXICAL_CANDIDATE_LIMIT,
    MEMORY_MAX_DISTANCE,
    MEMORY_MMR_CANDIDATE_CAP,
    MEMORY_MMR_LAMBDA,
    MEMORY_RETRIEVAL_MODE,
    MEMORY_RRF_K,
    MEMORY_SESSION_TTL_SECONDS,
)
from runtime.embedder import Embedder
from runtime.memory_rank import (
    MemoryHit,
    apply_distance_cutoff,
    hit_contents,
    mmr_select,
    reciprocal_rank_fusion,
    sanitize_websearch_query,
)


def session_ttl_cutoff() -> datetime | None:
    """UTC cutoff for session-scoped rows when MEMORY_SESSION_TTL_SECONDS > 0."""
    if MEMORY_SESSION_TTL_SECONDS <= 0:
        return None
    return datetime.now(UTC) - timedelta(seconds=MEMORY_SESSION_TTL_SECONDS)


def _session_filter_sql(session_id: str | None, *, ttl_cutoff: datetime | None) -> str:
    parts: list[str] = []
    if session_id:
        parts.append("AND (session_id IS NULL OR session_id = :session_id)")
    if ttl_cutoff is not None:
        parts.append(
            "AND (session_id IS NULL OR created_at IS NULL OR created_at >= :ttl_cutoff)"
        )
    return " ".join(parts)


def _parse_embedding(raw: Any) -> list[float] | None:
    if raw is None:
        return None
    if isinstance(raw, list):
        return [float(x) for x in raw]
    if isinstance(raw, str):
        s = raw.strip().lstrip("[").rstrip("]")
        if not s:
            return None
        try:
            return [float(x) for x in s.split(",")]
        except ValueError:
            return None
    return None


async def ingest_memory(
    db: AsyncConnection,
    embedder: Embedder,
    bot_id: str,
    content: str,
    session_id: str | None = None,
    *,
    importance: float | None = None,
    memory_kind: str = "episodic",
) -> None:
    embedding = await embedder.get_embedding(content)
    imp = 0.5 if importance is None else max(0.0, min(1.0, float(importance)))
    # Mild novelty boost for longer content
    if importance is None and len(content) > 200:
        imp = min(1.0, imp + 0.1)
    await db.execute(
        text("""
            INSERT INTO episodic_memories (
                bot_id, content, embedding, session_id, importance, memory_kind
            )
            VALUES (
                :bot_id, :content, :embedding, :session_id, :importance, :memory_kind
            )
        """),
        {
            "bot_id": bot_id,
            "content": content,
            "embedding": str(embedding),
            "session_id": session_id,
            "importance": imp,
            "memory_kind": memory_kind,
        },
    )


async def _dense_candidates(
    db: AsyncConnection,
    bot_id: str,
    embedding: list[float],
    *,
    session_id: str | None,
    ttl_cutoff: datetime | None,
    limit: int,
    memory_kind: str | None = None,
) -> list[MemoryHit]:
    session_clause = _session_filter_sql(session_id, ttl_cutoff=ttl_cutoff)
    kind_clause = ""
    params: dict[str, Any] = {
        "bot_id": bot_id,
        "embedding": str(embedding),
        "top_k": limit,
        "session_id": session_id,
        "ttl_cutoff": ttl_cutoff,
    }
    if memory_kind:
        kind_clause = "AND COALESCE(memory_kind, 'episodic') = :memory_kind"
        params["memory_kind"] = memory_kind
    result = await db.execute(
        text(f"""
            SELECT id::text AS id, content,
                   embedding <-> CAST(:embedding AS vector({EMBEDDING_DIMENSION})) AS distance,
                   COALESCE(importance, 0.5) AS importance,
                   COALESCE(memory_kind, 'episodic') AS memory_kind,
                   embedding::text AS embedding_text
            FROM episodic_memories
            WHERE bot_id = :bot_id
            {session_clause}
            {kind_clause}
            AND COALESCE(memory_kind, 'episodic') NOT IN ('consolidating', 'archived')
            ORDER BY distance
            LIMIT :top_k
        """),
        params,
    )
    hits: list[MemoryHit] = []
    for row in result.fetchall():
        content = getattr(row, "content", None)
        if content is None:
            continue
        hits.append(
            MemoryHit(
                content=content,
                id=getattr(row, "id", None),
                dense_distance=float(getattr(row, "distance", 0.0) or 0.0),
                importance=float(getattr(row, "importance", 0.5) or 0.5),
                memory_kind=getattr(row, "memory_kind", None) or "episodic",
                source="semantic"
                if getattr(row, "memory_kind", None) == "semantic"
                else "bot",
                embedding=_parse_embedding(getattr(row, "embedding_text", None)),
            )
        )
    return hits


async def _lexical_candidates(
    db: AsyncConnection,
    bot_id: str,
    query: str,
    *,
    session_id: str | None,
    ttl_cutoff: datetime | None,
    limit: int,
) -> list[MemoryHit]:
    safe = sanitize_websearch_query(query)
    if not safe:
        return []
    session_clause = _session_filter_sql(session_id, ttl_cutoff=ttl_cutoff)
    try:
        result = await db.execute(
            text(f"""
                SELECT id::text AS id, content,
                       ts_rank(
                         to_tsvector('english', content),
                         websearch_to_tsquery('english', :q)
                       ) AS rank,
                       COALESCE(importance, 0.5) AS importance,
                       COALESCE(memory_kind, 'episodic') AS memory_kind
                FROM episodic_memories
                WHERE bot_id = :bot_id
                {session_clause}
                AND COALESCE(memory_kind, 'episodic') NOT IN ('consolidating', 'archived')
                AND to_tsvector('english', content)
                    @@ websearch_to_tsquery('english', :q)
                ORDER BY rank DESC
                LIMIT :top_k
            """),
            {
                "bot_id": bot_id,
                "q": safe,
                "top_k": limit,
                "session_id": session_id,
                "ttl_cutoff": ttl_cutoff,
            },
        )
    except Exception:
        # Invalid tsquery / missing FTS support → skip lexical branch
        return []
    return [
        MemoryHit(
            content=row.content,
            id=row.id,
            fts_rank=float(row.rank),
            importance=float(row.importance),
            memory_kind=row.memory_kind or "episodic",
            source="semantic" if row.memory_kind == "semantic" else "bot",
        )
        for row in result.fetchall()
    ]


async def retrieve_memory_hits(
    db: AsyncConnection,
    embedder: Embedder,
    bot_id: str,
    query: str,
    top_k: int = 5,
    session_id: str | None = None,
    *,
    retrieval_mode: str | None = None,
) -> list[MemoryHit]:
    """Hybrid (or dense-only) retrieval returning structured MemoryHit list."""
    mode = (retrieval_mode or MEMORY_RETRIEVAL_MODE or "hybrid").lower()
    embedding = await embedder.get_embedding(query)
    ttl_cutoff = session_ttl_cutoff()
    dense = await _dense_candidates(
        db,
        bot_id,
        embedding,
        session_id=session_id,
        ttl_cutoff=ttl_cutoff,
        limit=max(top_k, MEMORY_DENSE_CANDIDATE_LIMIT),
    )
    dense = apply_distance_cutoff(dense, MEMORY_MAX_DISTANCE)

    if mode == "dense":
        ranked = dense
        for i, hit in enumerate(ranked):
            hit.rrf_score = 1.0 / (MEMORY_RRF_K + i + 1)
            hit.rrf_score *= 1.0 + hit.importance * MEMORY_IMPORTANCE_WEIGHT
    else:
        lexical = await _lexical_candidates(
            db,
            bot_id,
            query,
            session_id=session_id,
            ttl_cutoff=ttl_cutoff,
            limit=max(top_k, MEMORY_LEXICAL_CANDIDATE_LIMIT),
        )
        if not dense and not lexical:
            return []
        if not lexical:
            ranked = dense
            for i, hit in enumerate(ranked):
                hit.rrf_score = 1.0 / (MEMORY_RRF_K + i + 1)
                hit.rrf_score *= 1.0 + hit.importance * MEMORY_IMPORTANCE_WEIGHT
        elif not dense:
            ranked = lexical
            for i, hit in enumerate(ranked):
                hit.rrf_score = 1.0 / (MEMORY_RRF_K + i + 1)
                hit.rrf_score *= 1.0 + hit.importance * MEMORY_IMPORTANCE_WEIGHT
        else:
            ranked = reciprocal_rank_fusion(
                dense,
                lexical,
                k=MEMORY_RRF_K,
                importance_weight=MEMORY_IMPORTANCE_WEIGHT,
            )

    return mmr_select(
        ranked,
        top_k=top_k,
        lambda_mult=MEMORY_MMR_LAMBDA,
        candidate_cap=MEMORY_MMR_CANDIDATE_CAP,
        query_embedding=embedding,
    )


async def retrieve_memories(
    db: AsyncConnection,
    embedder: Embedder,
    bot_id: str,
    query: str,
    top_k: int = 5,
    session_id: str | None = None,
) -> list[str]:
    """Backward-compatible content-only retrieve."""
    hits = await retrieve_memory_hits(
        db, embedder, bot_id, query, top_k, session_id
    )
    return hit_contents(hits)


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


def _escape_ilike_pattern(value: str) -> str:
    """Escape ``\\``, ``%``, and ``_`` for PostgreSQL LIKE with ``ESCAPE '\\'``."""
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


async def forget_memory(
    db: AsyncConnection,
    bot_id: str,
    content_match: str,
) -> int:
    pattern = f"%{_escape_ilike_pattern(content_match)}%"
    result = await db.execute(
        text(
            "DELETE FROM episodic_memories "
            "WHERE bot_id = :bot_id AND content ILIKE :pattern ESCAPE '\\'"
        ),
        {"bot_id": bot_id, "pattern": pattern},
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
