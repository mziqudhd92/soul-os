"""Atomic handoffs with idempotency and allowlist checks."""

from __future__ import annotations

import json
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

from auth import AccountContext
from config import MAX_MEMORY_CONTENT_CHARS
from runtime.conversation_memory import (
    ingest_conversation_memory,
    normalize_conversation_id,
    require_tenant_uuid,
)
from runtime.errors import ACCESS_DENIED, SOUL_INVALID, SoulOSProblem
from runtime.memory import ingest_memory as ingest_memory_record
from tenant import verify_bot_access

_MAX_HANDOFF_PAYLOAD_CHARS = min(8192, MAX_MEMORY_CONTENT_CHARS)


def format_handoff_note(
    *,
    from_role: str,
    to_role: str,
    conversation_id: str,
    reason: str,
    summary: str,
    payload: dict[str, Any] | None,
    task_summary: str | None = None,
    unresolved_constraints: str | list[str] | None = None,
    user_emotional_state: str | None = None,
    source_bot_stance: str | None = None,
) -> str:
    lines = [
        "[SoulOS handoff]",
        f"from: {from_role}",
        f"to: {to_role}",
        f"conversation_id: {conversation_id}",
        f"reason: {reason}",
        f"summary: {summary}",
    ]
    if task_summary:
        lines.append(f"task_summary: {task_summary}")
    if unresolved_constraints is not None:
        if isinstance(unresolved_constraints, list):
            lines.append(
                "unresolved_constraints: "
                + json.dumps(unresolved_constraints, ensure_ascii=False)
            )
        else:
            lines.append(f"unresolved_constraints: {unresolved_constraints}")
    if user_emotional_state:
        lines.append(f"user_emotional_state: {user_emotional_state}")
    if source_bot_stance:
        lines.append(f"source_bot_stance: {source_bot_stance}")
    if payload:
        lines.append(f"payload: {json.dumps(payload, ensure_ascii=False)}")
    return "\n".join(lines)


def assert_handoff_allowed(
    *,
    from_bot_id: str,
    to_bot_id: str,
    allowed_targets: list[str] | None,
) -> None:
    """Deny lateral move when source soul defines an allowlist without the target."""
    if allowed_targets is None:
        return
    if to_bot_id not in allowed_targets:
        raise SoulOSProblem(
            ACCESS_DENIED,
            403,
            f"Handoff from {from_bot_id} to {to_bot_id} is not in allowed_handoff_targets",
        )


async def _load_idempotent(
    db: AsyncConnection, tenant_id: str | None, key: str
) -> dict | None:
    if tenant_id:
        result = await db.execute(
            text(
                "SELECT response FROM handoff_idempotency "
                "WHERE tenant_id = CAST(:t AS uuid) AND idempotency_key = :k"
            ),
            {"t": tenant_id, "k": key},
        )
    else:
        result = await db.execute(
            text(
                "SELECT response FROM handoff_idempotency "
                "WHERE tenant_id IS NULL AND idempotency_key = :k"
            ),
            {"k": key},
        )
    row = result.fetchone()
    if not row:
        return None
    resp = row.response
    return json.loads(resp) if isinstance(resp, str) else resp


async def _store_idempotent(
    db: AsyncConnection, tenant_id: str | None, key: str, response: dict
) -> bool:
    params = {"t": tenant_id, "k": key, "r": json.dumps(response)}
    if tenant_id:
        result = await db.execute(
            text(
                "INSERT INTO handoff_idempotency (tenant_id, idempotency_key, response) "
                "SELECT CAST(:t AS uuid), :k, CAST(:r AS jsonb) "
                "WHERE NOT EXISTS ("
                "  SELECT 1 FROM handoff_idempotency "
                "  WHERE tenant_id = CAST(:t AS uuid) AND idempotency_key = :k"
                ") "
                "RETURNING id"
            ),
            params,
        )
    else:
        result = await db.execute(
            text(
                "INSERT INTO handoff_idempotency (tenant_id, idempotency_key, response) "
                "SELECT NULL, :k, CAST(:r AS jsonb) "
                "WHERE NOT EXISTS ("
                "  SELECT 1 FROM handoff_idempotency "
                "  WHERE tenant_id IS NULL AND idempotency_key = :k"
                ") "
                "RETURNING id"
            ),
            params,
        )
    return result.fetchone() is not None


