"""Hybrid prepare/complete sidecar routes."""

import time

from fastapi import APIRouter, BackgroundTasks, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncConnection

from auth import AccountContext, get_account_context
from config import (
    MEMORY_BUDGET_EPISODIC,
    MEMORY_BUDGET_SEMANTIC,
    MEMORY_BUDGET_SHARED,
)
from dependencies import get_db, get_embedder, get_llm_service
from runtime.avatars import fetch_bot_identity
from runtime.conversation_memory import (
    normalize_conversation_id,
    parse_tenant_uuid,
    retrieve_conversation_memory_hits,
)
from runtime.dual_process import decide_reflect
from runtime.errors import BOT_NOT_FOUND, SoulOSProblem
from runtime.hybrid import apply_memory_budgets, build_hybrid_system_prompt, extract_inner_monologue
from runtime.hybrid_complete import resolve_turn_on_complete
from runtime.hybrid_tasks import run_reflect_background
from runtime.memory import ingest_memory as ingest_memory_record
from runtime.memory import retrieve_memory_hits
from runtime.memory_rank import hit_contents
from runtime.reflector import run_system_2_reflector
from runtime.telemetry import (
    hybrid_complete_span,
    hybrid_prepare_span,
    record_hybrid_duration,
)
from runtime.turn_contract import build_contract_context
from runtime.turn_session import (
    advance_turn_session,
    ensure_turn_session,
    get_turn_session,
    store_turn_success_response,
)
from schemas import HybridCompleteRequest, HybridPrepareRequest
from tenant import verify_bot_access

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


def _budgets_from_config(runtime_config: dict | None) -> tuple[float, float, float]:
    raw = (runtime_config or {}).get("memory_budgets") or {}
    if not isinstance(raw, dict):
        return MEMORY_BUDGET_EPISODIC, MEMORY_BUDGET_SHARED, MEMORY_BUDGET_SEMANTIC
    return (
        float(raw.get("episodic", MEMORY_BUDGET_EPISODIC)),
        float(raw.get("shared", MEMORY_BUDGET_SHARED)),
        float(raw.get("semantic", MEMORY_BUDGET_SEMANTIC)),
    )


