"""Per-tenant token buckets for expensive MCP cognitive tools."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from threading import Lock


@dataclass
class _Bucket:
    tokens: float
    updated_at: float


@dataclass
class TokenBucketLimiter:
    """Simple in-process token bucket (per key)."""

    rate_per_minute: float = 10.0
    burst: float = 5.0
    _buckets: dict[str, _Bucket] = field(default_factory=dict)
    _lock: Lock = field(default_factory=Lock)

    def allow(self, key: str) -> bool:
        now = time.monotonic()
        with self._lock:
            bucket = self._buckets.get(key)
            if bucket is None:
                bucket = _Bucket(tokens=self.burst, updated_at=now)
                self._buckets[key] = bucket
            elapsed = now - bucket.updated_at
            bucket.tokens = min(
                self.burst,
                bucket.tokens + elapsed * (self.rate_per_minute / 60.0),
            )
            bucket.updated_at = now
            if bucket.tokens < 1.0:
                return False
            bucket.tokens -= 1.0
            return True


# Shared limiters for MCP cognitive tools
reflect_limiter = TokenBucketLimiter(rate_per_minute=20.0, burst=5.0)
consolidate_limiter = TokenBucketLimiter(rate_per_minute=6.0, burst=2.0)


def rate_limit_key(tenant_id: str | None, tool: str) -> str:
    return f"{tenant_id or 'anon'}:{tool}"
