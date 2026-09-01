"""Distributed and in-memory token bucket rate limiters for Dhan REST API."""

from __future__ import annotations

import logging
import random
import threading
import time
from typing import Any, Protocol

import redis
from redis import Redis

from app.config import get_settings
from app.dhan.exceptions import DhanRateLimitError
from app.dhan.limits_config import (
    DhanLimitsConfig,
    load_dhan_limits,
)

logger = logging.getLogger(__name__)

# Atomic Lua script for Redis-backed token bucket
REDIS_TOKEN_BUCKET_LUA = """
local redis_time = redis.call('TIME')
local now = tonumber(redis_time[1]) + (tonumber(redis_time[2]) / 1000000.0)

local cost = tonumber(ARGV[1])
local capacity = tonumber(ARGV[2])
local rate = tonumber(ARGV[3])
local ttl = tonumber(ARGV[4])

local current_tokens = tonumber(redis.call('GET', KEYS[1]))
local last_time = tonumber(redis.call('GET', KEYS[2]))

if current_tokens == nil or last_time == nil then
    current_tokens = capacity
    last_time = now
else
    local elapsed = math.max(0.0, now - last_time)
    current_tokens = math.min(capacity, current_tokens + (elapsed * rate))
    last_time = now
end

if current_tokens >= cost then
    current_tokens = current_tokens - cost
    redis.call('SETEX', KEYS[1], ttl, tostring(current_tokens))
    redis.call('SETEX', KEYS[2], ttl, tostring(last_time))
    return {1, 0, current_tokens}
else
    local deficit = cost - current_tokens
    local wait_sec = deficit / rate
    redis.call('SETEX', KEYS[1], ttl, tostring(current_tokens))
    redis.call('SETEX', KEYS[2], ttl, tostring(last_time))
    return {0, wait_sec, current_tokens}
end
"""


class TokenBucket(Protocol):
    """Protocol for Dhan rate limiter implementations."""

    def acquire(self, category: str, cost: float = 1.0, timeout: float = 30.0) -> float:
        """Acquire token(s) for category, blocking with jittered backoff if necessary.

        Returns total time waited in seconds. Raises DhanRateLimitError if timeout exceeded.
        """
        ...

    def try_acquire(self, category: str, cost: float = 1.0) -> bool:
        """Attempt immediate token acquisition without blocking. Returns True if acquired."""
        ...


class InMemoryTokenBucket:
    """Thread-safe in-memory token bucket implementation for local/testing execution."""

    def __init__(self, config: DhanLimitsConfig | None = None) -> None:
        self.config = config or load_dhan_limits()
        self._lock = threading.Lock()
        # category -> (tokens: float, last_update_time: float)
        self._state: dict[str, tuple[float, float]] = {}

    def _replenish(self, category: str, now: float) -> tuple[float, float, float]:
        spec = self.config.get_rate_limit(category)
        capacity = float(spec.burst)
        rate = float(spec.rate)

        if category not in self._state:
            self._state[category] = (capacity, now)
            return capacity, rate, capacity

        tokens, last_time = self._state[category]
        elapsed = max(0.0, now - last_time)
        new_tokens = min(capacity, tokens + (elapsed * rate))
        self._state[category] = (new_tokens, now)
        return new_tokens, rate, capacity

    def try_acquire(self, category: str, cost: float = 1.0) -> bool:
        """Attempt to immediately consume tokens without sleeping."""
        now = time.monotonic()
        with self._lock:
            tokens, _rate, _cap = self._replenish(category, now)
            if tokens >= cost:
                self._state[category] = (tokens - cost, now)
                return True
            return False

    def acquire(self, category: str, cost: float = 1.0, timeout: float = 30.0) -> float:
        """Block until tokens are available or timeout expires."""
        start_time = time.monotonic()
        total_waited = 0.0

        while True:
            now = time.monotonic()
            with self._lock:
                tokens, rate, _cap = self._replenish(category, now)
                if tokens >= cost:
                    self._state[category] = (tokens - cost, now)
                    return total_waited

                deficit = cost - tokens
                wait_sec = deficit / rate if rate > 0 else 1.0

            elapsed = time.monotonic() - start_time
            if elapsed + wait_sec > timeout:
                raise DhanRateLimitError(
                    f"Rate limit timed out for '{category}' after {elapsed:.2f}s "
                    f"(wait: {wait_sec:.2f}s, timeout: {timeout}s)",
                    details={"retry_after": int(wait_sec) + 1},
                )

            # Apply backoff jitter
            jitter = (
                random.uniform(-self.config.backoff.jitter_ratio, self.config.backoff.jitter_ratio)
                * wait_sec
            )
            sleep_duration = min(
                self.config.backoff.max_delay_seconds,
                max(self.config.backoff.base_delay_seconds, wait_sec + jitter),
            )

            time.sleep(sleep_duration)
            total_waited = time.monotonic() - start_time


