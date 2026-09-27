"""Closed-enum trait → prompt directives (no free-text interpolation from MSV)."""

from __future__ import annotations

from typing import Any, Literal

Bucket = Literal["low", "mid", "high"]

# Fixed sanitized strings only — never interpolate raw MSV values into prompts.
TRAIT_DIRECTIVE_TABLE: dict[str, dict[Bucket, str]] = {
    "H": {
        "low": "Prefer helpful speculation when uncertain; still avoid fabricating citations.",
        "mid": "Be honest about uncertainty; do not invent facts or sources.",
        "high": "Prioritize honesty and anti-hallucination; refuse unsupported claims.",
    },
    "E": {
        "low": "Keep affective tone steady and measured.",
        "mid": "Show appropriate emotional awareness without dramatics.",
        "high": "Acknowledge feelings explicitly; validate emotional stakes.",
    },
    "X": {
        "low": "Keep replies concise; minimize filler.",
        "mid": "Use moderate length with clear structure.",
        "high": "Be expansive and conversational when it aids understanding.",
    },
    "A": {
        "low": "Be direct and critical when quality is at risk.",
        "mid": "Balance warmth with candor.",
        "high": "Be warm, cooperative, and supportive in tone.",
    },
    "C": {
        "low": "Allow flexible, exploratory structure.",
        "mid": "Organize answers clearly with light structure.",
        "high": "Be structured, precise, and checklist-oriented.",
    },
    "O": {
        "low": "Prefer proven patterns over novel tangents.",
        "mid": "Balance creativity with practicality.",
        "high": "Offer creative alternatives when useful.",
    },
}

UNCERTAINTY_DIRECTIVES: dict[Bucket, str] = {
    "low": "State conclusions with appropriate confidence.",
    "mid": "Hedge moderately when evidence is incomplete.",
    "high": "Hedge clearly; ask clarifying questions when uncertainty is high.",
}


def _bucket(value: float, *, lo: float = -1.0, hi: float = 1.0) -> Bucket:
    # Map range to thirds
    span = hi - lo
    if span <= 0:
        return "mid"
    t = (float(value) - lo) / span
    if t < 1.0 / 3.0:
        return "low"
    if t < 2.0 / 3.0:
        return "mid"
    return "high"


def _unit_bucket(value: float) -> Bucket:
    return _bucket(value, lo=0.0, hi=1.0)


def compile_trait_directives(msv: dict[str, Any] | None) -> str:
    """Map HEXACO + uncertainty to fixed template strings only."""
    if not isinstance(msv, dict):
        return ""
    hexaco = msv.get("hexaco") if isinstance(msv.get("hexaco"), dict) else {}
    lines: list[str] = []
    for key in ("H", "E", "X", "A", "C", "O"):
        raw = hexaco.get(key, 0.0)
        try:
            b = _bucket(float(raw))
        except (TypeError, ValueError):
            b = "mid"
        lines.append(TRAIT_DIRECTIVE_TABLE[key][b])
    try:
        u = float(msv.get("epistemic_uncertainty", 0.15))
    except (TypeError, ValueError):
        u = 0.15
    lines.append(UNCERTAINTY_DIRECTIVES[_unit_bucket(u)])
    return "\n".join(f"- {line}" for line in lines)
