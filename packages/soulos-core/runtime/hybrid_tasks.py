"""Background reflect tasks for hybrid integrations."""

from __future__ import annotations

import logging

from config import engine
from runtime.mcp_outbound import resolve_active_mcp_tools
from runtime.reflector import run_system_2_reflector

logger = logging.getLogger(__name__)


async def run_reflect_background(bot_id: str, message: str, current_msv: dict) -> None:
    try:
        tools: list[str] = []
        try:
            async with engine.connect() as conn:
                tools = await resolve_active_mcp_tools(conn, bot_id)
                await conn.commit()
        except Exception as e:
            logger.warning("Could not resolve outbound MCP tools: %s", e)
        await run_system_2_reflector(
            bot_id, message, current_msv, active_mcp_tools=tools
        )
    except Exception as e:
        logger.error("Background reflect failed for bot %s: %s", bot_id, e)
