"""Build and validate .soul.json for SoulOS Studio."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError as JsonSchemaValidationError

HEXACO_LABELS = {
    "H": "Honesty-Humility",
    "E": "Emotionality",
    "X": "eXtraversion",
    "A": "Agreeableness",
    "C": "Conscientiousness",
    "O": "Openness",
}

MORAL_META = [
    ("care_harm", "Care / Harm"),
    ("fairness_cheating", "Fairness"),
    ("loyalty_betrayal", "Loyalty"),
    ("authority_subversion", "Authority"),
    ("sanctity_degradation", "Sanctity"),
]

DRIVE_META = [
    ("curiosity", "Curiosity"),
    ("autonomy", "Autonomy"),
    ("social_approval", "Social approval"),
]

ATTACHMENT_STYLES = ("Secure", "Anxious-Preoccupied", "Dismissive-Avoidant")

_SCHEMA_PATH = Path(__file__).resolve().parent / "schemas" / "soul.schema.json"


def _load_schema() -> dict[str, Any]:
    with _SCHEMA_PATH.open(encoding="utf-8") as f:
        return json.load(f)


def default_form() -> dict[str, Any]:
    return {
        "name": "My Avatar",
        "role": "Assistant",
        "description": (
            "You are a helpful assistant. Be clear, honest, and consistent with the user's goals."
        ),
        "attachment_style": "Secure",
        "hexaco": {"H": 0.9, "E": 0.6, "X": 0.6, "A": 0.9, "C": 0.9, "O": 0.8},
        "moral_foundations": {
            "care_harm": 0.85,
            "fairness_cheating": 0.8,
            "loyalty_betrayal": 0.7,
            "authority_subversion": 0.5,
            "sanctity_degradation": 0.4,
        },
        "drives": {
            "curiosity": 0.7,
            "autonomy": 0.45,
            "social_approval": 0.75,
        },
        "epistemic_uncertainty": 0.1,
        "inner_monologue": "Ready to assist with clarity and care.",
    }


def build_soul_payload(form: dict[str, Any]) -> dict[str, Any]:
    return {
        "name": (form.get("name") or "My Avatar").strip(),
        "role": (form.get("role") or "Assistant").strip(),
        "description": (form.get("description") or "Assistant avatar.").strip(),
        "attachment_style": form.get("attachment_style") or "Secure",
        "baseline_msv": {
            "hexaco": dict(form.get("hexaco") or {}),
            "moral_foundations": dict(form.get("moral_foundations") or {}),
            "drives": dict(form.get("drives") or {}),
            "epistemic_uncertainty": float(form.get("epistemic_uncertainty", 0.1)),
            "inner_monologue": (form.get("inner_monologue") or "Ready.").strip(),
        },
        "status": "available",
    }


def parse_soul_file(data: dict[str, Any]) -> dict[str, Any]:
    msv = data.get("baseline_msv") or {}
    hexaco = msv.get("hexaco") or {}
    return {
        "name": data.get("name", ""),
        "role": data.get("role", ""),
        "description": data.get("description", ""),
        "attachment_style": data.get("attachment_style", "Secure"),
        "hexaco": {k: float(hexaco.get(k, 0.5)) for k in HEXACO_LABELS},
        "moral_foundations": {
            k: float((msv.get("moral_foundations") or {}).get(k, 0.5)) for k, _ in MORAL_META
        },
        "drives": {k: float((msv.get("drives") or {}).get(k, 0.5)) for k, _ in DRIVE_META},
        "epistemic_uncertainty": float(msv.get("epistemic_uncertainty", 0.1)),
        "inner_monologue": str(msv.get("inner_monologue", "Ready.")),
    }


def validate_soul(payload: dict[str, Any]) -> None:
    validator = Draft202012Validator(_load_schema())
    errors = sorted(validator.iter_errors(payload), key=lambda e: e.path)
    if errors:
        first = errors[0]
        path = "/" + "/".join(str(p) for p in first.path)
        raise ValueError(f"Soul validation failed at {path}: {first.message}")


def soul_filename(name: str) -> str:
    slug = "".join(c if c.isalnum() else "-" for c in name.lower()).strip("-")
    while "--" in slug:
        slug = slug.replace("--", "-")
    return f"{slug[:48] or 'my-bot'}.soul.json"
