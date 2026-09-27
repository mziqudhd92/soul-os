"""Capability lookup with short TTL in-process cache."""

from __future__ import annotations

import time
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

from config import CAPABILITY_CACHE_TTL_SECONDS

_cache: dict[tuple[str | None, str], tuple[float, list[dict[str, Any]]]] = {}


def invalidate_capability_cache() -> None:
    _cache.clear()


async def list_avatars_by_capability(
    db: AsyncConnection,
    capability: str,
    *,
    tenant_id: str | None = None,
    limit: int = 50,
) -> list[dict[str, Any]]:
    cap = (capability or "").strip().lower()
    if not cap:
        return []
    key = (tenant_id, cap)
    now = time.monotonic()
    cached = _cache.get(key)
    if cached and cached[0] > now:
        return cached[1]

    params: dict[str, Any] = {"cap": cap, "limit": limit}
    tenant_clause = ""
    if tenant_id:
        tenant_clause = "AND owner_id = CAST(:tenant_id AS uuid)"
        params["tenant_id"] = tenant_id

    result = await db.execute(
        text(f"""
            SELECT id::text AS id, name, role, capabilities
            FROM bots
            WHERE capabilities IS NOT NULL
              AND EXISTS (
                SELECT 1 FROM jsonb_array_elements_text(capabilities) AS c(val)
                WHERE lower(c.val) = :cap
              )
              {tenant_clause}
            ORDER BY created_at DESC NULLS LAST
            LIMIT :limit
        """),
        params,
    )
    rows = [
        {
            "id": r.id,
            "name": r.name,
            "role": r.role,
            "capabilities": r.capabilities
            if isinstance(r.capabilities, list)
            else r.capabilities,
        }
        for r in result.fetchall()
    ]
    _cache[key] = (now + CAPABILITY_CACHE_TTL_SECONDS, rows)
    return rows
