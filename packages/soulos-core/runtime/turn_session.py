"""Session turn state persistence for optional hybrid turn contracts."""

from __future__ import annotations

import json
from datetime import timezone
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

from config import MEMORY_SESSION_TTL_SECONDS
from runtime.memory import session_ttl_cutoff


def _parse_json_field(value: Any) -> Any:
    if isinstance(value, str):
        return json.loads(value)
    return value


async def get_turn_session(
    db: AsyncConnection, bot_id: str, session_id: str
) -> dict[str, Any] | None:
    result = await db.execute(
        text(
            """
            SELECT current_step, slots, turn_version,
                   last_idempotency_key, last_success_response, updated_at
            FROM turn_sessions
            WHERE bot_id = :bot_id AND session_id = :session_id
            """
        ),
        {"bot_id": bot_id, "session_id": session_id},
    )
    row = result.fetchone()
    if not row:
        return None
    cutoff = session_ttl_cutoff()
    if cutoff is not None and row.updated_at is not None:
        updated = row.updated_at
        if getattr(updated, "tzinfo", None) is None and getattr(cutoff, "tzinfo", None):
            updated = updated.replace(tzinfo=timezone.utc)
        if updated < cutoff:
            await delete_turn_session(db, bot_id, session_id)
            return None
    slots = _parse_json_field(row.slots)
    last_resp = _parse_json_field(row.last_success_response)
    return {
        "current_step": row.current_step,
        "slots": slots or {},
        "turn_version": int(row.turn_version or 0),
        "last_idempotency_key": row.last_idempotency_key,
        "last_success_response": last_resp,
    }


async def upsert_turn_session(
    db: AsyncConnection,
    *,
    bot_id: str,
    session_id: str,
    current_step: str,
    slots: dict[str, Any],
    turn_version: int,
    last_idempotency_key: str | None = None,
    last_success_response: dict[str, Any] | None = None,
) -> None:
    await db.execute(
        text(
            """
            INSERT INTO turn_sessions (
                bot_id, session_id, current_step, slots, turn_version,
                last_idempotency_key, last_success_response, updated_at
            ) VALUES (
                :bot_id, :session_id, :current_step, CAST(:slots AS jsonb), :turn_version,
                :last_idempotency_key, CAST(:last_success_response AS jsonb), CURRENT_TIMESTAMP
            )
            ON CONFLICT (bot_id, session_id) DO UPDATE SET
                current_step = EXCLUDED.current_step,
                slots = EXCLUDED.slots,
                turn_version = EXCLUDED.turn_version,
                last_idempotency_key = COALESCE(
                    EXCLUDED.last_idempotency_key, turn_sessions.last_idempotency_key
                ),
                last_success_response = COALESCE(
                    EXCLUDED.last_success_response, turn_sessions.last_success_response
                ),
                updated_at = CURRENT_TIMESTAMP
            """
        ),
        {
            "bot_id": bot_id,
            "session_id": session_id,
            "current_step": current_step,
            "slots": json.dumps(slots),
            "turn_version": turn_version,
            "last_idempotency_key": last_idempotency_key,
            "last_success_response": (
                json.dumps(last_success_response)
                if last_success_response is not None
                else None
            ),
        },
    )


async def advance_turn_session(
    db: AsyncConnection,
    *,
    bot_id: str,
    session_id: str,
    expected_version: int,
    current_step: str,
    slots: dict[str, Any],
    turn_version: int,
    last_idempotency_key: str | None = None,
    last_success_response: dict[str, Any] | None = None,
) -> bool:
    """Optimistic compare-and-set. Returns False if version mismatch (lost race)."""
    result = await db.execute(
        text(
            """
            UPDATE turn_sessions SET
                current_step = :current_step,
                slots = CAST(:slots AS jsonb),
                turn_version = :turn_version,
                last_idempotency_key = COALESCE(
                    :last_idempotency_key, last_idempotency_key
                ),
                last_success_response = COALESCE(
                    CAST(:last_success_response AS jsonb), last_success_response
                ),
                updated_at = CURRENT_TIMESTAMP
            WHERE bot_id = :bot_id
              AND session_id = :session_id
              AND turn_version = :expected_version
            """
        ),
        {
            "bot_id": bot_id,
            "session_id": session_id,
            "expected_version": expected_version,
            "current_step": current_step,
            "slots": json.dumps(slots),
            "turn_version": turn_version,
            "last_idempotency_key": last_idempotency_key,
            "last_success_response": (
                json.dumps(last_success_response)
                if last_success_response is not None
                else None
            ),
        },
    )
    return int(getattr(result, "rowcount", 0) or 0) == 1


async def store_turn_success_response(
    db: AsyncConnection,
    *,
    bot_id: str,
    session_id: str,
    turn_version: int,
    last_idempotency_key: str | None,
    last_success_response: dict[str, Any],
) -> None:
    await db.execute(
        text(
            """
            UPDATE turn_sessions SET
                last_idempotency_key = COALESCE(
                    :last_idempotency_key, last_idempotency_key
                ),
                last_success_response = CAST(:last_success_response AS jsonb),
                updated_at = CURRENT_TIMESTAMP
            WHERE bot_id = :bot_id
              AND session_id = :session_id
              AND turn_version = :turn_version
            """
        ),
        {
            "bot_id": bot_id,
            "session_id": session_id,
            "turn_version": turn_version,
            "last_idempotency_key": last_idempotency_key,
            "last_success_response": json.dumps(last_success_response),
        },
    )


async def ensure_turn_session(
    db: AsyncConnection,
    *,
    bot_id: str,
    session_id: str,
    initial_step: str,
) -> dict[str, Any]:
    existing = await get_turn_session(db, bot_id, session_id)
    if existing:
        return existing
    await upsert_turn_session(
        db,
        bot_id=bot_id,
        session_id=session_id,
        current_step=initial_step,
        slots={},
        turn_version=0,
    )
    return {
        "current_step": initial_step,
        "slots": {},
        "turn_version": 0,
        "last_idempotency_key": None,
        "last_success_response": None,
    }


async def delete_turn_session(
    db: AsyncConnection, bot_id: str, session_id: str
) -> int:
    result = await db.execute(
        text(
            """
            DELETE FROM turn_sessions
            WHERE bot_id = :bot_id AND session_id = :session_id
            """
        ),
        {"bot_id": bot_id, "session_id": session_id},
    )
    return int(getattr(result, "rowcount", 0) or 0)


async def purge_expired_turn_sessions(
    db: AsyncConnection,
    bot_id: str | None = None,
) -> int:
    """Delete turn_sessions past MEMORY_SESSION_TTL_SECONDS (same TTL as session memory)."""
    if MEMORY_SESSION_TTL_SECONDS <= 0:
        return 0
    ttl_cutoff = session_ttl_cutoff()
    if ttl_cutoff is None:
        return 0
    if bot_id:
        result = await db.execute(
            text(
                """
                DELETE FROM turn_sessions
                WHERE updated_at IS NOT NULL
                  AND updated_at < :ttl_cutoff
                  AND bot_id = :bot_id
                """
            ),
            {"ttl_cutoff": ttl_cutoff, "bot_id": bot_id},
        )
    else:
        result = await db.execute(
            text(
                """
                DELETE FROM turn_sessions
                WHERE updated_at IS NOT NULL
                  AND updated_at < :ttl_cutoff
                """
            ),
            {"ttl_cutoff": ttl_cutoff},
        )
    return int(getattr(result, "rowcount", 0) or 0)
