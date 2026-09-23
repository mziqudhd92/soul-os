import asyncio
import json
import logging
from contextlib import asynccontextmanager

from fastapi import BackgroundTasks
from fastapi.responses import JSONResponse
from mcp.server import Server
from mcp.types import (
    GetPromptResult,
    Prompt,
    PromptArgument,
    PromptMessage,
    Resource,
    ResourceTemplate,
    TextContent,
    Tool,
)
from pydantic import ValidationError
from sqlalchemy import text

from auth import get_mcp_account_context
from config import engine
from dependencies import get_llm_service
from routes.hybrid import hybrid_complete, hybrid_prepare
from runtime.avatars import (
    ensure_avatar_record,
    format_identity_prompt,
    get_bot_identity,
    list_avatars,
    register_avatar_record,
)
from runtime.embedder import Embedder
from runtime.errors import BOT_NOT_FOUND, SOUL_INVALID, SoulOSProblem
from runtime.memory import (
    delete_session_memories,
    forget_memory,
    list_memories,
    retrieve_memories,
)
from runtime.memory import ingest_memory as ingest_memory_record
from runtime.turn_session import delete_turn_session
from schemas import (
    HybridCompleteRequest,
    HybridPrepareRequest,
    MemoryForget,
    MemoryIngest,
    MemoryRetrieve,
)
from soul_validation import validate_msv_payload
from tenant import verify_bot_access

logger = logging.getLogger("mcp_server")

mcp_server = Server("soulos-kernel")
_embedder = Embedder()
# Strong refs so async-reflect tasks scheduled from MCP calls are not GC'd mid-run.
_background: set[asyncio.Task] = set()


def _json_text(data: object) -> list[TextContent]:
    return [TextContent(type="text", text=json.dumps(data, indent=2))]


def _problem(code: str, status: int, detail: str) -> list[TextContent]:
    """RFC 7807-aligned tool error payload (same fields as REST Problem Details)."""
    return _json_text(
        {"error": True, "code": code, "status": status, "detail": detail}
    )


def _parse_object(value: object, field: str) -> dict:
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except json.JSONDecodeError as e:
            raise ValueError(f"{field} must be valid JSON: {e}") from e
    if not isinstance(value, dict):
        raise ValueError(f"{field} must be a JSON object")
    return value


async def _call_route(route, **kwargs) -> dict:
    """Invoke a REST route handler so MCP shares its validation and side effects."""
    async with engine.connect() as conn:
        try:
            result = await route(
                db=conn,
                embedder=_embedder,
                pipeline=get_llm_service(),
                account=get_mcp_account_context(),
                **kwargs,
            )
        except SoulOSProblem as e:
            return {
                "error": True,
                "code": e.code,
                "status": e.status,
                "detail": e.detail,
            }
        await conn.commit()
    if isinstance(result, JSONResponse):
        return json.loads(result.body)
    return result


def _run_background(tasks: BackgroundTasks) -> None:
    if not tasks.tasks:
        return
    task = asyncio.create_task(tasks())
    _background.add(task)
    task.add_done_callback(_background.discard)


_SESSION_ID_PROP = {
    "type": "string",
    "description": "Optional session scope (TTL-purged; see hybrid API)",
}


@asynccontextmanager
async def _with_verified_bot(bot_id: str):
    """Yield a DB connection after optional tenant access check."""
    async with engine.connect() as conn:
        await verify_bot_access(conn, bot_id, get_mcp_account_context())
        yield conn


@mcp_server.list_resources()
async def handle_list_resources() -> list[Resource]:
    return []


@mcp_server.list_resource_templates()
async def handle_list_resource_templates() -> list[ResourceTemplate]:
    return [
        ResourceTemplate(
            uriTemplate="memory://episodic/{bot_id}",
            name="Bot Episodic Memory",
            description="Recent episodic memories for an avatar (chronological log)",
        ),
        ResourceTemplate(
            uriTemplate="soul://identity/{bot_id}",
            name="Avatar Identity",
            description="Name, role, description, baseline and current MSV as JSON",
        ),
    ]


