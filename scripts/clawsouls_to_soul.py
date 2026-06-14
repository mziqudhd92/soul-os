#!/usr/bin/env python3
"""Convert a ClawSouls persona package to SoulOS .soul.json or register with the kernel."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CORE = ROOT / "packages" / "soulos-core"
sys.path.insert(0, str(CORE))

import httpx  # noqa: E402

from runtime.clawsouls_import import (  # noqa: E402
    default_external_key,
    import_clawsouls_soul,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Import ClawSouls persona into SoulOS soul format"
    )
    parser.add_argument(
        "ref",
        nargs="?",
        help="owner/name (e.g. clawsouls/surgical-coder)",
    )
    parser.add_argument("--owner", help="ClawSouls owner namespace")
    parser.add_argument("--name", help="Soul name")
    parser.add_argument(
        "--dir",
        type=Path,
        help="Local ClawSouls package directory (soul.json + markdown)",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        help="Write .soul.json to this path",
    )
    parser.add_argument("--msv-preset", help="Override MSV preset name")
    parser.add_argument(
        "--register",
        action="store_true",
        help="POST to kernel /v1/avatars/import-clawsouls",
    )
    parser.add_argument(
        "--kernel-url",
        default=os.getenv("SOULOS_KERNEL_URL", "http://localhost:8000"),
        help="Kernel base URL for --register",
    )
    parser.add_argument(
        "--external-key",
        help="external_key for kernel registration",
    )
    return parser.parse_args()


def resolve_owner_name(args: argparse.Namespace) -> tuple[str, str]:
    if args.owner and args.name:
        return args.owner, args.name
    if args.ref:
        if "/" not in args.ref:
            raise SystemExit("ref must be owner/name")
        owner, name = args.ref.split("/", 1)
        return owner, name
    if args.dir:
        return "local", args.dir.name
    raise SystemExit("Provide owner/name ref, --owner + --name, or --dir")


async def main() -> int:
    args = parse_args()
    owner, name = resolve_owner_name(args)

    soul, runtime_config, warnings = await import_clawsouls_soul(
        owner,
        name,
        msv_preset=args.msv_preset,
        local_dir=args.dir,
    )

    external_key = args.external_key or default_external_key(
        owner,
        name,
        runtime_config.get("source", {}).get("version"),
    )

    if warnings:
        print("Warnings:", file=sys.stderr)
        for line in warnings:
            print(f"  • {line}", file=sys.stderr)

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(soul, indent=2) + "\n", encoding="utf-8")
        print(f"Wrote {args.output}")

    if args.register:
        if args.dir:
            ensure_url = f"{args.kernel_url.rstrip('/')}/v1/avatars/ensure"
            async with httpx.AsyncClient(timeout=60.0) as client:
                res = await client.post(
                    ensure_url,
                    json={
                        "external_key": external_key,
                        "soul": soul,
                        "runtime_config": runtime_config,
                    },
                )
            if res.status_code != 200:
                print(res.text, file=sys.stderr)
                return 1
            print(json.dumps(res.json(), indent=2))
            return 0

        url = f"{args.kernel_url.rstrip('/')}/v1/avatars/import-clawsouls"
        payload = {
            "owner": owner,
            "name": name,
            "persist": True,
            "external_key": external_key,
            "msv_preset": args.msv_preset,
            "runtime_config": runtime_config,
        }
        async with httpx.AsyncClient(timeout=60.0) as client:
            res = await client.post(url, json=payload)
        if res.status_code != 200:
            print(res.text, file=sys.stderr)
            return 1
        print(json.dumps(res.json(), indent=2))
        return 0

    if not args.output:
        print(json.dumps({"soul": soul, "runtime_config": runtime_config}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
