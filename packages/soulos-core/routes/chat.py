"""Chat SSE, MSV state, and bot identity/memory listing."""

import json

from fastapi import APIRouter, BackgroundTasks, Depends
from fastapi.responses import JSONResponse, StreamingResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

from auth import AccountContext, get_account_context
from dependencies import get_db, get_embedder, get_llm_service
from runtime.avatars import fetch_bot_identity
from runtime.errors import BOT_NOT_FOUND, SOUL_INVALID, SoulOSProblem
from runtime.hybrid_tasks import run_reflect_background
from runtime.memory import list_memories, retrieve_memories
from runtime.reflector import run_system_2_reflector
from schemas import ChatRequest, ReflectStateRequest, UpdateStateRequest
from soul_validation import validate_msv_payload
from tenant import verify_bot_access

router = APIRouter(tags=["chat"])


@router.post("/chat/generate")
async def chat_generate(
    payload: ChatRequest,
    db: AsyncConnection = Depends(get_db),
    embedder=Depends(get_embedder),
    pipeline=Depends(get_llm_service),
    account: AccountContext = Depends(get_account_context),
):
    await verify_bot_access(db, payload.bot_id, account)
    memories = await retrieve_memories(db, embedder, payload.bot_id, payload.message, 3)
    return StreamingResponse(
        pipeline.generate_chat_stream(payload.bot_id, payload.message, memories, db),
        media_type="text/event-stream",
    )


@router.post("/state/update")
async def update_state(
    payload: UpdateStateRequest,
    db: AsyncConnection = Depends(get_db),
    account: AccountContext = Depends(get_account_context),
):
    await verify_bot_access(db, payload.bot_id, account)
    try:
        validated_msv = validate_msv_payload(payload.new_msv)
    except ValueError as e:
        raise SoulOSProblem(SOUL_INVALID, 422, str(e))

    await db.execute(
        text("UPDATE bots SET current_msv = :msv WHERE id = :id"),
        {"msv": json.dumps(validated_msv), "id": payload.bot_id},
    )
    return {
        "status": "success",
        "message": f"Cognitive State updated for bot {payload.bot_id}",
    }


@router.post("/state/reflect")
async def reflect_state(
    payload: ReflectStateRequest,
    background_tasks: BackgroundTasks,
    db: AsyncConnection = Depends(get_db),
    pipeline=Depends(get_llm_service),
    account: AccountContext = Depends(get_account_context),
):
    """Run System 2 reflector for hybrid integrations that skip /chat/generate."""
    await verify_bot_access(db, payload.bot_id, account)
    current_msv = await pipeline.load_current_msv(db, payload.bot_id)
    if payload.reflect_async:
        background_tasks.add_task(
            run_reflect_background, payload.bot_id, payload.message, current_msv
        )
        return JSONResponse(
            status_code=202,
            content={
                "status": "accepted",
                "bot_id": payload.bot_id,
                "reflect": "async",
            },
        )
    result = await run_system_2_reflector(
        payload.bot_id, payload.message, current_msv, active_mcp_tools=[]
    )
    return {
        "status": "success",
        "bot_id": payload.bot_id,
        "current_msv": result.msv,
        "latency_ms": result.latency_ms,
    }


@router.get("/bot/{bot_id}/identity")
async def get_bot_identity_route(
    bot_id: str,
    db: AsyncConnection = Depends(get_db),
    account: AccountContext = Depends(get_account_context),
):
    await verify_bot_access(db, bot_id, account)
    identity = await fetch_bot_identity(db, bot_id)
    if not identity:
        raise SoulOSProblem(BOT_NOT_FOUND, 404, f"Bot not found: {bot_id}")
    return {
        "name": identity["name"],
        "role": identity["role"],
        "description": identity["description"],
        "current_msv": identity["current_msv"],
    }


@router.get("/bot/{bot_id}/memories")
async def get_bot_memories(
    bot_id: str,
    limit: int = 50,
    session_id: str | None = None,
    db: AsyncConnection = Depends(get_db),
    account: AccountContext = Depends(get_account_context),
):
    await verify_bot_access(db, bot_id, account)
    memories = await list_memories(db, bot_id, limit, session_id)
    return {"bot_id": bot_id, "session_id": session_id, "memories": memories}
