"""Memory crystallization: persist MSV drift into baseline after sustained stress."""

from __future__ import annotations

import json
import logging
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

logger = logging.getLogger(__name__)

CRYSTALLIZATION_STRESS_TURNS = 50
AGREEABLENESS_DROP_THRESHOLD = 0.08
EMOTIONALITY_RISE_THRESHOLD = 0.08


def is_stress_turn(baseline_msv: dict[str, Any], new_msv: dict[str, Any]) -> bool:
    baseline_hex = baseline_msv.get("hexaco") or {}
    new_hex = new_msv.get("hexaco") or {}
    a_drop = float(baseline_hex.get("A", 0.5)) - float(new_hex.get("A", 0.5))
    e_rise = float(new_hex.get("E", 0.5)) - float(baseline_hex.get("E", 0.5))
    return a_drop >= AGREEABLENESS_DROP_THRESHOLD or e_rise >= EMOTIONALITY_RISE_THRESHOLD


async def apply_crystallization_if_needed(
    conn: AsyncConnection,
    bot_id: str,
    baseline_msv: dict[str, Any],
    new_msv: dict[str, Any],
) -> bool:
    """Increment stress streak; crystallize baseline when threshold reached."""
    result = await conn.execute(
        text("SELECT cognitive_meta FROM bots WHERE id = :id"),
        {"id": bot_id},
    )
    row = result.fetchone()
    meta_raw = row.cognitive_meta if row else None
    if isinstance(meta_raw, str):
        meta = json.loads(meta_raw)
    elif isinstance(meta_raw, dict):
        meta = dict(meta_raw)
    else:
        meta = {}

    streak = int(meta.get("stress_streak", 0))
    if is_stress_turn(baseline_msv, new_msv):
        streak += 1
    else:
        streak = 0

    meta["stress_streak"] = streak
    crystallized = False

    if streak >= CRYSTALLIZATION_STRESS_TURNS:
        await conn.execute(
            text(
                "UPDATE bots SET baseline_msv = CAST(:msv AS jsonb), "
                "cognitive_meta = CAST(:meta AS jsonb) WHERE id = :id"
            ),
            {
                "msv": json.dumps(new_msv),
                "meta": json.dumps({**meta, "stress_streak": 0, "crystallized": True}),
                "id": bot_id,
            },
        )
        crystallized = True
        logger.info("Crystallized baseline_msv for bot %s after %s stress turns", bot_id, streak)
    else:
        await conn.execute(
            text("UPDATE bots SET cognitive_meta = CAST(:meta AS jsonb) WHERE id = :id"),
            {"meta": json.dumps(meta), "id": bot_id},
        )

    return crystallized
