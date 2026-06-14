"""Background reflect tasks for hybrid integrations."""

from __future__ import annotations

import logging

from runtime.reflector import run_system_2_reflector

logger = logging.getLogger(__name__)


async def run_reflect_background(bot_id: str, message: str, current_msv: dict) -> None:
    try:
        await run_system_2_reflector(bot_id, message, current_msv, active_mcp_tools=[])
    except Exception as e:
        logger.error("Background reflect failed for bot %s: %s", bot_id, e)
