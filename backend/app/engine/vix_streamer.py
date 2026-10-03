"""India VIX Market Volatility Context Provider & Live Streamer."""

from __future__ import annotations

from datetime import datetime


class VixProvider:
    """Provides India VIX values at specific timestamps or live market feed."""

    def __init__(self, vix_table_cache: dict[datetime, float] | None = None) -> None:
        self._cache = vix_table_cache or {}

    def get_vix_at(self, timestamp: datetime) -> float:
        """Get India VIX reading for a specific timestamp (with fallback)."""
        if timestamp in self._cache:
            return round(self._cache[timestamp], 2)

        # Baseline Indian market historical VIX average ~14.50
        return 14.50

    def register_vix_tick(self, timestamp: datetime, vix_value: float) -> None:
        """Cache a live or backtest VIX candle reading."""
        self._cache[timestamp] = vix_value
