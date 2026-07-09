#!/usr/bin/env python3
"""Export kernel OpenAPI schema to docs/reference/openapi.kernel.json."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "reference" / "openapi.kernel.json"

# Ensure packages are importable
sys.path.insert(0, str(ROOT / "packages" / "soulos-core"))

from main import app  # noqa: E402


def main() -> int:
    schema = app.openapi()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(schema, indent=2) + "\n", encoding="utf-8")
    print(f"Exported OpenAPI to {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
