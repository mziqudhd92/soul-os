import json
import logging
from contextlib import asynccontextmanager

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
from sqlalchemy import text

from auth import get_mcp_account_context
from config import engine
from runtime.avatars import (
    format_identity_prompt,
    get_bot_identity,
    list_avatars,
    register_avatar_record,
)
from runtime.embedder import Embedder
from runtime.memory import ingest_memory as ingest_memory_record
from runtime.memory import list_memories, retrieve_memories
from soul_validation import validate_msv_payload
from tenant import verify_bot_access

logger = logging.getLogger("mcp_server")

mcp_server = Server("soulos-kernel")
_embedder = Embedder()


def _json_text(data: object) -> list[TextContent]:
    return [TextContent(type="text", text=json.dumps(data, indent=2))]


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
                },
                "required": ["bot_id", "query"],
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
    if name == "retrieve_memory":
        bot_id = arguments.get("bot_id")
        query = arguments.get("query")
        top_k = int(arguments.get("top_k") or 5)
        if not bot_id or not query:
            raise ValueError("bot_id and query are required")

        async with _with_verified_bot(bot_id) as conn:
            memories = await retrieve_memories(
                conn, _embedder, bot_id, query, top_k
            )
            await conn.commit()
        return _json_text({"bot_id": bot_id, "query": query, "memories": memories})

    if name == "get_identity":
        bot_id = arguments.get("bot_id")
        if not bot_id:
            raise ValueError("bot_id is required")
        async with _with_verified_bot(bot_id) as conn:
            identity = await get_bot_identity(conn, bot_id)
            await conn.commit()
        if not identity:
            raise ValueError(f"Bot {bot_id} not found")
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
        bot_id = arguments.get("bot_id")
        content = arguments.get("content")
        if not bot_id or not content:
            raise ValueError("bot_id and content are required")

        async with _with_verified_bot(bot_id) as conn:
            await ingest_memory_record(conn, _embedder, bot_id, content)
            await conn.commit()

        return _json_text(
            {"status": "success", "bot_id": bot_id, "message": "Memory ingested"}
        )

    raise ValueError(f"Unknown tool: {name}")
