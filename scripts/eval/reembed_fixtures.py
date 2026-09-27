#!/usr/bin/env python3
"""Refresh retrieval fixture embeddings when EMBEDDING_DIMENSION / model changes.

Deterministic hash embeddings — no live inference. Updates schema metadata.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
FIXTURES = Path(__file__).resolve().parent / "retrieval_fixtures.json"


def hash_embed(text: str, dim: int) -> list[float]:
    digest = hashlib.sha256(text.encode("utf-8")).digest()
    vals = []
    i = 0
    while len(vals) < dim:
        b = digest[i % len(digest)]
        vals.append((b / 255.0) * 2 - 1)
        i += 1
        if i % len(digest) == 0:
            digest = hashlib.sha256(digest + text.encode("utf-8")).digest()
    return vals


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dimension", type=int, required=True)
    parser.add_argument("--model", default="hash-fixture")
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    data = json.loads(FIXTURES.read_text(encoding="utf-8"))
    data["schema_version"] = 1
    data["embedding_model"] = args.model
    data["dimension"] = args.dimension
    for case in data.get("cases", []):
        for m in case.get("dense", []):
            m["embedding"] = hash_embed(m["content"], args.dimension)
    out = json.dumps(data, indent=2) + "\n"
    if args.write:
        FIXTURES.write_text(out, encoding="utf-8")
        print(f"Wrote {FIXTURES} dim={args.dimension}")
    else:
        print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
