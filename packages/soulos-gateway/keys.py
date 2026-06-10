"""API key store for SoulOS Cloud."""

import json
import os
from dataclasses import dataclass

from config import API_KEYS_JSON, KEYS_FILE


@dataclass(frozen=True)
class ApiKeyRecord:
    account_id: str
    tier: str = "cloud"
    rate_limit_per_minute: int = 120


def _load_from_file(path: str) -> dict[str, ApiKeyRecord]:
    if not os.path.isfile(path):
        return {}
    with open(path, encoding="utf-8") as f:
        raw = json.load(f)
    out: dict[str, ApiKeyRecord] = {}
    for key, meta in raw.items():
        out[key] = ApiKeyRecord(
            account_id=meta["account_id"],
            tier=meta.get("tier", "cloud"),
            rate_limit_per_minute=int(meta.get("rate_limit_per_minute", 120)),
        )
    return out


def load_key_store() -> dict[str, ApiKeyRecord]:
    if API_KEYS_JSON.strip():
        raw = json.loads(API_KEYS_JSON)
        return {
            key: ApiKeyRecord(
                account_id=meta["account_id"],
                tier=meta.get("tier", "cloud"),
                rate_limit_per_minute=int(meta.get("rate_limit_per_minute", 120)),
            )
            for key, meta in raw.items()
        }
    return _load_from_file(KEYS_FILE)


KEY_STORE = load_key_store()


def lookup_api_key(token: str) -> ApiKeyRecord | None:
    return KEY_STORE.get(token)
