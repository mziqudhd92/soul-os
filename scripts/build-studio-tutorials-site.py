#!/usr/bin/env python3
"""Export SoulOS tutorials as a static site for GitHub Pages."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _ensure_base(base: str) -> str:
    if not base:
        return "/"
    if not base.startswith("/"):
        base = f"/{base}"
    if not base.endswith("/"):
        base = f"{base}/"
    return base


def build(out: Path, base: str) -> None:
    root = _repo_root()
    import os

    os.environ["SOULOS_DOCS_ROOT"] = str(root / "docs")

    from soulos_studio.tutorials import TUTORIALS
    from soulos_studio.docs_reader import get_tutorial_content, get_tutorials_catalog

    base = _ensure_base(base)
    static_src = root / "packages/soulos-studio/soulos_studio/static"
    static_out = out / "static"
    data_tutorials = out / "data" / "tutorials"

    if out.exists():
        shutil.rmtree(out)
    static_out.mkdir(parents=True)
    data_tutorials.mkdir(parents=True)

    for name in (
        "studio.css",
        "tutorial-python-bot.js",
        "tutorials-static.js",
    ):
        shutil.copy2(static_src / name, static_out / name)

    catalog_path = out / "data" / "tutorials.json"
    catalog_path.write_text(
        json.dumps({"tutorials": get_tutorials_catalog()}, indent=2),
        encoding="utf-8",
    )

    for tutorial in TUTORIALS:
        tid = tutorial["id"]
        doc = get_tutorial_content(tid)
        (data_tutorials / f"{tid}.json").write_text(
            json.dumps(doc, indent=2),
            encoding="utf-8",
        )

    template = (static_src / "tutorials-index.html").read_text(encoding="utf-8")
    html = template.replace("{{BASE}}", base)
    out_index = out / "index.html"
    out_index.write_text(html, encoding="utf-8")
    shutil.copy2(out_index, out / "404.html")
    (out / ".nojekyll").touch()

    print(f"Built static tutorials site → {out.resolve()}")
    print(f"  base URL path: {base}")
    print(f"  tutorials: {len(TUTORIALS)}")
    print(f"  example: data/tutorials/python-bot.json")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build SoulOS tutorials static site")
    parser.add_argument(
        "--out",
        type=Path,
        default=_repo_root() / "site",
        help="Output directory (default: site/)",
    )
    parser.add_argument(
        "--base",
        default="/soul-os/",
        help="GitHub Pages base path (default: /soul-os/)",
    )
    args = parser.parse_args(argv)

    try:
        build(args.out, args.base)
    except Exception as exc:
        print(f"build failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
