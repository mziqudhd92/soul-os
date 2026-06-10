import pytest

from soul_validation import validate_msv_payload, validate_soul_payload

VALID = {
    "name": "Evelyn",
    "role": "Therapist",
    "description": "Compassionate listener.",
    "attachment_style": "Secure",
    "baseline_msv": {
        "hexaco": {"H": 0.9, "E": 0.6, "X": 0.6, "A": 0.9, "C": 0.9, "O": 0.8},
        "moral_foundations": {
            "care_harm": 1.0,
            "fairness_cheating": 0.7,
            "loyalty_betrayal": 0.8,
            "authority_subversion": 0.3,
            "sanctity_degradation": 0.5,
        },
        "drives": {"curiosity": 0.8, "autonomy": 0.4, "social_approval": 0.9},
        "epistemic_uncertainty": 0.1,
        "inner_monologue": "Ready to listen.",
    },
}


def test_valid_soul():
    soul = validate_soul_payload(VALID)
    assert soul.name == "Evelyn"
    assert soul.baseline_msv.hexaco.H == 0.9


def test_invalid_hexaco_range():
    bad = {
        **VALID,
        "baseline_msv": {
            **VALID["baseline_msv"],
            "hexaco": {"H": 1.5, "E": 0.6, "X": 0.6, "A": 0.9, "C": 0.9, "O": 0.8},
        },
    }
    with pytest.raises(ValueError, match="Soul validation failed"):
        validate_soul_payload(bad)


def test_valid_msv_payload():
    msv = validate_msv_payload(VALID["baseline_msv"])
    assert msv["hexaco"]["H"] == 0.9


def test_invalid_msv_payload():
    bad = {**VALID["baseline_msv"], "epistemic_uncertainty": 2.0}
    with pytest.raises(ValueError, match="MSV validation failed"):
        validate_msv_payload(bad)


def test_missing_required_field():
    bad = {"name": "X", "role": "Y"}
    with pytest.raises(ValueError, match="Soul validation failed"):
        validate_soul_payload(bad)
