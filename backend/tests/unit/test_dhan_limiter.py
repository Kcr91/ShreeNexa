"""Unit tests for Dhan in-memory and Redis token bucket rate limiters."""

from __future__ import annotations

import time
from typing import Any

import pytest
from app.dhan.exceptions import DhanRateLimitError
from app.dhan.limiter import (
    InMemoryTokenBucket,
    RedisTokenBucket,
    get_dhan_rate_limiter,
)
from app.dhan.limits_config import (
    BackoffSpec,
    DhanLimitsConfig,
    RateLimitSpec,
)
from hypothesis import given, settings
from hypothesis import strategies as st


@pytest.fixture
def custom_limits_config() -> DhanLimitsConfig:
    return DhanLimitsConfig(
        schema_version=1,
        as_of="2026-09-01",
        default_limit=RateLimitSpec(rate=10.0, burst=3, description="Test default"),
        backoff=BackoffSpec(base_delay_seconds=0.01, max_delay_seconds=0.1, jitter_ratio=0.1),
        categories={
            "fast": RateLimitSpec(rate=20.0, burst=5, description="Fast"),
            "slow": RateLimitSpec(rate=2.0, burst=2, description="Slow"),
            "single": RateLimitSpec(rate=1.0, burst=1, description="Single"),
        },
    )


def test_in_memory_token_bucket_burst_capacity(custom_limits_config: DhanLimitsConfig) -> None:
    limiter = InMemoryTokenBucket(custom_limits_config)

    # Initial burst up to 3 tokens for default
    assert limiter.try_acquire("default") is True
    assert limiter.try_acquire("default") is True
    assert limiter.try_acquire("default") is True

    # 4th request must fail immediate acquisition
    assert limiter.try_acquire("default") is False


def test_in_memory_token_bucket_refill(custom_limits_config: DhanLimitsConfig) -> None:
    limiter = InMemoryTokenBucket(custom_limits_config)

    # Exhaust single bucket (capacity 1, rate 1.0/s)
    assert limiter.try_acquire("single") is True
    assert limiter.try_acquire("single") is False

    # Wait 1.1 seconds for refill
    time.sleep(1.1)
    assert limiter.try_acquire("single") is True


def test_in_memory_token_bucket_acquire_blocking(custom_limits_config: DhanLimitsConfig) -> None:
    limiter = InMemoryTokenBucket(custom_limits_config)

    # Exhaust fast category (burst 5)
    for _ in range(5):
        assert limiter.try_acquire("fast") is True

    # acquire should block briefly and succeed
    start = time.monotonic()
    waited = limiter.acquire("fast", timeout=1.0)
    elapsed = time.monotonic() - start

    assert waited > 0.0
    assert elapsed >= 0.04  # ~1 token at 20/s is 0.05s


def test_in_memory_token_bucket_timeout(custom_limits_config: DhanLimitsConfig) -> None:
    limiter = InMemoryTokenBucket(custom_limits_config)

    # Exhaust slow category (burst 2, rate 2.0/s)
    assert limiter.try_acquire("slow") is True
    assert limiter.try_acquire("slow") is True

    # acquire with a very small timeout should raise DhanRateLimitError
    with pytest.raises(DhanRateLimitError, match="Rate limit timed out"):
        limiter.acquire("slow", timeout=0.05)


class FakeRedisForLua:
    """Minimal fake Redis client supporting registered Lua scripts for unit tests."""

    def __init__(self) -> None:
        self.store: dict[str, str] = {}

    def register_script(self, script_body: str) -> FakeLuaScript:
        return FakeLuaScript(self, script_body)

    def ping(self) -> bool:
        return True

    def get(self, key: str) -> str | None:
        return self.store.get(key)


