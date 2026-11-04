"""SoulOS kernel MCP server (MCP Python SDK 2.x) — thin adapter over runtime/."""

from __future__ import annotations

import asyncio
import json
import logging
from contextlib import asynccontextmanager
from contextvars import ContextVar
from pathlib import Path
from typing import Any

from fastapi import BackgroundTasks
from fastapi.responses import JSONResponse
from mcp.server import Server
from mcp.server.context import ServerRequestContext
from mcp.types import (
    CallToolRequestParams,
    CallToolResult,
    GetPromptRequestParams,
    GetPromptResult,
    ListPromptsResult,
    ListResourcesResult,
    ListResourceTemplatesResult,
    ListToolsResult,
    PaginatedRequestParams,
    Prompt,
    PromptArgument,
    PromptMessage,
    ReadResourceRequestParams,
    ReadResourceResult,
    ResourceTemplate,
    TextContent,
    TextResourceContents,
    Tool,
)
from pydantic import ValidationError

from auth import AccountContext, get_mcp_account_context
from config import (
    CONSOLIDATE_MIN_CANDIDATES,
    MCP_EPISODIC_DEFAULT_LIMIT,
    MCP_EPISODIC_MAX_LIMIT,
    SOULOS_MCP_ADMIN_TOOLS,
    engine,
)
from dependencies import get_llm_service
from runtime.avatars import (
    ensure_avatar_record,
    format_identity_prompt,
    get_bot_identity,
    list_avatars,
    register_avatar_record,
)
from runtime.cognitive_msv import (
    apply_msv_delta,
    force_update_msv,
    msv_drift_payload,
    reflect_cognitive_state,
)
from runtime.conversation_memory import (
    ingest_conversation_memory,
    normalize_conversation_id,
    require_tenant_uuid,
    retrieve_conversation_memory_hits,
)
from runtime.embedder import Embedder
from runtime.errors import ACCESS_DENIED, BOT_NOT_FOUND, SOUL_INVALID, SoulOSProblem
from runtime.handoffs import create_handoff_record
from runtime.hybrid_service import complete_hybrid_turn, prepare_hybrid_turn
from runtime.mcp_ids import McpIdError, parse_resource_uri, validate_bot_id, validate_session_id
from runtime.mcp_rate_limit import (
    consolidate_limiter,
    rate_limit_key,
    reflect_limiter,
)
from runtime.memory import (
    delete_session_memories,
    forget_memory,
    list_memories,
    retrieve_memory_hits,
)
from runtime.memory import ingest_memory as ingest_memory_record
from runtime.memory_cognitive import rerank_hits_for_persona
from runtime.memory_consolidate import consolidate_memories
from runtime.memory_rank import hit_contents
from runtime.memory_trust import (
    TRUST_EXTERNAL_MCP,
    quarantine_untrusted,
    should_skip_as_duplicate,
)
from runtime.msv_update import HEXACO_KEYS, HEXACO_TRAIT_NAMES, SEMANTIC_SHIFT_DELTAS
from runtime.security_context import (
    SCOPE_MCP_ADMIN_MSV_WRITE,
    SecurityContext,
    security_context_from_account,
)
from runtime.turn_session import delete_turn_session, get_turn_session
from schemas import (
    HybridCompleteRequest,
    HybridPrepareRequest,
    MemoryForget,
    MemoryIngest,
    MemoryRetrieve,
)
from tenant import verify_bot_access

logger = logging.getLogger("mcp_server")

_embedder = Embedder()
_background: set[asyncio.Task] = set()
_mcp_security_context: ContextVar[SecurityContext | None] = ContextVar(
    "mcp_security_context", default=None
)

_SPEC_SOUL_SCHEMA = (
    Path(__file__).resolve().parents[2] / "spec" / "soul.schema.json"
)


def set_mcp_security_context(ctx: SecurityContext | None) -> None:
    """Bind SecurityContext to the current task (ContextVar — not process-global)."""
    _mcp_security_context.set(ctx)


def get_mcp_security_context() -> SecurityContext:
    ctx = _mcp_security_context.get()
    if ctx is not None:
        return ctx
    return security_context_from_account(
        get_mcp_account_context(),
        admin_tools_enabled=SOULOS_MCP_ADMIN_TOOLS,
    )


def require_security_context() -> SecurityContext:
    return get_mcp_security_context()


def _json_text(data: object) -> list[TextContent]:
    return [TextContent(type="text", text=json.dumps(data, indent=2))]


def _problem(code: str, status: int, detail: str) -> list[TextContent]:
    return _json_text(
        {"error": True, "code": code, "status": status, "detail": detail}
    )


