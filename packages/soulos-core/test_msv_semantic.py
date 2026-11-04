"""Unit tests for semantic MSV shifts and behavioral summary."""

import pytest

from runtime.msv_update import (
    apply_semantic_hexaco_shift,
    behavioral_summary_from_drift,
    clamp_msv,
)
from soul_validation import default_msv_dict


def test_semantic_shift_clamped():
    base = default_msv_dict()
    out = apply_semantic_hexaco_shift(base, trait="E", shift="moderate_increase")
    assert out["hexaco"]["E"] == pytest.approx(base["hexaco"]["E"] + 0.10)


def test_semantic_shift_invalid_key_message():
    with pytest.raises(ValueError, match="Valid HEXACO keys"):
        apply_semantic_hexaco_shift(default_msv_dict(), trait="anger", shift="slight_increase")


def test_behavioral_summary_on_drift():
    baseline = clamp_msv(default_msv_dict())
    current = clamp_msv(default_msv_dict())
    current["hexaco"]["E"] = min(1.0, baseline["hexaco"]["E"] + 0.2)
    summary = behavioral_summary_from_drift(baseline, current)
    assert "emotionality" in summary.lower() or "E" in summary
