"""Avatar registration and identity (shared by REST and MCP)."""

from __future__ import annotations

import json
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

from soul_validation import validate_soul_payload


async def get_bot_identity(conn: AsyncConnection, bot_id: str) -> dict[str, Any] | None:
    result = await conn.execute(
        text(
            "SELECT name, role, description, baseline_msv, current_msv "
            "FROM bots WHERE id = :bot_id"
        ),
        {"bot_id": bot_id},
    )
    row = result.fetchone()
    if not row:
        return None
    return {
        "bot_id": bot_id,
        "name": row.name,
        "role": row.role,
        "description": row.description,
        "baseline_msv": row.baseline_msv if row.baseline_msv else {},
        "current_msv": row.current_msv if row.current_msv else {},
    }


def format_identity_prompt(identity: dict[str, Any]) -> str:
    msv = identity.get("current_msv") or {}
    return (
        f"You are {identity['name']}, a {identity['role']}.\n"
        f"Description: {identity['description']}\n"
        f"Psychological State (MSV): {json.dumps(msv)}"
    )


async def register_avatar_record(
    conn: AsyncConnection,
    owner_id: str | None,
    payload: dict[str, Any],
    runtime_config: dict[str, Any] | None = None,
    external_key: str | None = None,
) -> dict[str, Any]:
    soul = validate_soul_payload(payload)
    msv_json = json.dumps(soul.baseline_msv.model_dump())
    capabilities_json = json.dumps(soul.capabilities) if soul.capabilities else None
    runtime_json = json.dumps(runtime_config or {})

    result = await conn.execute(
        text("""
            INSERT INTO bots (
                owner_id, name, role, description, attachment_style,
                baseline_msv, current_msv,
                capabilities, hourly_rate, status, avatar_url, runtime_config,
                external_key
            )
            VALUES (
                CAST(:owner_id AS uuid), :name, :role, :description, :attachment_style,
                CAST(:baseline_msv AS jsonb), CAST(:current_msv AS jsonb),
                CAST(:capabilities AS jsonb), :hourly_rate, :status, :avatar_url,
                CAST(:runtime_config AS jsonb), :external_key
            )
            RETURNING id
        """),
        {
            "owner_id": owner_id,
            "name": soul.name,
            "role": soul.role,
            "description": soul.description,
            "attachment_style": soul.attachment_style,
            "baseline_msv": msv_json,
            "current_msv": msv_json,
            "capabilities": capabilities_json,
            "hourly_rate": soul.hourly_rate,
            "status": soul.status or "available",
            "avatar_url": soul.avatar_url,
            "runtime_config": runtime_json,
            "external_key": external_key,
        },
    )
    row = result.fetchone()
    avatar_id = str(row.id)
    baseline = soul.baseline_msv.model_dump()
    return {
        "id": avatar_id,
        "name": soul.name,
        "role": soul.role,
        "attachment_style": soul.attachment_style,
        "baseline_msv": baseline,
        "current_msv": baseline,
    }


async def list_avatars(
    conn: AsyncConnection,
    owner_id: str | None,
    limit: int = 50,
) -> list[dict[str, Any]]:
    limit = min(max(limit, 1), 50)
    if owner_id:
        result = await conn.execute(
            text(
                "SELECT id, name, role, status FROM bots "
                "WHERE owner_id = CAST(:owner_id AS uuid) "
                "ORDER BY created_at DESC NULLS LAST, id DESC "
                "LIMIT :limit"
            ),
            {"owner_id": owner_id, "limit": limit},
        )
    else:
        result = await conn.execute(
            text(
                "SELECT id, name, role, status FROM bots "
                "ORDER BY created_at DESC NULLS LAST, id DESC "
                "LIMIT :limit"
            ),
            {"limit": limit},
        )
    return [
        {
            "id": str(row.id),
            "name": row.name,
            "role": row.role,
            "status": row.status,
        }
        for row in result.fetchall()
    ]


async def find_avatar_by_external_key(
    conn: AsyncConnection,
    owner_id: str | None,
    external_key: str,
) -> dict[str, Any] | None:
    if owner_id:
        result = await conn.execute(
            text(
                "SELECT id, name, role, baseline_msv, current_msv "
                "FROM bots WHERE external_key = :external_key "
                "AND owner_id = CAST(:owner_id AS uuid)"
            ),
            {"external_key": external_key, "owner_id": owner_id},
        )
    else:
        result = await conn.execute(
            text(
                "SELECT id, name, role, baseline_msv, current_msv "
                "FROM bots WHERE external_key = :external_key AND owner_id IS NULL"
            ),
            {"external_key": external_key},
        )
    row = result.fetchone()
    if not row:
        return None
    baseline = row.baseline_msv if row.baseline_msv else {}
    current = row.current_msv if row.current_msv else {}
    return {
        "id": str(row.id),
        "name": row.name,
        "role": row.role,
        "baseline_msv": baseline,
        "current_msv": current,
    }


async def ensure_avatar_record(
    conn: AsyncConnection,
    owner_id: str | None,
    external_key: str,
    payload: dict[str, Any],
    runtime_config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    existing = await find_avatar_by_external_key(conn, owner_id, external_key)
    if existing:
        return existing
    return await register_avatar_record(
        conn, owner_id, payload, runtime_config, external_key=external_key
    )


fetch_bot_identity = get_bot_identity
