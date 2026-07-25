#!/usr/bin/env python3
"""Phase A demo: Customer Front Desk → Inventory handoff (app-orchestrated).

Requires a running kernel (e.g. docker compose sidecar). Uses existing
ensure / prepare / complete / memory ingest — no teams API.

Usage:
  python3 examples/multi-agent-handoff/run_handoff.py
  python3 examples/multi-agent-handoff/run_handoff.py --kernel http://localhost:8000
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[2]
SDK = ROOT / "packages" / "soulos-sdk" / "python"
if str(SDK) not in sys.path:
    sys.path.insert(0, str(SDK))

from soulos.handoff import (  # noqa: E402
    conversation_session_id,
    handoff_to,
    role_external_key,
)
from soulos.hybrid import SoulHybridClient  # noqa: E402


async def _import_pack(kernel: str, pack_id: str) -> dict:
    async with httpx.AsyncClient(timeout=60.0) as http:
        resp = await http.post(
            f"{kernel.rstrip('/')}/v1/avatars/import-soulpack",
            json={"pack_id": pack_id, "persist": False},
        )
        resp.raise_for_status()
        return resp.json()


async def run(kernel: str, org_id: str, conversation_id: str) -> int:
    client = SoulHybridClient(base_url=kernel, enabled=True)
    session_id = conversation_session_id(conversation_id)
    try:
        customer_soul = (await _import_pack(kernel, "customer-front"))["soul"]
        inventory_soul = (await _import_pack(kernel, "inventory"))["soul"]

        customer = await client.ensure_avatar(
            role_external_key(org_id, "customer"),
            customer_soul,
        )
        inventory = await client.ensure_avatar(
            role_external_key(org_id, "inventory"),
            inventory_soul,
        )
        customer_id = customer.get("id") or customer.get("bot_id")
        inventory_id = inventory.get("id") or inventory.get("bot_id")
        if not customer_id or not inventory_id:
            print("ensure did not return bot ids", file=sys.stderr)
            return 1

        user_q = "Do you have SKU-42 in stock for overnight shipping?"
        prepared = await client.prepare_turn(
            user_q,
            bot_id=customer_id,
            session_id=session_id,
        )
        if not prepared:
            print("prepare failed on customer bot", file=sys.stderr)
            return 1

        # Mock LLM: front desk decides to hand off.
        customer_reply = (
            "I can help with that — I'll transfer you to Inventory for SKU-42 stock."
        )
        transfer = await handoff_to(
            client,
            from_bot_id=customer_id,
            to_bot_id=inventory_id,
            from_role="customer",
            to_role="inventory",
            conversation_id=conversation_id,
            reason="stock and overnight feasibility",
            summary=customer_reply,
            user_message=user_q,
            payload={"sku": "SKU-42", "need": "overnight"},
        )

        inv_prepared = await client.prepare_turn(
            "Confirm SKU-42 availability for overnight shipping.",
            bot_id=inventory_id,
            session_id=session_id,
        )
        if not inv_prepared:
            print("prepare failed on inventory bot", file=sys.stderr)
            return 1

        memories = inv_prepared.get("memories") or []
        handoff_hit = any(
            isinstance(m, dict)
            and "handoff" in str(m.get("content") or m.get("text") or "").lower()
            for m in memories
        ) or "handoff" in str(inv_prepared.get("system_prompt") or "").lower()

        out = {
            "org_id": org_id,
            "conversation_id": conversation_id,
            "session_id": session_id,
            "customer_bot_id": customer_id,
            "inventory_bot_id": inventory_id,
            "customer_external_key": role_external_key(org_id, "customer"),
            "inventory_external_key": role_external_key(org_id, "inventory"),
            "customer_prepare_ok": True,
            "handoff_note_preview": transfer["note"][:200],
            "inventory_saw_handoff_context": handoff_hit,
            "inventory_memory_count": len(memories),
        }
        print(json.dumps(out, indent=2))
        return 0
    finally:
        await client.close()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--kernel", default="http://localhost:8000")
    parser.add_argument("--org-id", default="demo")
    parser.add_argument("--conversation-id", default="thread-demo-1")
    args = parser.parse_args(argv)
    return asyncio.run(run(args.kernel, args.org_id, args.conversation_id))


if __name__ == "__main__":
    raise SystemExit(main())
