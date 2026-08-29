"""Hybrid prepare/complete sidecar routes."""

import time

from fastapi import APIRouter, BackgroundTasks, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncConnection

from auth import AccountContext, get_account_context
from dependencies import get_db, get_embedder, get_llm_service
from runtime.avatars import fetch_bot_identity
from runtime.errors import (
    BOT_NOT_FOUND,
    TURN_CONTRACT_VIOLATION,
    TURN_REJECT_TOKEN,
    TURN_SESSION_EXPIRED,
    TURN_STATE_STALE,
    TURN_STEP_MISMATCH,
    SoulOSProblem,
)
from runtime.hybrid import build_hybrid_system_prompt, extract_inner_monologue
from runtime.hybrid_tasks import run_reflect_background
from runtime.memory import ingest_memory as ingest_memory_record
from runtime.memory import retrieve_memories
from runtime.reflector import run_system_2_reflector
from runtime.telemetry import (
    hybrid_complete_span,
    hybrid_prepare_span,
    record_hybrid_duration,
)
from runtime.turn_contract import apply_turn, build_contract_context
from runtime.turn_session import (
    advance_turn_session,
    ensure_turn_session,
    get_turn_session,
    store_turn_success_response,
)
from schemas import HybridCompleteRequest, HybridPrepareRequest
from tenant import verify_bot_access

router = APIRouter(tags=["hybrid"])


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
        memories = await retrieve_memories(
            db,
            embedder,
            payload.bot_id,
            payload.query,
            payload.top_k,
            payload.session_id,
        )
        runtime_config = await pipeline.load_runtime_config(db, payload.bot_id)
        system_prompt = build_hybrid_system_prompt(identity, memories, runtime_config)
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
        session = await get_turn_session(db, payload.bot_id, payload.session_id)
        if session is None:
            raise SoulOSProblem(
                TURN_SESSION_EXPIRED,
                404,
                f"Turn session expired or missing: {payload.session_id}",
                extra={"session_id": payload.session_id},
            )
        if (
            payload.idempotency_key
            and session.get("last_idempotency_key") == payload.idempotency_key
            and session.get("last_success_response")
        ):
            cached = dict(session["last_success_response"])
            record_hybrid_duration("complete", time.perf_counter() - t0)
            status = 202 if cached.get("status") == "accepted" else 200
            return JSONResponse(status_code=status, content=cached)

        if payload.expected_version is None:
            raise SoulOSProblem(
                TURN_CONTRACT_VIOLATION,
                422,
                "expected_version is required when a turn contract is active",
                extra={"turn_version": session["turn_version"]},
            )
        if payload.expected_version != session["turn_version"]:
            raise SoulOSProblem(
                TURN_STATE_STALE,
                409,
                "expected_version does not match session turn_version",
                extra={
                    "turn_version": session["turn_version"],
                    "expected_step": session["current_step"],
                    "filled_slots": session["slots"],
                },
            )
        if (
            payload.expected_step
            and payload.expected_step != session["current_step"]
        ):
            raise SoulOSProblem(
                TURN_STEP_MISMATCH,
                422,
                "expected_step does not match session current_step",
                extra={
                    "expected_step": session["current_step"],
                    "turn_version": session["turn_version"],
                },
            )

        result = apply_turn(
            contract,
            current_step=session["current_step"],
            slots=session["slots"],
            filled_slots=payload.filled_slots,
            intent=payload.intent,
            assistant_text=payload.assistant_text,
            advance=payload.advance,
        )
        if not result.ok:
            code = result.code or TURN_CONTRACT_VIOLATION
            if code == TURN_REJECT_TOKEN:
                raise SoulOSProblem(
                    TURN_REJECT_TOKEN,
                    422,
                    result.detail or "Reject token detected",
                    extra={
                        "expected_step": session["current_step"],
                        "turn_version": session["turn_version"],
                        "remedial_prompt_hint": result.remedial_prompt_hint,
                    },
                )
            raise SoulOSProblem(
                TURN_CONTRACT_VIOLATION,
                422,
                result.detail or "Turn contract violation",
                extra={
                    "invalid_slots": result.invalid_slots,
                    "missing_slots": result.missing_slots,
                    "expected_step": session["current_step"],
                    "turn_version": session["turn_version"],
                    "remedial_prompt_hint": result.remedial_prompt_hint,
                },
            )

        new_version = session["turn_version"] + 1
        claimed = await advance_turn_session(
            db,
            bot_id=payload.bot_id,
            session_id=payload.session_id,
            expected_version=session["turn_version"],
            current_step=result.step,
            slots=result.slots,
            turn_version=new_version,
            last_idempotency_key=payload.idempotency_key,
            last_success_response=None,
        )
        if not claimed:
            raise SoulOSProblem(
                TURN_STATE_STALE,
                409,
                "expected_version does not match session turn_version",
                extra={
                    "turn_version": session["turn_version"],
                    "expected_step": session["current_step"],
                    "filled_slots": session["slots"],
                },
            )
        turn_payload = {
            "step": result.step,
            "slots": result.slots,
            "advanced": result.advanced,
            "turn_version": new_version,
        }
    elif isinstance(contract, dict) and not payload.session_id:
        pass

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
        if payload.reflect_async:
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
