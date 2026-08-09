"""SoulOS kernel — FastAPI HTTP surface (routes only)."""

import json
import logging
import time
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import BackgroundTasks, Depends, FastAPI, Request
from fastapi.responses import JSONResponse, StreamingResponse
from mcp.server.sse import SseServerTransport
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection
from starlette.middleware.base import BaseHTTPMiddleware

from auth import (
    AccountContext,
    get_account_context,
    resolve_account_context,
    set_mcp_account_context,
)
from config import (
    ACCOUNT_ID_HEADER,
    EMBEDDING_DIMENSION,
    GATEWAY_SECRET_HEADER,
    INFERENCE_MODE,
    validate_gateway_secret,
)
from dependencies import get_db, get_embedder, get_llm_service
from mcp_server import mcp_server
from runtime.boot_memory import sync_memory_on_boot
from runtime.bootstrap import init_database, pull_model, wait_for_ollama
from runtime.avatars import (
    ensure_avatar_record,
    fetch_bot_identity,
    register_avatar_record,
)
from runtime.hybrid import build_hybrid_system_prompt, extract_inner_monologue
from runtime.hybrid_tasks import run_reflect_background
from runtime.soulpacks import (
    SoulPackError,
    SoulPackLicenseError,
    SoulPackNotFoundError,
    compile_pack,
    default_external_key,
    list_packs,
)
from runtime.errors import (
    BOT_NOT_FOUND,
    READY_DEGRADED,
    SOUL_INVALID,
    SOULPACK_INVALID,
    SOULPACK_LICENSE_REJECTED,
    SOULPACK_NOT_FOUND,
    TURN_CONTRACT_VIOLATION,
    TURN_REJECT_TOKEN,
    TURN_SESSION_EXPIRED,
    TURN_STATE_STALE,
    TURN_STEP_MISMATCH,
    SoulOSProblem,
    problem_response,
    register_exception_handlers,
)
from runtime.turn_contract import apply_turn, build_contract_context
from runtime.turn_session import (
    advance_turn_session,
    delete_turn_session,
    ensure_turn_session,
    get_turn_session,
    purge_expired_turn_sessions,
    store_turn_success_response,
)
from runtime.memory import ingest_memory as ingest_memory_record
from runtime.memory import (
    delete_session_memories,
    forget_memory,
    list_memories,
    purge_expired_session_memories,
    retrieve_memories,
)
from runtime.memory_sync import sync_memory_directory
from runtime.readiness import build_ready_payload
from runtime.telemetry import (
    hybrid_complete_span,
    hybrid_prepare_span,
    record_hybrid_duration,
)
from schemas import (
    ChatRequest,
    EnsureAvatarRequest,
    HybridCompleteRequest,
    HybridPrepareRequest,
    ImportSoulPackRequest,
    MemoryForget,
    MemoryIngest,
    MemoryPurgeExpired,
    MemoryRetrieve,
    MemorySync,
    ReflectStateRequest,
    UpdateStateRequest,
)
from runtime.reflector import run_system_2_reflector
from soul_compile import parse_soul_request_bundle
from soul_validation import validate_msv_payload
from tenant import verify_bot_access

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class McpAuthMiddleware(BaseHTTPMiddleware):
    """Apply the same account context rules as HTTP routes to MCP endpoints."""

    async def dispatch(self, request: Request, call_next):
        if request.url.path.startswith("/mcp/"):
            account_id = request.headers.get(ACCOUNT_ID_HEADER)
            gateway_secret = request.headers.get(GATEWAY_SECRET_HEADER)
            try:
                ctx = resolve_account_context(account_id, gateway_secret)
            except SoulOSProblem as exc:
                return problem_response(exc.code, exc.status, exc.detail)
            set_mcp_account_context(ctx)
        return await call_next(request)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting SoulOS Kernel...")
    validate_gateway_secret()
    try:
        await init_database()
    except Exception as e:
        logger.error("Failed to initialize database: %s", e)

    try:
        await wait_for_ollama()
        from config import EMBED_MODEL_NAME, INFERENCE_MODE, INFERENCE_SKIP_PULL, MODEL_NAME

        if not INFERENCE_SKIP_PULL:
            if INFERENCE_MODE != "embeddings_only":
                await pull_model(MODEL_NAME)
            await pull_model(EMBED_MODEL_NAME)
        else:
            logger.info("INFERENCE_SKIP_PULL=1 — skipping model pull")
    except Exception as e:
        logger.error("Failed to initialize inference API: %s", e)

    try:
        await sync_memory_on_boot()
    except Exception as e:
        logger.error("Boot memory sync failed: %s", e)

    yield
    logger.info("Shutting down SoulOS Kernel...")


app = FastAPI(lifespan=lifespan, title="SoulOS Kernel")
register_exception_handlers(app)
app.add_middleware(McpAuthMiddleware)
sse_transport = SseServerTransport("/mcp/messages")


@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "soulos-kernel"}


@app.get("/ready")
async def ready_check(db: AsyncConnection = Depends(get_db)):
    payload = await build_ready_payload(db)
    if payload["status"] == "ok":
        return JSONResponse(status_code=200, content=payload)
    checks = payload.get("checks", {})
    detail = (
        f"Kernel degraded: database={checks.get('database')}, "
        f"inference={checks.get('inference')}"
    )
    return problem_response(
        READY_DEGRADED,
        503,
        detail,
        extra={k: v for k, v in payload.items() if k not in ("status",)},
    )


