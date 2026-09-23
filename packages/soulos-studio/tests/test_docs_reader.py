"""Tests for documentation and tutorial serving."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from soulos_studio.docs_reader import (
    _description_from_markdown,
    _safe_path,
    _safe_tutorial_path,
    _title_from_markdown,
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


def test_docs_root_from_env(monkeypatch, tmp_path):
    docs = tmp_path / "docs"
    docs.mkdir()
    monkeypatch.setenv("SOULOS_DOCS_ROOT", str(docs))
    assert find_docs_root() == docs.resolve()


def test_docs_root_bundled(monkeypatch, tmp_path):
    monkeypatch.delenv("SOULOS_DOCS_ROOT", raising=False)
    fake_pkg = tmp_path / "pkg"
    (fake_pkg / "bundled_docs").mkdir(parents=True)
    with patch("soulos_studio.docs_reader.PACKAGE_DIR", fake_pkg):
        assert find_docs_root() == (fake_pkg / "bundled_docs").resolve()


def test_docs_root_none(monkeypatch, tmp_path):
    monkeypatch.delenv("SOULOS_DOCS_ROOT", raising=False)
    isolated = tmp_path / "a" / "b" / "c"
    isolated.mkdir(parents=True)

    real_path = Path

    def path_factory(arg=".", *args, **kwargs):
        if str(arg) == "/docs":
            m = MagicMock()
            m.is_dir.return_value = False
            return m
        return real_path(arg, *args, **kwargs)

    with (
        patch("soulos_studio.docs_reader.PACKAGE_DIR", isolated),
        patch("soulos_studio.docs_reader.Path", side_effect=path_factory),
    ):
        assert find_docs_root() is None


def test_docs_catalog_has_sections():
    catalog = build_docs_catalog()
    assert catalog["sections"]
    ids = {s["id"] for s in catalog["sections"]}
    assert "getting-started" in ids or "guides" in ids


def test_docs_catalog_empty_when_no_root():
    with patch("soulos_studio.docs_reader.find_docs_root", return_value=None):
        assert build_docs_catalog() == {"sections": [], "docs_root": None}


def test_docs_catalog_custom_tree(tmp_path):
    (tmp_path / "README.md").write_text("# Docs\n\nOverview body.\n", encoding="utf-8")
    guides = tmp_path / "guides"
    guides.mkdir()
    (guides / "one.md").write_text("# One\n\nDesc.\n", encoding="utf-8")
    extra = tmp_path / "custom-section"
    extra.mkdir()
    (extra / "x.md").write_text("No title line\n\nBody only.\n", encoding="utf-8")
    with patch("soulos_studio.docs_reader.find_docs_root", return_value=tmp_path):
        catalog = build_docs_catalog()
    ids = [s["id"] for s in catalog["sections"]]
    assert ids[0] == "index"
    assert "guides" in ids
    assert "custom-section" in ids


def test_safe_path_rejects_bad_paths(tmp_path):
    (tmp_path / "ok.md").write_text("# Ok\n", encoding="utf-8")
    (tmp_path / "note.txt").write_text("x", encoding="utf-8")
    with pytest.raises(ValueError, match="Invalid"):
        _safe_path(tmp_path, "../ok.md")
    with pytest.raises(ValueError, match="Invalid"):
        _safe_path(tmp_path, "/abs.md")
    with pytest.raises(FileNotFoundError):
        _safe_path(tmp_path, "missing.md")
    with pytest.raises(ValueError, match="markdown"):
        _safe_path(tmp_path, "note.txt")


def test_safe_tutorial_path_errors(tmp_path):
    with patch("soulos_studio.docs_reader.TUTORIALS_DIR", tmp_path):
        with pytest.raises(ValueError):
            _safe_tutorial_path("../x.md")
        with pytest.raises(ValueError):
            _safe_tutorial_path("/abs.md")
        with pytest.raises(FileNotFoundError):
            _safe_tutorial_path("nope.md")


def test_title_and_description_fallbacks():
    assert _title_from_markdown("no heading\n", "Fallback") == "Fallback"
    assert _description_from_markdown("# Only\n") == ""
    assert _description_from_markdown("# T\n\nFirst para\n") == "First para"


def test_load_quickstart_doc():
    doc = get_doc_content("getting-started/quickstart.md")
    assert "Quickstart" in doc["title"]
    assert "<" in doc["html"]


def test_get_doc_content_no_root():
    with patch("soulos_studio.docs_reader.find_docs_root", return_value=None):
        with pytest.raises(FileNotFoundError, match="Documentation root"):
            get_doc_content("x.md")


def test_tutorials_catalog():
    tutorials = get_tutorials_catalog()
    assert len(tutorials) >= 5
    assert any(t["id"] == "first-soul" for t in tutorials)


def test_load_bundled_tutorial():
    doc = get_tutorial_content("first-soul")
    assert "Wizard" in doc["title"] or "soul" in doc["title"].lower()
    assert doc["html"]


def test_load_docs_backed_tutorial():
    doc = get_tutorial_content("psychometrics")
    assert doc["tutorial_id"] == "psychometrics"
    assert doc["html"]
    assert doc["category"]


def test_unknown_tutorial_raises():
    with pytest.raises(FileNotFoundError):
        get_tutorial_content("no-such-tutorial")


def test_interactive_unknown_id_meta():
    fake = {
        "id": "fake-interactive",
        "interactive": True,
        "source": {"type": "interactive", "path": "x"},
    }
    with patch.dict(
        "soulos_studio.tutorials.TUTORIALS_BY_ID",
        {"fake-interactive": fake},
        clear=False,
    ):
        # get_tutorial_content imports TUTORIALS_BY_ID inside the function
        with patch(
            "soulos_studio.tutorials.TUTORIALS_BY_ID",
            {"fake-interactive": fake},
        ):
            with pytest.raises(FileNotFoundError):
                get_tutorial_content("fake-interactive")


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


def test_load_interactive_soul_builder_tutorial():
    doc = get_tutorial_content("soul-builder")
    assert doc["format"] == "interactive_studio"
    assert len(doc["steps"]) >= 5
    assert doc["steps"][0]["kind"] == "paths"