@mcp_server.read_resource()
async def handle_read_resource(uri: str) -> str:
    if uri.startswith("memory://episodic/"):
        bot_id = uri.split("/")[-1]
        async with _with_verified_bot(bot_id) as conn:
            memories = await list_memories(conn, bot_id, 50)
            await conn.commit()
            return json.dumps(memories, indent=2)

    if uri.startswith("soul://identity/"):
        bot_id = uri.split("/")[-1]
        async with _with_verified_bot(bot_id) as conn:
            identity = await get_bot_identity(conn, bot_id)
            await conn.commit()
            if not identity:
                raise ValueError(f"Bot {bot_id} not found")
            return json.dumps(identity, indent=2)

    raise ValueError(f"Unknown resource: {uri}")


@mcp_server.list_prompts()
async def handle_list_prompts() -> list[Prompt]:
    return [
        Prompt(
            name="identity",
            description="Persona and current MSV for prompt injection.",
            arguments=[
                PromptArgument(
                    name="bot_id", description="The UUID of the avatar", required=True
                )
            ],
        )
    ]


@mcp_server.get_prompt()
async def handle_get_prompt(name: str, arguments: dict | None) -> GetPromptResult:
    if name == "identity":
        bot_id = (arguments or {}).get("bot_id")
        if not bot_id:
            raise ValueError("bot_id is required")
        async with _with_verified_bot(bot_id) as conn:
            identity = await get_bot_identity(conn, bot_id)
            await conn.commit()
            if not identity:
                raise ValueError(f"Bot {bot_id} not found")
            content = format_identity_prompt(identity)
            return GetPromptResult(
                description=f"Identity for {identity['name']}",
                messages=[
                    PromptMessage(
                        role="user",
                        content=TextContent(type="text", text=content),
                    )
                ],
            )
    raise ValueError(f"Unknown prompt: {name}")


@mcp_server.list_tools()
async def handle_list_tools() -> list[Tool]:
    return [
        Tool(
            name="ingest_memory",
            description="Store episodic memory for an avatar (pgvector).",
            inputSchema={
                "type": "object",
                "properties": {
                    "bot_id": {"type": "string", "description": "Avatar UUID"},
                    "content": {
                        "type": "string",
                        "description": "Memory text to embed and store",
                    },
                    "session_id": _SESSION_ID_PROP,
                },
                "required": ["bot_id", "content"],
            },
        ),
        Tool(
            name="retrieve_memory",
            description="Semantic recall from episodic memory (RAG).",
            inputSchema={
                "type": "object",
                "properties": {
                    "bot_id": {"type": "string"},
                    "query": {"type": "string"},
                    "top_k": {
                        "type": "integer",
                        "description": "Max memories to return",
                        "default": 5,
                    },
                    "session_id": _SESSION_ID_PROP,
                },
                "required": ["bot_id", "query"],
            },
        ),
        Tool(
            name="forget_memory",
            description="Delete episodic memories whose content contains content_match.",
            inputSchema={
                "type": "object",
                "properties": {
                    "bot_id": {"type": "string"},
                    "content_match": {
                        "type": "string",
                        "description": "Substring to match (case-insensitive)",
                    },
                },
                "required": ["bot_id", "content_match"],
            },
        ),
        Tool(
            name="delete_session",
            description="Delete session-scoped memories and turn-contract state.",
            inputSchema={
                "type": "object",
                "properties": {
                    "bot_id": {"type": "string"},
                    "session_id": {"type": "string"},
                },
                "required": ["bot_id", "session_id"],
            },
        ),
        Tool(
            name="ensure_avatar",
            description=(
                "Idempotent avatar bootstrap: return the avatar for external_key, "
                "registering it from soul if missing."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "external_key": {
                        "type": "string",
                        "description": "Stable app key, e.g. 'my-app:user-1'",
                    },
                    "soul": {"type": "object", "description": "Full soul payload"},
                    "runtime_config": {"type": "object"},
                },
                "required": ["external_key", "soul"],
            },
        ),
        Tool(
            name="hybrid_prepare",
            description=(
                "Hybrid sidecar step 1: recall memories and build a persona "
                "system_prompt for your own LLM."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "bot_id": {"type": "string"},
                    "query": {"type": "string", "description": "User message"},
                    "session_id": _SESSION_ID_PROP,
                    "top_k": {"type": "integer", "default": 5},
                },
                "required": ["bot_id", "query"],
            },
        ),
        Tool(
            name="hybrid_complete",
            description=(
                "Hybrid sidecar step 2: ingest the turn summary and optionally run "
                "System 2 reflection (same contract as POST /hybrid/complete)."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "bot_id": {"type": "string"},
                    "summary": {"type": "string", "description": "Turn summary"},
                    "user_message": {"type": "string"},
                    "session_id": _SESSION_ID_PROP,
                    "reflect": {"type": "boolean", "default": True},
                    "reflect_async": {"type": "boolean", "default": False},
                    "filled_slots": {"type": "object"},
                    "intent": {"type": "string"},
                    "assistant_text": {"type": "string"},
                    "expected_version": {"type": "integer"},
                    "expected_step": {"type": "string"},
                    "idempotency_key": {"type": "string"},
                    "advance": {"type": "boolean", "default": True},
                },
                "required": ["bot_id", "summary"],
            },
        ),
        Tool(
            name="get_identity",
            description="Avatar persona and baseline/current MSV as JSON.",
            inputSchema={
                "type": "object",
                "properties": {
                    "bot_id": {"type": "string"},
                },
                "required": ["bot_id"],
            },
        ),
        Tool(
            name="register_avatar",
            description="Register a new avatar from a .soul.json payload.",
            inputSchema={
                "type": "object",
                "properties": {
                    "soul": {
                        "type": "object",
                        "description": "Full soul file (name, role, baseline_msv, ...)",
                    },
                },
                "required": ["soul"],
            },
        ),
        Tool(
            name="list_avatars",
            description="List avatars (tenant-scoped when auth is enabled).",
            inputSchema={
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "Max avatars (1-50)",
                        "default": 50,
                    },
                },
            },
        ),
        Tool(
            name="update_cognitive_state",
            description="Force-update the Metacognitive State Vector (MSV).",
            inputSchema={
                "type": "object",
                "properties": {
                    "bot_id": {"type": "string"},
                    "new_msv": {
                        "type": "string",
                        "description": "JSON string or object of the new MSV",
                    },
                },
                "required": ["bot_id", "new_msv"],
            },
        ),
    ]


