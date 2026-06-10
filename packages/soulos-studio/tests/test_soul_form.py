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