class RedisTokenBucket:
    """Distributed Redis-backed token bucket using atomic Lua script."""

    def __init__(
        self,
        redis_client: Redis,
        config: DhanLimitsConfig | None = None,
        key_prefix: str = "shreenexa:ratelimit",
        ttl_seconds: int = 3600,
    ) -> None:
        self.redis = redis_client
        self.config = config or load_dhan_limits()
        self.key_prefix = key_prefix
        self.ttl_seconds = ttl_seconds
        # Register Lua script
        self._script: Any = self.redis.register_script(REDIS_TOKEN_BUCKET_LUA)

    def _keys_for_category(self, category: str) -> tuple[str, str]:
        tokens_key = f"{self.key_prefix}:tokens:{category}"
        last_key = f"{self.key_prefix}:last:{category}"
        return tokens_key, last_key

    def try_acquire(self, category: str, cost: float = 1.0) -> bool:
        """Attempt immediate token acquisition via Lua script."""
        spec = self.config.get_rate_limit(category)
        tokens_key, last_key = self._keys_for_category(category)

        res = self._script(
            keys=[tokens_key, last_key],
            args=[cost, float(spec.burst), float(spec.rate), self.ttl_seconds],
        )
        return bool(res[0] == 1)

    def acquire(self, category: str, cost: float = 1.0, timeout: float = 30.0) -> float:
        """Acquire token(s) from Redis, applying jittered backoff on rate-limit contention."""
        spec = self.config.get_rate_limit(category)
        tokens_key, last_key = self._keys_for_category(category)
        start_time = time.monotonic()
        total_waited = 0.0

        while True:
            res = self._script(
                keys=[tokens_key, last_key],
                args=[cost, float(spec.burst), float(spec.rate), self.ttl_seconds],
            )
            allowed = int(res[0])
            wait_sec = float(res[1])

            if allowed == 1:
                return total_waited

            elapsed = time.monotonic() - start_time
            if elapsed + wait_sec > timeout:
                raise DhanRateLimitError(
                    f"Distributed rate limit timed out for '{category}' after {elapsed:.2f}s "
                    f"(wait: {wait_sec:.2f}s, timeout: {timeout}s)",
                    details={"retry_after": int(wait_sec) + 1},
                )

            # Apply backoff jitter
            jitter = (
                random.uniform(-self.config.backoff.jitter_ratio, self.config.backoff.jitter_ratio)
                * wait_sec
            )
            sleep_duration = min(
                self.config.backoff.max_delay_seconds,
                max(self.config.backoff.base_delay_seconds, wait_sec + jitter),
            )

            time.sleep(sleep_duration)
            total_waited = time.monotonic() - start_time


def get_dhan_rate_limiter(
    redis_client: Redis | None = None,
    config: DhanLimitsConfig | None = None,
) -> TokenBucket:
    """Construct rate limiter with Redis/Valkey if available, falling back to in-memory."""
    active_config = config or load_dhan_limits()

    if redis_client is not None:
        try:
            redis_client.ping()
            return RedisTokenBucket(redis_client, active_config)
        except Exception as err:
            logger.warning(
                "Failed connecting to provided Redis client: %s. Using in-memory limiter.",
                err,
            )
            return InMemoryTokenBucket(active_config)

    settings = get_settings()
    try:
        client: Redis = redis.from_url(  # type: ignore[no-untyped-call]
            settings.get_redis_dsn(),
            decode_responses=True,
            socket_timeout=1.0,
            socket_connect_timeout=1.0,
        )
        client.ping()
        return RedisTokenBucket(client, active_config)
    except Exception as err:
        logger.info(
            "Redis/Valkey service not reachable (%s). Initializing InMemoryTokenBucket.",
            err,
        )
        return InMemoryTokenBucket(active_config)
