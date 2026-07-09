#!/usr/bin/env python3
"""Minimal persona regression eval — assert simple slider deltas change system_prompt."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "packages" / "soulos-core"))

from runtime.hybrid import build_hybrid_system_prompt
from runtime.persona_simple import build_simple_baseline_msv, simple_sliders_to_hexaco


def build_identity(warmth: float, rigor: float, caution: float) -> dict:
    msv = build_simple_baseline_msv(warmth, rigor, caution)
    return {
        "name": "Eval Bot",
        "role": "Tester",
        "description": "Eval fixture.",
        "current_msv": msv,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="SoulOS persona eval stub")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    errors: list[str] = []

    warm = build_hybrid_system_prompt(build_identity(0.9, 0.5, 0.5), [], {})
    cold = build_hybrid_system_prompt(build_identity(0.2, 0.5, 0.5), [], {})
    if warm == cold:
        errors.append("warmth delta did not change system_prompt")

    strict = build_hybrid_system_prompt(build_identity(0.5, 0.95, 0.5), [], {})
    loose = build_hybrid_system_prompt(build_identity(0.5, 0.1, 0.5), [], {})
    if strict == loose:
        errors.append("rigor delta did not change system_prompt")

    h1 = simple_sliders_to_hexaco(0.2, 0.5, 0.9)
    h2 = simple_sliders_to_hexaco(0.8, 0.5, 0.2)
    if h1["H"] <= h2["H"]:
        errors.append("caution should increase H in simple mapping")

    if args.verbose:
        print(json.dumps({"warm_len": len(warm), "cold_len": len(cold)}, indent=2))

    if errors:
        for e in errors:
            print(f"FAIL: {e}", file=sys.stderr)
        return 1
    print("soulos-eval: OK (persona/simple mapping)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
