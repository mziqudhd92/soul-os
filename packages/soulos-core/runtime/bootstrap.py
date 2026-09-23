"""Kernel boot: database schema and inference model warmup."""

import asyncio
import logging

import httpx
from sqlalchemy.ext.asyncio import create_async_engine

from config import (
    DATABASE_URL,
    INFERENCE_API_URL,
    inference_headers,
)
from runtime.migrations import apply_migrations

logger = logging.getLogger(__name__)


async def init_database(database_url: str = DATABASE_URL) -> list[int]:
    """Apply pending schema migrations; returns the versions applied on this boot."""
    engine = create_async_engine(database_url)
    try:
        async with engine.begin() as conn:
            applied = await apply_migrations(conn)
    finally:
        await engine.dispose()
    if applied:
        logger.info("Database migrated (applied: %s).", applied)
    else:
        logger.info("Database schema up to date.")
    return applied


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
            headers=inference_headers(),
            timeout=600.0,
        )
        if resp.status_code == 200:
            logger.info("Model %s pulled successfully.", model_name)
        else:
            logger.error("Failed to pull model %s: %s", model_name, resp.text)
