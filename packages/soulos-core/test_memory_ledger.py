"""Tests for .soul-memory ledger and soulignore (Phase 3)."""

import json
from pathlib import Path

import pytest

from runtime.memory_ledger import append_episode_line, export_memory_json, memory_root
from runtime.soulignore import contains_secret, validate_memory_content


def test_contains_secret_blocks_api_key():
    assert contains_secret("my key is sk-abcdefghijklmnopqrstuvwxyz123456")


def test_validate_memory_content_raises_on_secret():
    with pytest.raises(ValueError, match="secret"):
        validate_memory_content("token sk-abcdefghijklmnopqrstuvwxyz123456")


def test_append_episode_line_creates_jsonl(tmp_path: Path):
    path = append_episode_line(tmp_path, "User prefers composition over inheritance.")
    assert path.is_file()
    assert path.suffix == ".jsonl"
    lines = path.read_text(encoding="utf-8").strip().splitlines()
    row = json.loads(lines[0])
    assert row["summary"] == "User prefers composition over inheritance."
    assert row["type"] == "interaction"
    assert (memory_root(tmp_path) / "index.json").is_file()


def test_export_memory_json(tmp_path: Path):
    append_episode_line(tmp_path, "First memory line.")
    data = export_memory_json(tmp_path)
    assert len(data["episodes"]) == 1
    assert data["episodes"][0]["summary"] == "First memory line."
