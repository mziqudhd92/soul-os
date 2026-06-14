"""Kernel readiness checks for sidecar deployments."""

from __future__ import annotations

import httpx
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

from config import EMBEDDING_DIMENSION, INFERENCE_API_URL


async def check_database(conn: AsyncConnection) -> bool:
    try:
        await conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


async def check_inference() -> bool:
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(INFERENCE_API_URL, timeout=5.0)
            return resp.status_code == 200
    except httpx.HTTPError:
        return False


async def build_ready_payload(conn: AsyncConnection) -> dict:
    db_ok = await check_database(conn)
    inference_ok = await check_inference()
    status = "ok" if db_ok and inference_ok else "degraded"
    return {
        "status": status,
        "service": "soulos-kernel",
        "checks": {
            "database": "ok" if db_ok else "error",
            "inference": "ok" if inference_ok else "error",
        },
        "embedding_dimension": EMBEDDING_DIMENSION,
        "inference_api_url": INFERENCE_API_URL,
    }
