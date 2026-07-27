"""Tests for gateway rate limiter backends."""

from unittest.mock import MagicMock, patch

from keys import ApiKeyRecord
from rate_limit import InMemoryRateLimiter, RedisRateLimiter, build_rate_limiter


def test_in_memory_rate_limiter_blocks_after_limit():
    limiter = InMemoryRateLimiter()
    record = ApiKeyRecord(
        account_id="a",
        tier="cloud",
        rate_limit_per_minute=2,
    )
    assert limiter.allow("k1", record) is True
    assert limiter.allow("k1", record) is True
    assert limiter.allow("k1", record) is False


def test_build_rate_limiter_defaults_to_memory(monkeypatch):
    monkeypatch.setattr("rate_limit.REDIS_URL", "")
    limiter = build_rate_limiter()
    assert isinstance(limiter, InMemoryRateLimiter)


def test_redis_rate_limiter_uses_incr():
    fake = MagicMock()
    fake.incr.return_value = 1
    with patch("redis.Redis.from_url", return_value=fake):
        limiter = RedisRateLimiter("redis://localhost:6379/0")
    record = ApiKeyRecord(account_id="a", tier="cloud", rate_limit_per_minute=10)
    assert limiter.allow("key", record) is True
    fake.incr.assert_called_once()
    fake.expire.assert_called_once()
