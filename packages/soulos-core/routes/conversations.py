"""Phase B conversation shared-memory routes."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncConnection

from auth import AccountContext, get_account_context
from config import MAX_MEMORY_CONTENT_CHARS
from dependencies import get_db, get_embedder
from runtime.conversation_memory import (
    ingest_conversation_memory,
    normalize_conversation_id,
    parse_tenant_uuid,
    retrieve_conversation_memories,
    retrieve_conversation_memory_hits,
)
from runtime.errors import SOUL_INVALID, SoulOSProblem

router = APIRouter(prefix="/v1/conversations", tags=["conversations"])


class ConversationMemoryIngest(BaseModel):
    content: str = Field(max_length=MAX_MEMORY_CONTENT_CHARS)
    source_bot_id: str | None = None
    importance: float = 0.6


class ConversationMemoryRetrieve(BaseModel):
    query: str = Field(max_length=MAX_MEMORY_CONTENT_CHARS)
    top_k: int = 5
    include_scores: bool = False


@router.post("/{conversation_id}/memory")
async def ingest_shared_memory(
    conversation_id: str,
    payload: ConversationMemoryIngest,
    db: AsyncConnection = Depends(get_db),
    embedder=Depends(get_embedder),
    account: AccountContext = Depends(get_account_context),
):
    try:
        cid = normalize_conversation_id(conversation_id)
    except ValueError as e:
        raise SoulOSProblem(SOUL_INVALID, 422, str(e)) from e
    tenant_id = parse_tenant_uuid(account.account_id)
    mem_id = await ingest_conversation_memory(
        db,
        embedder,
        cid,
        payload.content,
        tenant_id=tenant_id,
        source_bot_id=payload.source_bot_id,
        importance=payload.importance,
    )
    return {"status": "success", "id": mem_id, "conversation_id": cid}


@router.post("/{conversation_id}/memory/retrieve")
async def retrieve_shared_memory(
    conversation_id: str,
    payload: ConversationMemoryRetrieve,
    db: AsyncConnection = Depends(get_db),
    embedder=Depends(get_embedder),
    account: AccountContext = Depends(get_account_context),
):
    try:
        cid = normalize_conversation_id(conversation_id)
    except ValueError as e:
        raise SoulOSProblem(SOUL_INVALID, 422, str(e)) from e
    tenant_id = parse_tenant_uuid(account.account_id)
    if payload.include_scores:
        hits = await retrieve_conversation_memory_hits(
            db, embedder, cid, payload.query, payload.top_k, tenant_id=tenant_id
        )
        return {
            "conversation_id": cid,
            "memories": [h.content for h in hits],
            "hits": [h.to_dict() for h in hits],
        }
    memories = await retrieve_conversation_memories(
        db, embedder, cid, payload.query, payload.top_k, tenant_id=tenant_id
    )
    return {"conversation_id": cid, "memories": memories}
