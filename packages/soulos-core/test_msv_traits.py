"""Unit tests for constrained MSV updates and trait directives."""

import pytest

from runtime.hybrid import build_hybrid_system_prompt
from runtime.msv_update import (
    apply_uncertainty_hysteresis,
    merge_reflected_msv,
    reflect_confidence,
)
from runtime.trait_directives import TRAIT_DIRECTIVE_TABLE, compile_trait_directives
from soul_validation import default_msv_dict


def test_ema_gated_on_low_confidence():
    prev = default_msv_dict()
    prev["hexaco"]["A"] = 0.5
    proposed = default_msv_dict()
    proposed["hexaco"]["A"] = -1.0
    proposed["epistemic_uncertainty"] = 0.9  # confidence 0.1 < 0.60
    proposed["inner_monologue"] = "noisy"
    out = merge_reflected_msv(prev, proposed)
    assert out["hexaco"]["A"] == 0.5
    assert out["inner_monologue"] == "noisy"


def test_ema_applies_when_confident():
    prev = default_msv_dict()
    prev["hexaco"]["A"] = 0.0
    proposed = default_msv_dict()
    proposed["hexaco"]["A"] = 1.0
    proposed["epistemic_uncertainty"] = 0.1
    out = merge_reflected_msv(prev, proposed)
    assert 0.0 < out["hexaco"]["A"] <= 0.15 + 1e-9  # max step


def test_uncertainty_hysteresis_not_direct_assign():
    u = apply_uncertainty_hysteresis(0.2, 0.9, retrieval_weak=True, decay=0.7, nudge=0.05)
    assert u < 0.9
    assert u >= 0.05


def test_trait_directives_closed_enum_only():
    msv = default_msv_dict()
    msv["hexaco"]["H"] = 0.95
    text = compile_trait_directives(msv)
    assert TRAIT_DIRECTIVE_TABLE["H"]["high"] in text
    assert "0.95" not in text
    assert "<script>" not in text


def test_hybrid_prompt_includes_traits():
    identity = {
        "name": "Ada",
        "role": "Support",
        "description": "Helpful.",
        "current_msv": default_msv_dict(),
    }
    prompt = build_hybrid_system_prompt(identity, ["fact one"], {})
    assert "Behavior directives:" in prompt
    assert "fact one" in prompt


def test_reflect_confidence():
    assert reflect_confidence({"epistemic_uncertainty": 0.2}) == pytest.approx(0.8)
