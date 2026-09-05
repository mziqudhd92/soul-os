#!/usr/bin/env python3
"""Sync product version from repo-root VERSION into all mirrors."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from soulos_version import read_version, sync_version  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Fail if mirrors would change (dry-run)",
    )
    args = parser.parse_args(argv)
    version = read_version(ROOT)
    changed = sync_version(ROOT, write=not args.check)
    if args.check:
        if changed:
            print("Version mirrors out of sync with VERSION:", file=sys.stderr)
            for path in changed:
                print(f"  - {path}", file=sys.stderr)
            print("Run: npm run version:sync", file=sys.stderr)
            return 1
        print(f"Version sync check: OK ({version})")
        return 0
    if changed:
        print(f"Synced VERSION={version} →")
        for path in changed:
            print(f"  {path}")
    else:
        print(f"Already in sync (VERSION={version})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
