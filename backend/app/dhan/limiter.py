"""Distributed and in-memory token bucket rate limiters for Dhan REST API."""

from __future__ import annotations

import logging
import random
import threading
import time
from bisect import bisect_left
from collections import deque
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

# Atomic Lua script for Redis-backed token bucket with multi-window caps
REDIS_TOKEN_BUCKET_LUA = """
local redis_time = redis.call('TIME')
local now = tonumber(redis_time[1]) + (tonumber(redis_time[2]) / 1000000.0)

local cost = tonumber(ARGV[1])
local capacity = tonumber(ARGV[2])
local rate = tonumber(ARGV[3])
local ttl = tonumber(ARGV[4])
local per_min = tonumber(ARGV[5] or 0)
local per_hr = tonumber(ARGV[6] or 0)
local per_day = tonumber(ARGV[7] or 0)

local key_tokens = KEYS[1]
local key_last = KEYS[2]
local key_min = KEYS[3]
local key_hr = KEYS[4]
local key_day = KEYS[5]

-- 1. Check window counters
if per_min > 0 then
    local cur_min = tonumber(redis.call('GET', key_min) or '0')
    if cur_min + cost > per_min then
        local ttl_min = redis.call('TTL', key_min)
        local wait_sec = (ttl_min > 0) and ttl_min or 60.0
        return {0, wait_sec, 0}
    end
end

if per_hr > 0 then
    local cur_hr = tonumber(redis.call('GET', key_hr) or '0')
    if cur_hr + cost > per_hr then
        local ttl_hr = redis.call('TTL', key_hr)
        local wait_sec = (ttl_hr > 0) and ttl_hr or 3600.0
        return {0, wait_sec, 0}
    end
end

if per_day > 0 then
    local cur_day = tonumber(redis.call('GET', key_day) or '0')
    if cur_day + cost > per_day then
        local ttl_day = redis.call('TTL', key_day)
        local wait_sec = (ttl_day > 0) and ttl_day or 86400.0
        return {0, wait_sec, 0}
    end
end

-- 2. Token bucket replenishment
local current_tokens = tonumber(redis.call('GET', key_tokens))
local last_time = tonumber(redis.call('GET', key_last))

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
    redis.call('SETEX', key_tokens, ttl, tostring(current_tokens))
    redis.call('SETEX', key_last, ttl, tostring(last_time))

    -- Increment window counters
    if per_min > 0 then
        redis.call('INCRBY', key_min, cost)
        if redis.call('TTL', key_min) < 0 then
            redis.call('EXPIRE', key_min, 120)
        end
    end
    if per_hr > 0 then
        redis.call('INCRBY', key_hr, cost)
        if redis.call('TTL', key_hr) < 0 then
            redis.call('EXPIRE', key_hr, 7200)
        end
    end
    if per_day > 0 then
        redis.call('INCRBY', key_day, cost)
        if redis.call('TTL', key_day) < 0 then
            redis.call('EXPIRE', key_day, 172800)
        end
    end

    return {1, 0, current_tokens}
else
    local deficit = cost - current_tokens
    local wait_sec = deficit / rate
    redis.call('SETEX', key_tokens, ttl, tostring(current_tokens))
    redis.call('SETEX', key_last, ttl, tostring(last_time))
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

    def get_budget_usage(self, category: str) -> dict[str, Any]:
        """Return rate limit window usage metrics and 80% threshold alert state."""
        ...


class InMemoryTokenBucket:
    """Thread-safe in-memory token bucket with multi-window sliding timestamp enforcement."""

    def __init__(self, config: DhanLimitsConfig | None = None) -> None:
        self.config = config or load_dhan_limits()
        self._lock = threading.Lock()
        # category -> (tokens: float, last_update_time: float)
        self._state: dict[str, tuple[float, float]] = {}
        # category -> sliding deque of monotonic timestamps
        self._history: dict[str, deque[float]] = {}

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

    def _check_windows(self, category: str, now: float, cost: float) -> tuple[bool, float]:
        spec = self.config.get_rate_limit(category)
        history = self._history.setdefault(category, deque())
        cutoff_day = now - 86400.0
        while history and history[0] < cutoff_day:
            history.popleft()

        max_wait = 0.0
        cost_int = int(cost) if cost >= 1 else 1

        # 1. Per minute check
        if spec.per_minute is not None:
            cutoff_min = now - 60.0
            idx_min = bisect_left(history, cutoff_min)
            count_min = len(history) - idx_min
            if count_min + cost_int > spec.per_minute:
                excess = (count_min + cost_int) - spec.per_minute
                expire_idx = idx_min + excess - 1
                if 0 <= expire_idx < len(history):
                    wait_min = max(0.0, (history[expire_idx] + 60.0) - now)
                    if wait_min > max_wait:
                        max_wait = wait_min

        # 2. Per hour check
        if spec.per_hour is not None:
            cutoff_hr = now - 3600.0
            idx_hr = bisect_left(history, cutoff_hr)
            count_hr = len(history) - idx_hr
            if count_hr + cost_int > spec.per_hour:
                excess = (count_hr + cost_int) - spec.per_hour
                expire_idx = idx_hr + excess - 1
                if 0 <= expire_idx < len(history):
                    wait_hr = max(0.0, (history[expire_idx] + 3600.0) - now)
                    if wait_hr > max_wait:
                        max_wait = wait_hr

        # 3. Per day check
        if spec.per_day is not None:
            count_day = len(history)
            if count_day + cost_int > spec.per_day:
                excess = (count_day + cost_int) - spec.per_day
                expire_idx = excess - 1
                if 0 <= expire_idx < len(history):
                    wait_day = max(0.0, (history[expire_idx] + 86400.0) - now)
                    if wait_day > max_wait:
                        max_wait = wait_day

        if max_wait > 0.0:
            return False, max_wait
        return True, 0.0

    def try_acquire(self, category: str, cost: float = 1.0, *, now: float | None = None) -> bool:
        """Attempt to immediately consume tokens without sleeping."""
        cur_now = now if now is not None else time.monotonic()
        with self._lock:
            allowed, _ = self._check_windows(category, cur_now, cost)
            if not allowed:
                return False
            tokens, _rate, _cap = self._replenish(category, cur_now)
            if tokens >= cost:
                self._state[category] = (tokens - cost, cur_now)
                history = self._history.setdefault(category, deque())
                cost_int = int(cost) if cost >= 1 else 1
                for _ in range(cost_int):
                    history.append(cur_now)
                return True
            return False

    def acquire(self, category: str, cost: float = 1.0, timeout: float = 30.0) -> float:
        """Block until tokens are available or timeout expires."""
        start_time = time.monotonic()
        total_waited = 0.0

        while True:
            now = time.monotonic()
            with self._lock:
                allowed, win_wait = self._check_windows(category, now, cost)
                tokens, rate, _cap = self._replenish(category, now)
                token_wait = 0.0
                if tokens < cost:
                    deficit = cost - tokens
                    token_wait = deficit / rate if rate > 0 else 1.0

                wait_sec = max(win_wait, token_wait)
                if allowed and tokens >= cost:
                    self._state[category] = (tokens - cost, now)
                    history = self._history.setdefault(category, deque())
                    cost_int = int(cost) if cost >= 1 else 1
                    for _ in range(cost_int):
                        history.append(now)
                    return total_waited

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

    def get_budget_usage(self, category: str) -> dict[str, Any]:
        """Return rate limit window usage metrics and 80% threshold alert state."""
        spec = self.config.get_rate_limit(category)
        now = time.monotonic()
        with self._lock:
            history = self._history.get(category, deque())
            cutoff_day = now - 86400.0
            cutoff_hr = now - 3600.0
            cutoff_min = now - 60.0

            idx_day = bisect_left(history, cutoff_day)
            idx_hr = bisect_left(history, cutoff_hr)
            idx_min = bisect_left(history, cutoff_min)

            count_day = len(history) - idx_day
            count_hr = len(history) - idx_hr
            count_min = len(history) - idx_min

        limit_day = spec.per_day
        pct = (count_day / limit_day * 100.0) if limit_day else 0.0
        return {
            "category": category,
            "requests_last_minute": count_min,
            "limit_per_minute": spec.per_minute,
            "requests_last_hour": count_hr,
            "limit_per_hour": spec.per_hour,
            "requests_today": count_day,
            "limit_per_day": limit_day,
            "remaining_today": (limit_day - count_day) if limit_day else None,
            "used_pct_today": round(pct, 1),
            "alert_80_pct": pct >= 80.0,
        }


class RedisTokenBucket:
    """Distributed Redis-backed token bucket using atomic Lua script and multi-window counters."""

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

    def _keys_for_category(
        self, category: str, now_ts: int | None = None
    ) -> tuple[str, str, str, str, str]:
        prefix_tag = f"{{{self.key_prefix}:{category}}}"
        now_utc = now_ts if now_ts is not None else int(time.time())
        min_bucket = now_utc // 60
        hr_bucket = now_utc // 3600
        day_bucket = now_utc // 86400
        return (
            f"{prefix_tag}:tokens",
            f"{prefix_tag}:last",
            f"{prefix_tag}:min:{min_bucket}",
            f"{prefix_tag}:hr:{hr_bucket}",
            f"{prefix_tag}:day:{day_bucket}",
        )

    def try_acquire(self, category: str, cost: float = 1.0) -> bool:
        """Attempt immediate token acquisition via Lua script."""
        spec = self.config.get_rate_limit(category)
        keys = list(self._keys_for_category(category))

        res = self._script(
            keys=keys,
            args=[
                cost,
                float(spec.burst),
                float(spec.rate),
                self.ttl_seconds,
                spec.per_minute or 0,
                spec.per_hour or 0,
                spec.per_day or 0,
            ],
        )
        return bool(res[0] == 1)

    def acquire(self, category: str, cost: float = 1.0, timeout: float = 30.0) -> float:
        """Acquire token(s) from Redis, applying jittered backoff on rate-limit contention."""
        spec = self.config.get_rate_limit(category)
        keys = list(self._keys_for_category(category))
        start_time = time.monotonic()
        total_waited = 0.0

        while True:
            res = self._script(
                keys=keys,
                args=[
                    cost,
                    float(spec.burst),
                    float(spec.rate),
                    self.ttl_seconds,
                    spec.per_minute or 0,
                    spec.per_hour or 0,
                    spec.per_day or 0,
                ],
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

    def get_budget_usage(self, category: str) -> dict[str, Any]:
        """Return rate limit window usage metrics and 80% threshold alert state from Redis."""
        spec = self.config.get_rate_limit(category)
        keys = self._keys_for_category(category)
        try:
            raw_min = self.redis.get(keys[2])
            raw_hr = self.redis.get(keys[3])
            raw_day = self.redis.get(keys[4])
            count_min = int(str(raw_min)) if raw_min else 0
            count_hr = int(str(raw_hr)) if raw_hr else 0
            count_day = int(str(raw_day)) if raw_day else 0
        except Exception:
            count_min, count_hr, count_day = 0, 0, 0

        limit_day = spec.per_day
        pct = (count_day / limit_day * 100.0) if limit_day else 0.0
        return {
            "category": category,
            "requests_last_minute": count_min,
            "limit_per_minute": spec.per_minute,
            "requests_last_hour": count_hr,
            "limit_per_hour": spec.per_hour,
            "requests_today": count_day,
            "limit_per_day": limit_day,
            "remaining_today": (limit_day - count_day) if limit_day else None,
            "used_pct_today": round(pct, 1),
            "alert_80_pct": pct >= 80.0,
        }


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
