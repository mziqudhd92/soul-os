"""Kernel boot: database schema and inference model warmup."""

import asyncio
import logging

import httpx
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from config import (
    DATABASE_URL,
    EMBED_MODEL_NAME,
    EMBEDDING_DIMENSION,
    INFERENCE_API_URL,
    MODEL_NAME,
)

logger = logging.getLogger(__name__)


async def init_database() -> None:
    engine = create_async_engine(DATABASE_URL, echo=True)
    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
        await conn.execute(
            text("""
            CREATE TABLE IF NOT EXISTS bots (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                owner_id UUID,
                name TEXT NOT NULL,
                baseline_msv JSONB,
                current_msv JSONB,
                role VARCHAR(255),
                description TEXT,
                attachment_style VARCHAR(50),
                capabilities JSONB,
                hourly_rate INTEGER,
                status VARCHAR(50),
                avatar_url VARCHAR(255),
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            );
        """)
        )
        await conn.execute(
            text(f"""
            CREATE TABLE IF NOT EXISTS episodic_memories (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                bot_id UUID REFERENCES bots(id) ON DELETE CASCADE,
                content TEXT NOT NULL,
                embedding vector({EMBEDDING_DIMENSION})
            );
        """)
        )
        await conn.execute(
            text(
                "ALTER TABLE bots ADD COLUMN IF NOT EXISTS attachment_style VARCHAR(50);"
            )
        )
        await conn.execute(
            text(
                "ALTER TABLE bots ADD COLUMN IF NOT EXISTS runtime_config JSONB;"
            )
        )
        await conn.execute(
            text(
                "ALTER TABLE episodic_memories "
                "ADD COLUMN IF NOT EXISTS source_hash VARCHAR(64);"
            )
        )
        await conn.execute(
            text("ALTER TABLE bots ADD COLUMN IF NOT EXISTS cognitive_meta JSONB;")
        )
    await engine.dispose()
    logger.info("Database initialized successfully.")


async def wait_for_ollama() -> bool:
    async with httpx.AsyncClient() as client:
        for _ in range(30):
            try:
                resp = await client.get(INFERENCE_API_URL)
                if resp.status_code == 200:
                    logger.info("Inference API is up!")
                    return True
            except httpx.RequestError:
                pass
            logger.info("Waiting for inference API...")
            await asyncio.sleep(2)
    raise RuntimeError("Inference API failed to start in time.")


async def pull_model(model_name: str) -> None:
    async with httpx.AsyncClient() as client:
        logger.info("Pulling model %s (this may take a while)...", model_name)
        resp = await client.post(
            f"{INFERENCE_API_URL}/api/pull",
            json={"name": model_name},
            timeout=600.0,
        )
        if resp.status_code == 200:
            logger.info("Model %s pulled successfully.", model_name)
        else:
            logger.error("Failed to pull model %s: %s", model_name, resp.text)
