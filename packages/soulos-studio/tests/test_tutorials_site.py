"""Tests for static tutorials site export."""

import json
import subprocess
import sys
from pathlib import Path


REPO = Path(__file__).resolve().parents[3]


def test_build_tutorials_site():
    out = REPO / "site-test-output"
    if out.exists():
        import shutil

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
    assert "<base href=\"/soul-os/\"" in index
    assert (out / "static" / "tutorials-static.js").is_file()

    catalog = json.loads((out / "data" / "tutorials.json").read_text())
    assert len(catalog["tutorials"]) >= 5

    python_bot = json.loads((out / "data" / "tutorials" / "python-bot.json").read_text())
    assert python_bot["format"] == "interactive"
    assert len(python_bot["steps"]) >= 5

    quickstart = json.loads((out / "data" / "tutorials" / "quickstart.json").read_text())
    assert quickstart["html"]

    import shutil

    shutil.rmtree(out)