async def _load_allowed_handoff_targets(
    db: AsyncConnection, bot_id: str
) -> list[str] | None:
    result = await db.execute(
        text("SELECT runtime_config FROM bots WHERE id = :id"),
        {"id": bot_id},
    )
    row = result.fetchone()
    if not row or row.runtime_config is None:
        return None
    cfg = row.runtime_config
    if isinstance(cfg, str):
        try:
            cfg = json.loads(cfg)
        except json.JSONDecodeError:
            return None
    if not isinstance(cfg, dict):
        return None
    targets = cfg.get("allowed_handoff_targets")
    if targets is None:
        return None
    if not isinstance(targets, list):
        return []
    return [str(t) for t in targets]


async def create_handoff_record(
    db: AsyncConnection,
    embedder: Any,
    account: AccountContext,
    *,
    from_bot_id: str,
    to_bot_id: str,
    from_role: str,
    to_role: str,
    conversation_id: str,
    reason: str,
    summary: str,
    user_message: str | None = None,
    payload: dict[str, Any] | None = None,
    idempotency_key: str | None = None,
    task_summary: str | None = None,
    unresolved_constraints: str | list[str] | None = None,
    user_emotional_state: str | None = None,
    source_bot_stance: str | None = None,
) -> dict:
    await verify_bot_access(db, from_bot_id, account)
    await verify_bot_access(db, to_bot_id, account)
    allowed = await _load_allowed_handoff_targets(db, from_bot_id)
    assert_handoff_allowed(
        from_bot_id=from_bot_id, to_bot_id=to_bot_id, allowed_targets=allowed
    )
    try:
        cid = normalize_conversation_id(conversation_id)
    except ValueError as e:
        raise SoulOSProblem(SOUL_INVALID, 422, str(e)) from e

    if payload is not None:
        encoded = json.dumps(payload, ensure_ascii=False)
        if len(encoded) > _MAX_HANDOFF_PAYLOAD_CHARS:
            raise SoulOSProblem(
                SOUL_INVALID,
                422,
                f"payload JSON must be at most {_MAX_HANDOFF_PAYLOAD_CHARS} characters",
            )

    tenant_id = require_tenant_uuid(account.account_id)
    if idempotency_key:
        cached = await _load_idempotent(db, tenant_id, idempotency_key)
        if cached:
            return cached

    note = format_handoff_note(
        from_role=from_role,
        to_role=to_role,
        conversation_id=cid,
        reason=reason,
        summary=summary,
        payload=payload,
        task_summary=task_summary,
        unresolved_constraints=unresolved_constraints,
        user_emotional_state=user_emotional_state,
        source_bot_stance=source_bot_stance,
    )
    session_id = cid

    complete_text = summary
    if user_message:
        complete_text = f"{summary}\nUser: {user_message}"
    await ingest_memory_record(db, embedder, from_bot_id, complete_text, session_id)
    shared_id = await ingest_conversation_memory(
        db,
        embedder,
        cid,
        note,
        tenant_id=tenant_id,
        source_bot_id=from_bot_id,
        importance=0.85,
    )
    await ingest_memory_record(
        db, embedder, to_bot_id, note, session_id, importance=0.85
    )

    response = {
        "status": "success",
        "from_bot_id": from_bot_id,
        "to_bot_id": to_bot_id,
        "session_id": session_id,
        "conversation_id": cid,
        "note": note,
        "shared_memory_id": shared_id,
    }
    if idempotency_key:
        stored = await _store_idempotent(db, tenant_id, idempotency_key, response)
        if not stored:
            cached = await _load_idempotent(db, tenant_id, idempotency_key)
            if cached:
                return cached
    return response
