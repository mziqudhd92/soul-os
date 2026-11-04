"""Atomic Phase B handoffs with idempotency (thin REST adapter)."""

from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.ext.asyncio import AsyncConnection

from auth import AccountContext, get_account_context
from config import MAX_MEMORY_CONTENT_CHARS
from dependencies import get_db, get_embedder
from runtime.handoffs import (
    _load_idempotent,
    _store_idempotent,
    create_handoff_record,
    format_handoff_note,
)
from runtime.conversation_memory import ingest_conversation_memory
from runtime.memory import ingest_memory as ingest_memory_record
from tenant import verify_bot_access

router = APIRouter(tags=["handoffs"])

_MAX_HANDOFF_PAYLOAD_CHARS = min(8192, MAX_MEMORY_CONTENT_CHARS)


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
    idempotency_key: str | None = Field(default=None, max_length=128)
    task_summary: str | None = Field(default=None, max_length=MAX_MEMORY_CONTENT_CHARS)
    unresolved_constraints: str | list[str] | None = None
    user_emotional_state: str | None = Field(
        default=None, max_length=MAX_MEMORY_CONTENT_CHARS
    )
    source_bot_stance: str | None = Field(
        default=None, max_length=MAX_MEMORY_CONTENT_CHARS
    )

    @field_validator("payload")
    @classmethod
    def _bound_payload(cls, value: dict[str, Any] | None) -> dict[str, Any] | None:
        if value is None:
            return None
        encoded = json.dumps(value, ensure_ascii=False)
        if len(encoded) > _MAX_HANDOFF_PAYLOAD_CHARS:
            raise ValueError(
                f"payload JSON must be at most {_MAX_HANDOFF_PAYLOAD_CHARS} characters"
            )
        return value


@router.post("/v1/handoffs")
async def create_handoff(
    payload: HandoffRequest,
    db: AsyncConnection = Depends(get_db),
    embedder=Depends(get_embedder),
    account: AccountContext = Depends(get_account_context),
):
    return await create_handoff_record(
        db,
        embedder,
        account,
        from_bot_id=payload.from_bot_id,
        to_bot_id=payload.to_bot_id,
        from_role=payload.from_role,
        to_role=payload.to_role,
        conversation_id=payload.conversation_id,
        reason=payload.reason,
        summary=payload.summary,
        user_message=payload.user_message,
        payload=payload.payload,
        idempotency_key=payload.idempotency_key,
        task_summary=payload.task_summary,
        unresolved_constraints=payload.unresolved_constraints,
        user_emotional_state=payload.user_emotional_state,
        source_bot_stance=payload.source_bot_stance,
    )


# Re-export for older imports/tests
__all__ = ["router", "create_handoff", "HandoffRequest", "format_handoff_note"]
