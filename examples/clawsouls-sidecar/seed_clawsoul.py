#!/usr/bin/env python3
"""Seed a ClawSouls persona into a running SoulOS kernel."""

from __future__ import annotations

import argparse
import json
import sys

import httpx


def main() -> int:
    parser = argparse.ArgumentParser(description="Import ClawSouls soul into kernel")
    parser.add_argument(
        "--kernel-url",
        default="http://localhost:8001",
        help="SoulOS kernel URL",
    )
    parser.add_argument(
        "--soul",
        default="clawsouls/surgical-coder",
        help="owner/name ref",
    )
    parser.add_argument("--msv-preset", help="Optional MSV preset override")
    args = parser.parse_args()

    if "/" not in args.soul:
        print("--soul must be owner/name", file=sys.stderr)
        return 1
    owner, name = args.soul.split("/", 1)
    url = f"{args.kernel_url.rstrip('/')}/v1/avatars/import-clawsouls"
    payload: dict = {"owner": owner, "name": name, "persist": True}
    if args.msv_preset:
        payload["msv_preset"] = args.msv_preset

    res = httpx.post(url, json=payload, timeout=60.0)
    if res.status_code != 200:
        print(res.text, file=sys.stderr)
        return 1
    print(json.dumps(res.json(), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
