#!/usr/bin/env python3
"""CI check: committed OpenAPI must match live FastAPI schema."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
COMMITTED = ROOT / "docs" / "reference" / "openapi.kernel.json"

sys.path.insert(0, str(ROOT / "packages" / "soulos-core"))
from main import app  # noqa: E402


def main() -> int:
    if not COMMITTED.is_file():
        print(f"ERROR: missing {COMMITTED.relative_to(ROOT)}", file=sys.stderr)
        return 1
    live = app.openapi()
    committed = json.loads(COMMITTED.read_text(encoding="utf-8"))
    if live != committed:
        print(
            "ERROR: OpenAPI drift — run: npm run openapi:export",
            file=sys.stderr,
        )
        return 1
    print("OpenAPI drift check: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
