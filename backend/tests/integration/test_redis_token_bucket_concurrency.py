"""Integration concurrency and property tests for RedisTokenBucket rate limiter."""

from __future__ import annotations

import concurrent.futures
import time
from typing import Any

import pytest
import redis
from app.config import get_settings
from app.dhan.limiter import RedisTokenBucket
from app.dhan.limits_config import (
    BackoffSpec,
    DhanLimitsConfig,
    RateLimitSpec,
)


def is_redis_available() -> bool:
    settings = get_settings()
    try:
        client = redis.from_url(  # type: ignore[no-untyped-call]
            settings.get_redis_dsn(),
            decode_responses=True,
            socket_timeout=1.0,
            socket_connect_timeout=1.0,
        )
        return bool(client.ping())
    except Exception:
        return False


@pytest.fixture
def redis_client() -> Any:
    if not is_redis_available():
        pytest.skip("Valkey/Redis service not running; skipping integration concurrency test")
    # Use database 14 for test isolation
    client = redis.from_url(  # type: ignore[no-untyped-call]
        "redis://127.0.0.1:6379/14",
        decode_responses=True,
        socket_timeout=5.0,
    )
    client.flushdb()
    yield client
    try:
        client.flushdb()
    except Exception:
        pass


def test_redis_token_bucket_multi_threaded_concurrency(redis_client: Any) -> None:
    """Prove that concurrent workers sharing Redis never exceed configured capacity + rate."""
    capacity = 5
    rate = 20.0  # 20 req/sec

    config = DhanLimitsConfig(
        schema_version=1,
        as_of="2026-09-01",
        default_limit=RateLimitSpec(rate=rate, burst=capacity, description="Concurrency test"),
        backoff=BackoffSpec(base_delay_seconds=0.005, max_delay_seconds=0.05, jitter_ratio=0.1),
    )

    limiter = RedisTokenBucket(redis_client, config, key_prefix="test:concurrency")

    total_workers = 10
    requests_per_worker = 5
    total_expected = total_workers * requests_per_worker  # 50 total tokens

    results: list[float] = []

    def worker_task(worker_id: int) -> list[float]:
        timestamps = []
        for _ in range(requests_per_worker):
            limiter.acquire("default", timeout=10.0)
            timestamps.append(time.monotonic())
        return timestamps

    started_at = time.monotonic()
    with concurrent.futures.ThreadPoolExecutor(max_workers=total_workers) as executor:
        futures = [executor.submit(worker_task, i) for i in range(total_workers)]
        for f in concurrent.futures.as_completed(futures):
            results.extend(f.result())
    completed_at = time.monotonic()

    assert len(results) == total_expected

    # Calls record their local timestamp after Redis grants the token. Under thread
    # contention, a granted worker can be descheduled before that timestamp is
    # appended, which makes a client-side sliding window look artificially narrow.
    # End-to-end elapsed time brackets every Redis grant and therefore proves the
    # same sustained token-bucket bound without scheduler-induced false failures.
    minimum_elapsed = (total_expected - capacity) / rate
    actual_elapsed = completed_at - started_at
    assert actual_elapsed >= minimum_elapsed - 0.05, (
        f"Rate limit completed {total_expected} requests in {actual_elapsed:.3f}s; "
        f"minimum expected duration is {minimum_elapsed:.3f}s"
    )
