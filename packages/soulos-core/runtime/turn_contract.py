"""Pure turn-contract resolver: merge, validate, transitions, context builders."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import date
from typing import Any

MAX_SLOTS_BYTES = 64 * 1024
MAX_SLOT_DEPTH = 3
MAX_SLOT_KEYS = 50

_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


class TurnContractError(Exception):
    """Raised for payload bound violations before apply_turn."""

    def __init__(self, detail: str, *, code: str = "TURN_CONTRACT_VIOLATION") -> None:
        self.detail = detail
        self.code = code
        super().__init__(detail)


@dataclass
class TurnApplyResult:
    ok: bool
    step: str
    slots: dict[str, Any]
    advanced: bool = False
    missing_slots: list[str] | None = None
    invalid_slots: dict[str, str] | None = None
    remedial_prompt_hint: str | None = None
    code: str | None = None
    detail: str | None = None


def _step_map(contract: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {s["id"]: s for s in contract.get("steps") or [] if isinstance(s, dict) and "id" in s}


def _json_size(obj: Any) -> int:
    return len(json.dumps(obj, default=str).encode("utf-8"))


def _max_depth(obj: Any, depth: int = 0) -> int:
    if not isinstance(obj, dict):
        if isinstance(obj, list):
            return max((_max_depth(x, depth + 1) for x in obj), default=depth)
        return depth
    if not obj:
        return depth
    return max(_max_depth(v, depth + 1) for v in obj.values())


def validate_filled_slots_bounds(filled_slots: dict[str, Any] | None) -> None:
    patch = filled_slots or {}
    if not isinstance(patch, dict):
        raise TurnContractError("filled_slots must be an object")
    if _json_size(patch) > MAX_SLOTS_BYTES:
        raise TurnContractError(
            f"filled_slots exceeds {MAX_SLOTS_BYTES} bytes",
            code="TURN_CONTRACT_VIOLATION",
        )
    if _max_depth(patch) > MAX_SLOT_DEPTH:
        raise TurnContractError(
            f"filled_slots nesting depth exceeds {MAX_SLOT_DEPTH}",
            code="TURN_CONTRACT_VIOLATION",
        )
    if len(patch) > MAX_SLOT_KEYS:
        raise TurnContractError(
            f"filled_slots has more than {MAX_SLOT_KEYS} keys",
            code="TURN_CONTRACT_VIOLATION",
        )


def merge_slots(
    existing: dict[str, Any] | None, patch: dict[str, Any] | None
) -> dict[str, Any]:
    out = dict(existing or {})
    for key, value in (patch or {}).items():
        if value is None:
            out.pop(key, None)
        else:
            out[key] = value
    return out


def _allowed_slot_keys(step: dict[str, Any]) -> set[str] | None:
    schemas = step.get("slot_schemas") or {}
    required = step.get("required_slots") or []
    clear = step.get("clear_slots_on_entry") or []
    keys: set[str] = set()
    if isinstance(schemas, dict):
        keys.update(schemas.keys())
    keys.update(required)
    keys.update(clear)
    # Include sibling step schemas for carry-over slots when allowlist is present
    return keys if keys else None


def _validate_type(value: Any, schema: dict[str, Any]) -> str | None:
    t = schema.get("type")
    fmt = schema.get("format")
    if t == "string":
        if not isinstance(value, str):
            return "Must be a string"
        if fmt == "date":
            if not _DATE_RE.match(value):
                return "Must match format YYYY-MM-DD"
            try:
                date.fromisoformat(value)
            except ValueError:
                return "Must match format YYYY-MM-DD"
        return None
    if t == "boolean":
        if not isinstance(value, bool):
            return "Must be a boolean"
        return None
    if t == "number":
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            return "Must be a number"
        return None
    if t == "integer":
        if not isinstance(value, int) or isinstance(value, bool):
            return "Must be an integer"
        return None
    if t == "object":
        if not isinstance(value, dict):
            return "Must be an object"
        return None
    if t == "array":
        if not isinstance(value, list):
            return "Must be an array"
        return None
    return None


def _validate_slots(
    step: dict[str, Any], slots: dict[str, Any], *, contract: dict[str, Any]
) -> tuple[list[str], dict[str, str]]:
    missing: list[str] = []
    invalid: dict[str, str] = {}
    schemas: dict[str, Any] = {}
    for s in contract.get("steps") or []:
        if isinstance(s, dict):
            schemas.update(s.get("slot_schemas") or {})
    schemas.update(step.get("slot_schemas") or {})

    allow = _allowed_slot_keys(step)
    # Expand allowlist with all declared slot_schemas across contract when step has schemas
    if step.get("slot_schemas") or step.get("required_slots"):
        all_declared: set[str] = set()
        for s in contract.get("steps") or []:
            if isinstance(s, dict):
                all_declared.update((s.get("slot_schemas") or {}).keys())
                all_declared.update(s.get("required_slots") or [])
                all_declared.update(s.get("clear_slots_on_entry") or [])
        allow = all_declared if all_declared else allow

    if allow is not None:
        for key in slots:
            if key not in allow:
                invalid[key] = "Unknown slot key"

    for key, value in slots.items():
        schema = schemas.get(key)
        if schema:
            err = _validate_type(value, schema)
            if err:
                invalid[key] = err

    for req in step.get("required_slots") or []:
        if req not in slots or slots[req] is None:
            missing.append(req)

    return missing, invalid


def _scan_reject_tokens(contract: dict[str, Any], assistant_text: str | None) -> str | None:
    if not assistant_text:
        return None
    lower = assistant_text.lower()
    for token in contract.get("reject_tokens") or []:
        if str(token).lower() in lower:
            return str(token)
    return None


def missing_slots_for_step(
    contract: dict[str, Any], step_id: str, slots: dict[str, Any]
) -> list[str]:
    steps = _step_map(contract)
    step = steps.get(step_id) or {}
    return [r for r in (step.get("required_slots") or []) if r not in slots or slots[r] is None]


def build_prompt_appendix(
    contract: dict[str, Any],
    *,
    step_id: str,
    slots: dict[str, Any],
) -> str:
    steps = _step_map(contract)
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
    steps = _step_map(contract)
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

    hit = _scan_reject_tokens(contract, assistant_text)
    if hit:
        return TurnApplyResult(
            ok=False,
            step=current_step,
            slots=dict(slots or {}),
            code="TURN_REJECT_TOKEN",
            detail=f"Assistant text contained reject token: {hit}",
            remedial_prompt_hint="Do not include forbidden phrases; rewrite the reply.",
        )

    steps = _step_map(contract)
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
            missing_cur, invalid_cur = _validate_slots(step, working, contract=contract)
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
        missing, invalid = _validate_slots(target, working, contract=contract)
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
    missing, invalid = _validate_slots(eval_step, working, contract=contract)

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
            target = steps.get(nxt) or {}
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
