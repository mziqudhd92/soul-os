"""RECALL + persist: episodic memory via pgvector."""

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

from config import EMBEDDING_DIMENSION
from runtime.embedder import Embedder


def _session_filter_sql(session_id: str | None) -> str:
    if session_id:
        return "AND (session_id IS NULL OR session_id = :session_id)"
    return ""


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
    session_clause = _session_filter_sql(session_id)
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
        },
    )
    return [row.content for row in result.fetchall()]


async def list_memories(
    db: AsyncConnection,
    bot_id: str,
    limit: int = 50,
    session_id: str | None = None,
) -> list[str]:
    if session_id:
        result = await db.execute(
            text(
                "SELECT content FROM episodic_memories "
                "WHERE bot_id = :bot_id AND session_id = :session_id "
                "ORDER BY id DESC LIMIT :limit"
            ),
            {"bot_id": bot_id, "session_id": session_id, "limit": limit},
        )
    else:
        result = await db.execute(
            text(
                "SELECT content FROM episodic_memories WHERE bot_id = :bot_id "
                "ORDER BY id DESC LIMIT :limit"
            ),
            {"bot_id": bot_id, "limit": limit},
        )
    return [row.content for row in result.fetchall()]
