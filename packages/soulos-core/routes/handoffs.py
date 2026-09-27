"""Atomic Phase B handoffs with idempotency."""

from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

from auth import AccountContext, get_account_context
from config import MAX_MEMORY_CONTENT_CHARS
from dependencies import get_db, get_embedder
from runtime.conversation_memory import (
    ingest_conversation_memory,
    normalize_conversation_id,
    parse_tenant_uuid,
)
from runtime.errors import SOUL_INVALID, SoulOSProblem
from runtime.memory import ingest_memory as ingest_memory_record
from tenant import verify_bot_access

router = APIRouter(tags=["handoffs"])


class HandoffRequest(BaseModel):
    from_bot_id: str
    to_bot_id: str
    from_role: str
    to_role: str
    conversation_id: str
    reason: str = Field(max_length=MAX_MEMORY_CONTENT_CHARS)
    summary: str = Field(max_length=MAX_MEMORY_CONTENT_CHARS)
    user_message: str | None = Field(default=None, max_length=MAX_MEMORY_CONTENT_CHARS)
    payload: dict[str, Any] | None = None
    idempotency_key: str | None = None


def format_handoff_note(
    *,
    from_role: str,
    to_role: str,
    conversation_id: str,
    reason: str,
    summary: str,
    payload: dict[str, Any] | None,
) -> str:
    lines = [
        "[SoulOS handoff]",
        f"from: {from_role}",
        f"to: {to_role}",
        f"conversation_id: {conversation_id}",
        f"reason: {reason}",
        f"summary: {summary}",
    ]
    if payload:
        lines.append(f"payload: {json.dumps(payload, ensure_ascii=False)}")
    return "\n".join(lines)


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
) -> None:
    await db.execute(
        text(
            "INSERT INTO handoff_idempotency (tenant_id, idempotency_key, response) "
            "VALUES (CAST(:t AS uuid), :k, CAST(:r AS jsonb)) "
            "ON CONFLICT DO NOTHING"
        )
        if tenant_id
        else text(
            "INSERT INTO handoff_idempotency (tenant_id, idempotency_key, response) "
            "VALUES (NULL, :k, CAST(:r AS jsonb)) "
            "ON CONFLICT DO NOTHING"
        ),
        {"t": tenant_id, "k": key, "r": json.dumps(response)},
    )


@router.post("/v1/handoffs")
async def create_handoff(
    payload: HandoffRequest,
    db: AsyncConnection = Depends(get_db),
    embedder=Depends(get_embedder),
    account: AccountContext = Depends(get_account_context),
):
    await verify_bot_access(db, payload.from_bot_id, account)
    await verify_bot_access(db, payload.to_bot_id, account)
    try:
        cid = normalize_conversation_id(payload.conversation_id)
    except ValueError as e:
        raise SoulOSProblem(SOUL_INVALID, 422, str(e)) from e

    tenant_id = parse_tenant_uuid(account.account_id)
    if payload.idempotency_key:
        cached = await _load_idempotent(db, tenant_id, payload.idempotency_key)
        if cached:
            return cached

    note = format_handoff_note(
        from_role=payload.from_role,
        to_role=payload.to_role,
        conversation_id=cid,
        reason=payload.reason,
        summary=payload.summary,
        payload=payload.payload,
    )
    session_id = cid

    # Complete-side effect: ingest summary on from_bot
    complete_text = payload.summary
    if payload.user_message:
        complete_text = f"{payload.summary}\nUser: {payload.user_message}"
    await ingest_memory_record(
        db, embedder, payload.from_bot_id, complete_text, session_id
    )
    shared_id = await ingest_conversation_memory(
        db,
        embedder,
        cid,
        note,
        tenant_id=tenant_id,
        source_bot_id=payload.from_bot_id,
        importance=0.85,
    )
    await ingest_memory_record(
        db, embedder, payload.to_bot_id, note, session_id, importance=0.85
    )

    response = {
        "status": "success",
        "from_bot_id": payload.from_bot_id,
        "to_bot_id": payload.to_bot_id,
        "session_id": session_id,
        "conversation_id": cid,
        "note": note,
        "shared_memory_id": shared_id,
    }
    if payload.idempotency_key:
        await _store_idempotent(db, tenant_id, payload.idempotency_key, response)
    return response
