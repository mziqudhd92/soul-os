"""Tests for .soul markdown build/parse in Studio."""

import json
from pathlib import Path

import pytest

from soulos_studio.soul_form import build_soul_payload, parse_soul_file, validate_soul
from soulos_studio.soul_markdown import (
    _hexaco_from_raw,
    build_soul_markdown,
    parse_soul_markdown,
)

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


def test_hexaco_from_raw_empty_and_long_keys():
    assert _hexaco_from_raw(None) == {k: 0.5 for k in "HEXACO"}
    mapped = _hexaco_from_raw({"honesty_humility": 0.9, "E": 0.2})
    assert mapped["H"] == 0.9
    assert mapped["E"] == 0.2


def test_parse_soul_markdown_errors():
    with pytest.raises(ValueError, match="front matter"):
        parse_soul_markdown("no fences")
    with pytest.raises(ValueError, match="closing ---"):
        parse_soul_markdown("---\nname: x\n")
    with pytest.raises(ValueError, match="YAML"):
        parse_soul_markdown("---\n: bad: [\n---\n")
    with pytest.raises(ValueError, match="mapping"):
        parse_soul_markdown("---\njust-a-string\n---\nbody\n")


def test_parse_soul_markdown_non_dict_psychology():
    text = "---\nname: X\npsychology: not-a-map\n---\nHello\n"
    form = parse_soul_markdown(text)
    assert form["name"] == "X"
    assert form["description"] == "Hello"
    assert form["hexaco"] == {k: 0.5 for k in "HEXACO"}
