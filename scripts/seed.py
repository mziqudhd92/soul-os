#!/usr/bin/env python3
"""Seed example avatars into the SoulOS kernel."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import httpx

KERNEL_URL = os.getenv("SOULOS_KERNEL_URL", "http://localhost:8000").rstrip("/")
REPO_ROOT = Path(__file__).resolve().parents[1]
EXAMPLES_DIR = REPO_ROOT / "examples"

SEED_SOULS = [
    {
        "file": "support-bot/support-bot.soul.json",
        "extras": {
            "capabilities": ["Billing", "Refunds", "Product"],
            "hourly_rate": 80,
            "avatar_url": (
                "https://images.unsplash.com/photo-1531297122539-5692f6e13b24"
                "?auto=format&fit=crop&q=80&w=200&h=200"
            ),
        },
    },
    {
        "file": "dev-twin/dev-twin.soul.json",
        "extras": {
            "hourly_rate": 150,
            "avatar_url": (
                "https://images.unsplash.com/photo-1550745165-9bc0b252726f"
                "?auto=format&fit=crop&q=80&w=200&h=200"
            ),
        },
    },
    {
        "file": "companion/companion.soul.json",
        "extras": {
            "hourly_rate": 60,
            "avatar_url": (
                "https://images.unsplash.com/photo-1620712943543-bcc4688e7485"
                "?auto=format&fit=crop&q=80&w=200&h=200"
            ),
        },
    },
]


def register_soul(relative_path: str, extras: dict) -> dict:
    path = EXAMPLES_DIR / relative_path
    soul = json.loads(path.read_text(encoding="utf-8"))
    payload = {**soul, **extras}
    with httpx.Client(timeout=30.0) as client:
        res = client.post(f"{KERNEL_URL}/v1/avatars", json=payload)
    data = res.json()
    if res.status_code != 200:
        raise RuntimeError(f"Failed to register {relative_path}: {data.get('detail', res.text)}")
    print(f"Registered avatar: {data['name']} ({data['id']})")
    return data


def main() -> None:
    print(f"Seeding avatars via POST {KERNEL_URL}/v1/avatars ...")
    for entry in SEED_SOULS:
        register_soul(entry["file"], entry.get("extras", {}))
    print("Seeding completed successfully.")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"Error during seeding: {exc}", file=sys.stderr)
        sys.exit(1)
