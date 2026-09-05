"""Prompt appendix and UI progress helpers for turn contracts."""

from __future__ import annotations

from typing import Any

from runtime.turn_contract.slots import missing_slots_for_step, step_map


def build_prompt_appendix(
    contract: dict[str, Any],
    *,
    step_id: str,
    slots: dict[str, Any],
) -> str:
    steps = step_map(contract)
    step = steps.get(step_id) or {}
    missing = missing_slots_for_step(contract, step_id, slots)
    intents = step.get("allowed_intents") or []
    parts = [
        f"[SYSTEM DIRECTIVE: Step '{step_id}'.",
    ]
    if missing:
        parts.append(f" Required slots missing: {', '.join(missing)}.")
    else:
        parts.append(" Required slots satisfied.")
    if intents:
        parts.append(f" Allowed intents: {', '.join(intents)}.")
    parts.append("]")
    return "".join(parts)


def build_remedial_prompt_hint(
    *,
    missing_slots: list[str] | None = None,
    invalid_slots: dict[str, str] | None = None,
) -> str:
    bits: list[str] = []
    if invalid_slots:
        for k, msg in invalid_slots.items():
            bits.append(f"The {k} value was invalid ({msg}). Ask the user for a valid {k}.")
    if missing_slots:
        bits.append(
            "Ask the user for: " + ", ".join(missing_slots) + "."
        )
    return " ".join(bits) or "Ask the user to provide the required information."


def build_ui_progress(contract: dict[str, Any], step_id: str) -> dict[str, Any]:
    ordered = [
        s["id"]
        for s in contract.get("steps") or []
        if isinstance(s, dict) and s.get("id") not in ("completed", "cancelled")
    ]
    try:
        idx = ordered.index(step_id)
    except ValueError:
        idx = max(0, len(ordered) - 1)
    return {
        "step_index": idx,
        "step_count": max(len(ordered), 1),
        "label": step_id,
    }


def build_contract_context(
    contract: dict[str, Any],
    *,
    step_id: str,
    slots: dict[str, Any],
    turn_version: int,
) -> dict[str, Any]:
    steps = step_map(contract)
    step = steps.get(step_id) or {}
    return {
        "contract_id": contract.get("id"),
        "expected_step": step_id,
        "missing_slots": missing_slots_for_step(contract, step_id, slots),
        "filled_slots": dict(slots),
        "reject_tokens": list(contract.get("reject_tokens") or []),
        "ui_progress": build_ui_progress(contract, step_id),
        "allowed_intents": list(step.get("allowed_intents") or []),
        "prompt_appendix": build_prompt_appendix(contract, step_id=step_id, slots=slots),
        "turn_version": turn_version,
    }
