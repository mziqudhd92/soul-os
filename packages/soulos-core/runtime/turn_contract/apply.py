"""Apply a turn against a contract (merge, validate, advance)."""

from __future__ import annotations

from typing import Any

from runtime.turn_contract.bounds import validate_filled_slots_bounds
from runtime.turn_contract.prompts import build_remedial_prompt_hint
from runtime.turn_contract.slots import merge_slots, scan_reject_tokens, step_map, validate_slots
from runtime.turn_contract.types import MAX_SLOT_KEYS, TurnApplyResult, TurnContractError


def apply_turn(
    contract: dict[str, Any],
    *,
    current_step: str,
    slots: dict[str, Any] | None,
    filled_slots: dict[str, Any] | None = None,
    intent: str | None = None,
    assistant_text: str | None = None,
    advance: bool = True,
) -> TurnApplyResult:
    try:
        validate_filled_slots_bounds(filled_slots)
    except TurnContractError as e:
        return TurnApplyResult(
            ok=False,
            step=current_step,
            slots=dict(slots or {}),
            code=e.code,
            detail=e.detail,
            remedial_prompt_hint=e.detail,
            invalid_slots={"_payload": e.detail},
        )

    hit = scan_reject_tokens(contract, assistant_text)
    if hit:
        return TurnApplyResult(
            ok=False,
            step=current_step,
            slots=dict(slots or {}),
            code="TURN_REJECT_TOKEN",
            detail=f"Assistant text contained reject token: {hit}",
            remedial_prompt_hint="Do not include forbidden phrases; rewrite the reply.",
        )

    steps = step_map(contract)
    step = steps.get(current_step)
    if not step:
        return TurnApplyResult(
            ok=False,
            step=current_step,
            slots=dict(slots or {}),
            code="TURN_CONTRACT_VIOLATION",
            detail=f"Unknown step: {current_step}",
        )

    # Resolve target step before merge when intent has an explicit transition
    target_step_id = current_step
    used_transition = False
    if intent and intent in (step.get("transitions") or {}):
        target_step_id = step["transitions"][intent]
        used_transition = True
    elif intent and (step.get("allowed_intents") or []) and intent not in (
        step.get("allowed_intents") or []
    ):
        return TurnApplyResult(
            ok=False,
            step=current_step,
            slots=dict(slots or {}),
            code="TURN_CONTRACT_VIOLATION",
            detail=f"Intent not allowed: {intent}",
            invalid_slots={"intent": f"Not in allowed_intents for {current_step}"},
            remedial_prompt_hint=f"Use one of: {', '.join(step.get('allowed_intents') or [])}.",
        )

    working = dict(slots or {})
    # Merge first so type checks see the patch
    working = merge_slots(working, filled_slots)

    if len(working) > MAX_SLOT_KEYS:
        return TurnApplyResult(
            ok=False,
            step=current_step,
            slots=dict(slots or {}),
            code="TURN_CONTRACT_VIOLATION",
            detail=f"Session slots exceed {MAX_SLOT_KEYS} keys",
            invalid_slots={"_payload": f"Max {MAX_SLOT_KEYS} keys"},
            remedial_prompt_hint="Reduce the number of filled slots.",
        )

    if used_transition and target_step_id != current_step:
        if target_step_id not in steps:
            return TurnApplyResult(
                ok=False,
                step=current_step,
                slots=dict(slots or {}),
                code="TURN_CONTRACT_VIOLATION",
                detail=f"Unknown transition target step: {target_step_id}",
                invalid_slots={"intent": f"transitions[{intent}] → unknown step"},
                remedial_prompt_hint="Contract configuration error: invalid transition target.",
            )
        # Completing the flow requires current-step slots; backtrack/cancel do not.
        if target_step_id == "completed":
            missing_cur, invalid_cur = validate_slots(step, working, contract=contract)
            if missing_cur or invalid_cur:
                hint = build_remedial_prompt_hint(
                    missing_slots=missing_cur or None,
                    invalid_slots=invalid_cur or None,
                )
                return TurnApplyResult(
                    ok=False,
                    step=current_step,
                    slots=dict(slots or {}),
                    missing_slots=missing_cur or None,
                    invalid_slots=invalid_cur or None,
                    remedial_prompt_hint=hint,
                    code="TURN_CONTRACT_VIOLATION",
                    detail="Slot validation failed",
                )
        target = steps[target_step_id]
        for key in target.get("clear_slots_on_entry") or []:
            working.pop(key, None)
        missing, invalid = validate_slots(target, working, contract=contract)
        if invalid:
            hint = build_remedial_prompt_hint(missing_slots=None, invalid_slots=invalid)
            return TurnApplyResult(
                ok=False,
                step=current_step,
                slots=dict(slots or {}),
                missing_slots=missing or None,
                invalid_slots=invalid,
                remedial_prompt_hint=hint,
                code="TURN_CONTRACT_VIOLATION",
                detail="Slot validation failed",
            )
        return TurnApplyResult(
            ok=True,
            step=target_step_id,
            slots=working,
            advanced=True,
        )

    eval_step = step
    missing, invalid = validate_slots(eval_step, working, contract=contract)

    soft_intent = bool(
        intent
        and intent in (step.get("allowed_intents") or [])
        and intent not in (step.get("transitions") or {})
    )
    # Soft intents with no slot patch (e.g. clarify) may stay without completing.
    # Any filled_slots patch that still leaves required slots missing is a violation
    # when advance is requested.
    if soft_intent and not invalid and not (filled_slots or {}):
        return TurnApplyResult(
            ok=True,
            step=current_step,
            slots=working,
            advanced=False,
        )

    if invalid or (advance and missing):
        hint = build_remedial_prompt_hint(
            missing_slots=missing if advance else None,
            invalid_slots=invalid or None,
        )
        return TurnApplyResult(
            ok=False,
            step=current_step,
            slots=dict(slots or {}),
            missing_slots=missing or None,
            invalid_slots=invalid or None,
            remedial_prompt_hint=hint,
            code="TURN_CONTRACT_VIOLATION",
            detail="Slot validation failed",
        )

    if not advance:
        return TurnApplyResult(
            ok=True, step=current_step, slots=working, advanced=False
        )

    # Completion-based advance
    completion = step.get("completion") or {}
    if completion.get("all_required_slots") and not missing:
        nxt = step.get("next")
        if nxt:
            if nxt not in steps:
                return TurnApplyResult(
                    ok=False,
                    step=current_step,
                    slots=dict(slots or {}),
                    code="TURN_CONTRACT_VIOLATION",
                    detail=f"Unknown next step: {nxt}",
                    invalid_slots={"next": f"steps[{current_step}].next → unknown step"},
                    remedial_prompt_hint="Contract configuration error: invalid next target.",
                )
            target = steps[nxt]
            for key in target.get("clear_slots_on_entry") or []:
                working.pop(key, None)
            return TurnApplyResult(
                ok=True, step=nxt, slots=working, advanced=True
            )

    if used_transition:
        return TurnApplyResult(
            ok=True, step=target_step_id, slots=working, advanced=target_step_id != current_step
        )

    return TurnApplyResult(
        ok=True, step=current_step, slots=working, advanced=False
    )
