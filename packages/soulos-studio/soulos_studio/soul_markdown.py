"""Build and parse unified .soul (YAML front matter + Markdown) for Studio."""

from __future__ import annotations

from typing import Any

import yaml

HEXACO_SHORT_TO_LONG: dict[str, str] = {
    "H": "honesty_humility",
    "E": "emotionality",
    "X": "extraversion",
    "A": "agreeableness",
    "C": "conscientiousness",
    "O": "openness",
}

HEXACO_LONG_TO_SHORT: dict[str, str] = {v: k for k, v in HEXACO_SHORT_TO_LONG.items()}
HEXACO_LONG_TO_SHORT["honesty-humility"] = "H"

MORAL_KEYS = (
    "care_harm",
    "fairness_cheating",
    "loyalty_betrayal",
    "authority_subversion",
    "sanctity_degradation",
)
DRIVE_KEYS = ("curiosity", "autonomy", "social_approval")


def _hexaco_to_long(hexaco: dict[str, float]) -> dict[str, float]:
    return {
        HEXACO_SHORT_TO_LONG[k]: float(hexaco.get(k, 0.5))
        for k in "HEXACO"
    }


def _hexaco_from_raw(raw: dict[str, Any] | None) -> dict[str, float]:
    if not raw:
        return {k: 0.5 for k in "HEXACO"}
    mapped: dict[str, float] = {}
    for key, value in raw.items():
        short = key if key in "HEXACO" else HEXACO_LONG_TO_SHORT.get(key.lower())
        if short and short not in mapped:
            mapped[short] = float(value)
    return {k: mapped.get(k, 0.5) for k in "HEXACO"}


def build_soul_markdown(form: dict[str, Any]) -> str:
    """Serialize form state to .soul text (YAML front matter + Markdown body)."""
    front_matter: dict[str, Any] = {
        "name": (form.get("name") or "My Avatar").strip(),
        "role": (form.get("role") or "Assistant").strip(),
        "attachment_style": form.get("attachment_style") or "Secure",
        "status": "available",
        "psychology": {
            "hexaco": _hexaco_to_long(form.get("hexaco") or {}),
            "moral_foundations": dict(form.get("moral_foundations") or {}),
            "drives": dict(form.get("drives") or {}),
            "epistemic_uncertainty": float(form.get("epistemic_uncertainty", 0.1)),
            "inner_monologue": (form.get("inner_monologue") or "Ready.").strip(),
        },
    }

    yaml_text = yaml.dump(
        front_matter,
        default_flow_style=False,
        allow_unicode=True,
        sort_keys=False,
    ).rstrip()

    description = (form.get("description") or "Assistant avatar.").strip()
    return f"---\n{yaml_text}\n---\n\n{description}\n"


def parse_soul_markdown(text: str) -> dict[str, Any]:
    """Parse .soul text into Studio form dict (mirrors core compile mapping)."""
    normalized = text.lstrip("\ufeff")
    if not normalized.startswith("---"):
        raise ValueError(".soul file must start with YAML front matter (---)")

    parts = normalized.split("---", 2)
    if len(parts) < 3:
        raise ValueError(".soul file must include closing --- after front matter")

    yaml_block = parts[1]
    body = parts[2].lstrip("\r\n")

    try:
        fm = yaml.safe_load(yaml_block)
    except yaml.YAMLError as exc:
        raise ValueError(f"YAML parse error: {exc}") from exc

    if not isinstance(fm, dict):
        raise ValueError("Front matter must be a YAML mapping")

    psychology = fm.get("psychology") or {}
    if not isinstance(psychology, dict):
        psychology = {}

    return {
        "name": str(fm.get("name", "")).strip(),
        "role": str(fm.get("role", "")).strip(),
        "description": body.strip(),
        "attachment_style": str(fm.get("attachment_style", "Secure")).strip(),
        "hexaco": _hexaco_from_raw(psychology.get("hexaco")),
        "moral_foundations": {
            k: float((psychology.get("moral_foundations") or {}).get(k, 0.5))
            for k in MORAL_KEYS
        },
        "drives": {
            k: float((psychology.get("drives") or {}).get(k, 0.5)) for k in DRIVE_KEYS
        },
        "epistemic_uncertainty": float(psychology.get("epistemic_uncertainty", 0.1)),
        "inner_monologue": str(psychology.get("inner_monologue", "Ready.")).strip(),
    }