@app.post("/v1/avatars")
async def register_avatar(
    request: Request,
    db: AsyncConnection = Depends(get_db),
    account: AccountContext = Depends(get_account_context),
):
    raw = await request.body()
    content_type = request.headers.get("content-type", "")
    filename_hint = request.headers.get("x-filename")
    try:
        payload, runtime_config = parse_soul_request_bundle(
            raw, content_type, filename_hint
        )
        return await register_avatar_record(
            db, account.account_id, payload, runtime_config
        )
    except ValueError as e:
        raise SoulOSProblem(SOUL_INVALID, 422, str(e)) from e


@app.post("/v1/avatars/ensure")
async def ensure_avatar(
    payload: EnsureAvatarRequest,
    db: AsyncConnection = Depends(get_db),
    account: AccountContext = Depends(get_account_context),
):
    try:
        return await ensure_avatar_record(
            db,
            account.account_id,
            payload.external_key,
            payload.soul,
            payload.runtime_config,
        )
    except ValueError as e:
        raise SoulOSProblem(SOUL_INVALID, 422, str(e)) from e


@app.get("/v1/soulpacks")
async def get_soulpacks(q: str | None = None):
    packs = list_packs(q=q)
    return {"packs": packs, "total": len(packs)}


@app.post("/v1/avatars/import-soulpack")
async def import_soulpack_avatar(
    payload: ImportSoulPackRequest,
    db: AsyncConnection = Depends(get_db),
    account: AccountContext = Depends(get_account_context),
):
    try:
        soul, runtime_config, warnings = compile_pack(
            payload.pack_id.strip(),
            msv_preset=payload.msv_preset,
        )
    except SoulPackNotFoundError as e:
        raise SoulOSProblem(SOULPACK_NOT_FOUND, 404, str(e)) from e
    except SoulPackLicenseError as e:
        raise SoulOSProblem(SOULPACK_LICENSE_REJECTED, 422, str(e)) from e
    except SoulPackError as e:
        raise SoulOSProblem(SOULPACK_INVALID, 422, str(e)) from e

    merged_runtime = dict(runtime_config)
    if payload.runtime_config:
        merged_runtime.update(payload.runtime_config)

    version = merged_runtime.get("source", {}).get("version") or "0.0.0"
    pack_id = merged_runtime.get("source", {}).get("id") or payload.pack_id.strip()
    external_key = payload.external_key or default_external_key(pack_id, str(version))

    if not payload.persist:
        return {
            "soul": soul,
            "runtime_config": merged_runtime,
            "warnings": warnings,
            "external_key": external_key,
        }

    try:
        record = await ensure_avatar_record(
            db,
            account.account_id,
            external_key,
            soul,
            merged_runtime,
        )
    except ValueError as e:
        raise SoulOSProblem(SOUL_INVALID, 422, str(e)) from e

    return {
        **record,
        "warnings": warnings,
        "external_key": external_key,
        "runtime_config": merged_runtime,
    }


@app.post("/memory/ingest")
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


@app.post("/memory/retrieve")
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


@app.post("/memory/forget")
async def forget_memory_route(
    payload: MemoryForget,
    db: AsyncConnection = Depends(get_db),
    account: AccountContext = Depends(get_account_context),
):
    await verify_bot_access(db, payload.bot_id, account)
    deleted = await forget_memory(db, payload.bot_id, payload.content_match)
    return {"status": "success", "deleted": deleted}


@app.delete("/memory/session/{bot_id}/{session_id}")
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


@app.post("/memory/purge-expired")
async def purge_expired_memories_route(
    payload: MemoryPurgeExpired,
    db: AsyncConnection = Depends(get_db),
    account: AccountContext = Depends(get_account_context),
):
    """Delete session-scoped memories and turn_sessions past MEMORY_SESSION_TTL_SECONDS."""
    await verify_bot_access(db, payload.bot_id, account)
    deleted = await purge_expired_session_memories(db, payload.bot_id)
    turn_deleted = await purge_expired_turn_sessions(db, payload.bot_id)
    return {
        "status": "success",
        "deleted": deleted,
        "turn_sessions_deleted": turn_deleted,
        "bot_id": payload.bot_id,
    }


@app.post("/hybrid/prepare")
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


@app.post("/hybrid/complete")
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
        # Contract configured but no session — ignore contract path (legacy-compatible)
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


@app.post("/memory/sync")
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


@app.post("/chat/generate")
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


@app.post("/state/update")
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


@app.post("/state/reflect")
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


@app.get("/bot/{bot_id}/identity")
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


@app.get("/bot/{bot_id}/memories")
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


@app.get("/mcp/sse")
async def handle_sse(request: Request):
    async with sse_transport.connect_sse(
        request.scope, request.receive, request._send
    ) as streams:
        await mcp_server.run(
            streams[0], streams[1], mcp_server.create_initialization_options()
        )


@app.post("/mcp/messages")
async def handle_messages(request: Request):
    await sse_transport.handle_post_message(
        request.scope, request.receive, request._send
    )
