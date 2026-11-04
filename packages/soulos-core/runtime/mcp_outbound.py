"""Resolve per-bot outbound MCP tool allowlists for reflect/hybrid."""

from __future__ import annotations

import json
import logging
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

from runtime.mcp_client import MAX_TOOL_ITERATIONS, get_outbound_client

logger = logging.getLogger("mcp_outbound")


async def load_allowed_mcp_servers(
    db: AsyncConnection, bot_id: str
) -> list[str] | None:
    """Return allowed_mcp_servers from runtime_config, or None to inherit global."""
    result = await db.execute(
        text("SELECT runtime_config FROM bots WHERE id = :id"),
        {"id": bot_id},
    )
    row = result.fetchone()
    if not row or row.runtime_config is None:
        return None
    cfg = row.runtime_config
    if isinstance(cfg, str):
        try:
            cfg = json.loads(cfg)
        except json.JSONDecodeError:
            return None
    if not isinstance(cfg, dict):
        return None
    allowed = cfg.get("allowed_mcp_servers")
    if allowed is None:
        return None
    if not isinstance(allowed, list):
        return []
    return [str(x) for x in allowed]


async def resolve_active_mcp_tools(db: AsyncConnection, bot_id: str) -> list[str]:
    client = get_outbound_client()
    if not client.enabled():
        return []
    allowed = await load_allowed_mcp_servers(db, bot_id)
    return client.active_tool_names(allowed)


async def run_budgeted_outbound_calls(
    planned_calls: list[dict[str, Any]],
) -> list[str]:
    """Execute outbound tool calls with a hard max_tool_iterations budget."""
    client = get_outbound_client()
    if not client.enabled():
        return []
    out: list[str] = []
    for i, call in enumerate(planned_calls):
        if i >= MAX_TOOL_ITERATIONS:
            logger.info("Outbound MCP tool budget exhausted at %s", MAX_TOOL_ITERATIONS)
            break
        name = str(call.get("name") or "")
        args = call.get("arguments") if isinstance(call.get("arguments"), dict) else {}
        try:
            out.append(await client.call_tool(name, args))
        except Exception as e:
            out.append(
                f'<untrusted_tool_output server="error">tool {name} failed: {e}'
                f"</untrusted_tool_output>"
            )
    return out
