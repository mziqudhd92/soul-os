"""Tests for .soul markdown build/parse in Studio."""

import json
from pathlib import Path

from soulos_studio.soul_form import build_soul_payload, parse_soul_file, validate_soul
from soulos_studio.soul_markdown import build_soul_markdown, parse_soul_markdown

EXAMPLE_JSON = Path(__file__).resolve().parents[3] / "examples" / "support-bot" / "support-bot.soul.json"
EXAMPLE_SOUL = Path(__file__).resolve().parents[3] / "examples" / "support-bot" / "support-bot.soul"


def test_build_soul_markdown_uses_long_hexaco_names():
    data = json.loads(EXAMPLE_JSON.read_text(encoding="utf-8"))
    form = parse_soul_file(data)
    text = build_soul_markdown(form)
    assert text.startswith("---\n")
    assert "honesty_humility:" in text
    assert "emotionality:" in text
    assert "extraversion:" in text
    assert data["description"] in text


def test_parse_soul_markdown_roundtrip():
    soul_text = EXAMPLE_SOUL.read_text(encoding="utf-8")
    form = parse_soul_markdown(soul_text)
    payload = build_soul_payload(form)
    validate_soul(payload)
    expected = json.loads(EXAMPLE_JSON.read_text(encoding="utf-8"))
    assert form["name"] == expected["name"]
    assert payload["baseline_msv"]["hexaco"] == expected["baseline_msv"]["hexaco"]
