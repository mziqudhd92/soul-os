"""Gateway rate limiting — in-memory by default; Redis when REDIS_URL is set."""

from __future__ import annotations

import logging
import time
import uuid
from collections import deque

from config import GATEWAY_REPLICAS, REDIS_URL
from keys import ApiKeyRecord

logger = logging.getLogger(__name__)

WINDOW_SECONDS = 60.0
# Cap distinct keys so a flood of unique tokens cannot grow unbounded.
DEFAULT_MAX_KEYS = 10_000


class InMemoryRateLimiter:
    """Per-process sliding window. Safe for single gateway replica only."""

    def __init__(self, max_keys: int = DEFAULT_MAX_KEYS) -> None:
        self._hits: dict[str, deque[float]] = {}
        self._last_seen: dict[str, float] = {}
        self._max_keys = max_keys

    def _purge_idle(self, now: float) -> None:
        """Drop keys with no hits left in the sliding window."""
        window_start = now - WINDOW_SECONDS
        stale = [
            key
            for key, last in self._last_seen.items()
            if last < window_start or not self._hits.get(key)
        ]
        for key in stale:
            self._hits.pop(key, None)
            self._last_seen.pop(key, None)

    def _evict_if_needed(self, now: float) -> None:
        self._purge_idle(now)
        if len(self._hits) < self._max_keys:
            return
        # Drop idle keys first (oldest last_seen).
        for key, _ in sorted(self._last_seen.items(), key=lambda kv: kv[1]):
            if len(self._hits) < self._max_keys:
                break
            self._hits.pop(key, None)
            self._last_seen.pop(key, None)

    def allow(self, key: str, record: ApiKeyRecord) -> bool:
        limit = record.rate_limit_per_minute
        now = time.monotonic()
        window_start = now - WINDOW_SECONDS
        if key not in self._hits:
            self._evict_if_needed(now)
            self._hits[key] = deque()
        hits = self._hits[key]
        while hits and hits[0] < window_start:
            hits.popleft()
        self._last_seen[key] = now
        if len(hits) >= limit:
            return False
        hits.append(now)
        return True


# Atomic sliding-window log: trim entries older than the window, admit if under limit.
_SLIDING_WINDOW_LUA = """
local key = KEYS[1]
local now_ms = tonumber(ARGV[1])
local window_ms = tonumber(ARGV[2])
local limit = tonumber(ARGV[3])
redis.call('ZREMRANGEBYSCORE', key, 0, now_ms - window_ms)
if redis.call('ZCARD', key) >= limit then
  return 0
end
redis.call('ZADD', key, now_ms, ARGV[4])
redis.call('PEXPIRE', key, window_ms)
return 1
"""


class RedisRateLimiter:
    """Shared sliding window (sorted-set log) across gateway replicas.

    When ``fail_closed`` is True (multi-replica), Redis errors deny the request
    instead of falling back to per-process limits (which would multiply the cap).
    Single-replica deployments may fall back to in-memory limits.
    """

    def __init__(self, redis_url: str, *, fail_closed: bool = False) -> None:
        import redis

        self._redis_error = redis.RedisError
        self._client = redis.Redis.from_url(redis_url, decode_responses=True)
        self._script = self._client.register_script(_SLIDING_WINDOW_LUA)
        self._fallback = InMemoryRateLimiter()
        self._fail_closed = fail_closed
        self._degraded = False

    def allow(self, key: str, record: ApiKeyRecord) -> bool:
        now_ms = int(time.time() * 1000)
        try:
            allowed = self._script(
                keys=[f"soulos:rl:{key}"],
                args=[
                    now_ms,
                    int(WINDOW_SECONDS * 1000),
                    record.rate_limit_per_minute,
                    f"{now_ms}:{uuid.uuid4().hex}",
                ],
            )
        except self._redis_error as exc:
            if not self._degraded:
                if self._fail_closed:
                    logger.error(
                        "Redis rate limiter unavailable (%s); denying requests "
                        "(fail-closed multi-replica mode)",
                        exc,
                    )
                else:
                    logger.error(
                        "Redis rate limiter unavailable (%s); using per-process limits",
                        exc,
                    )
                self._degraded = True
            if self._fail_closed:
                return False
            return self._fallback.allow(key, record)
        if self._degraded:
            logger.info("Redis rate limiter recovered")
            self._degraded = False
        return int(allowed) == 1


def build_rate_limiter(
    redis_url: str | None = None, replicas: int | None = None
):
    redis_url = REDIS_URL if redis_url is None else redis_url
    replicas = GATEWAY_REPLICAS if replicas is None else replicas
    if redis_url:
        fail_closed = replicas > 1
        limiter = RedisRateLimiter(redis_url, fail_closed=fail_closed)
        mode = "fail-closed" if fail_closed else "fail-open fallback"
        logger.info(
            "Gateway rate limiter: Redis (%s) [%s]",
            redis_url.split("@")[-1],
            mode,
        )
        return limiter
    if replicas > 1:
        raise RuntimeError(
            f"GATEWAY_REPLICAS={replicas} but REDIS_URL is unset: in-memory rate "
            "limits are per-process and would allow N× the configured limit. "
            "Set REDIS_URL or run a single gateway replica."
        )
    logger.warning(
        "Gateway rate limiter: in-memory (single replica only). "
        "Set REDIS_URL before scaling the gateway horizontally."
    )
    return InMemoryRateLimiter()


rate_limiter = build_rate_limiter()
