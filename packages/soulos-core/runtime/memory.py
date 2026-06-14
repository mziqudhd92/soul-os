"""RECALL + persist: episodic memory via pgvector."""

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

from config import EMBEDDING_DIMENSION
from runtime.embedder import Embedder


async def ingest_memory(
    db: AsyncConnection, embedder: Embedder, bot_id: str, content: str
) -> None:
    embedding = await embedder.get_embedding(content)
    await db.execute(
        text("""
            INSERT INTO episodic_memories (bot_id, content, embedding)
            VALUES (:bot_id, :content, :embedding)
        """),
        {"bot_id": bot_id, "content": content, "embedding": str(embedding)},
    )


async def retrieve_memories(
    db: AsyncConnection,
    embedder: Embedder,
    bot_id: str,
    query: str,
    top_k: int = 5,
) -> list[str]:
    embedding = await embedder.get_embedding(query)
    result = await db.execute(
        text("""
            SELECT content, embedding <-> CAST(:embedding AS vector({EMBEDDING_DIMENSION})) AS distance
            FROM episodic_memories
            WHERE bot_id = :bot_id
            ORDER BY distance
            LIMIT :top_k
        """),
        {"bot_id": bot_id, "embedding": str(embedding), "top_k": top_k},
    )
    return [row.content for row in result.fetchall()]


async def list_memories(db: AsyncConnection, bot_id: str, limit: int = 50) -> list[str]:
    result = await db.execute(
        text(
            "SELECT content FROM episodic_memories WHERE bot_id = :bot_id "
            "ORDER BY id DESC LIMIT :limit"
        ),
        {"bot_id": bot_id, "limit": limit},
    )
    return [row.content for row in result.fetchall()]
