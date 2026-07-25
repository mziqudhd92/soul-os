#!/usr/bin/env python3
"""Seed a SoulPack into a running SoulOS kernel."""

from __future__ import annotations

import argparse
import json
import sys

import httpx


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pack-id", default="support-agent")
    parser.add_argument("--kernel", default="http://localhost:8000")
    parser.add_argument(
        "--persist",
        default="true",
        choices=("true", "false"),
        help="Write avatar via ensure (true) or convert-only (false)",
    )
    args = parser.parse_args(argv)
    persist = args.persist == "true"
    url = f"{args.kernel.rstrip('/')}/v1/avatars/import-soulpack"
    payload = {"pack_id": args.pack_id, "persist": persist}
    try:
        with httpx.Client(timeout=60.0) as client:
            res = client.post(url, json=payload)
    except httpx.RequestError as e:
        print(f"kernel unreachable: {e}", file=sys.stderr)
        return 1
    body = res.json()
    print(json.dumps(body, indent=2))
    return 0 if res.status_code == 200 else 1


if __name__ == "__main__":
    raise SystemExit(main())