@router.post("/hybrid/prepare")
async def hybrid_prepare(
    payload: HybridPrepareRequest,
    db: AsyncConnection = Depends(get_db),
    embedder=Depends(get_embedder),
    pipeline=Depends(get_llm_service),
    account: AccountContext = Depends(get_account_context),
):
    await verify_bot_access(db, payload.bot_id, account)
    identity = await fetch_bot_identity(db, payload.bot_id)
    if not identity:
        raise SoulOSProblem(BOT_NOT_FOUND, 404, f"Bot not found: {payload.bot_id}")
    t0 = time.perf_counter()
    with hybrid_prepare_span(payload.bot_id, payload.session_id, payload.query) as span:
        hits = await retrieve_memory_hits(
            db,
            embedder,
            payload.bot_id,
            payload.query,
            payload.top_k * 2,
            payload.session_id,
        )
        episodic = [h.content for h in hits if h.memory_kind != "semantic"]
        semantic = [h.content for h in hits if h.memory_kind == "semantic"]
        shared: list[str] = []
        include_shared = payload.include_shared_memory
        if include_shared is None and payload.session_id:
            include_shared = str(payload.session_id).startswith("conv:")
        if include_shared and payload.session_id:
            try:
                cid = normalize_conversation_id(payload.session_id)
                tenant_id = parse_tenant_uuid(account.account_id)
                shared_hits = await retrieve_conversation_memory_hits(
                    db,
                    embedder,
                    cid,
                    payload.query,
                    payload.top_k,
                    tenant_id=tenant_id,
                )
                shared = hit_contents(shared_hits)
            except ValueError:
                shared = []
        runtime_config = await pipeline.load_runtime_config(db, payload.bot_id)
        b_ep, b_sh, b_se = _budgets_from_config(runtime_config)
        memories = apply_memory_budgets(
            episodic,
            shared,
            semantic,
            top_k=payload.top_k,
            budget_episodic=b_ep,
            budget_shared=b_sh,
            budget_semantic=b_se,
        )
        system_prompt = build_hybrid_system_prompt(identity, memories, runtime_config)
        best_distance = None
        if hits:
            dists = [h.dense_distance for h in hits if h.dense_distance is not None]
            if dists:
                best_distance = min(dists)
        if span is not None:
            span.set_attribute("retrieval.documents.count", len(memories))
            span.set_attribute("output.value", system_prompt[:500])
    record_hybrid_duration("prepare", time.perf_counter() - t0)
    body: dict = {
        "bot_id": payload.bot_id,
        "identity": {
            "name": identity["name"],
            "role": identity["role"],
            "description": identity["description"],
            "current_msv": identity["current_msv"],
        },
        "memories": memories,
        "system_prompt": system_prompt,
        "inner_monologue": extract_inner_monologue(identity),
        "retrieval": {
            "best_distance": best_distance,
            "shared_count": len(shared),
            "episodic_count": len(episodic),
            "semantic_count": len(semantic),
        },
    }
    contract = (runtime_config or {}).get("turn_contract")
    if isinstance(contract, dict) and payload.session_id:
        session = await ensure_turn_session(
            db,
            bot_id=payload.bot_id,
            session_id=payload.session_id,
            initial_step=str(contract.get("initial_step") or "start"),
        )
        body["contract_context"] = build_contract_context(
            contract,
            step_id=session["current_step"],
            slots=session["slots"],
            turn_version=session["turn_version"],
        )
    return body


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
    await verify_bot_access(db, payload.bot_id, account)
    t0 = time.perf_counter()
    runtime_config = await pipeline.load_runtime_config(db, payload.bot_id)
    contract = (runtime_config or {}).get("turn_contract")
    turn_payload: dict | None = None
    contract_session_id: str | None = None

    if isinstance(contract, dict) and payload.session_id:
        contract_session_id = payload.session_id
        resolved = await resolve_turn_on_complete(db, contract=contract, payload=payload)
        if resolved and "_cached_response" in resolved:
            cached = resolved["_cached_response"]
            record_hybrid_duration("complete", time.perf_counter() - t0)
            status = 202 if cached.get("status") == "accepted" else 200
            return JSONResponse(status_code=status, content=cached)
        turn_payload = resolved

    with hybrid_complete_span(payload.bot_id, payload.session_id, payload.summary) as span:
        await ingest_memory_record(
            db, embedder, payload.bot_id, payload.summary, payload.session_id
        )
        if span is not None:
            span.set_attribute("input.value", (payload.user_message or payload.summary)[:500])
    record_hybrid_duration("complete", time.perf_counter() - t0)

    response: dict = {"status": "success", "ingested": True, "reflect": "skipped"}
    if turn_payload is not None:
        response["turn"] = turn_payload

    if payload.reflect and payload.user_message:
        current_msv = await pipeline.load_current_msv(db, payload.bot_id)
        missing_slots = False
        if turn_payload and isinstance(turn_payload.get("missing_slots"), list):
            missing_slots = bool(turn_payload["missing_slots"])
        run_s2, _features = decide_reflect(
            current_msv,
            runtime_config,
            query=payload.user_message,
            contract_incomplete=missing_slots,
            reflect_force=payload.reflect_force,
            bot_id=payload.bot_id,
        )
        if not run_s2:
            response["reflect"] = "skipped_by_router"
        elif payload.reflect_async:
            background_tasks.add_task(
                run_reflect_background,
                payload.bot_id,
                payload.user_message,
                current_msv,
            )
            async_body = {
                "status": "accepted",
                "ingested": True,
                "reflect": "async",
                "bot_id": payload.bot_id,
            }
            if turn_payload is not None:
                async_body["turn"] = turn_payload
            if turn_payload is not None and contract_session_id:
                await store_turn_success_response(
                    db,
                    bot_id=payload.bot_id,
                    session_id=contract_session_id,
                    turn_version=turn_payload["turn_version"],
                    last_idempotency_key=payload.idempotency_key,
                    last_success_response=async_body,
                )
            return JSONResponse(status_code=202, content=async_body)
        else:
            reflect_result = await run_system_2_reflector(
                payload.bot_id,
                payload.user_message,
                current_msv,
                active_mcp_tools=[],
            )
            response["reflect"] = "completed"
            response["current_msv"] = reflect_result.msv
            response["reflect_latency_ms"] = reflect_result.latency_ms

    if turn_payload is not None and contract_session_id:
        await store_turn_success_response(
            db,
            bot_id=payload.bot_id,
            session_id=contract_session_id,
            turn_version=turn_payload["turn_version"],
            last_idempotency_key=payload.idempotency_key,
            last_success_response=response,
        )
    return response
