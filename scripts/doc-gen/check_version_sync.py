#!/usr/bin/env python3
"""CI check: all product version mirrors match repo-root VERSION."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from soulos_version import collect_mismatches, read_version  # noqa: E402


def main() -> int:
    version = read_version(ROOT)
    errors = collect_mismatches(ROOT)
    if errors:
        print(f"ERROR: version drift from VERSION={version}", file=sys.stderr)
        for err in errors:
            print(f"  {err}", file=sys.stderr)
        print("Fix: edit VERSION, then npm run version:sync && npm run openapi:export", file=sys.stderr)
        return 1
    print(f"Version sync check: OK ({version})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
