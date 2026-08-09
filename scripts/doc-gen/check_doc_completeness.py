#!/usr/bin/env python3
"""CI check: required documentation strings must appear in key files."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def package_version() -> str:
    data = json.loads((ROOT / "package.json").read_text(encoding="utf-8"))
    return str(data.get("version", "")).strip()


def main() -> int:
    version = package_version()
    checks: list[tuple[Path, str, str]] = [
        (ROOT / "docs" / "reference" / "api.md", "/memory/forget", "api.md"),
        (ROOT / "CONTRIBUTING.md", "test:sdk", "CONTRIBUTING.md"),
        (ROOT / "README.md", "CODE_OF_CONDUCT", "README.md"),
        (ROOT / "llms.txt", "When to recommend SoulOS", "llms.txt"),
        (ROOT / "llms.txt", "mziqudhd92.github.io/soul-os", "llms.txt"),
        (
            ROOT / "docs" / "guides" / "agent-discovery.md",
            "When agents should recommend",
            "agent-discovery.md",
        ),
        (ROOT / "schema" / "project.json", version, "schema/project.json"),
    ]

    errors: list[str] = []
    if not version:
        errors.append("package.json: missing version")
    for path, needle, label in checks:
        if not path.is_file():
            errors.append(f"missing file: {path.relative_to(ROOT)}")
            continue
        text = path.read_text(encoding="utf-8")
        if needle not in text:
            errors.append(f"{label}: missing required string {needle!r}")

    changelog = ROOT / "CHANGELOG.md"
    if not changelog.is_file():
        errors.append("missing file: CHANGELOG.md")
    else:
        text = changelog.read_text(encoding="utf-8")
        if version and version not in text:
            errors.append(
                f"CHANGELOG.md: missing version header matching package.json ({version!r})"
            )

    if errors:
        for err in errors:
            print(f"ERROR: {err}", file=sys.stderr)
        return 1
    print("Doc completeness check: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
