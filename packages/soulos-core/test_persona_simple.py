"""Unit tests for simple persona mode (sliders → HEXACO MSV)."""

from runtime.hybrid import build_hybrid_system_prompt
from runtime.persona_simple import (
    SIMPLE_DEFAULTS,
    apply_persona_mode,
    build_simple_baseline_msv,
    simple_sliders_to_hexaco,
)


def _identity(warmth: float, rigor: float, caution: float) -> dict:
    msv = build_simple_baseline_msv(warmth, rigor, caution)
    return {
        "name": "Eval Bot",
        "role": "Tester",
        "description": "Eval fixture.",
        "current_msv": msv,
    }


def test_simple_sliders_to_hexaco_in_range():
    hexaco = simple_sliders_to_hexaco(0.5, 0.5, 0.5)
    for key in ("H", "E", "X", "A", "C", "O"):
        assert -1.0 <= hexaco[key] <= 1.0


def test_caution_increases_honesty():
    cautious = simple_sliders_to_hexaco(0.5, 0.5, 0.9)
    bold = simple_sliders_to_hexaco(0.5, 0.5, 0.2)
    assert cautious["H"] > bold["H"]


def test_warmth_increases_agreeableness():
    warm = simple_sliders_to_hexaco(0.9, 0.5, 0.5)
    cold = simple_sliders_to_hexaco(0.2, 0.5, 0.5)
    assert warm["A"] > cold["A"]


def test_rigor_increases_conscientiousness():
    strict = simple_sliders_to_hexaco(0.5, 0.95, 0.5)
    loose = simple_sliders_to_hexaco(0.5, 0.1, 0.5)
    assert strict["C"] > loose["C"]


def test_build_simple_baseline_msv_shape():
    msv = build_simple_baseline_msv(0.7, 0.7, 0.6, inner_monologue="Ready.")
    assert set(msv["hexaco"]) == {"H", "E", "X", "A", "C", "O"}
    assert "moral_foundations" in msv
    assert "drives" in msv
    assert 0.0 <= msv["epistemic_uncertainty"] <= 1.0
    assert msv["inner_monologue"] == "Ready."


def test_apply_persona_mode_noop_for_advanced():
    soul = {"name": "X", "persona_mode": "advanced", "baseline_msv": {"hexaco": {}}}
    assert apply_persona_mode(soul) is soul


def test_apply_persona_mode_derives_baseline_msv():
    soul = {
        "name": "Simple Bot",
        "persona_mode": "simple",
        "simple_persona": {"warmth": 0.9, "rigor": 0.8, "caution": 0.3},
        "baseline_msv": {"inner_monologue": "Custom mono."},
    }
    out = apply_persona_mode(soul)
    assert out["baseline_msv"]["inner_monologue"] == "Custom mono."
    assert out["baseline_msv"]["hexaco"]["A"] > 0


def test_apply_persona_mode_runtime_config_fallback():
    soul = {
        "name": "Simple Bot",
        "runtime_config": {"persona_mode": "simple"},
        "simple_persona": SIMPLE_DEFAULTS,
    }
    out = apply_persona_mode(soul)
    assert "hexaco" in out["baseline_msv"]


def test_apply_persona_mode_strips_authoring_fields():
    soul = {
        "name": "Simple Bot",
        "persona_mode": "simple",
        "simple_persona": SIMPLE_DEFAULTS,
    }
    out = apply_persona_mode(soul)
    assert "persona_mode" not in out
    assert "simple_persona" not in out
    assert "hexaco" in out["baseline_msv"]


def test_warmth_delta_changes_system_prompt():
    warm = build_hybrid_system_prompt(_identity(0.9, 0.5, 0.5), [], {})
    cold = build_hybrid_system_prompt(_identity(0.2, 0.5, 0.5), [], {})
    assert warm != cold


def test_rigor_delta_changes_system_prompt():
    strict = build_hybrid_system_prompt(_identity(0.5, 0.95, 0.5), [], {})
    loose = build_hybrid_system_prompt(_identity(0.5, 0.1, 0.5), [], {})
    assert strict != loose
