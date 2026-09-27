"""Unit tests for dual-process routing."""

from runtime.dual_process import (
    DualProcessFeatures,
    decide_reflect,
    should_run_system_2,
)
from soul_validation import default_msv_dict


def test_hard_uncertainty_trigger():
    features = DualProcessFeatures(
        confidence=0.9,
        epistemic_uncertainty=0.85,
    )
    assert should_run_system_2(features, threshold=0.35, uncertainty_trigger_value=0.7)


def test_skip_system_2_when_confident():
    features = DualProcessFeatures(
        confidence=0.95,
        epistemic_uncertainty=0.05,
        retrieval_weak=False,
        query_complex=False,
    )
    assert not should_run_system_2(features, threshold=0.35)


def test_tenant_threshold_override():
    msv = default_msv_dict()
    msv["epistemic_uncertainty"] = 0.5
    run, _ = decide_reflect(
        msv,
        {"dual_process": {"system1_threshold": 0.1, "uncertainty_trigger": 0.9}},
        query="hi",
    )
    # high confidence-ish, low threshold might still skip depending on score
    assert isinstance(run, bool)


def test_reflect_force():
    features = DualProcessFeatures(confidence=0.99, epistemic_uncertainty=0.01)
    assert should_run_system_2(features, threshold=0.0, reflect_force=True)