@mcp_server.call_tool()
async def handle_call_tool(name: str, arguments: dict) -> list[TextContent]:
    try:
        return await _dispatch_tool(name, arguments)
    except SoulOSProblem as e:
        return _problem(e.code, e.status, e.detail)
    except (ValueError, ValidationError) as e:
        return _problem(SOUL_INVALID, 422, str(e))


async def _dispatch_tool(name: str, arguments: dict) -> list[TextContent]:
    if name == "retrieve_memory":
        payload = MemoryRetrieve.model_validate(
            {
                "bot_id": arguments.get("bot_id"),
                "query": arguments.get("query"),
                "top_k": int(arguments.get("top_k") or 5),
                "session_id": arguments.get("session_id"),
            }
        )

        async with _with_verified_bot(payload.bot_id) as conn:
            memories = await retrieve_memories(
                conn,
                _embedder,
                payload.bot_id,
                payload.query,
                payload.top_k,
                payload.session_id,
            )
            await conn.commit()
        return _json_text(
            {"bot_id": payload.bot_id, "query": payload.query, "memories": memories}
        )

    if name == "forget_memory":
        payload = MemoryForget.model_validate(
            {
                "bot_id": arguments.get("bot_id"),
                "content_match": arguments.get("content_match"),
            }
        )
        async with _with_verified_bot(payload.bot_id) as conn:
            deleted = await forget_memory(
                conn, payload.bot_id, payload.content_match
            )
            await conn.commit()
        return _json_text(
            {"status": "success", "bot_id": payload.bot_id, "deleted": deleted}
        )

    if name == "delete_session":
        bot_id = arguments.get("bot_id")
        session_id = arguments.get("session_id")
        if not bot_id or not session_id:
            raise ValueError("bot_id and session_id are required")
        async with _with_verified_bot(bot_id) as conn:
            deleted = await delete_session_memories(conn, bot_id, session_id)
            turn_deleted = await delete_turn_session(conn, bot_id, session_id)
            await conn.commit()
        return _json_text(
            {
                "status": "success",
                "deleted": deleted,
                "turn_sessions_deleted": turn_deleted,
                "bot_id": bot_id,
                "session_id": session_id,
            }
        )

    if name == "ensure_avatar":
        external_key = arguments.get("external_key")
        if not external_key or not arguments.get("soul"):
            raise ValueError("external_key and soul are required")
        soul = _parse_object(arguments["soul"], "soul")
        runtime_config = arguments.get("runtime_config")
        if runtime_config is not None:
            runtime_config = _parse_object(runtime_config, "runtime_config")
        account = get_mcp_account_context()
        async with engine.connect() as conn:
            record = await ensure_avatar_record(
                conn, account.account_id, external_key, soul, runtime_config
            )
            await conn.commit()
        return _json_text(record)

    if name == "hybrid_prepare":
        if not arguments.get("bot_id") or not arguments.get("query"):
            raise ValueError("bot_id and query are required")
        payload = HybridPrepareRequest.model_validate(arguments)
        return _json_text(await _call_route(hybrid_prepare, payload=payload))

    if name == "hybrid_complete":
        if not arguments.get("bot_id") or not arguments.get("summary"):
            raise ValueError("bot_id and summary are required")
        payload = HybridCompleteRequest.model_validate(arguments)
        tasks = BackgroundTasks()
        body = await _call_route(hybrid_complete, payload=payload, background_tasks=tasks)
        _run_background(tasks)
        return _json_text(body)

    if name == "get_identity":
        bot_id = arguments.get("bot_id")
        if not bot_id:
            raise ValueError("bot_id is required")
        async with _with_verified_bot(bot_id) as conn:
            identity = await get_bot_identity(conn, bot_id)
            await conn.commit()
        if not identity:
            return _problem(BOT_NOT_FOUND, 404, f"Bot not found: {bot_id}")
        return _json_text(identity)

    if name == "register_avatar":
        soul = arguments.get("soul")
        if not soul:
            raise ValueError("soul is required")
        if isinstance(soul, str):
            try:
                soul = json.loads(soul)
            except json.JSONDecodeError as e:
                raise ValueError(f"soul must be valid JSON: {e}") from e
        if not isinstance(soul, dict):
            raise ValueError("soul must be a JSON object")

        account = get_mcp_account_context()
        async with engine.connect() as conn:
            record = await register_avatar_record(conn, account.account_id, soul)
            await conn.commit()
        return _json_text(record)

    if name == "list_avatars":
        limit = int(arguments.get("limit") or 50)
        account = get_mcp_account_context()
        async with engine.connect() as conn:
            avatars = await list_avatars(conn, account.account_id, limit)
            await conn.commit()
        return _json_text({"avatars": avatars})

    if name == "update_cognitive_state":
        bot_id = arguments.get("bot_id")
        new_msv_raw = arguments.get("new_msv")
        if not bot_id or not new_msv_raw:
            raise ValueError("bot_id and new_msv are required")

        if isinstance(new_msv_raw, str):
            try:
                new_msv_dict = json.loads(new_msv_raw)
            except json.JSONDecodeError as e:
                raise ValueError(f"new_msv must be valid JSON: {e}") from e
        elif isinstance(new_msv_raw, dict):
            new_msv_dict = new_msv_raw
        else:
            raise ValueError("new_msv must be a JSON string or object")

        validated_msv = validate_msv_payload(new_msv_dict)
        msv_json = json.dumps(validated_msv)

        async with _with_verified_bot(bot_id) as conn:
            await conn.execute(
                text("UPDATE bots SET current_msv = :msv WHERE id = :id"),
                {"msv": msv_json, "id": bot_id},
            )
            await conn.commit()

        return _json_text(
            {
                "status": "success",
                "bot_id": bot_id,
                "message": "Cognitive state (MSV) updated",
            }
        )

    if name == "ingest_memory":
        payload = MemoryIngest.model_validate(
            {
                "bot_id": arguments.get("bot_id"),
                "content": arguments.get("content"),
                "session_id": arguments.get("session_id"),
            }
        )

        async with _with_verified_bot(payload.bot_id) as conn:
            await ingest_memory_record(
                conn,
                _embedder,
                payload.bot_id,
                payload.content,
                payload.session_id,
            )
            await conn.commit()

        return _json_text(
            {
                "status": "success",
                "bot_id": payload.bot_id,
                "message": "Memory ingested",
            }
        )

    raise ValueError(f"Unknown tool: {name}")
