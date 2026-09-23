"""Tests for soul form build/parse/validate."""

import json
from pathlib import Path

from soulos_studio.soul_form import (
    build_soul_payload,
    default_form,
    parse_soul_file,
    soul_filename,
    validate_soul,
)

EXAMPLE_SOUL = Path(__file__).resolve().parents[3] / "examples" / "support-bot" / "support-bot.soul.json"


def test_default_form_builds_valid_soul():
    form = default_form()
    payload = build_soul_payload(form)
    validate_soul(payload)
    assert payload["name"] == "My Avatar"
    assert "hexaco" in payload["baseline_msv"]


def test_parse_example_soul_roundtrip():
    data = json.loads(EXAMPLE_SOUL.read_text(encoding="utf-8"))
    form = parse_soul_file(data)
    payload = build_soul_payload(form)
    validate_soul(payload)
    assert form["name"] == data["name"]
    assert payload["baseline_msv"]["hexaco"]["H"] == data["baseline_msv"]["hexaco"]["H"]


def test_soul_filename_slug():
    assert soul_filename("Site Support") == "site-support.soul.json"
    assert soul_filename("!!!") == "my-bot.soul.json"
    assert soul_filename("a--b---c") == "a-b-c.soul.json"


def test_build_simple_persona_mode():
    form = default_form()
    form["persona_mode"] = "simple"
    form["simple_persona"] = {"warmth": 0.5, "rigor": 0.6, "caution": 0.4}
    payload = build_soul_payload(form)
    assert payload["persona_mode"] == "simple"
    assert payload["simple_persona"]["warmth"] == 0.5


def test_validate_soul_raises_on_invalid():
    import pytest

    with pytest.raises(ValueError, match="Soul validation failed"):
        validate_soul({"name": "x"})

