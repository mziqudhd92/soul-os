"""API key store for SoulOS Cloud."""

import hashlib
import json
import logging
import os
from dataclasses import dataclass

from config import API_KEYS_JSON, KEYS_FILE

logger = logging.getLogger(__name__)

_PLAINTEXT_HASH_WARNED = False


@dataclass(frozen=True)
class ApiKeyRecord:
    account_id: str
    tier: str = "cloud"
    rate_limit_per_minute: int = 120


def hash_api_key(token: str) -> str:
    """Return a stable in-memory / on-disk key id: ``sha256:<hex>``."""
    digest = hashlib.sha256(token.encode("utf-8")).hexdigest()
    return f"sha256:{digest}"


def _record_from_meta(meta: dict) -> ApiKeyRecord:
    return ApiKeyRecord(
        account_id=meta["account_id"],
        tier=meta.get("tier", "cloud"),
        rate_limit_per_minute=int(meta.get("rate_limit_per_minute", 120)),
    )


def _store_entry(out: dict[str, ApiKeyRecord], key: str, meta: dict) -> None:
    """Index by pre-hashed key, or hash plaintext and warn once."""
    global _PLAINTEXT_HASH_WARNED
    if key.startswith("_"):
        return
    if not isinstance(meta, dict):
        return
    record = _record_from_meta(meta)
    if key.startswith("sha256:"):
        out[key] = record
        return
    out[hash_api_key(key)] = record
    if not _PLAINTEXT_HASH_WARNED:
        logger.warning(
            "Plaintext API keys were hashed in-memory; "
            "prefer storing pre-hashed keys (sha256:<hex>)"
        )
        _PLAINTEXT_HASH_WARNED = True


def _load_from_file(path: str) -> dict[str, ApiKeyRecord]:
    if not os.path.isfile(path):
        return {}
    with open(path, encoding="utf-8") as f:
        raw = json.load(f)
    out: dict[str, ApiKeyRecord] = {}
    for key, meta in raw.items():
        _store_entry(out, key, meta)
    return out


def load_key_store() -> dict[str, ApiKeyRecord]:
    if API_KEYS_JSON.strip():
        raw = json.loads(API_KEYS_JSON)
        out: dict[str, ApiKeyRecord] = {}
        for key, meta in raw.items():
            _store_entry(out, key, meta)
        return out
    return _load_from_file(KEYS_FILE)


KEY_STORE = load_key_store()


def lookup_api_key(token: str) -> ApiKeyRecord | None:
    return KEY_STORE.get(hash_api_key(token))