def _error_result(code: str, status: int, detail: str) -> CallToolResult:
    return CallToolResult(
        content=_problem(code, status, detail),
        is_error=True,
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
async def _with_verified_bot(bot_id: str, sec: SecurityContext):
    bot_id = validate_bot_id(bot_id)
    async with engine.connect() as conn:
        await verify_bot_access(conn, bot_id, sec.account)
        yield conn, bot_id


def _admin_msv_enabled(sec: SecurityContext) -> bool:
    return sec.has_admin_msv_write() or SOULOS_MCP_ADMIN_TOOLS


# --- Resources / prompts / tools listings ------------------------------------


async def handle_list_resources() -> list:
    return []


async def handle_list_resource_templates() -> list[ResourceTemplate]:
    return [
        ResourceTemplate(
            uri_template="memory://episodic/{bot_id}",
            name="Bot Episodic Memory",
            description=(
                "Recent episodic memories (default last 50; ?limit=N, max 100). "
                "Use retrieve_memory / retrieve_conversation_memory for semantic search."
            ),
        ),
        ResourceTemplate(
            uri_template="soul://identity/{bot_id}",
            name="Avatar Identity",
            description="Name, role, description, baseline and current MSV as JSON",
        ),
        ResourceTemplate(
            uri_template="session://turn/{bot_id}/{session_id}",
            name="Turn Session",
            description="Turn-contract session state JSON",
        ),
        ResourceTemplate(
            uri_template="soul://schema",
            name="Soul Schema",
            description="SoulOS soul.schema.json",
        ),
        ResourceTemplate(
            uri_template="msv://drift/{bot_id}",
            name="MSV Drift",
            description=(
                "Snapshot baseline vs current MSV with delta and behavioral_summary "
                "(not a time-series history)"
            ),
        ),
    ]


async def handle_read_resource(uri: str) -> str:
    sec = require_security_context()
    parsed = parse_resource_uri(
        uri,
        default_episodic_limit=MCP_EPISODIC_DEFAULT_LIMIT,
        max_limit=MCP_EPISODIC_MAX_LIMIT,
    )
    if parsed.kind == "schema":
        if _SPEC_SOUL_SCHEMA.is_file():
            return _SPEC_SOUL_SCHEMA.read_text(encoding="utf-8")
        return json.dumps({"error": "soul.schema.json not found"})

    assert parsed.bot_id is not None
    async with _with_verified_bot(parsed.bot_id, sec) as (conn, bot_id):
        if parsed.kind == "episodic":
            memories = await list_memories(
                conn, bot_id, parsed.limit or MCP_EPISODIC_DEFAULT_LIMIT
            )
            await conn.commit()
            return json.dumps(memories, indent=2)
        if parsed.kind == "identity":
            identity = await get_bot_identity(conn, bot_id)
            await conn.commit()
            if not identity:
                raise ValueError(f"Bot {bot_id} not found")
            return json.dumps(identity, indent=2)
        if parsed.kind == "drift":
            identity = await get_bot_identity(conn, bot_id)
            await conn.commit()
            if not identity:
                raise ValueError(f"Bot {bot_id} not found")
            return json.dumps(msv_drift_payload(identity), indent=2)
        if parsed.kind == "turn":
            session = await get_turn_session(conn, bot_id, parsed.session_id or "")
            await conn.commit()
            if not session:
                raise ValueError("Turn session not found")
            return json.dumps(session, indent=2)
    raise ValueError(f"Unknown resource: {uri}")


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
        ),
        Prompt(
            name="hybrid_turn",
            description=(
                "Hydrated hybrid turn: prepare runs server-side. "
                "Generate the user-facing reply, then call hybrid_complete with "
                "turn_token/expected_version to commit."
            ),
            arguments=[
                PromptArgument(name="bot_id", description="Avatar id", required=True),
                PromptArgument(name="query", description="User message", required=True),
                PromptArgument(
                    name="session_id", description="Session / turn scope", required=False
                ),
            ],
        ),
        Prompt(
            name="soul_author",
            description="Guide drafting a .soul.json against soul://schema.",
            arguments=[
                PromptArgument(
                    name="role", description="Intended avatar role", required=False
                )
            ],
        ),
        Prompt(
            name="debug_msv",
            description="Explain baseline vs current MSV and safe mutation tools.",
            arguments=[
                PromptArgument(name="bot_id", description="Avatar id", required=True)
            ],
        ),
    ]