class FakeLuaScript:
    """Emulates Redis Lua script execution in Python for unit testing."""

    def __init__(self, redis_client: FakeRedisForLua, script_body: str) -> None:
        self.redis = redis_client
        self.script_body = script_body

    def __call__(self, keys: list[str], args: list[float | int | str]) -> list[Any]:
        cost = float(args[0])
        capacity = float(args[1])
        rate = float(args[2])
        _ttl = int(args[3])
        per_min = int(args[4]) if len(args) > 4 else 0
        per_hr = int(args[5]) if len(args) > 5 else 0
        per_day = int(args[6]) if len(args) > 6 else 0

        k_tokens = keys[0]
        k_last = keys[1]
        k_min = keys[2] if len(keys) > 2 else ""
        k_hr = keys[3] if len(keys) > 3 else ""
        k_day = keys[4] if len(keys) > 4 else ""
        now = time.time()

        # Check multi-window caps
        if per_min > 0 and k_min:
            cur_min = int(self.redis.store.get(k_min, "0"))
            if cur_min + cost > per_min:
                return [0, 60.0, 0]

        if per_hr > 0 and k_hr:
            cur_hr = int(self.redis.store.get(k_hr, "0"))
            if cur_hr + cost > per_hr:
                return [0, 3600.0, 0]

        if per_day > 0 and k_day:
            cur_day = int(self.redis.store.get(k_day, "0"))
            if cur_day + cost > per_day:
                return [0, 86400.0, 0]

        raw_tokens = self.redis.store.get(k_tokens)
        raw_last = self.redis.store.get(k_last)

        if raw_tokens is None or raw_last is None:
            current_tokens = capacity
            last_time = now
        else:
            elapsed = max(0.0, now - float(raw_last))
            current_tokens = min(capacity, float(raw_tokens) + elapsed * rate)
            last_time = now

        if current_tokens >= cost:
            current_tokens -= cost
            self.redis.store[k_tokens] = str(current_tokens)
            self.redis.store[k_last] = str(last_time)
            if per_min > 0 and k_min:
                self.redis.store[k_min] = str(int(self.redis.store.get(k_min, "0")) + int(cost))
            if per_hr > 0 and k_hr:
                self.redis.store[k_hr] = str(int(self.redis.store.get(k_hr, "0")) + int(cost))
            if per_day > 0 and k_day:
                self.redis.store[k_day] = str(int(self.redis.store.get(k_day, "0")) + int(cost))
            return [1, 0, current_tokens]
        else:
            deficit = cost - current_tokens
            wait_sec = deficit / rate
            self.redis.store[k_tokens] = str(current_tokens)
            self.redis.store[k_last] = str(last_time)
            return [0, wait_sec, current_tokens]


def test_redis_token_bucket_with_fake(custom_limits_config: DhanLimitsConfig) -> None:
    fake_redis = FakeRedisForLua()
    limiter = RedisTokenBucket(fake_redis, custom_limits_config)  # type: ignore[arg-type]

    assert limiter.try_acquire("fast") is True
    assert limiter.try_acquire("fast") is True
    assert limiter.try_acquire("fast") is True
    assert limiter.try_acquire("fast") is True
    assert limiter.try_acquire("fast") is True
    assert limiter.try_acquire("fast") is False

    time.sleep(0.1)
    assert limiter.try_acquire("fast") is True


def test_redis_token_bucket_timeout_with_fake(custom_limits_config: DhanLimitsConfig) -> None:
    fake_redis = FakeRedisForLua()
    limiter = RedisTokenBucket(fake_redis, custom_limits_config)  # type: ignore[arg-type]

    assert limiter.try_acquire("slow") is True
    assert limiter.try_acquire("slow") is True

    with pytest.raises(DhanRateLimitError, match="Distributed rate limit timed out"):
        limiter.acquire("slow", timeout=0.05)


def test_get_dhan_rate_limiter_fallback() -> None:
    # Factory gracefully returns an InMemoryTokenBucket when Redis is unreachable or None
    limiter = get_dhan_rate_limiter(redis_client=None)
    assert hasattr(limiter, "acquire")
    assert hasattr(limiter, "try_acquire")


def test_in_memory_token_bucket_per_minute_window() -> None:
    config = DhanLimitsConfig(
        schema_version=1,
        as_of="2026-09-01",
        default_limit=RateLimitSpec(rate=100.0, burst=100, description="Default"),
        categories={
            "min_test": RateLimitSpec(rate=100.0, burst=100, per_minute=3, description="3 per min"),
        },
    )
    limiter = InMemoryTokenBucket(config)
    now = 1000.0

    assert limiter.try_acquire("min_test", now=now) is True
    assert limiter.try_acquire("min_test", now=now + 0.1) is True
    assert limiter.try_acquire("min_test", now=now + 0.2) is True
    # 4th request inside 60s must fail despite high per-second capacity
    assert limiter.try_acquire("min_test", now=now + 0.3) is False

    # After 61s from the first request, one slot opens
    assert limiter.try_acquire("min_test", now=now + 60.05) is True
    # But another immediate request within the same 60s block fails
    assert limiter.try_acquire("min_test", now=now + 60.06) is False


