"""SoulOS kernel — FastAPI app factory and middleware."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from starlette.middleware.base import BaseHTTPMiddleware

from auth import (
    resolve_account_context,
    set_mcp_account_context,
)
from config import ACCOUNT_ID_HEADER, GATEWAY_SECRET_HEADER, validate_gateway_secret
from runtime.boot_memory import sync_memory_on_boot
from runtime.bootstrap import init_database, pull_model, wait_for_ollama
from runtime.errors import SoulOSProblem, problem_response, register_exception_handlers
from routes import avatars, chat, health, hybrid, mcp, memory
from versioning import get_product_version

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


app = FastAPI(
    lifespan=lifespan,
    title="SoulOS Kernel",
    version=get_product_version(),
)
register_exception_handlers(app)
app.add_middleware(McpAuthMiddleware)

app.include_router(health.router)
app.include_router(avatars.router)
app.include_router(memory.router)
app.include_router(hybrid.router)
app.include_router(chat.router)
app.include_router(mcp.router)

# Back-compat for tests and patches that target main.* symbols.
from routes import hybrid as hybrid_routes  # noqa: E402
from routes import memory as memory_routes  # noqa: E402

ensure_turn_session = hybrid_routes.ensure_turn_session
get_turn_session = hybrid_routes.get_turn_session
advance_turn_session = hybrid_routes.advance_turn_session
store_turn_success_response = hybrid_routes.store_turn_success_response
delete_turn_session = memory_routes.delete_turn_session

__all__ = [
    "app",
    "McpAuthMiddleware",
    "ensure_turn_session",
    "get_turn_session",
    "advance_turn_session",
    "store_turn_success_response",
    "delete_turn_session",
]
