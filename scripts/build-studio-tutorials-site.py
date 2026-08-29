#!/usr/bin/env python3
"""Build the SoulOS GitHub Pages site (landing + docs index + tutorials)."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SITE_SRC = ROOT / "site-src"
TEMPLATES = SITE_SRC / "templates"
PAGES = SITE_SRC / "pages"
sys.path.insert(0, str(TEMPLATES))
sys.path.insert(0, str(PAGES.parent))

from pages import (  # noqa: E402
    ensure_base,
    load_soulpack_catalog,
    render_adopters,
    render_agents,
    render_community,
    render_docs,
    render_get_started,
    render_home,
    render_not_found,
    render_soulpack_detail,
    render_soulpacks,
    render_tutorials_page,
    write,
)
from _shell import absolute_url  # noqa: E402

# Back-compat for tests that import private helpers from this module.
from pages.faq import faq_items as _faq_items  # noqa: E402
from pages.home import render_home as _home  # noqa: E402
from pages.adopters import render_adopters as _adopters  # noqa: E402
from pages.not_found import render_not_found as _not_found  # noqa: E402


def build(out: Path, base: str) -> None:
    os.environ["SOULOS_DOCS_ROOT"] = str(ROOT / "docs")

    from soulos_studio.tutorials import TUTORIALS
    from soulos_studio.docs_reader import get_tutorial_content, get_tutorials_catalog

    base = ensure_base(base)
    static_studio = ROOT / "packages/soulos-studio/soulos_studio/static"
    static_out = out / "static"
    data_tutorials = out / "data" / "tutorials"

    if out.exists():
        shutil.rmtree(out)
    static_out.mkdir(parents=True)
    data_tutorials.mkdir(parents=True)

    shutil.copy2(SITE_SRC / "static" / "site.css", static_out / "site.css")
    hero_svg = SITE_SRC / "static" / "hero-sidecar.svg"
    if hero_svg.is_file():
        shutil.copy2(hero_svg, static_out / "hero-sidecar.svg")
    for name in (
        "studio.css",
        "tutorial-python-bot.js",
        "tutorial-terminal.js",
        "tutorial-soul-builder.js",
        "tutorials-static.js",
    ):
        shutil.copy2(static_studio / name, static_out / name)

    adopters_path = ROOT / "docs" / "adopters.json"
    adopters_data = json.loads(adopters_path.read_text(encoding="utf-8"))
    adopters = adopters_data.get("adopters", [])
    shutil.copy2(adopters_path, out / "data" / "adopters.json")

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

    for name in ("llms.txt", "llms-full.txt"):
        shutil.copy2(ROOT / name, out / name)
    schema_out = out / "schema"
    schema_out.mkdir(parents=True, exist_ok=True)
    shutil.copy2(ROOT / "schema" / "project.json", schema_out / "project.json")

    write(out / "index.html", render_home(base, adopters))
    write(out / "get-started" / "index.html", render_get_started(base))
    write(out / "soulpacks" / "index.html", render_soulpacks(base))
    pack_entries = load_soulpack_catalog()
    for entry in pack_entries:
        pid = str(entry.get("id", "")).strip()
        if not pid or "/" in pid or ".." in pid:
            continue
        write(out / "soulpacks" / pid / "index.html", render_soulpack_detail(base, entry))
    write(out / "docs" / "index.html", render_docs(base))
    write(out / "adopters" / "index.html", render_adopters(base, adopters))
    write(out / "agents" / "index.html", render_agents(base))
    write(out / "community" / "index.html", render_community(base))
    write(out / "tutorials" / "index.html", render_tutorials_page(base))

    packs_data = out / "data" / "soulpacks"
    packs_data.mkdir(parents=True, exist_ok=True)
    catalog_src = ROOT / "packs" / "soulpacks" / "catalog.json"
    if catalog_src.is_file():
        shutil.copy2(catalog_src, packs_data / "catalog.json")

    site_paths = [
        "",
        "get-started/",
        "soulpacks/",
        "docs/",
        "tutorials/",
        "adopters/",
        "agents/",
        "community/",
        "llms.txt",
        "llms-full.txt",
        "schema/project.json",
        "data/soulpacks/catalog.json",
    ]
    for entry in pack_entries:
        pid = str(entry.get("id", "")).strip()
        if pid and "/" not in pid and ".." not in pid:
            site_paths.append(f"soulpacks/{pid}/")
    sitemap_urls = "\n".join(
        f"  <url><loc>{absolute_url(base, p)}</loc><changefreq>weekly</changefreq></url>"
        for p in site_paths
    )
    write(
        out / "sitemap.xml",
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f"{sitemap_urls}\n"
        "</urlset>\n",
    )
    write(
        out / "robots.txt",
        f"""# SoulOS — allow crawlers & AI agents; truth stays in the GitHub repo
User-agent: *
Allow: /

Sitemap: {absolute_url(base, "sitemap.xml")}

# Agent / GEO indexes (mirrored from repo root on each deploy)
# https://raw.githubusercontent.com/mziqudhd92/soul-os/main/llms.txt
# {absolute_url(base, "llms.txt")}
""",
    )

    write(out / "404.html", render_not_found(base))
    (out / ".nojekyll").touch()

    print(f"Built SoulOS site → {out.resolve()}")
    print(f"  base URL path: {base}")
    print(
        "  pages: home, get-started, soulpacks (+ detail), docs, tutorials, "
        "adopters, agents, community"
    )
    print("  agent mirrors: llms.txt, llms-full.txt, schema/project.json")
    print(f"  tutorials: {len(TUTORIALS)}")
    print(f"  soulpacks: {len(pack_entries)}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build SoulOS GitHub Pages site")
    parser.add_argument(
        "--out",
        type=Path,
        default=ROOT / "site",
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
