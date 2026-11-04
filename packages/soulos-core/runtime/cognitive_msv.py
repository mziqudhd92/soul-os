"""Cognitive state (MSV) mutations shared by REST and MCP."""

from __future__ import annotations

import json
from typing import Any

from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

from auth import AccountContext
from runtime.errors import SOUL_INVALID, SoulOSProblem
from runtime.hybrid_tasks import run_reflect_background
from runtime.msv_update import (
    apply_semantic_hexaco_shift,
    behavioral_summary_from_drift,
    clamp_msv,
    hexaco_delta,
)
from runtime.reflector import run_system_2_reflector
from soul_validation import validate_msv_payload
from tenant import verify_bot_access


async def force_update_msv(
    db: AsyncConnection,
    account: AccountContext,
    bot_id: str,
    new_msv: dict[str, Any],
) -> dict:
    await verify_bot_access(db, bot_id, account)
    try:
        validated_msv = validate_msv_payload(new_msv)
    except ValueError as e:
        raise SoulOSProblem(SOUL_INVALID, 422, str(e)) from e
    await db.execute(
        text("UPDATE bots SET current_msv = :msv WHERE id = :id"),
        {"msv": json.dumps(validated_msv), "id": bot_id},
    )
    return {
        "status": "success",
        "bot_id": bot_id,
        "message": f"Cognitive State updated for bot {bot_id}",
    }


async def apply_msv_delta(
    db: AsyncConnection,
    account: AccountContext,
    *,
    bot_id: str,
    appraisal_reasoning: str,
    trait: str,
    shift: str,
) -> dict:
    if not appraisal_reasoning or not str(appraisal_reasoning).strip():
        raise SoulOSProblem(
            SOUL_INVALID,
            422,
            "appraisal_reasoning is required before MSV mutation "
            "(explain why the interaction warrants a shift)",
        )
    await verify_bot_access(db, bot_id, account)
    result = await db.execute(
        text("SELECT baseline_msv, current_msv FROM bots WHERE id = :id"),
        {"id": bot_id},
    )
    row = result.fetchone()
    if not row:
        raise SoulOSProblem("BOT_NOT_FOUND", 404, f"Bot not found: {bot_id}")
    current = row.current_msv if isinstance(row.current_msv, dict) else {}
    if isinstance(row.current_msv, str):
        current = json.loads(row.current_msv)
    baseline = row.baseline_msv if isinstance(row.baseline_msv, dict) else current
    if isinstance(row.baseline_msv, str):
        baseline = json.loads(row.baseline_msv)
    try:
        updated = apply_semantic_hexaco_shift(current, trait=trait, shift=shift)
    except ValueError as e:
        raise SoulOSProblem(SOUL_INVALID, 422, str(e)) from e
    # Stamp reasoning into monologue for audit (truncated).
    reason = str(appraisal_reasoning).strip()[:400]
    updated["inner_monologue"] = f"[appraisal] {reason}"
    await db.execute(
        text("UPDATE bots SET current_msv = :msv WHERE id = :id"),
        {"msv": json.dumps(clamp_msv(updated)), "id": bot_id},
    )
    return {
        "status": "success",
        "bot_id": bot_id,
        "appraisal_reasoning": reason,
        "trait": trait,
        "shift": shift,
        "delta": hexaco_delta(baseline, updated),
        "behavioral_summary": behavioral_summary_from_drift(baseline, updated),
        "current_msv": clamp_msv(updated),
    }


async def reflect_cognitive_state(
    db: AsyncConnection,
    pipeline: Any,
    account: AccountContext,
    *,
    bot_id: str,
    message: str,
    appraisal_reasoning: str,
    reflect_async: bool = False,
    add_background_task: Any | None = None,
    active_mcp_tools: list[str] | None = None,
) -> dict | JSONResponse:
    if not appraisal_reasoning or not str(appraisal_reasoning).strip():
        raise SoulOSProblem(
            SOUL_INVALID,
            422,
            "appraisal_reasoning is required before reflect_cognitive_state",
        )
    await verify_bot_access(db, bot_id, account)
    current_msv = await pipeline.load_current_msv(db, bot_id)
    # Prepend appraisal so the reflector sees the host's reasoning first.
    reflect_message = (
        f"Appraisal: {str(appraisal_reasoning).strip()}\n\nUser/context: {message}"
    )
    tools = list(active_mcp_tools or [])
    if not tools:
        from runtime.mcp_outbound import resolve_active_mcp_tools

        tools = await resolve_active_mcp_tools(db, bot_id)
    if reflect_async:
        if add_background_task is not None:
            add_background_task(
                run_reflect_background, bot_id, reflect_message, current_msv
            )
        return JSONResponse(
            status_code=202,
            content={
                "status": "accepted",
                "bot_id": bot_id,
                "reflect": "async",
            },
        )
    result = await run_system_2_reflector(
        bot_id,
        reflect_message,
        current_msv,
        active_mcp_tools=tools,
    )
    return {
        "status": "success",
        "bot_id": bot_id,
        "current_msv": result.msv,
        "latency_ms": result.latency_ms,
    }


def msv_drift_payload(identity: dict[str, Any]) -> dict[str, Any]:
    baseline = identity.get("baseline_msv") or {}
    current = identity.get("current_msv") or baseline
    if not isinstance(baseline, dict):
        baseline = {}
    if not isinstance(current, dict):
        current = {}
    return {
        "baseline_msv": baseline,
        "current_msv": current,
        "delta": hexaco_delta(baseline, current),
        "behavioral_summary": behavioral_summary_from_drift(baseline, current),
    }
