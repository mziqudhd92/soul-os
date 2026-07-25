"""SoulOS kernel CLI — memory ledger + SoulPacks helpers."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

import httpx

from runtime.memory_ledger import append_episode_line, export_memory_json, memory_root
from runtime.soulpacks import compile_pack, export_pack, list_packs


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


def cmd_pack_list(args: argparse.Namespace) -> None:
    packs = list_packs(q=getattr(args, "q", None))
    for p in packs:
        tags = ",".join(p.get("tags") or [])
        print(f"{p.get('id')}\t{p.get('version')}\t{p.get('name')}\t{tags}")


def cmd_pack_import(args: argparse.Namespace) -> None:
    persist = args.persist == "true"
    if persist:
        kernel = args.kernel.rstrip("/")
        payload = {
            "pack_id": args.pack_id,
            "persist": True,
            "msv_preset": args.msv_preset,
        }
        with httpx.Client(timeout=60.0) as client:
            res = client.post(f"{kernel}/v1/avatars/import-soulpack", json=payload)
        body = res.json()
        print(json.dumps(body, indent=2))
        if res.status_code != 200:
            raise SystemExit(1)
        return

    soul, runtime_config, warnings = compile_pack(
        args.pack_id, msv_preset=args.msv_preset
    )
    version = runtime_config.get("source", {}).get("version") or "0.0.0"
    pack_id = runtime_config.get("source", {}).get("id") or args.pack_id
    from runtime.soulpacks import default_external_key

    print(
        json.dumps(
            {
                "soul": soul,
                "runtime_config": runtime_config,
                "warnings": warnings,
                "external_key": default_external_key(pack_id, str(version)),
            },
            indent=2,
        )
    )


def cmd_pack_export(args: argparse.Namespace) -> None:
    soul, _, _ = compile_pack(args.pack_id)
    out = export_pack(soul, Path(args.output))
    print(f"Exported SoulPack to {out}")


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
    sync_p.add_argument(
        "--kernel", default=os.getenv("SOULOS_KERNEL_URL", "http://localhost:8000")
    )
    sync_p.set_defaults(func=lambda a: asyncio.run(cmd_memory_sync(a)))

    pack_p = sub.add_parser("pack", help="SoulPacks (list / import / export)")
    pack_sub = pack_p.add_subparsers(dest="pack_command", required=True)

    pack_list = pack_sub.add_parser("list", help="List installed SoulPacks")
    pack_list.add_argument("-q", "--q", help="Filter by id/name/tags")
    pack_list.set_defaults(func=cmd_pack_list)

    pack_import = pack_sub.add_parser("import", help="Compile or ensure a SoulPack")
    pack_import.add_argument("pack_id")
    pack_import.add_argument(
        "--persist",
        default="false",
        choices=("true", "false"),
        help="false=convert only; true=POST to kernel",
    )
    pack_import.add_argument("--msv-preset", default=None)
    pack_import.add_argument(
        "--kernel", default=os.getenv("SOULOS_KERNEL_URL", "http://localhost:8000")
    )
    pack_import.set_defaults(func=cmd_pack_import)

    pack_export = pack_sub.add_parser("export", help="Export a SoulPack directory")
    pack_export.add_argument("pack_id")
    pack_export.add_argument("-o", "--output", required=True, help="Output pack directory")
    pack_export.set_defaults(func=cmd_pack_export)

    args = parser.parse_args(argv)
    if args.command == "memory-sync":
        asyncio.run(cmd_memory_sync(args))
    else:
        args.func(args)


if __name__ == "__main__":
    main()
