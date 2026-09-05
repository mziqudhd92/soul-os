"""Slot merge and type validation."""

from __future__ import annotations

import re
from datetime import date
from typing import Any

_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def step_map(contract: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {s["id"]: s for s in contract.get("steps") or [] if isinstance(s, dict) and "id" in s}


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
    return keys if keys else None


def validate_type(value: Any, schema: dict[str, Any]) -> str | None:
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


def validate_slots(
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
            err = validate_type(value, schema)
            if err:
                invalid[key] = err

    for req in step.get("required_slots") or []:
        if req not in slots or slots[req] is None:
            missing.append(req)

    return missing, invalid


def scan_reject_tokens(contract: dict[str, Any], assistant_text: str | None) -> str | None:
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
    steps = step_map(contract)
    step = steps.get(step_id) or {}
    return [r for r in (step.get("required_slots") or []) if r not in slots or slots[r] is None]
