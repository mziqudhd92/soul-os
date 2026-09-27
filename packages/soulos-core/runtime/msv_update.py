"""Constrained MSV updates: validate, clamp, EMA, confidence gate, uncertainty hysteresis."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from config import (
    MSV_EMA_ALPHA,
    MSV_EMA_MIN_CONFIDENCE,
    MSV_MAX_STEP,
    MSV_RETRIEVAL_UNCERTAINTY_NUDGE,
    MSV_UNCERTAINTY_DECAY,
    MSV_UNCERTAINTY_FLOOR,
)

HEXACO_KEYS = ("H", "E", "X", "A", "C", "O")
MORAL_KEYS = (
    "care_harm",
    "fairness_cheating",
    "loyalty_betrayal",
    "authority_subversion",
    "sanctity_degradation",
)
DRIVE_KEYS = ("curiosity", "autonomy", "social_approval")


def _clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def clamp_msv(msv: dict[str, Any]) -> dict[str, Any]:
    """Clamp numeric MSV fields to schema ranges; leave unknown keys."""
    out = deepcopy(msv) if isinstance(msv, dict) else {}
    hexaco = out.get("hexaco") if isinstance(out.get("hexaco"), dict) else {}
    out["hexaco"] = {
        k: _clamp(float(hexaco.get(k, 0.0)), -1.0, 1.0) for k in HEXACO_KEYS
    }
    morals = (
        out.get("moral_foundations")
        if isinstance(out.get("moral_foundations"), dict)
        else {}
    )
    out["moral_foundations"] = {
        k: _clamp(float(morals.get(k, 0.5)), 0.0, 1.0) for k in MORAL_KEYS
    }
    drives = out.get("drives") if isinstance(out.get("drives"), dict) else {}
    out["drives"] = {
        k: _clamp(float(drives.get(k, 0.5)), 0.0, 1.0) for k in DRIVE_KEYS
    }
    out["epistemic_uncertainty"] = _clamp(
        float(out.get("epistemic_uncertainty", 0.1)), 0.0, 1.0
    )
    mono = out.get("inner_monologue", "")
    out["inner_monologue"] = str(mono)[:500] if mono is not None else ""
    return out


def reflect_confidence(proposed: dict[str, Any]) -> float:
    """Confidence in a proposed MSV update (higher = safer to EMA)."""
    u = float(proposed.get("epistemic_uncertainty", 0.5))
    return _clamp(1.0 - u, 0.0, 1.0)


def _ema_scalar(prev: float, proposed: float, alpha: float, max_step: float) -> float:
    blended = (1.0 - alpha) * prev + alpha * proposed
    delta = _clamp(blended - prev, -max_step, max_step)
    return prev + delta


def apply_ema_msv(
    previous: dict[str, Any],
    proposed: dict[str, Any],
    *,
    alpha: float = MSV_EMA_ALPHA,
    max_step: float = MSV_MAX_STEP,
) -> dict[str, Any]:
    prev = clamp_msv(previous)
    prop = clamp_msv(proposed)
    out = deepcopy(prev)
    out["hexaco"] = {
        k: _ema_scalar(prev["hexaco"][k], prop["hexaco"][k], alpha, max_step)
        for k in HEXACO_KEYS
    }
    out["moral_foundations"] = {
        k: _ema_scalar(
            prev["moral_foundations"][k], prop["moral_foundations"][k], alpha, max_step
        )
        for k in MORAL_KEYS
    }
    out["drives"] = {
        k: _ema_scalar(prev["drives"][k], prop["drives"][k], alpha, max_step)
        for k in DRIVE_KEYS
    }
    out["inner_monologue"] = prop.get("inner_monologue") or prev.get("inner_monologue", "")
    out["epistemic_uncertainty"] = prop["epistemic_uncertainty"]
    return out


def apply_uncertainty_hysteresis(
    previous_u: float,
    proposed_u: float,
    *,
    retrieval_weak: bool = False,
    floor: float = MSV_UNCERTAINTY_FLOOR,
    decay: float = MSV_UNCERTAINTY_DECAY,
    nudge: float = MSV_RETRIEVAL_UNCERTAINTY_NUDGE,
) -> float:
    """Blend uncertainty with decay; optional small nudge if retrieval was weak."""
    blended = decay * previous_u + (1.0 - decay) * proposed_u
    if retrieval_weak:
        blended = min(1.0, blended + nudge)
    return max(floor, min(1.0, blended))


def merge_reflected_msv(
    previous: dict[str, Any],
    proposed: dict[str, Any],
    *,
    retrieval_weak: bool = False,
    min_confidence: float = MSV_EMA_MIN_CONFIDENCE,
) -> dict[str, Any]:
    """Apply confidence gate, EMA, and uncertainty hysteresis."""
    prev = clamp_msv(previous)
    prop = clamp_msv(proposed)
    conf = reflect_confidence(prop)
    if conf < min_confidence:
        # Keep prior traits; allow short monologue update only
        out = deepcopy(prev)
        mono = prop.get("inner_monologue")
        if isinstance(mono, str) and mono.strip():
            out["inner_monologue"] = mono[:500]
        out["epistemic_uncertainty"] = apply_uncertainty_hysteresis(
            float(prev["epistemic_uncertainty"]),
            float(prop["epistemic_uncertainty"]),
            retrieval_weak=retrieval_weak,
        )
        return out

    out = apply_ema_msv(prev, prop)
    out["epistemic_uncertainty"] = apply_uncertainty_hysteresis(
        float(prev["epistemic_uncertainty"]),
        float(prop["epistemic_uncertainty"]),
        retrieval_weak=retrieval_weak,
    )
    return clamp_msv(out)
