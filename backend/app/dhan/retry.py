"""Bounded retry policy for Dhan REST requests, with Retry-After support.

Retries are driven from :class:`app.dhan.client.DhanRestClient._request` rather than
from the transport, so that every attempt re-acquires a rate-limiter token. Retrying
inside the transport would issue API calls the token bucket never counted, which would
silently overrun the documented per-day budgets in ``config/dhan_limits.yaml``.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime

from app.dhan.limits_config import load_dhan_limits

# Status codes worth a second attempt. 429 is included because Dhan may reject a call
# the local bucket believed was in budget (clock skew, or usage from another process).
RETRYABLE_STATUS_CODES: frozenset[int] = frozenset({429, 500, 502, 503, 504})

MAX_RETRY_AFTER_SECONDS = 120.0


@dataclass(frozen=True)
class RetryPolicy:
    """Bounded exponential backoff with jitter for transient Dhan failures."""

    max_attempts: int = 4
    base_delay_seconds: float = 0.5
    max_delay_seconds: float = 30.0
    jitter_ratio: float = 0.25

    def __post_init__(self) -> None:
        if self.max_attempts < 1:
            raise ValueError(f"max_attempts must be >= 1, got {self.max_attempts}")
        if self.base_delay_seconds <= 0:
            raise ValueError(f"base_delay_seconds must be > 0, got {self.base_delay_seconds}")
        if self.max_delay_seconds < self.base_delay_seconds:
            raise ValueError("max_delay_seconds must be >= base_delay_seconds")
        if not 0.0 <= self.jitter_ratio <= 1.0:
            raise ValueError(f"jitter_ratio must be in [0, 1], got {self.jitter_ratio}")

    @classmethod
    def from_limits_config(cls) -> RetryPolicy:
        """Build a policy seeded from the dated backoff block in dhan_limits.yaml."""
        backoff = load_dhan_limits().backoff
        return cls(jitter_ratio=backoff.jitter_ratio)

    def should_retry(self, attempt: int, status_code: int) -> bool:
        """Return True when this status is transient and attempts remain."""
        return attempt < self.max_attempts and status_code in RETRYABLE_STATUS_CODES

    def compute_delay(self, attempt: int, retry_after: float | None = None) -> float:
        """Return seconds to wait before ``attempt`` + 1, honouring Retry-After."""
        if retry_after is not None:
            # Server guidance wins, but never block a worker indefinitely.
            return min(max(retry_after, 0.0), MAX_RETRY_AFTER_SECONDS)

        raw = self.base_delay_seconds * (2.0 ** (attempt - 1))
        capped = min(raw, self.max_delay_seconds)
        jitter = capped * random.uniform(-self.jitter_ratio, self.jitter_ratio)
        return max(0.0, capped + jitter)


def parse_retry_after(headers: dict[str, str] | None, now: datetime | None = None) -> float | None:
    """Parse a Retry-After header in delta-seconds or HTTP-date form.

    Returns None when the header is absent or unparseable, so the caller falls back to
    exponential backoff rather than treating a malformed header as "retry immediately".
    """
    if not headers:
        return None

    raw = next(
        (v for k, v in headers.items() if k.lower() == "retry-after" and v is not None),
        None,
    )
    if raw is None:
        return None

    value = str(raw).strip()
    if not value:
        return None

    try:
        return max(0.0, float(value))
    except ValueError:
        pass

    try:
        when = parsedate_to_datetime(value)
    except TypeError, ValueError:
        return None
    if when is None:
        return None
    if when.tzinfo is None:
        when = when.replace(tzinfo=UTC)

    reference = now or datetime.now(UTC)
    return max(0.0, (when - reference).total_seconds())
