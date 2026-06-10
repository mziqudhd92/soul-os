"""FastAPI dependency injection for the SoulOS kernel."""

from sqlalchemy.ext.asyncio import AsyncConnection

from config import engine
from runtime.embedder import Embedder
from runtime.pipeline import ChatPipeline


async def get_db() -> AsyncConnection:
    async with engine.connect() as conn:
        try:
            yield conn
            await conn.commit()
        except Exception:
            await conn.rollback()
            raise


def get_embedder() -> Embedder:
    return Embedder()


def get_pipeline() -> ChatPipeline:
    return ChatPipeline()


# Back-compat alias for tests
def get_llm_service() -> ChatPipeline:
    return get_pipeline()
