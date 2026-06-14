"""SoulOS kernel CLI — memory ledger helpers (Phase 3)."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

import httpx

from runtime.memory_ledger import append_episode_line, export_memory_json, memory_root


def _workspace(path: str | None) -> Path:
    return Path(path or os.getcwd()).resolve()


def cmd_memory_append(args: argparse.Namespace) -> None:
    workspace = _workspace(args.workspace)
    path = append_episode_line(
        workspace,
        args.summary,
        episode_type=args.type,
    )
    print(f"Appended episode line to {path}")


def cmd_memory_export(args: argparse.Namespace) -> None:
    workspace = _workspace(args.workspace)
    data = export_memory_json(workspace)
    if args.output:
        Path(args.output).write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        print(f"Exported memory to {args.output}")
    else:
        print(json.dumps(data, indent=2))


async def cmd_memory_sync(args: argparse.Namespace) -> None:
    workspace = _workspace(args.workspace)
    kernel = args.kernel.rstrip("/")
    payload = {"bot_id": args.bot_id, "workspace_path": str(workspace)}
    async with httpx.AsyncClient(timeout=120.0) as client:
        res = await client.post(f"{kernel}/memory/sync", json=payload)
        body = res.json()
        if res.status_code != 200:
            raise SystemExit(body.get("detail") or f"sync failed ({res.status_code})")
        print(json.dumps(body, indent=2))


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="soulos", description="SoulOS kernel utilities")
    sub = parser.add_subparsers(dest="command", required=True)

    append_p = sub.add_parser("memory-append", help="Append line to .soul-memory ledger")
    append_p.add_argument("summary", help="Episode summary text")
    append_p.add_argument("--workspace", help="Project root (default: cwd)")
    append_p.add_argument("--type", default="interaction", help="Episode type")
    append_p.set_defaults(func=cmd_memory_append)

    export_p = sub.add_parser("memory-export", help="Export .soul-memory as JSON")
    export_p.add_argument("--workspace", help="Project root (default: cwd)")
    export_p.add_argument("-o", "--output", help="Write JSON file instead of stdout")
    export_p.set_defaults(func=cmd_memory_export)

    sync_p = sub.add_parser("memory-sync", help="Sync .soul-memory to kernel pgvector")
    sync_p.add_argument("bot_id", help="Avatar / bot UUID")
    sync_p.add_argument("--workspace", help="Project root (default: cwd)")
    sync_p.add_argument("--kernel", default=os.getenv("SOULOS_KERNEL_URL", "http://localhost:8000"))
    sync_p.set_defaults(func=lambda a: asyncio.run(cmd_memory_sync(a)))

    args = parser.parse_args(argv)
    if args.command == "memory-sync":
        asyncio.run(cmd_memory_sync(args))
    else:
        args.func(args)


if __name__ == "__main__":
    main()
