"""Validate .soul.json payloads against spec/soul.schema.json."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError as JsonSchemaValidationError
from pydantic import BaseModel, Field, ValidationError, field_validator

def _resolve_schema_path() -> Path:
    here = Path(__file__).resolve().parent
    candidates = [Path("/spec/soul.schema.json")]
    for ancestor in [here.parent, here.parent.parent, here.parent.parent.parent]:
        candidates.append(ancestor / "spec" / "soul.schema.json")
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return here.parent.parent.parent / "spec" / "soul.schema.json"


SCHEMA_PATH = _resolve_schema_path()

HEXACO_FIELD_LABELS = {
    "H": "Honesty-Humility (H)",
    "E": "Emotionality (E)",
    "X": "eXtraversion (X)",
    "A": "Agreeableness (A)",
    "C": "Conscientiousness (C)",
    "O": "Openness (O)",
}


def _load_schema() -> dict[str, Any]:
    with SCHEMA_PATH.open(encoding="utf-8") as f:
        return json.load(f)


class HexacoTraits(BaseModel):
    H: float = Field(..., ge=-1.0, le=1.0)
    E: float = Field(..., ge=-1.0, le=1.0)
    X: float = Field(..., ge=-1.0, le=1.0)
    A: float = Field(..., ge=-1.0, le=1.0)
    C: float = Field(..., ge=-1.0, le=1.0)
    O: float = Field(..., ge=-1.0, le=1.0)


class MoralFoundations(BaseModel):
    care_harm: float = Field(..., ge=0.0, le=1.0)
    fairness_cheating: float = Field(..., ge=0.0, le=1.0)
    loyalty_betrayal: float = Field(..., ge=0.0, le=1.0)
    authority_subversion: float = Field(..., ge=0.0, le=1.0)
    sanctity_degradation: float = Field(..., ge=0.0, le=1.0)


class IntrinsicDrives(BaseModel):
    curiosity: float = Field(..., ge=0.0, le=1.0)
    autonomy: float = Field(..., ge=0.0, le=1.0)
    social_approval: float = Field(..., ge=0.0, le=1.0)


class MetacognitiveStateVector(BaseModel):
    hexaco: HexacoTraits
    moral_foundations: MoralFoundations
    drives: IntrinsicDrives
    epistemic_uncertainty: float = Field(..., ge=0.0, le=1.0)
    inner_monologue: str = Field(..., min_length=1, max_length=500)


class SoulFile(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    role: str = Field(..., min_length=1, max_length=255)
    description: str = Field(..., min_length=1)
    attachment_style: str
    baseline_msv: MetacognitiveStateVector
    capabilities: list[str] | None = None
    hourly_rate: int | None = Field(None, ge=0)
    status: str | None = None
    avatar_url: str | None = None

    @field_validator("attachment_style")
    @classmethod
    def validate_attachment_style(cls, value: str) -> str:
        allowed = {"Secure", "Anxious-Preoccupied", "Dismissive-Avoidant"}
        if value not in allowed:
            raise ValueError(
                f"attachment_style must be one of: {', '.join(sorted(allowed))}"
            )
        return value

    @field_validator("status")
    @classmethod
    def validate_status(cls, value: str | None) -> str | None:
        if value is None:
            return value
        allowed = {"available", "busy", "offline"}
        if value not in allowed:
            raise ValueError(f"status must be one of: {', '.join(sorted(allowed))}")
        return value


def _humanize_jsonschema_error(error: JsonSchemaValidationError) -> str:
    path = ".".join(str(p) for p in error.absolute_path) or "root"
    message = error.message

    if error.validator == "required":
        missing = error.message.split("'")[1] if "'" in error.message else "field"
        return f"{path}: missing required field '{missing}'"

    if error.validator in ("minimum", "maximum"):
        trait_hint = ""
        for part in error.absolute_path:
            if part in HEXACO_FIELD_LABELS:
                trait_hint = f" ({HEXACO_FIELD_LABELS[part]})"
                break
        return f"{path}{trait_hint}: {message}"

    if error.validator == "enum":
        return f"{path}: {message}"

    return f"{path}: {message}"


def _humanize_pydantic_error(error: ValidationError) -> list[str]:
    lines: list[str] = []
    for err in error.errors():
        loc = ".".join(str(part) for part in err["loc"])
        msg = err["msg"]
        if err["type"] == "missing":
            lines.append(f"{loc}: missing required field")
        elif "greater_than_equal" in err["type"] or "less_than_equal" in err["type"]:
            trait = loc.split(".")[-1]
            label = HEXACO_FIELD_LABELS.get(trait, trait)
            lines.append(f"{loc}: HEXACO trait {label} must stay between -1.0 and 1.0")
        else:
            lines.append(f"{loc}: {msg}")
    return lines


def validate_soul_payload(payload: dict[str, Any]) -> SoulFile:
    """Validate a soul dict; raise ValueError with readable messages on failure."""
    schema = _load_schema()
    validator = Draft202012Validator(schema)
    schema_errors = sorted(validator.iter_errors(payload), key=lambda e: list(e.path))

    if schema_errors:
        detail_lines = [_humanize_jsonschema_error(err) for err in schema_errors]
        raise ValueError(
            "Soul validation failed. Fix the following issues in your .soul.json:\n"
            + "\n".join(f"  • {line}" for line in detail_lines)
        )

    try:
        return SoulFile.model_validate(payload)
    except ValidationError as exc:
        detail_lines = _humanize_pydantic_error(exc)
        raise ValueError(
            "Soul validation failed. Fix the following issues in your .soul.json:\n"
            + "\n".join(f"  • {line}" for line in detail_lines)
        ) from exc


def validate_msv_payload(msv: dict[str, Any]) -> dict[str, Any]:
    """Validate a complete MSV payload; raise ValueError with readable messages."""
    try:
        return MetacognitiveStateVector.model_validate(msv).model_dump()
    except ValidationError as exc:
        detail_lines = _humanize_pydantic_error(exc)
        raise ValueError(
            "MSV validation failed. Fix the following issues:\n"
            + "\n".join(f"  • {line}" for line in detail_lines)
        ) from exc


def default_msv_dict() -> dict[str, Any]:
    """Default MSV matching soul schema shape."""
    return MetacognitiveStateVector(
        hexaco=HexacoTraits(H=0.5, E=0.5, X=0.5, A=0.5, C=0.5, O=0.5),
        moral_foundations=MoralFoundations(
            care_harm=0.5,
            fairness_cheating=0.5,
            loyalty_betrayal=0.5,
            authority_subversion=0.5,
            sanctity_degradation=0.5,
        ),
        drives=IntrinsicDrives(curiosity=0.5, autonomy=0.5, social_approval=0.5),
        epistemic_uncertainty=0.1,
        inner_monologue="Initiating interaction.",
    ).model_dump()
