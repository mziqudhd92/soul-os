"""Hybrid prepare/complete sidecar routes (thin adapters over runtime)."""

from fastapi import APIRouter, BackgroundTasks, Depends
from sqlalchemy.ext.asyncio import AsyncConnection

from auth import AccountContext, get_account_context
from dependencies import get_db, get_embedder, get_llm_service
from runtime.avatars import fetch_bot_identity  # noqa: F401 — test patches
from runtime.hybrid_service import complete_hybrid_turn, prepare_hybrid_turn
from runtime.turn_session import (
    advance_turn_session,
    ensure_turn_session,
    get_turn_session,
    store_turn_success_response,
)
from schemas import HybridCompleteRequest, HybridPrepareRequest
from tenant import verify_bot_access  # noqa: F401 — re-exported for tests

router = APIRouter(tags=["hybrid"])

# Re-export for test patches targeting routes.hybrid.*
__all__ = [
    "router",
    "hybrid_prepare",
    "hybrid_complete",
    "ensure_turn_session",
    "get_turn_session",
    "advance_turn_session",
    "store_turn_success_response",
]


@router.post("/hybrid/prepare")
async def hybrid_prepare(
    payload: HybridPrepareRequest,
    db: AsyncConnection = Depends(get_db),
    embedder=Depends(get_embedder),
    pipeline=Depends(get_llm_service),
    account: AccountContext = Depends(get_account_context),
):
    return await prepare_hybrid_turn(db, embedder, pipeline, account, payload)


@router.post(
    "/hybrid/complete",
    responses={
        200: {"description": "Complete succeeded (sync reflect or reflect skipped)"},
        202: {"description": "Accepted — async reflect"},
        404: {
            "description": "TURN_SESSION_EXPIRED — turn session missing or TTL-purged",
        },
        409: {
            "description": "TURN_STATE_STALE — expected_version mismatch (CAS lost race)",
        },
        422: {
            "description": (
                "TURN_CONTRACT_VIOLATION | TURN_REJECT_TOKEN | TURN_STEP_MISMATCH "
                "| request validation"
            ),
        },
    },
)
async def hybrid_complete(
    payload: HybridCompleteRequest,
    background_tasks: BackgroundTasks,
    db: AsyncConnection = Depends(get_db),
    embedder=Depends(get_embedder),
    pipeline=Depends(get_llm_service),
    account: AccountContext = Depends(get_account_context),
):
    return await complete_hybrid_turn(
        db,
        embedder,
        pipeline,
        account,
        payload,
        add_background_task=background_tasks.add_task,
    )
