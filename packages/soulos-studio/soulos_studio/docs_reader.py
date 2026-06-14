"""Read and render SoulOS documentation for the Studio UI."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import markdown

PACKAGE_DIR = Path(__file__).resolve().parent
TUTORIALS_DIR = PACKAGE_DIR / "content" / "tutorials"

SECTION_LABELS = {
    "getting-started": "Getting started",
    "guides": "Guides",
    "reference": "Reference",
    "deployment": "Deployment",
}


def find_docs_root() -> Path | None:
    env = os.getenv("SOULOS_DOCS_ROOT")
    if env:
        candidate = Path(env).expanduser()
        if candidate.is_dir():
            return candidate.resolve()

    monorepo = PACKAGE_DIR.parents[2] / "docs"
    if monorepo.is_dir():
        return monorepo.resolve()

    bundled = PACKAGE_DIR / "bundled_docs"
    if bundled.is_dir():
        return bundled.resolve()

    if Path("/docs").is_dir():
        return Path("/docs").resolve()

    return None


def _safe_path(root: Path, rel: str) -> Path:
    clean = Path(rel)
    if clean.is_absolute() or ".." in clean.parts:
        raise ValueError("Invalid document path")
    full = (root / clean).resolve()
    root_resolved = root.resolve()
    if not str(full).startswith(str(root_resolved)):
        raise ValueError("Invalid document path")
    if not full.is_file():
        raise FileNotFoundError(rel)
    if full.suffix.lower() != ".md":
        raise ValueError("Only markdown documents are supported")
    return full


def _safe_tutorial_path(rel: str) -> Path:
    clean = Path(rel)
    if clean.is_absolute() or ".." in clean.parts:
        raise ValueError("Invalid tutorial path")
    full = (TUTORIALS_DIR / clean).resolve()
    root_resolved = TUTORIALS_DIR.resolve()
    if not str(full).startswith(str(root_resolved)):
        raise ValueError("Invalid tutorial path")
    if not full.is_file():
        raise FileNotFoundError(rel)
    return full


def _title_from_markdown(text: str, fallback: str) -> str:
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("# "):
            return stripped[2:].strip()
    return fallback


def _description_from_markdown(text: str) -> str:
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        return stripped[:160]
    return ""


def render_markdown(text: str) -> str:
    return markdown.markdown(
        text,
        extensions=["fenced_code", "tables", "nl2br", "sane_lists"],
        output_format="html5",
    )


def read_markdown_file(path: Path, rel_path: str | None = None) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    rel = rel_path or path.name
    return {
        "path": rel.replace("\\", "/"),
        "title": _title_from_markdown(text, path.stem.replace("-", " ").title()),
        "description": _description_from_markdown(text),
        "markdown": text,
        "html": render_markdown(text),
    }


def build_docs_catalog() -> dict[str, Any]:
    root = find_docs_root()
    if root is None:
        return {"sections": [], "docs_root": None}

    sections: dict[str, list[dict[str, str]]] = {}
    for path in sorted(root.rglob("*.md")):
        if path.name == "README.md" and path.parent == root:
            continue
        rel = path.relative_to(root).as_posix()
        text = path.read_text(encoding="utf-8")
        section_key = rel.split("/")[0] if "/" in rel else "root"
        if section_key == "README.md":
            continue
        if section_key not in sections:
            sections[section_key] = []
        sections[section_key].append(
            {
                "path": rel,
                "title": _title_from_markdown(text, path.stem.replace("-", " ").title()),
                "description": _description_from_markdown(text),
            }
        )

    ordered = []
    for key in ["getting-started", "guides", "reference", "deployment"]:
        if key in sections:
            ordered.append(
                {
                    "id": key,
                    "title": SECTION_LABELS.get(key, key),
                    "items": sections[key],
                }
            )
    for key in sorted(sections.keys()):
        if key not in {s["id"] for s in ordered}:
            ordered.append({"id": key, "title": key.replace("-", " ").title(), "items": sections[key]})

    if (root / "README.md").is_file():
        text = (root / "README.md").read_text(encoding="utf-8")
        ordered.insert(
            0,
            {
                "id": "index",
                "title": "Overview",
                "items": [
                    {
                        "path": "README.md",
                        "title": _title_from_markdown(text, "Documentation index"),
                        "description": _description_from_markdown(text),
                    }
                ],
            },
        )

    return {"sections": ordered, "docs_root": str(root)}


def get_doc_content(rel_path: str) -> dict[str, Any]:
    root = find_docs_root()
    if root is None:
        raise FileNotFoundError("Documentation root not found")
    path = _safe_path(root, rel_path)
    return read_markdown_file(path)


def get_tutorials_catalog() -> list[dict[str, Any]]:
    from soulos_studio.tutorials import TUTORIALS

    return [dict(t) for t in TUTORIALS]


def get_tutorial_content(tutorial_id: str) -> dict[str, Any]:
    from soulos_studio.tutorials import TUTORIALS_BY_ID

    meta = TUTORIALS_BY_ID.get(tutorial_id)
    if meta is None:
        raise FileNotFoundError(tutorial_id)

    if meta.get("interactive"):
        if tutorial_id == "python-bot":
            from soulos_studio.interactive_tutorials.python_bot import get_python_bot_tutorial

            doc = get_python_bot_tutorial()
        elif tutorial_id == "quickstart":
            from soulos_studio.interactive_tutorials.quickstart import get_quickstart_tutorial

            doc = get_quickstart_tutorial()
        elif tutorial_id == "soul-builder":
            from soulos_studio.interactive_tutorials.soul_builder import get_soul_builder_tutorial

            doc = get_soul_builder_tutorial()
        else:
            raise FileNotFoundError(tutorial_id)
        doc["category"] = meta.get("category", "")
        doc["duration"] = meta.get("duration", "")
        return doc

    source = meta["source"]
    if source["type"] == "docs":
        doc = get_doc_content(source["path"])
        doc["tutorial_id"] = tutorial_id
        doc["category"] = meta.get("category", "")
        doc["duration"] = meta.get("duration", "")
        return doc

    path = _safe_tutorial_path(source["path"])
    doc = read_markdown_file(path, f"tutorials/{source['path']}")
    doc["tutorial_id"] = tutorial_id
    doc["category"] = meta.get("category", "")
    doc["duration"] = meta.get("duration", "")
    return doc
