"""Token, cost, and latency accounting for runtime AI generation."""

from __future__ import annotations

from dataclasses import dataclass
from threading import Lock


@dataclass
class UsageSummary:
    """Summary of cumulative AI provider usage."""

    total_calls: int = 0
    total_tokens: int = 0
    total_cost_usd: float = 0.0
    avg_latency_ms: float = 0.0


class AIUsageAccounting:
    """Thread-safe ledger tracking token usage, costs, and call latencies."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._total_calls = 0
        self._total_tokens = 0
        self._total_cost_usd = 0.0
        self._latencies: list[float] = []

    def record_call(
        self,
        *,
        tokens_used: int,
        cost_usd: float,
        latency_ms: float,
    ) -> None:
        """Record a completed provider call."""
        with self._lock:
            self._total_calls += 1
            self._total_tokens += tokens_used
            self._total_cost_usd += cost_usd
            self._latencies.append(latency_ms)

    def get_summary(self) -> UsageSummary:
        """Return snapshot of cumulative usage metrics."""
        with self._lock:
            avg_lat = sum(self._latencies) / len(self._latencies) if self._latencies else 0.0
            return UsageSummary(
                total_calls=self._total_calls,
                total_tokens=self._total_tokens,
                total_cost_usd=round(self._total_cost_usd, 6),
                avg_latency_ms=round(avg_lat, 2),
            )

    def reset(self) -> None:
        """Reset the usage ledger (e.g. for testing)."""
        with self._lock:
            self._total_calls = 0
            self._total_tokens = 0
            self._total_cost_usd = 0.0
            self._latencies.clear()


# Global default accounting instance
usage_ledger = AIUsageAccounting()
