"""Shared site build helpers."""

from __future__ import annotations

import json
from html import escape
from pathlib import Path
from urllib.parse import urlparse

from _shell import absolute_url, page

ROOT = Path(__file__).resolve().parents[2]

def ensure_base(base: str) -> str:
    if not base:
        return "/"
    if not base.startswith("/"):
        base = f"/{base}"
    if not base.endswith("/"):
        base = f"{base}/"
    return base


def write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def safe_http_url(url: str) -> str:
    """Allow only http(s) adopter URLs; reject javascript: and other schemes."""
    try:
        parsed = urlparse((url or "").strip())
    except ValueError:
        return "#"
    if parsed.scheme in ("http", "https") and parsed.netloc:
        return parsed.geturl()
    return "#"

def load_soulpack_catalog() -> list[dict]:
    path = ROOT / "packs" / "soulpacks" / "catalog.json"
    if not path.is_file():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    packs = data.get("packs") if isinstance(data, dict) else data
    return [p for p in (packs or []) if isinstance(p, dict)]


def load_pack_file(pack_id: str, filename: str) -> str:
    path = ROOT / "packs" / "soulpacks" / pack_id / filename
    if not path.is_file():
        return ""
    return path.read_text(encoding="utf-8").strip()


def load_pack_manifest(pack_id: str) -> dict:
    path = ROOT / "packs" / "soulpacks" / pack_id / "pack.json"
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except json.JSONDecodeError:
        return {}


def load_hero_svg() -> str:
    """Inline hero diagram (avoids broken external img on GitHub Pages)."""
    path = ROOT / "site-src" / "static" / "hero-sidecar.svg"
    if not path.is_file():
        return ""
    return path.read_text(encoding="utf-8").strip()
