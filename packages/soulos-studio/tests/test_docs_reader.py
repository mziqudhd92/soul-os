"""Tests for documentation and tutorial serving."""

from soulos_studio.docs_reader import (
    build_docs_catalog,
    find_docs_root,
    get_doc_content,
    get_tutorial_content,
    get_tutorials_catalog,
)


def test_docs_root_found():
    root = find_docs_root()
    assert root is not None
    assert (root / "getting-started").is_dir()


def test_docs_catalog_has_sections():
    catalog = build_docs_catalog()
    assert catalog["sections"]
    ids = {s["id"] for s in catalog["sections"]}
    assert "getting-started" in ids or "guides" in ids


def test_load_quickstart_doc():
    doc = get_doc_content("getting-started/quickstart.md")
    assert "Quickstart" in doc["title"]
    assert "<" in doc["html"]


def test_tutorials_catalog():
    tutorials = get_tutorials_catalog()
    assert len(tutorials) >= 5
    assert any(t["id"] == "first-soul" for t in tutorials)


def test_load_bundled_tutorial():
    doc = get_tutorial_content("first-soul")
    assert "Wizard" in doc["title"] or "soul" in doc["title"].lower()
    assert doc["html"]


def test_load_interactive_python_bot_tutorial():
    doc = get_tutorial_content("python-bot")
    assert doc["format"] == "interactive"
    assert len(doc["steps"]) >= 5
    assert doc["steps"][0]["id"] == "intro"


def test_load_interactive_quickstart_tutorial():
    doc = get_tutorial_content("quickstart")
    assert doc["format"] == "interactive_terminal"
    assert len(doc["steps"]) >= 5
    assert doc["steps"][0]["script"]
