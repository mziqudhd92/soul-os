"""Simple in-memory per-key rate limiting."""

import time
from collections import defaultdict, deque

from keys import ApiKeyRecord


class RateLimiter:
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


rate_limiter = RateLimiter()
