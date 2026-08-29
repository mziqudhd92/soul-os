"""Episodic memory REST routes."""

from pathlib import Path

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncConnection

from auth import AccountContext, get_account_context
from dependencies import get_db, get_embedder
from runtime.errors import ACCESS_DENIED, SOUL_INVALID, SoulOSProblem
from runtime.memory import ingest_memory as ingest_memory_record
from runtime.memory import (
    delete_session_memories,
    forget_memory,
    purge_expired_session_memories,
    retrieve_memories,
)
from runtime.memory_sync import sync_memory_directory
from runtime.turn_session import delete_turn_session, purge_expired_turn_sessions
from schemas import (
    MemoryForget,
    MemoryIngest,
    MemoryPurgeExpired,
    MemoryRetrieve,
    MemorySync,
)
from tenant import verify_bot_access

router = APIRouter(tags=["memory"])


@router.post("/memory/ingest")
async def ingest_memory(
    payload: MemoryIngest,
    db: AsyncConnection = Depends(get_db),
    embedder=Depends(get_embedder),
    account: AccountContext = Depends(get_account_context),
):
    await verify_bot_access(db, payload.bot_id, account)
    await ingest_memory_record(
        db, embedder, payload.bot_id, payload.content, payload.session_id
    )
    return {"status": "success"}


@router.post("/memory/retrieve")
async def retrieve_memory(
    payload: MemoryRetrieve,
    db: AsyncConnection = Depends(get_db),
    embedder=Depends(get_embedder),
    account: AccountContext = Depends(get_account_context),
):
    await verify_bot_access(db, payload.bot_id, account)
    memories = await retrieve_memories(
        db,
        embedder,
        payload.bot_id,
        payload.query,
        payload.top_k,
        payload.session_id,
    )
    return {"memories": memories}


@router.post("/memory/forget")
async def forget_memory_route(
    payload: MemoryForget,
    db: AsyncConnection = Depends(get_db),
    account: AccountContext = Depends(get_account_context),
):
    await verify_bot_access(db, payload.bot_id, account)
    deleted = await forget_memory(db, payload.bot_id, payload.content_match)
    return {"status": "success", "deleted": deleted}


@router.delete("/memory/session/{bot_id}/{session_id}")
async def delete_session_memories_route(
    bot_id: str,
    session_id: str,
    db: AsyncConnection = Depends(get_db),
    account: AccountContext = Depends(get_account_context),
):
    await verify_bot_access(db, bot_id, account)
    deleted = await delete_session_memories(db, bot_id, session_id)
    turn_deleted = await delete_turn_session(db, bot_id, session_id)
    return {
        "status": "success",
        "deleted": deleted,
        "turn_sessions_deleted": turn_deleted,
        "bot_id": bot_id,
        "session_id": session_id,
    }


@router.post("/memory/purge-expired")
async def purge_expired_memories_route(
    payload: MemoryPurgeExpired,
    db: AsyncConnection = Depends(get_db),
    account: AccountContext = Depends(get_account_context),
):
    """Delete session-scoped memories and turn_sessions past MEMORY_SESSION_TTL_SECONDS."""
    if payload.bot_id:
        await verify_bot_access(db, payload.bot_id, account)
    elif account.account_id is not None:
        raise SoulOSProblem(
            ACCESS_DENIED,
            403,
            "bot_id is required when tenant auth is enabled",
        )
    deleted = await purge_expired_session_memories(db, payload.bot_id)
    turn_deleted = await purge_expired_turn_sessions(db, payload.bot_id)
    return {
        "status": "success",
        "deleted": deleted,
        "turn_sessions_deleted": turn_deleted,
        "bot_id": payload.bot_id,
    }


@router.post("/memory/sync")
async def sync_memory(
    payload: MemorySync,
    db: AsyncConnection = Depends(get_db),
    embedder=Depends(get_embedder),
    account: AccountContext = Depends(get_account_context),
):
    await verify_bot_access(db, payload.bot_id, account)
    workspace = Path(payload.workspace_path).resolve()
    if not workspace.is_dir():
        raise SoulOSProblem(SOUL_INVALID, 422, "workspace_path is not a directory")
    try:
        stats = await sync_memory_directory(db, embedder, payload.bot_id, workspace)
    except ValueError as e:
        raise SoulOSProblem(SOUL_INVALID, 422, str(e)) from e
    return {"status": "success", **stats}
