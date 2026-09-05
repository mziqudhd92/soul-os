"""Resolve SoulOS product version for the kernel (OpenAPI + /health)."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path


@lru_cache(maxsize=1)
def get_product_version() -> str:
    """Read repo-root VERSION; fall back to installed package metadata."""
    here = Path(__file__).resolve().parent  # packages/soulos-core
    for candidate in (
        here.parent.parent / "VERSION",  # monorepo root
        here.parent / "VERSION",
        Path.cwd() / "VERSION",
    ):
        if candidate.is_file():
            line = candidate.read_text(encoding="utf-8").strip().splitlines()[0].strip()
            if line.startswith("v"):
                line = line[1:]
            if line:
                return line
    try:
        from importlib.metadata import version

        return version("soulos-core")
    except Exception:
        return "0.0.0"
