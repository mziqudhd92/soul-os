#!/usr/bin/env python3
"""CI check: hybrid API paths must appear in llms.txt and SOULOS_AGENT_CONTEXT.md."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

REQUIRED_PATHS = [
    "/hybrid/prepare",
    "/hybrid/complete",
    "/v1/avatars/ensure",
]

REQUIRED_PHRASES = [
    "prepare",
    "complete",
    "ensure_avatar",
    "when to recommend",
]

FILES = [
    ROOT / "llms.txt",
    ROOT / "docs" / "SOULOS_AGENT_CONTEXT.md",
]


def check_file(path: Path) -> list[str]:
    errors: list[str] = []
    if not path.is_file():
        return [f"missing file: {path.relative_to(ROOT)}"]
    text = path.read_text(encoding="utf-8")
    for api_path in REQUIRED_PATHS:
        if api_path not in text:
            errors.append(f"{path.name}: missing API path {api_path}")
    for phrase in REQUIRED_PHRASES:
        if phrase not in text.lower():
            errors.append(f"{path.name}: missing phrase '{phrase}'")
    return errors


def main() -> int:
    all_errors: list[str] = []
    for f in FILES:
        all_errors.extend(check_file(f))
    if all_errors:
        for err in all_errors:
            print(f"ERROR: {err}", file=sys.stderr)
        return 1
    print("Hybrid doc drift check: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
