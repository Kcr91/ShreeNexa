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

        k_tokens = keys[0]
        k_last = keys[1]
        now = time.time()

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