async def handle_get_prompt(name: str, arguments: dict | None) -> GetPromptResult:
    sec = require_security_context()
    args = arguments or {}
    if name == "identity":
        bot_id = validate_bot_id(args.get("bot_id"))
        async with _with_verified_bot(bot_id, sec) as (conn, bid):
            identity = await get_bot_identity(conn, bid)
            await conn.commit()
            if not identity:
                raise ValueError(f"Bot {bid} not found")
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
    if name == "hybrid_turn":
        bot_id = validate_bot_id(args.get("bot_id"))
        query = args.get("query")
        if not query:
            raise ValueError("query is required")
        payload = HybridPrepareRequest(
            bot_id=bot_id,
            query=query,
            session_id=args.get("session_id"),
        )
        async with engine.connect() as conn:
            body = await prepare_hybrid_turn(
                conn, _embedder, get_llm_service(), sec.account, payload
            )
            await conn.commit()
        commit_hint = (
            "COMMIT REQUIRED: After you generate the assistant reply, call tool "
            "hybrid_complete with bot_id, summary, user_message, session_id, and "
            f"expected_version={body.get('expected_version')!r} / turn_token="
            f"{body.get('turn_token')!r}. Skipping hybrid_complete drops memory/MSV updates."
        )
        messages = [
            PromptMessage(
                role="user",
                content=TextContent(
                    type="text",
                    text=json.dumps(
                        {
                            "system_prompt": body.get("system_prompt"),
                            "memories": body.get("memories"),
                            "behavioral_summary": body.get("behavioral_summary"),
                            "identity": body.get("identity"),
                            "turn_token": body.get("turn_token"),
                            "expected_version": body.get("expected_version"),
                            "contract_context": body.get("contract_context"),
                            "instructions": commit_hint,
                        },
                        indent=2,
                    ),
                ),
            )
        ]
        return GetPromptResult(description="Hydrated hybrid turn", messages=messages)
    if name == "soul_author":
        role = args.get("role") or "assistant"
        text = (
            f"Draft a SoulOS .soul.json for role={role}. "
            "Read resource soul://schema. Include name, role, description, "
            "attachment_style, baseline_msv with HEXACO keys H,E,X,A,C,O in [-1,1]."
        )
        return GetPromptResult(
            description="Soul authoring guide",
            messages=[
                PromptMessage(role="user", content=TextContent(type="text", text=text))
            ],
        )
    if name == "debug_msv":
        bot_id = validate_bot_id(args.get("bot_id"))
        async with _with_verified_bot(bot_id, sec) as (conn, bid):
            identity = await get_bot_identity(conn, bid)
            await conn.commit()
            if not identity:
                raise ValueError(f"Bot {bid} not found")
            drift = msv_drift_payload(identity)
        admin_note = (
            "Admin force update_cognitive_state is available."
            if _admin_msv_enabled(sec)
            else "Prefer apply_msv_delta (semantic shifts) or reflect_cognitive_state; "
            "force update is hidden without mcp:admin:msv_write."
        )
        text = json.dumps({**drift, "guidance": admin_note}, indent=2)
        return GetPromptResult(
            description="MSV debug",
            messages=[
                PromptMessage(role="user", content=TextContent(type="text", text=text))
            ],
        )
    raise ValueError(f"Unknown prompt: {name}")


def _tool_apply_msv_delta() -> Tool:
    return Tool(
        name="apply_msv_delta",
        description=(
            "Apply a categorical HEXACO shift after emotionally meaningful turns. "
            "Do not use for routine factual Q&A. Requires appraisal_reasoning first. "
            "Side effect: updates current_msv with clamped EMA-safe delta."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "appraisal_reasoning": {
                    "type": "string",
                    "description": "Why this interaction warrants an MSV shift (required first)",
                },
                "bot_id": {"type": "string"},
                "trait": {
                    "type": "string",
                    "description": "HEXACO letter H|E|X|A|C|O",
                    "enum": list(HEXACO_KEYS),
                },
                "shift": {
                    "type": "string",
                    "enum": list(SEMANTIC_SHIFT_DELTAS.keys()),
                },
            },
            "required": ["appraisal_reasoning", "bot_id", "trait", "shift"],
        },
    )


