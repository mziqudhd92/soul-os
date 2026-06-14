"""SoulOS kernel — FastAPI HTTP surface (routes only)."""

import json
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Request
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
    GATEWAY_SECRET_HEADER,
    validate_gateway_secret,
)
from dependencies import get_db, get_embedder, get_llm_service
from mcp_server import mcp_server
from runtime.boot_memory import sync_memory_on_boot
from runtime.bootstrap import init_database, pull_model, wait_for_ollama
from runtime.avatars import get_bot_identity, register_avatar_record
from runtime.memory import ingest_memory as ingest_memory_record
from runtime.memory import list_memories, retrieve_memories
from runtime.memory_sync import sync_memory_directory
from schemas import (
    ChatRequest,
    MemoryIngest,
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
            except HTTPException as exc:
                return JSONResponse(
                    status_code=exc.status_code, content={"detail": exc.detail}
                )
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
        from config import EMBED_MODEL_NAME, INFERENCE_SKIP_PULL, MODEL_NAME

        if not INFERENCE_SKIP_PULL:
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
app.add_middleware(McpAuthMiddleware)
sse_transport = SseServerTransport("/mcp/messages")


@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "soulos-kernel"}


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
        raise HTTPException(status_code=422, detail=str(e)) from e


@app.post("/memory/ingest")
async def ingest_memory(
    payload: MemoryIngest,
    db: AsyncConnection = Depends(get_db),
    embedder=Depends(get_embedder),
    account: AccountContext = Depends(get_account_context),
):
    await verify_bot_access(db, payload.bot_id, account)
    await ingest_memory_record(db, embedder, payload.bot_id, payload.content)
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
        db, embedder, payload.bot_id, payload.query, payload.top_k
    )
    return {"memories": memories}


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
        raise HTTPException(status_code=422, detail="workspace_path is not a directory")
    try:
        stats = await sync_memory_directory(db, embedder, payload.bot_id, workspace)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
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
        raise HTTPException(status_code=422, detail=str(e))

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
    db: AsyncConnection = Depends(get_db),
    pipeline=Depends(get_llm_service),
    account: AccountContext = Depends(get_account_context),
):
    """Run System 2 reflector for hybrid integrations that skip /chat/generate."""
    await verify_bot_access(db, payload.bot_id, account)
    current_msv = await pipeline.load_current_msv(db, payload.bot_id)
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
async def get_bot_identity(
    bot_id: str,
    db: AsyncConnection = Depends(get_db),
    account: AccountContext = Depends(get_account_context),
):
    await verify_bot_access(db, bot_id, account)
    identity = await get_bot_identity(db, bot_id)
    if not identity:
        raise HTTPException(status_code=404, detail="Bot not found")
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
    db: AsyncConnection = Depends(get_db),
    account: AccountContext = Depends(get_account_context),
):
    await verify_bot_access(db, bot_id, account)
    memories = await list_memories(db, bot_id, limit)
    return {"bot_id": bot_id, "memories": memories}


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
