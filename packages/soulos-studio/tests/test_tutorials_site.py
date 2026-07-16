"""Tests for SoulOS GitHub Pages site export."""

import json
import shutil
import subprocess
import sys
from pathlib import Path


REPO = Path(__file__).resolve().parents[3]


def test_build_project_site():
    out = REPO / "site-test-output"
    if out.exists():
        shutil.rmtree(out)

    subprocess.run(
        [
            sys.executable,
            str(REPO / "scripts" / "build-studio-tutorials-site.py"),
            "--out",
            str(out),
            "--base",
            "/soul-os/",
        ],
        check=True,
        cwd=REPO,
    )

    index = (out / "index.html").read_text(encoding="utf-8")
    assert '<base href="/soul-os/"' in index
    assert "SoulOS" in index
    assert "ensure" in index
    assert "Get started" in index

    for rel in (
        "get-started/index.html",
        "docs/index.html",
        "adopters/index.html",
        "community/index.html",
        "tutorials/index.html",
    ):
        assert (out / rel).is_file(), rel

    assert (out / "static" / "site.css").is_file()
    assert (out / "static" / "tutorials-static.js").is_file()
    assert (out / "data" / "adopters.json").is_file()

    catalog = json.loads((out / "data" / "tutorials.json").read_text())
    assert len(catalog["tutorials"]) >= 5

    python_bot = json.loads((out / "data" / "tutorials" / "python-bot.json").read_text())
    assert python_bot["format"] == "interactive"
    assert len(python_bot["steps"]) >= 5

    quickstart = json.loads((out / "data" / "tutorials" / "quickstart.json").read_text())
    assert quickstart["format"] == "interactive_terminal"
    assert len(quickstart["steps"]) >= 5

    soul_builder = json.loads(
        (out / "data" / "tutorials" / "soul-builder.json").read_text()
    )
    assert soul_builder["format"] == "interactive_studio"
    assert len(soul_builder["steps"]) >= 5

    adopters = json.loads((out / "data" / "adopters.json").read_text())
    assert len(adopters["adopters"]) >= 3

    shutil.rmtree(out)
