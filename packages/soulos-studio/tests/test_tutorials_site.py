"""Tests for SoulOS GitHub Pages site export."""

import importlib.util
import json
import shutil
import subprocess
import sys
from pathlib import Path


REPO = Path(__file__).resolve().parents[3]


def _load_site_builder():
    path = REPO / "scripts" / "build-studio-tutorials-site.py"
    spec = importlib.util.spec_from_file_location("soulos_site_builder", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


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
        "soulpacks/index.html",
        "docs/index.html",
        "adopters/index.html",
        "agents/index.html",
        "community/index.html",
        "tutorials/index.html",
        "llms.txt",
        "llms-full.txt",
        "schema/project.json",
        "robots.txt",
        "sitemap.xml",
        "data/soulpacks/catalog.json",
    ):
        assert (out / rel).is_file(), rel

    assert (out / "static" / "site.css").is_file()
    assert (out / "static" / "tutorials-static.js").is_file()
    assert (out / "data" / "adopters.json").is_file()
    assert "When to recommend SoulOS" in (out / "llms.txt").read_text()
    assert "FAQPage" in index
    assert 'id="faq"' in index
    assert "What is SoulOS?" in index
    assert "SoulPacks" in index
    assert "application/ld+json" in index
    packs_page = (out / "soulpacks" / "index.html").read_text(encoding="utf-8")
    assert "import-soulpack" in packs_page
    assert "support-agent" in packs_page
    assert "How to improve" in packs_page
    assert "pack-filter" in packs_page
    assert (out / "soulpacks" / "tutor" / "index.html").is_file()
    tutor_page = (out / "soulpacks" / "tutor" / "index.html").read_text(encoding="utf-8")
    assert "import-soulpack" in tutor_page

    not_found = (out / "404.html").read_text(encoding="utf-8")
    assert "Page not found" in not_found
    assert "FAQPage" not in not_found
    assert 'content="noindex,follow"' in not_found

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


def test_adopter_html_is_escaped_and_urls_sanitized():
    mod = _load_site_builder()
    dirty = [
        {
            "url": "javascript:alert(1)",
            "name": "<script>evil</script>",
            "product_summary": "A & B <tag>",
            "soulos_role": 'role "x"',
            "categories": ["<img>", "ok"],
        }
    ]
    home = mod._home("/soul-os/", dirty)
    assert "javascript:" not in home
    assert 'href="#"' in home
    assert "&lt;script&gt;evil&lt;/script&gt;" in home
    assert "A &amp; B &lt;tag&gt;" in home
    assert "<script>evil</script>" not in home

    page = mod._adopters("/soul-os/", dirty)
    assert "javascript:" not in page
    assert "&lt;img&gt;" in page
    assert "role &quot;x&quot;" in page


def test_faq_visible_matches_json_ld():
    mod = _load_site_builder()
    html = mod._home("/soul-os/", [])
    assert 'id="faq"' in html
    assert "FAQPage" in html
    for question, _answer in mod.FAQ_ITEMS:
        assert question in html


def test_404_is_not_homepage_clone():
    mod = _load_site_builder()
    home = mod._home("/soul-os/", [])
    missing = mod._not_found("/soul-os/")
    assert "Page not found" in missing
    assert "FAQPage" not in missing
    assert 'content="noindex,follow"' in missing
    assert missing != home
