"""Tests for gateway rate limiter backends."""

from unittest.mock import MagicMock, patch

import pytest
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


def test_in_memory_evicts_idle_keys(monkeypatch):
    limiter = InMemoryRateLimiter(max_keys=2)
    record = ApiKeyRecord(account_id="a", tier="cloud", rate_limit_per_minute=10)
    t = {"now": 1000.0}
    monkeypatch.setattr("rate_limit.time.monotonic", lambda: t["now"])
    assert limiter.allow("a", record)
    t["now"] = 1001.0
    assert limiter.allow("b", record)
    t["now"] = 1002.0
    assert limiter.allow("c", record)  # evicts oldest idle key "a"
    assert "a" not in limiter._hits
    assert set(limiter._hits) == {"b", "c"}


def test_build_rate_limiter_defaults_to_memory():
    limiter = build_rate_limiter(redis_url="", replicas=1)
    assert isinstance(limiter, InMemoryRateLimiter)


def test_build_rate_limiter_rejects_multi_replica_without_redis():
    with pytest.raises(RuntimeError, match="REDIS_URL"):
        build_rate_limiter(redis_url="", replicas=2)


def test_redis_rate_limiter_uses_sliding_window_script():
    fake = MagicMock()
    fake.register_script.return_value = MagicMock(return_value=1)
    with patch("redis.Redis.from_url", return_value=fake):
        limiter = RedisRateLimiter("redis://localhost:6379/0")
    record = ApiKeyRecord(account_id="a", tier="cloud", rate_limit_per_minute=10)
    assert limiter.allow("key", record) is True
    fake.register_script.assert_called_once()
    limiter._script.assert_called_once()


def test_redis_rate_limiter_falls_back_when_redis_errors():
    import redis

    fake = MagicMock()
    script = MagicMock(side_effect=redis.RedisError("down"))
    fake.register_script.return_value = script
    with patch("redis.Redis.from_url", return_value=fake):
        limiter = RedisRateLimiter("redis://localhost:6379/0", fail_closed=False)
    record = ApiKeyRecord(account_id="a", tier="cloud", rate_limit_per_minute=1)
    assert limiter.allow("k", record) is True
    assert limiter.allow("k", record) is False  # in-memory fallback


def test_redis_rate_limiter_fail_closed_denies_when_redis_down():
    import redis

    fake = MagicMock()
    script = MagicMock(side_effect=redis.RedisError("down"))
    fake.register_script.return_value = script
    with patch("redis.Redis.from_url", return_value=fake):
        limiter = RedisRateLimiter("redis://localhost:6379/0", fail_closed=True)
    record = ApiKeyRecord(account_id="a", tier="cloud", rate_limit_per_minute=100)
    assert limiter.allow("k", record) is False


def test_build_rate_limiter_multi_replica_redis_is_fail_closed():
    fake = MagicMock()
    fake.register_script.return_value = MagicMock(return_value=1)
    with patch("redis.Redis.from_url", return_value=fake):
        limiter = build_rate_limiter(redis_url="redis://localhost:6379/0", replicas=2)
    assert isinstance(limiter, RedisRateLimiter)
    assert limiter._fail_closed is True


def test_in_memory_purges_idle_keys(monkeypatch):
    limiter = InMemoryRateLimiter(max_keys=10)
    record = ApiKeyRecord(account_id="a", tier="cloud", rate_limit_per_minute=10)
    t = {"now": 1000.0}
    monkeypatch.setattr("rate_limit.time.monotonic", lambda: t["now"])
    assert limiter.allow("old", record)
    t["now"] = 1000.0 + 61.0  # past WINDOW_SECONDS
    assert limiter.allow("new", record)
    # purge runs on evict path; force via max_keys overflow after idle
    limiter._purge_idle(t["now"])
    assert "old" not in limiter._hits
