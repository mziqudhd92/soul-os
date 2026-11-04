"""Chat SSE, MSV state, and bot identity/memory listing."""

from fastapi import APIRouter, BackgroundTasks, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncConnection

from auth import AccountContext, get_account_context
from dependencies import get_db, get_embedder, get_llm_service
from runtime.avatars import fetch_bot_identity
from runtime.errors import BOT_NOT_FOUND, SoulOSProblem
from runtime.hybrid_tasks import run_reflect_background  # noqa: F401 — test patches
from runtime.memory import list_memories, retrieve_memories
from runtime.reflector import run_system_2_reflector  # noqa: F401 — test patches
from schemas import ChatRequest, ReflectStateRequest, UpdateStateRequest
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
    from runtime.cognitive_msv import force_update_msv

    return await force_update_msv(db, account, payload.bot_id, payload.new_msv)


@router.post("/state/reflect")
async def reflect_state(
    payload: ReflectStateRequest,
    background_tasks: BackgroundTasks,
    db: AsyncConnection = Depends(get_db),
    pipeline=Depends(get_llm_service),
    account: AccountContext = Depends(get_account_context),
):
    """Run System 2 reflector for hybrid integrations that skip /chat/generate."""
    from runtime.cognitive_msv import reflect_cognitive_state

    # REST keeps appraisal optional for backward compatibility.
    appraisal = getattr(payload, "appraisal_reasoning", None) or "REST /state/reflect"
    return await reflect_cognitive_state(
        db,
        pipeline,
        account,
        bot_id=payload.bot_id,
        message=payload.message,
        appraisal_reasoning=appraisal,
        reflect_async=payload.reflect_async,
        add_background_task=background_tasks.add_task,
    )


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