async def handle_list_tools() -> list[Tool]:
    sec = get_mcp_security_context()
    tools = [
        Tool(
            name="ingest_memory",
            description=(
                "Store a salient episodic memory. Avoid trivial chitchat; "
                "near-duplicates may be skipped. Side effect: writes episodic store."
            ),
            input_schema={
                "type": "object",
                "properties": {
                    "bot_id": {"type": "string"},
                    "content": {"type": "string"},
                    "session_id": _SESSION_ID_PROP,
                    "importance": {"type": "number", "default": 0.6},
                },
                "required": ["bot_id", "content"],
            },
        ),
        Tool(
            name="retrieve_memory",
            description=(
                "Semantic recall from episodic memory. Prefer over dumping "
                "memory://episodic resources for Q&A."
            ),
            input_schema={
                "type": "object",
                "properties": {
                    "bot_id": {"type": "string"},
                    "query": {"type": "string"},
                    "top_k": {"type": "integer", "default": 5},
                    "session_id": _SESSION_ID_PROP,
                    "recency_weight": {"type": "number", "default": 0.0},
                    "mood_congruent": {"type": "boolean", "default": False},
                },
                "required": ["bot_id", "query"],
            },
        ),
        Tool(
            name="forget_memory",
            description="Delete episodic memories containing content_match (GDPR-style).",
            input_schema={
                "type": "object",
                "properties": {
                    "bot_id": {"type": "string"},
                    "content_match": {"type": "string"},
                },
                "required": ["bot_id", "content_match"],
            },
        ),
        Tool(
            name="delete_session",
            description="Delete session-scoped memories and turn-contract state.",
            input_schema={
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
            description="Idempotent avatar bootstrap by external_key.",
            input_schema={
                "type": "object",
                "properties": {
                    "external_key": {"type": "string"},
                    "soul": {"type": "object"},
                    "runtime_config": {"type": "object"},
                },
                "required": ["external_key", "soul"],
            },
        ),
        Tool(
            name="hybrid_prepare",
            description=(
                "Build persona system_prompt + memories for your LLM. "
                "Always follow with hybrid_complete to commit the turn."
            ),
            input_schema={
                "type": "object",
                "properties": {
                    "bot_id": {"type": "string"},
                    "query": {"type": "string"},
                    "session_id": _SESSION_ID_PROP,
                    "top_k": {"type": "integer", "default": 5},
                },
                "required": ["bot_id", "query"],
            },
        ),
        Tool(
            name="hybrid_complete",
            description=(
                "COMMIT the hybrid turn: ingest summary and optional reflect. "
                "Required after generating the assistant reply; pass expected_version "
                "from prepare/hybrid_turn."
            ),
            input_schema={
                "type": "object",
                "properties": {
                    "bot_id": {"type": "string"},
                    "summary": {"type": "string"},
                    "user_message": {"type": "string"},
                    "session_id": _SESSION_ID_PROP,
                    "reflect": {"type": "boolean", "default": True},
                    "reflect_async": {"type": "boolean", "default": False},
                    "expected_version": {"type": "integer"},
                    "expected_step": {"type": "string"},
                    "idempotency_key": {"type": "string"},
                    "advance": {"type": "boolean", "default": True},
                    "filled_slots": {"type": "object"},
                    "intent": {"type": "string"},
                    "assistant_text": {"type": "string"},
                },
                "required": ["bot_id", "summary"],
            },
        ),
        Tool(
            name="get_identity",
            description="Read persona + baseline/current MSV JSON.",
            input_schema={
                "type": "object",
                "properties": {"bot_id": {"type": "string"}},
                "required": ["bot_id"],
            },
        ),
        Tool(
            name="register_avatar",
            description="Register a new avatar from a full .soul.json (high privilege).",
            input_schema={
                "type": "object",
                "properties": {"soul": {"type": "object"}},
                "required": ["soul"],
            },
        ),
        Tool(
            name="list_avatars",
            description="List avatars (tenant-scoped when auth enabled).",
            input_schema={
                "type": "object",
                "properties": {"limit": {"type": "integer", "default": 50}},
            },
        ),
        _tool_apply_msv_delta(),
        Tool(
            name="reflect_cognitive_state",
            description=(
                "Run System 2 reflection after emotionally charged turns or goal "
                "transitions. Do not call on routine factual queries. Rate-limited. "
                "Requires appraisal_reasoning."
            ),
            input_schema={
                "type": "object",
                "properties": {
                    "appraisal_reasoning": {"type": "string"},
                    "bot_id": {"type": "string"},
                    "message": {"type": "string"},
                    "reflect_async": {"type": "boolean", "default": False},
                },
                "required": ["appraisal_reasoning", "bot_id", "message"],
            },
        ),
        Tool(
            name="ingest_conversation_memory",
            description=(
                "Write shared conversation memory with salience/novelty gating. "
                "Tagged trust_level=external_mcp when written via MCP."
            ),
            input_schema={
                "type": "object",
                "properties": {
                    "conversation_id": {"type": "string"},
                    "content": {"type": "string"},
                    "source_bot_id": {"type": "string"},
                    "importance": {"type": "number", "default": 0.6},
                },
                "required": ["conversation_id", "content"],
            },
        ),
        Tool(
            name="retrieve_conversation_memory",
            description=(
                "Semantic retrieve over shared conversation memory. "
                "Optional mood_congruent rerank requires bot_id for current MSV."
            ),
            input_schema={
                "type": "object",
                "properties": {
                    "conversation_id": {"type": "string"},
                    "query": {"type": "string"},
                    "top_k": {"type": "integer", "default": 5},
                    "bot_id": {"type": "string"},
                    "recency_weight": {"type": "number", "default": 0.0},
                    "mood_congruent": {"type": "boolean", "default": False},
                },
                "required": ["conversation_id", "query"],
            },
        ),
        Tool(
            name="create_handoff",
            description=(
                "Hand off to another bot in the same tenant. Target must be in "
                "source allowed_handoff_targets when configured. Pass structured "
                "task_summary, unresolved_constraints, user_emotional_state, "
                "source_bot_stance."
            ),
            input_schema={
                "type": "object",
                "properties": {
                    "from_bot_id": {"type": "string"},
                    "to_bot_id": {"type": "string"},
                    "from_role": {"type": "string"},
                    "to_role": {"type": "string"},
                    "conversation_id": {"type": "string"},
                    "reason": {"type": "string"},
                    "summary": {"type": "string"},
                    "task_summary": {"type": "string"},
                    "unresolved_constraints": {
                        "oneOf": [
                            {"type": "string"},
                            {"type": "array", "items": {"type": "string"}},
                        ]
                    },
                    "user_emotional_state": {"type": "string"},
                    "source_bot_stance": {"type": "string"},
                    "user_message": {"type": "string"},
                    "idempotency_key": {"type": "string"},
                    "expected_version": {"type": "integer"},
                },
                "required": [
                    "from_bot_id",
                    "to_bot_id",
                    "from_role",
                    "to_role",
                    "conversation_id",
                    "reason",
                    "summary",
                    "task_summary",
                    "unresolved_constraints",
                    "user_emotional_state",
                    "source_bot_stance",
                ],
            },
        ),
        Tool(
            name="consolidate_memory",
            description=(
                "Compress low-importance episodics into semantic memory. "
                "Destructive; no-ops if too few candidates (too_early). Rate-limited."
            ),
            input_schema={
                "type": "object",
                "properties": {
                    "bot_id": {"type": "string"},
                    "session_id": _SESSION_ID_PROP,
                    "limit": {"type": "integer", "default": 8},
                },
                "required": ["bot_id"],
            },
        ),
    ]
    if _admin_msv_enabled(sec):
        tools.append(
            Tool(
                name="update_cognitive_state",
                description=(
                    "ADMIN: force-overwrite current_msv. Requires mcp:admin:msv_write "
                    "or SOULOS_MCP_ADMIN_TOOLS=1. Prefer apply_msv_delta / reflect."
                ),
                input_schema={
                    "type": "object",
                    "properties": {
                        "bot_id": {"type": "string"},
                        "new_msv": {"type": "object"},
                    },
                    "required": ["bot_id", "new_msv"],
                },
            )
        )
    return tools


async def handle_call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Backward-compatible helper returning TextContent list (tests)."""
    result = await _call_tool_result(name, arguments)
    return list(result.content)


async def _call_tool_result(name: str, arguments: dict) -> CallToolResult:
    try:
        content = await _dispatch_tool(name, arguments)
        return CallToolResult(content=content, is_error=False)
    except SoulOSProblem as e:
        return _error_result(e.code, e.status, e.detail)
    except McpIdError as e:
        return _error_result(SOUL_INVALID, 422, str(e))
    except (ValueError, ValidationError) as e:
        return _error_result(SOUL_INVALID, 422, str(e))


async def _dispatch_tool(name: str, arguments: dict) -> list[TextContent]:
    sec = require_security_context()
    arguments = dict(arguments or {})

    if name == "update_cognitive_state":
        if not _admin_msv_enabled(sec):
            raise SoulOSProblem(
                ACCESS_DENIED,
                403,
                "update_cognitive_state requires mcp:admin:msv_write scope",
            )
        bot_id = validate_bot_id(arguments.get("bot_id"))
        new_msv = arguments.get("new_msv")
        if isinstance(new_msv, str):
            new_msv = json.loads(new_msv)
        # Validate before DB so unit tests can assert schema errors without engine.
        from soul_validation import validate_msv_payload

        try:
            if not isinstance(new_msv, dict):
                raise ValueError("new_msv must be an object")
            validate_msv_payload(new_msv)
        except ValueError as e:
            raise SoulOSProblem(SOUL_INVALID, 422, str(e)) from e
        async with engine.connect() as conn:
            body = await force_update_msv(conn, sec.account, bot_id, new_msv)
            await conn.commit()
        return _json_text(body)

    if name == "apply_msv_delta":
        bot_id = validate_bot_id(arguments.get("bot_id"))
        appraisal = arguments.get("appraisal_reasoning") or ""
        if not str(appraisal).strip():
            raise SoulOSProblem(
                SOUL_INVALID,
                422,
                "appraisal_reasoning is required before MSV mutation "
                "(explain why the interaction warrants a shift)",
            )
        async with engine.connect() as conn:
            body = await apply_msv_delta(
                conn,
                sec.account,
                bot_id=bot_id,
                appraisal_reasoning=appraisal,
                trait=arguments.get("trait") or "",
                shift=arguments.get("shift") or "",
            )
            await conn.commit()
        return _json_text(body)

    if name == "reflect_cognitive_state":
        key = rate_limit_key(sec.tenant_id, "reflect")
        if not reflect_limiter.allow(key):
            raise SoulOSProblem(
                "RATE_LIMITED", 429, "reflect_cognitive_state rate limit exceeded"
            )
        bot_id = validate_bot_id(arguments.get("bot_id"))
        tasks = BackgroundTasks()
        async with engine.connect() as conn:
            body = await reflect_cognitive_state(
                conn,
                get_llm_service(),
                sec.account,
                bot_id=bot_id,
                message=arguments.get("message") or "",
                appraisal_reasoning=arguments.get("appraisal_reasoning") or "",
                reflect_async=bool(arguments.get("reflect_async")),
                add_background_task=tasks.add_task,
            )
            await conn.commit()
        _run_background(tasks)
        if isinstance(body, JSONResponse):
            return _json_text(json.loads(body.body))
        return _json_text(body)

    if name == "retrieve_memory":
        bot_id = validate_bot_id(arguments.get("bot_id"))
        payload = MemoryRetrieve.model_validate(
            {
                "bot_id": bot_id,
                "query": arguments.get("query"),
                "top_k": int(arguments.get("top_k") or 5),
                "session_id": validate_session_id(
                    arguments.get("session_id"), required=False
                ),
            }
        )
        recency_weight = float(arguments.get("recency_weight") or 0.0)
        mood_congruent = bool(arguments.get("mood_congruent"))
        async with _with_verified_bot(payload.bot_id, sec) as (conn, _):
            hits = await retrieve_memory_hits(
                conn,
                _embedder,
                payload.bot_id,
                payload.query,
                max(payload.top_k * 2, payload.top_k),
                payload.session_id,
            )
            current_msv = None
            if mood_congruent:
                identity = await get_bot_identity(conn, payload.bot_id)
                current_msv = (identity or {}).get("current_msv")
            ranked = rerank_hits_for_persona(
                hits,
                top_k=payload.top_k,
                recency_weight=recency_weight,
                mood_congruent=mood_congruent,
                current_msv=current_msv if isinstance(current_msv, dict) else None,
            )
            memories = hit_contents(ranked)
            await conn.commit()
        return _json_text(
            {
                "bot_id": payload.bot_id,
                "query": payload.query,
                "memories": memories,
                "recency_weight": recency_weight,
                "mood_congruent": mood_congruent,
            }
        )

    if name == "forget_memory":
        payload = MemoryForget.model_validate(
            {
                "bot_id": validate_bot_id(arguments.get("bot_id")),
                "content_match": arguments.get("content_match"),
            }
        )
        async with _with_verified_bot(payload.bot_id, sec) as (conn, _):
            deleted = await forget_memory(conn, payload.bot_id, payload.content_match)
            await conn.commit()
        return _json_text(
            {"status": "success", "bot_id": payload.bot_id, "deleted": deleted}
        )

    if name == "delete_session":
        bot_id = validate_bot_id(arguments.get("bot_id"))
        session_id = validate_session_id(arguments.get("session_id"))
        async with _with_verified_bot(bot_id, sec) as (conn, _):
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
        async with engine.connect() as conn:
            record = await ensure_avatar_record(
                conn, sec.account_id, external_key, soul, runtime_config
            )
            await conn.commit()
        return _json_text(record)

    if name == "hybrid_prepare":
        bot_id = validate_bot_id(arguments.get("bot_id"))
        if not arguments.get("query"):
            raise ValueError("query is required")
        payload = HybridPrepareRequest.model_validate(
            {**arguments, "bot_id": bot_id}
        )
        async with engine.connect() as conn:
            try:
                body = await prepare_hybrid_turn(
                    conn, _embedder, get_llm_service(), sec.account, payload
                )
            except SoulOSProblem as e:
                return _problem(e.code, e.status, e.detail)
            await conn.commit()
        return _json_text(body)

    if name == "hybrid_complete":
        bot_id = validate_bot_id(arguments.get("bot_id"))
        if not arguments.get("summary"):
            raise ValueError("summary is required")
        payload = HybridCompleteRequest.model_validate(
            {**arguments, "bot_id": bot_id}
        )
        tasks = BackgroundTasks()
        async with engine.connect() as conn:
            try:
                body = await complete_hybrid_turn(
                    conn,
                    _embedder,
                    get_llm_service(),
                    sec.account,
                    payload,
                    add_background_task=tasks.add_task,
                )
            except SoulOSProblem as e:
                return _problem(e.code, e.status, e.detail)
            await conn.commit()
        _run_background(tasks)
        if isinstance(body, JSONResponse):
            return _json_text(json.loads(body.body))
        return _json_text(body)

    if name == "get_identity":
        bot_id = validate_bot_id(arguments.get("bot_id"))
        async with _with_verified_bot(bot_id, sec) as (conn, _):
            identity = await get_bot_identity(conn, bot_id)
            await conn.commit()
        if not identity:
            return _problem(BOT_NOT_FOUND, 404, f"Bot not found: {bot_id}")
        return _json_text(identity)

    if name == "register_avatar":
        soul = arguments.get("soul")
        if not soul:
            raise ValueError("soul is required")
        soul = _parse_object(soul, "soul") if not isinstance(soul, dict) else soul
        async with engine.connect() as conn:
            record = await register_avatar_record(conn, sec.account_id, soul)
            await conn.commit()
        return _json_text(record)

    if name == "list_avatars":
        limit = int(arguments.get("limit") or 50)
        async with engine.connect() as conn:
            avatars = await list_avatars(conn, sec.account_id, limit)
            await conn.commit()
        return _json_text({"avatars": avatars})

    if name == "ingest_memory":
        bot_id = validate_bot_id(arguments.get("bot_id"))
        payload = MemoryIngest.model_validate(
            {
                "bot_id": bot_id,
                "content": arguments.get("content"),
                "session_id": validate_session_id(
                    arguments.get("session_id"), required=False
                ),
            }
        )
        importance = float(arguments.get("importance") or 0.6)
        async with _with_verified_bot(payload.bot_id, sec) as (conn, _):
            hits = await retrieve_memory_hits(
                conn,
                _embedder,
                payload.bot_id,
                payload.content,
                3,
                payload.session_id,
            )
            best = None
            if hits:
                dists = [h.dense_distance for h in hits if h.dense_distance is not None]
                if dists:
                    best = min(dists)
            if should_skip_as_duplicate(best_distance=best):
                await conn.commit()
                return _json_text(
                    {
                        "status": "noop",
                        "reason": "deduped",
                        "bot_id": payload.bot_id,
                        "best_distance": best,
                    }
                )
            tagged = quarantine_untrusted(
                payload.content,
                trust_level=TRUST_EXTERNAL_MCP,
                source_principal=sec.principal_hash or sec.account_id or "mcp",
            )
            await ingest_memory_record(
                conn,
                _embedder,
                payload.bot_id,
                tagged,
                payload.session_id,
                importance=importance,
            )
            await conn.commit()
        return _json_text(
            {
                "status": "success",
                "bot_id": payload.bot_id,
                "message": "Memory ingested",
                "trust_level": TRUST_EXTERNAL_MCP,
            }
        )

    if name == "ingest_conversation_memory":
        cid = arguments.get("conversation_id")
        content = arguments.get("content")
        if not cid or not content:
            raise ValueError("conversation_id and content are required")
        try:
            cid = normalize_conversation_id(cid)
        except ValueError as e:
            raise ValueError(str(e)) from e
        importance = float(arguments.get("importance") or 0.6)
        tenant_id = require_tenant_uuid(sec.account_id)
        tagged = quarantine_untrusted(
            content,
            trust_level=TRUST_EXTERNAL_MCP,
            source_principal=sec.principal_hash or sec.account_id or "mcp",
        )
        async with engine.connect() as conn:
            mem_id = await ingest_conversation_memory(
                conn,
                _embedder,
                cid,
                tagged,
                tenant_id=tenant_id,
                source_bot_id=arguments.get("source_bot_id"),
                importance=importance,
            )
            await conn.commit()
        return _json_text(
            {
                "status": "success",
                "id": mem_id,
                "conversation_id": cid,
                "trust_level": TRUST_EXTERNAL_MCP,
            }
        )

    if name == "retrieve_conversation_memory":
        cid = arguments.get("conversation_id")
        query = arguments.get("query")
        if not cid or not query:
            raise ValueError("conversation_id and query are required")
        cid = normalize_conversation_id(cid)
        tenant_id = require_tenant_uuid(sec.account_id)
        top_k = int(arguments.get("top_k") or 5)
        recency_weight = float(arguments.get("recency_weight") or 0.0)
        mood_congruent = bool(arguments.get("mood_congruent"))
        bot_id_raw = arguments.get("bot_id")
        bot_id = validate_bot_id(bot_id_raw) if bot_id_raw else None
        if mood_congruent and not bot_id:
            raise ValueError("bot_id is required when mood_congruent is true")
        async with engine.connect() as conn:
            if bot_id:
                await verify_bot_access(conn, bot_id, sec.account)
            hits = await retrieve_conversation_memory_hits(
                conn,
                _embedder,
                cid,
                query,
                max(top_k * 2, top_k),
                tenant_id=tenant_id,
            )
            current_msv = None
            if mood_congruent and bot_id:
                identity = await get_bot_identity(conn, bot_id)
                current_msv = (identity or {}).get("current_msv")
            ranked = rerank_hits_for_persona(
                hits,
                top_k=top_k,
                recency_weight=recency_weight,
                mood_congruent=mood_congruent,
                current_msv=current_msv if isinstance(current_msv, dict) else None,
            )
            memories = hit_contents(ranked)
            await conn.commit()
        return _json_text(
            {
                "conversation_id": cid,
                "query": query,
                "memories": memories,
                "recency_weight": recency_weight,
                "mood_congruent": mood_congruent,
            }
        )

    if name == "create_handoff":
        for req in (
            "task_summary",
            "unresolved_constraints",
            "user_emotional_state",
            "source_bot_stance",
        ):
            if arguments.get(req) in (None, ""):
                raise ValueError(f"{req} is required for create_handoff")
        async with engine.connect() as conn:
            body = await create_handoff_record(
                conn,
                _embedder,
                sec.account,
                from_bot_id=validate_bot_id(arguments.get("from_bot_id")),
                to_bot_id=validate_bot_id(arguments.get("to_bot_id")),
                from_role=arguments.get("from_role") or "",
                to_role=arguments.get("to_role") or "",
                conversation_id=arguments.get("conversation_id") or "",
                reason=arguments.get("reason") or "",
                summary=arguments.get("summary") or "",
                user_message=arguments.get("user_message"),
                idempotency_key=arguments.get("idempotency_key"),
                task_summary=arguments.get("task_summary"),
                unresolved_constraints=arguments.get("unresolved_constraints"),
                user_emotional_state=arguments.get("user_emotional_state"),
                source_bot_stance=arguments.get("source_bot_stance"),
            )
            await conn.commit()
        return _json_text(body)

    if name == "consolidate_memory":
        key = rate_limit_key(sec.tenant_id, "consolidate")
        if not consolidate_limiter.allow(key):
            raise SoulOSProblem(
                "RATE_LIMITED", 429, "consolidate_memory rate limit exceeded"
            )
        bot_id = validate_bot_id(arguments.get("bot_id"))
        async with _with_verified_bot(bot_id, sec) as (conn, _):
            body = await consolidate_memories(
                conn,
                _embedder,
                bot_id,
                session_id=validate_session_id(
                    arguments.get("session_id"), required=False
                ),
                limit=int(arguments.get("limit") or 8),
                min_candidates=CONSOLIDATE_MIN_CANDIDATES,
            )
            await conn.commit()
        return _json_text(body)

    raise ValueError(f"Unknown tool: {name}")


# --- MCP 2.x handlers --------------------------------------------------------


async def _on_list_resources(
    _ctx: ServerRequestContext[Any],
    _params: PaginatedRequestParams | None,
) -> ListResourcesResult:
    return ListResourcesResult(resources=await handle_list_resources())


async def _on_list_resource_templates(
    _ctx: ServerRequestContext[Any],
    _params: PaginatedRequestParams | None,
) -> ListResourceTemplatesResult:
    return ListResourceTemplatesResult(
        resource_templates=await handle_list_resource_templates()
    )


async def _on_read_resource(
    _ctx: ServerRequestContext[Any],
    params: ReadResourceRequestParams,
) -> ReadResourceResult:
    uri = str(params.uri)
    try:
        text_body = await handle_read_resource(uri)
    except (McpIdError, ValueError, SoulOSProblem) as e:
        text_body = json.dumps(
            {
                "error": True,
                "detail": str(getattr(e, "detail", e)),
                "code": getattr(e, "code", SOUL_INVALID),
            }
        )
    return ReadResourceResult(
        contents=[
            TextResourceContents(uri=uri, mime_type="application/json", text=text_body)
        ]
    )


async def _on_list_prompts(
    _ctx: ServerRequestContext[Any],
    _params: PaginatedRequestParams | None,
) -> ListPromptsResult:
    return ListPromptsResult(prompts=await handle_list_prompts())


async def _on_get_prompt(
    _ctx: ServerRequestContext[Any],
    params: GetPromptRequestParams,
) -> GetPromptResult:
    return await handle_get_prompt(params.name, params.arguments)


async def _on_list_tools(
    _ctx: ServerRequestContext[Any],
    _params: PaginatedRequestParams | None,
) -> ListToolsResult:
    return ListToolsResult(tools=await handle_list_tools())


async def _on_call_tool(
    _ctx: ServerRequestContext[Any],
    params: CallToolRequestParams,
) -> CallToolResult:
    return await _call_tool_result(params.name, dict(params.arguments or {}))


mcp_server = Server(
    "soulos-kernel",
    on_list_resources=_on_list_resources,
    on_list_resource_templates=_on_list_resource_templates,
    on_read_resource=_on_read_resource,
    on_list_prompts=_on_list_prompts,
    on_get_prompt=_on_get_prompt,
    on_list_tools=_on_list_tools,
    on_call_tool=_on_call_tool,
)
