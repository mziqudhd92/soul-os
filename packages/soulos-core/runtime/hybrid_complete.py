"""Turn-contract handling for hybrid complete (extracted from routes)."""

from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncConnection

from runtime.errors import (
    TURN_CONTRACT_VIOLATION,
    TURN_REJECT_TOKEN,
    TURN_SESSION_EXPIRED,
    TURN_STATE_STALE,
    TURN_STEP_MISMATCH,
    SoulOSProblem,
)
from runtime.turn_contract import apply_turn
from runtime.turn_session import advance_turn_session, get_turn_session
from schemas import HybridCompleteRequest


async def resolve_turn_on_complete(
    db: AsyncConnection,
    *,
    contract: dict[str, Any],
    payload: HybridCompleteRequest,
) -> dict[str, Any] | None:
    """Validate CAS/idempotency and advance turn session.

    Returns:
        ``turn_payload`` dict on success, or a cached success response dict
        tagged with ``_cached_response`` when replaying an idempotent key.
        ``None`` when no session_id (caller skips turn).
    """
    if not payload.session_id:
        return None

    session = await get_turn_session(db, payload.bot_id, payload.session_id)
    if session is None:
        raise SoulOSProblem(
            TURN_SESSION_EXPIRED,
            404,
            f"Turn session expired or missing: {payload.session_id}",
            extra={"session_id": payload.session_id},
        )
    if (
        payload.idempotency_key
        and session.get("last_idempotency_key") == payload.idempotency_key
        and session.get("last_success_response")
    ):
        return {"_cached_response": dict(session["last_success_response"])}

    if payload.expected_version is None:
        raise SoulOSProblem(
            TURN_CONTRACT_VIOLATION,
            422,
            "expected_version is required when a turn contract is active",
            extra={"turn_version": session["turn_version"]},
        )
    if payload.expected_version != session["turn_version"]:
        raise SoulOSProblem(
            TURN_STATE_STALE,
            409,
            "expected_version does not match session turn_version",
            extra={
                "turn_version": session["turn_version"],
                "expected_step": session["current_step"],
                "filled_slots": session["slots"],
            },
        )
    if payload.expected_step and payload.expected_step != session["current_step"]:
        raise SoulOSProblem(
            TURN_STEP_MISMATCH,
            422,
            "expected_step does not match session current_step",
            extra={
                "expected_step": session["current_step"],
                "turn_version": session["turn_version"],
            },
        )

    result = apply_turn(
        contract,
        current_step=session["current_step"],
        slots=session["slots"],
        filled_slots=payload.filled_slots,
        intent=payload.intent,
        assistant_text=payload.assistant_text,
        advance=payload.advance,
    )
    if not result.ok:
        code = result.code or TURN_CONTRACT_VIOLATION
        if code == TURN_REJECT_TOKEN:
            raise SoulOSProblem(
                TURN_REJECT_TOKEN,
                422,
                result.detail or "Reject token detected",
                extra={
                    "expected_step": session["current_step"],
                    "turn_version": session["turn_version"],
                    "remedial_prompt_hint": result.remedial_prompt_hint,
                },
            )
        raise SoulOSProblem(
            TURN_CONTRACT_VIOLATION,
            422,
            result.detail or "Turn contract violation",
            extra={
                "invalid_slots": result.invalid_slots,
                "missing_slots": result.missing_slots,
                "expected_step": session["current_step"],
                "turn_version": session["turn_version"],
                "remedial_prompt_hint": result.remedial_prompt_hint,
            },
        )

    new_version = session["turn_version"] + 1
    claimed = await advance_turn_session(
        db,
        bot_id=payload.bot_id,
        session_id=payload.session_id,
        expected_version=session["turn_version"],
        current_step=result.step,
        slots=result.slots,
        turn_version=new_version,
        last_idempotency_key=payload.idempotency_key,
        last_success_response=None,
    )
    if not claimed:
        raise SoulOSProblem(
            TURN_STATE_STALE,
            409,
            "expected_version does not match session turn_version",
            extra={
                "turn_version": session["turn_version"],
                "expected_step": session["current_step"],
                "filled_slots": session["slots"],
            },
        )
    return {
        "step": result.step,
        "slots": result.slots,
        "advanced": result.advanced,
        "turn_version": new_version,
    }