def test_in_memory_token_bucket_per_day_window() -> None:
    config = DhanLimitsConfig(
        schema_version=1,
        as_of="2026-09-01",
        default_limit=RateLimitSpec(rate=100.0, burst=100, description="Default"),
        categories={
            "day_test": RateLimitSpec(rate=100.0, burst=100, per_day=2, description="2 per day"),
        },
    )
    limiter = InMemoryTokenBucket(config)
    now = 50000.0

    assert limiter.try_acquire("day_test", now=now) is True
    assert limiter.try_acquire("day_test", now=now + 10.0) is True
    assert limiter.try_acquire("day_test", now=now + 20.0) is False

    # After 86401s, first request rolls out
    assert limiter.try_acquire("day_test", now=now + 86400.5) is True


def test_in_memory_token_bucket_budget_usage_and_80_pct_alert() -> None:
    config = DhanLimitsConfig(
        schema_version=1,
        as_of="2026-09-01",
        default_limit=RateLimitSpec(rate=100.0, burst=100, description="Default"),
        categories={
            "orders": RateLimitSpec(
                rate=10.0, burst=10, per_minute=250, per_hour=1000, per_day=10, description="Orders"
            ),
        },
    )
    limiter = InMemoryTokenBucket(config)
    usage_init = limiter.get_budget_usage("orders")
    assert usage_init["requests_today"] == 0
    assert usage_init["remaining_today"] == 10
    assert usage_init["used_pct_today"] == 0.0
    assert usage_init["alert_80_pct"] is False

    # Perform 8 requests (8 / 10 = 80%)
    for _ in range(8):
        assert limiter.try_acquire("orders") is True

    usage_80 = limiter.get_budget_usage("orders")
    assert usage_80["requests_today"] == 8
    assert usage_80["remaining_today"] == 2
    assert usage_80["used_pct_today"] == 80.0
    assert usage_80["alert_80_pct"] is True


def test_redis_token_bucket_multi_window_with_fake() -> None:
    fake_redis = FakeRedisForLua()
    config = DhanLimitsConfig(
        schema_version=1,
        as_of="2026-09-01",
        default_limit=RateLimitSpec(rate=100.0, burst=100, description="Default"),
        categories={
            "redis_test": RateLimitSpec(
                rate=100.0, burst=100, per_minute=2, per_day=5, description="Redis multi-window"
            ),
        },
    )
    limiter = RedisTokenBucket(fake_redis, config)  # type: ignore[arg-type]

    assert limiter.try_acquire("redis_test") is True
    assert limiter.try_acquire("redis_test") is True
    # 3rd request blocked by per_minute cap
    assert limiter.try_acquire("redis_test") is False

    budget = limiter.get_budget_usage("redis_test")
    assert budget["requests_today"] == 2
    assert budget["limit_per_day"] == 5
    assert budget["remaining_today"] == 3
    assert budget["alert_80_pct"] is False


@given(
    burst=st.integers(min_value=1, max_value=20),
    rate=st.floats(min_value=1.0, max_value=50.0),
    time_deltas=st.lists(st.floats(min_value=0.0, max_value=2.0), min_size=1, max_size=15),
)
@settings(max_examples=30)
def test_token_bucket_replenishment_property_hypothesis(
    burst: int, rate: float, time_deltas: list[float]
) -> None:
    """Hypothesis property test: Token bucket capacity is never exceeded and non-negative."""
    config = DhanLimitsConfig(
        schema_version=1,
        as_of="2026-09-01",
        default_limit=RateLimitSpec(rate=rate, burst=burst, description="Property test"),
    )
    limiter = InMemoryTokenBucket(config)

    simulated_now = 1000.0
    # Step through simulated time increments
    for delta in time_deltas:
        simulated_now += delta
        tokens, calculated_rate, cap = limiter._replenish("default", simulated_now)
        assert 0.0 <= tokens <= burst
        assert cap == burst
        assert calculated_rate == rate

        # Consume if possible
        if tokens >= 1.0:
            limiter._state["default"] = (tokens - 1.0, simulated_now)
            tokens_after = limiter._state["default"][0]
            assert 0.0 <= tokens_after <= burst
