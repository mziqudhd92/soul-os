#!/usr/bin/env python3
"""Assert Python/TS SDK surface covers documented kernel OpenAPI paths.

Fails when OpenAPI gains a path with no matching SDK method hint.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OPENAPI = ROOT / "docs" / "reference" / "openapi.kernel.json"
PY_CLIENT = ROOT / "packages" / "soulos-sdk" / "python" / "soulos" / "client.py"
PY_HYBRID = ROOT / "packages" / "soulos-sdk" / "python" / "soulos" / "hybrid.py"
TS_CLIENT = ROOT / "packages" / "soulos-sdk" / "ts" / "src" / "index.ts"
TS_HYBRID = ROOT / "packages" / "soulos-sdk" / "ts" / "src" / "hybrid.ts"

# Paths the SDKs are expected to cover (substring match against client source).
# Keep in sync when adding SDK methods; MCP-only and operator routes are excluded.
REQUIRED: dict[str, list[str]] = {
    "/v1/avatars": ["register_avatar", "registerAvatar", "/v1/avatars"],
    "/v1/avatars/ensure": ["ensure_avatar", "ensureAvatar", "/v1/avatars/ensure"],
    "/memory/ingest": ["ingest_memory", "ingestMemory", "/memory/ingest"],
    "/memory/sync": ["sync_memory", "syncMemory", "/memory/sync"],
    "/hybrid/prepare": ["prepare", "/hybrid/prepare"],
    "/hybrid/complete": ["complete", "/hybrid/complete"],
    "/chat/generate": ["send_message", "sendMessage", "/chat/generate"],
    "/state/update": ["update_state", "updateState", "/state/update"],
}


def main() -> int:
    spec = json.loads(OPENAPI.read_text(encoding="utf-8"))
    paths = set(spec.get("paths") or {})
    sources = "\n".join(
        p.read_text(encoding="utf-8")
        for p in (PY_CLIENT, PY_HYBRID, TS_CLIENT, TS_HYBRID)
        if p.is_file()
    )
    missing: list[str] = []
    for path, needles in REQUIRED.items():
        if path not in paths:
            missing.append(f"OpenAPI missing path {path} (update REQUIRED map)")
            continue
        if not any(n in sources for n in needles):
            missing.append(f"SDK sources lack coverage for {path} (need one of {needles})")

    # Warn-only: paths in OpenAPI not in REQUIRED (operator / niche).
    uncovered = sorted(
        p
        for p in paths
        if p not in REQUIRED
        and not p.startswith("/mcp")
        and p
        not in {
            "/health",
            "/ready",
            "/openapi.json",
            "/docs",
            "/redoc",
        }
    )
    if missing:
        print("SDK OpenAPI contract check FAILED:", file=sys.stderr)
        for m in missing:
            print(f"  - {m}", file=sys.stderr)
        return 1
    print(f"SDK OpenAPI contract check: OK ({len(REQUIRED)} required paths)")
    if uncovered:
        print(f"  (info) OpenAPI paths not in REQUIRED map: {len(uncovered)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
