"""JSON Schema + graph validation for turn contracts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from runtime.turn_contract.types import TurnContractError


def _resolve_turn_contract_schema_path() -> Path:
    here = Path(__file__).resolve().parent
    candidates = [Path("/spec/turn-contract.schema.json")]
    # turn_contract/ → runtime → soulos-core → packages → repo root
    for ancestor in [
        here.parent,
        here.parent.parent,
        here.parent.parent.parent,
        here.parent.parent.parent.parent,
    ]:
        candidates.append(ancestor / "spec" / "turn-contract.schema.json")
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return here.parent.parent.parent.parent / "spec" / "turn-contract.schema.json"


def validate_turn_contract(contract: dict[str, Any] | None) -> None:
    """Validate ``runtime_config.turn_contract`` against the published JSON Schema."""
    if contract is None:
        return
    if not isinstance(contract, dict):
        raise TurnContractError("turn_contract must be an object")
    schema_path = _resolve_turn_contract_schema_path()
    with schema_path.open(encoding="utf-8") as f:
        schema = json.load(f)
    validator = Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(contract), key=lambda e: list(e.path))
    if errors:
        first = errors[0]
        path = ".".join(str(p) for p in first.path) or "(root)"
        raise TurnContractError(f"Invalid turn_contract at {path}: {first.message}")
    steps = contract.get("steps") or []
    step_ids = {s.get("id") for s in steps if isinstance(s, dict)}
    initial = contract.get("initial_step")
    if initial and initial not in step_ids:
        raise TurnContractError(
            f"initial_step {initial!r} is not defined in steps",
        )
    for step in steps:
        if not isinstance(step, dict):
            continue
        nxt = step.get("next")
        if nxt and nxt not in step_ids:
            raise TurnContractError(
                f"steps[{step.get('id')}].next → unknown step {nxt!r}",
            )
        for intent, target in (step.get("transitions") or {}).items():
            if target not in step_ids:
                raise TurnContractError(
                    f"steps[{step.get('id')}].transitions[{intent}] → unknown step {target!r}",
                )
