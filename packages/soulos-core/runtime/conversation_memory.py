"""Shared conversation memory (Phase B) — tenant-scoped."""

from __future__ import annotations

from typing import Any
from uuid import UUID

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
    MEMORY_RRF_K,
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


def normalize_conversation_id(conversation_id: str) -> str:
    cid = (conversation_id or "").strip()
    if not cid:
        raise ValueError("conversation_id is required")
    if cid.startswith("conv:"):
        return cid
    return f"conv:{cid}"


def _tenant_clause(tenant_id: str | None) -> str:
    if tenant_id:
        return "AND tenant_id = CAST(:tenant_id AS uuid)"
    return "AND tenant_id IS NULL"


async def ingest_conversation_memory(
    db: AsyncConnection,
    embedder: Embedder,
    conversation_id: str,
    content: str,
    *,
    tenant_id: str | None = None,
    source_bot_id: str | None = None,
    importance: float = 0.6,
) -> str:
    cid = normalize_conversation_id(conversation_id)
    embedding = await embedder.get_embedding(content)
    if tenant_id:
        result = await db.execute(
            text("""
                INSERT INTO conversation_memories (
                    tenant_id, conversation_id, content, embedding, source_bot_id, importance
                )
                VALUES (
                    CAST(:tenant_id AS uuid), :conversation_id, :content, :embedding,
                    CAST(:source_bot_id AS uuid), :importance
                )
                RETURNING id::text AS id
            """),
            {
                "tenant_id": tenant_id,
                "conversation_id": cid,
                "content": content,
                "embedding": str(embedding),
                "source_bot_id": source_bot_id,
                "importance": max(0.0, min(1.0, importance)),
            },
        )
    elif source_bot_id:
        result = await db.execute(
            text("""
                INSERT INTO conversation_memories (
                    tenant_id, conversation_id, content, embedding, source_bot_id, importance
                )
                VALUES (
                    NULL, :conversation_id, :content, :embedding,
                    CAST(:source_bot_id AS uuid), :importance
                )
                RETURNING id::text AS id
            """),
            {
                "conversation_id": cid,
                "content": content,
                "embedding": str(embedding),
                "source_bot_id": source_bot_id,
                "importance": max(0.0, min(1.0, importance)),
            },
        )
    else:
        result = await db.execute(
            text("""
                INSERT INTO conversation_memories (
                    tenant_id, conversation_id, content, embedding, source_bot_id, importance
                )
                VALUES (
                    NULL, :conversation_id, :content, :embedding, NULL, :importance
                )
                RETURNING id::text AS id
            """),
            {
                "conversation_id": cid,
                "content": content,
                "embedding": str(embedding),
                "importance": max(0.0, min(1.0, importance)),
            },
        )
    row = result.fetchone()
    return row.id if row else ""


async def retrieve_conversation_memory_hits(
    db: AsyncConnection,
    embedder: Embedder,
    conversation_id: str,
    query: str,
    top_k: int = 5,
    *,
    tenant_id: str | None = None,
) -> list[MemoryHit]:
    cid = normalize_conversation_id(conversation_id)
    embedding = await embedder.get_embedding(query)
    tenant_sql = _tenant_clause(tenant_id)
    dense_result = await db.execute(
        text(f"""
            SELECT id::text AS id, content,
                   embedding <-> CAST(:embedding AS vector({EMBEDDING_DIMENSION})) AS distance,
                   COALESCE(importance, 0.5) AS importance,
                   embedding::text AS embedding_text
            FROM conversation_memories
            WHERE conversation_id = :conversation_id
            {tenant_sql}
            ORDER BY distance
            LIMIT :top_k
        """),
        {
            "conversation_id": cid,
            "embedding": str(embedding),
            "top_k": max(top_k, MEMORY_DENSE_CANDIDATE_LIMIT),
            "tenant_id": tenant_id,
        },
    )
    dense = [
        MemoryHit(
            content=row.content,
            id=row.id,
            dense_distance=float(row.distance),
            importance=float(row.importance),
            memory_kind="episodic",
            source="shared",
            embedding=_parse_embedding(row.embedding_text),
        )
        for row in dense_result.fetchall()
    ]
    dense = apply_distance_cutoff(dense, MEMORY_MAX_DISTANCE)

    lexical: list[MemoryHit] = []
    safe = sanitize_websearch_query(query)
    if safe:
        try:
            lex_result = await db.execute(
                text(f"""
                    SELECT id::text AS id, content,
                           ts_rank(
                             to_tsvector('english', content),
                             websearch_to_tsquery('english', :q)
                           ) AS rank,
                           COALESCE(importance, 0.5) AS importance
                    FROM conversation_memories
                    WHERE conversation_id = :conversation_id
                    {tenant_sql}
                    AND to_tsvector('english', content)
                        @@ websearch_to_tsquery('english', :q)
                    ORDER BY rank DESC
                    LIMIT :top_k
                """),
                {
                    "conversation_id": cid,
                    "q": safe,
                    "top_k": max(top_k, MEMORY_LEXICAL_CANDIDATE_LIMIT),
                    "tenant_id": tenant_id,
                },
            )
            lexical = [
                MemoryHit(
                    content=row.content,
                    id=row.id,
                    fts_rank=float(row.rank),
                    importance=float(row.importance),
                    source="shared",
                )
                for row in lex_result.fetchall()
            ]
        except Exception:
            lexical = []

    if dense and lexical:
        ranked = reciprocal_rank_fusion(
            dense, lexical, k=MEMORY_RRF_K, importance_weight=MEMORY_IMPORTANCE_WEIGHT
        )
    else:
        ranked = dense or lexical
        for i, hit in enumerate(ranked):
            hit.rrf_score = (1.0 / (MEMORY_RRF_K + i + 1)) * (
                1.0 + hit.importance * MEMORY_IMPORTANCE_WEIGHT
            )

    return mmr_select(
        ranked,
        top_k=top_k,
        lambda_mult=MEMORY_MMR_LAMBDA,
        candidate_cap=MEMORY_MMR_CANDIDATE_CAP,
        query_embedding=embedding,
    )


async def retrieve_conversation_memories(
    db: AsyncConnection,
    embedder: Embedder,
    conversation_id: str,
    query: str,
    top_k: int = 5,
    *,
    tenant_id: str | None = None,
) -> list[str]:
    hits = await retrieve_conversation_memory_hits(
        db, embedder, conversation_id, query, top_k, tenant_id=tenant_id
    )
    return hit_contents(hits)


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


def parse_tenant_uuid(account_id: str | None) -> str | None:
    if not account_id:
        return None
    try:
        return str(UUID(account_id))
    except (TypeError, ValueError):
        return None
