"""Simple persona mode: warmth / rigor / caution → HEXACO MSV."""

from __future__ import annotations

from typing import Any

# warmth → A, E; rigor → C, H; caution → H, epistemic_uncertainty inverse
SIMPLE_DEFAULTS = {"warmth": 0.7, "rigor": 0.7, "caution": 0.6}


def simple_sliders_to_hexaco(
    warmth: float, rigor: float, caution: float
) -> dict[str, float]:
    """Map 0..1 sliders to HEXACO range -1..1."""
    w, r, c = float(warmth), float(rigor), float(caution)
    return {
        "H": round(0.2 + c * 0.6 + r * 0.2, 3),  # -1..1 via 2*x-1 later
        "E": round(2 * (0.3 + w * 0.5) - 1, 3),
        "X": round(2 * (0.4 + w * 0.4) - 1, 3),
        "A": round(2 * (0.3 + w * 0.6) - 1, 3),
        "C": round(2 * (0.2 + r * 0.7) - 1, 3),
        "O": round(2 * (0.4 + (1 - c) * 0.3) - 1, 3),
    }


def build_simple_baseline_msv(
    warmth: float = 0.7,
    rigor: float = 0.7,
    caution: float = 0.6,
    inner_monologue: str | None = None,
) -> dict[str, Any]:
    hexaco = simple_sliders_to_hexaco(warmth, rigor, caution)
    mono = inner_monologue or (
        f"Calibrated: warmth={warmth:.2f}, rigor={rigor:.2f}, caution={caution:.2f}."
    )
    return {
        "hexaco": hexaco,
        "moral_foundations": {
            "care_harm": round(0.5 + warmth * 0.4, 3),
            "fairness_cheating": round(0.5 + rigor * 0.4, 3),
            "loyalty_betrayal": 0.65,
            "authority_subversion": round(0.3 + rigor * 0.4, 3),
            "sanctity_degradation": 0.4,
        },
        "drives": {
            "curiosity": round(0.4 + (1 - caution) * 0.4, 3),
            "autonomy": round(0.3 + rigor * 0.3, 3),
            "social_approval": round(0.4 + warmth * 0.5, 3),
        },
        "epistemic_uncertainty": round(0.05 + (1 - caution) * 0.25, 3),
        "inner_monologue": mono,
    }


def apply_persona_mode(soul: dict[str, Any]) -> dict[str, Any]:
    """If persona_mode=simple, derive baseline_msv from simple_persona sliders."""
    mode = soul.get("persona_mode") or (soul.get("runtime_config") or {}).get(
        "persona_mode"
    )
    if mode != "simple":
        return soul
    sp = soul.get("simple_persona") or SIMPLE_DEFAULTS
    baseline = build_simple_baseline_msv(
        warmth=sp.get("warmth", 0.7),
        rigor=sp.get("rigor", 0.7),
        caution=sp.get("caution", 0.6),
        inner_monologue=soul.get("baseline_msv", {}).get("inner_monologue", "Ready."),
    )
    out = dict(soul)
    out["baseline_msv"] = baseline
    return out
