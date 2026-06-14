"""Tests for .soul compiler (Phase 1 Evolution Matrix)."""

import json
from pathlib import Path

import pytest

from soul_compile import (
    compile_soul_bytes,
    compile_soul_text,
    load_soul_path,
    parse_soul_request_payload,
)
from soul_validation import validate_soul_payload

EXAMPLE_JSON = (
    Path(__file__).resolve().parents[2] / "examples" / "support-bot" / "support-bot.soul.json"
)
EXAMPLE_SOUL = (
    Path(__file__).resolve().parents[2] / "examples" / "support-bot" / "support-bot.soul"
)


def test_compile_support_bot_soul_matches_json():
    text = EXAMPLE_SOUL.read_text(encoding="utf-8")
    compiled = compile_soul_text(text)
    expected = json.loads(EXAMPLE_JSON.read_text(encoding="utf-8"))

    assert compiled["name"] == expected["name"]
    assert compiled["role"] == expected["role"]
    assert compiled["description"] == expected["description"]
    assert compiled["attachment_style"] == expected["attachment_style"]
    assert compiled["status"] == expected["status"]
    assert compiled["baseline_msv"]["hexaco"] == expected["baseline_msv"]["hexaco"]
    assert (
        compiled["baseline_msv"]["moral_foundations"]
        == expected["baseline_msv"]["moral_foundations"]
    )
    assert compiled["baseline_msv"]["drives"] == expected["baseline_msv"]["drives"]
    assert (
        compiled["baseline_msv"]["epistemic_uncertainty"]
        == expected["baseline_msv"]["epistemic_uncertainty"]
    )
    assert (
        compiled["baseline_msv"]["inner_monologue"]
        == expected["baseline_msv"]["inner_monologue"]
    )


def test_compile_roundtrip_validates():
    text = EXAMPLE_SOUL.read_text(encoding="utf-8")
    compiled = compile_soul_text(text)
    soul = validate_soul_payload(compiled)
    assert soul.name == "Site Support"


def test_json_request_payload_still_works():
    raw = EXAMPLE_JSON.read_bytes()
    payload = parse_soul_request_payload(raw, "application/json", None)
    soul = validate_soul_payload(payload)
    assert soul.role == "Customer Support Agent"


def test_soul_request_payload_from_front_matter():
    raw = EXAMPLE_SOUL.read_bytes()
    payload = parse_soul_request_payload(raw, "text/plain", "support-bot.soul")
    assert payload["name"] == "Site Support"
    validate_soul_payload(payload)


def test_load_soul_path_json_and_soul():
    json_payload = load_soul_path(EXAMPLE_JSON)
    soul_payload = load_soul_path(EXAMPLE_SOUL)
    assert json_payload["name"] == soul_payload["name"]


def test_invalid_soul_raises_value_error():
    with pytest.raises(ValueError, match="front matter"):
        compile_soul_text("no front matter here")


def test_missing_name_raises():
    text = "---\nrole: Bot\npsychology:\n  hexaco:\n    H: 0.5\n---\n\nBody text here.\n"
    with pytest.raises(ValueError, match="name"):
        compile_soul_text(text)


def test_hexaco_long_name_mapping():
    text = """---
name: Test
role: Tester
attachment_style: Secure
psychology:
  hexaco:
    honesty_humility: 0.1
    emotionality: 0.2
    extraversion: 0.3
    agreeableness: 0.4
    conscientiousness: 0.5
    openness: 0.6
  inner_monologue: Testing.
---

Description line.
"""
    compiled = compile_soul_text(text)
    hexaco = compiled["baseline_msv"]["hexaco"]
    assert hexaco == {"H": 0.1, "E": 0.2, "X": 0.3, "A": 0.4, "C": 0.5, "O": 0.6}


def test_hexaco_short_keys_accepted():
    text = """---
name: Test
role: Tester
attachment_style: Secure
psychology:
  hexaco:
    H: 0.9
    E: 0.8
    X: 0.7
    A: 0.6
    C: 0.5
    O: 0.4
  inner_monologue: Short keys.
---

Body.
"""
    compiled = compile_soul_text(text)
    assert compiled["baseline_msv"]["hexaco"]["H"] == 0.9


def test_phase2_fields_ignored():
    text = """---
id: legacy-id
version: "2.0"
engine:
  llm: claude
dual_process:
  system1_threshold: 0.35
name: Phase2
role: Ignored
attachment_style: Secure
psychology:
  dual_process:
    system1_threshold: 0.2
  hexaco:
    H: 0.5
    E: 0.5
    X: 0.5
    A: 0.5
    C: 0.5
    O: 0.5
  inner_monologue: ok
---

Phase 2 metadata stripped.
"""
    compiled = compile_soul_text(text)
    assert "id" not in compiled
    assert "engine" not in compiled
    validate_soul_payload(compiled)


def test_default_moral_and_drives_when_missing():
    text = """---
name: Defaults
role: Bot
attachment_style: Secure
psychology:
  hexaco:
    H: 0.5
    E: 0.5
    X: 0.5
    A: 0.5
    C: 0.5
    O: 0.5
  inner_monologue: Defaults applied.
---

Uses defaults for moral and drives.
"""
    compiled = compile_soul_text(text)
    msv = compiled["baseline_msv"]
    assert msv["moral_foundations"]["care_harm"] == 0.5
    assert msv["drives"]["curiosity"] == 0.5


def test_compile_soul_bytes():
    raw = EXAMPLE_SOUL.read_bytes()
    compiled = compile_soul_bytes(raw, filename_hint="support-bot.soul")
    assert compiled["name"] == "Site Support"
