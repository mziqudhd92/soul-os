"""Gateway rate limiting — in-memory by default; Redis when REDIS_URL is set."""

from __future__ import annotations

import logging
import time
from collections import defaultdict, deque

from config import REDIS_URL
from keys import ApiKeyRecord

logger = logging.getLogger(__name__)


class InMemoryRateLimiter:
    """Per-process sliding window. Safe for single gateway replica only."""

    def __init__(self) -> None:
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    def allow(self, key: str, record: ApiKeyRecord) -> bool:
        limit = record.rate_limit_per_minute
        now = time.monotonic()
        window_start = now - 60.0
        hits = self._hits[key]
        while hits and hits[0] < window_start:
            hits.popleft()
        if len(hits) >= limit:
            return False
        hits.append(now)
        return True


class RedisRateLimiter:
    """Shared sliding window via Redis INCR + EXPIRE (approx per-minute)."""

    def __init__(self, redis_url: str) -> None:
        import redis

        self._client = redis.Redis.from_url(redis_url, decode_responses=True)

    def allow(self, key: str, record: ApiKeyRecord) -> bool:
        limit = record.rate_limit_per_minute
        bucket = f"soulos:rl:{key}:{int(time.time() // 60)}"
        count = self._client.incr(bucket)
        if count == 1:
            self._client.expire(bucket, 120)
        return int(count) <= limit


def build_rate_limiter():
    if REDIS_URL:
        try:
            limiter = RedisRateLimiter(REDIS_URL)
            logger.info("Gateway rate limiter: Redis (%s)", REDIS_URL.split("@")[-1])
            return limiter
        except Exception as exc:  # noqa: BLE001 — fall back for ops safety
            logger.warning(
                "REDIS_URL set but Redis rate limiter failed (%s); using in-memory",
                exc,
            )
    logger.info(
        "Gateway rate limiter: in-memory (single replica). "
        "Set REDIS_URL for multi-replica shared limits."
    )
    return InMemoryRateLimiter()


rate_limiter = build_rate_limiter()
