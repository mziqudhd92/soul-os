"""CLI tests for `soulos pack`."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from cli import main

REPO = Path(__file__).resolve().parents[2]
PACKS = REPO / "packs" / "soulpacks"


@pytest.fixture(autouse=True)
def _root(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("SOULPACKS_ROOT", str(PACKS))


def test_cli_pack_list(capsys: pytest.CaptureFixture[str]):
    main(["pack", "list"])
    out = capsys.readouterr().out
    assert "support-agent" in out
    assert "companion" in out


def test_cli_pack_import_persist_false(capsys: pytest.CaptureFixture[str]):
    main(["pack", "import", "companion", "--persist", "false"])
    out = capsys.readouterr().out
    data = json.loads(out)
    assert data["external_key"].startswith("soulos:companion@")
    assert "soul" in data


def test_cli_pack_export(tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    out_dir = tmp_path / "exported-pack"
    main(["pack", "export", "dev-twin", "-o", str(out_dir)])
    assert (out_dir / "pack.json").is_file()
    manifest = json.loads((out_dir / "pack.json").read_text(encoding="utf-8"))
    assert manifest["license"] == "MIT"
    assert "Exported" in capsys.readouterr().out
