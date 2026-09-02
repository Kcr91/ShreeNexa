"""Session-aware live one-minute bar builder merged onto warehouse history."""

from __future__ import annotations

import logging
from collections import defaultdict
from datetime import UTC, datetime, timedelta

from pydantic import BaseModel

from app.marketdata.calendar import TradingCalendar, to_ist
from app.warehouse.schema import BarRecord

logger = logging.getLogger(__name__)


class LiveTick(BaseModel):
    """Input tick from live market data feed."""

    segment: str = "NSE_EQ"
    security_id: str
    symbol: str
    price: float
    volume: int = 0
    timestamp: datetime
    open_interest: int = 0
    sequence: int | None = None


class LiveMinuteBar(BaseModel):
    """Live 1-minute bar representation."""

    timestamp: datetime  # Minute bucket start in UTC
    segment: str
    security_id: str
    symbol: str
    open: float
    high: float
    low: float
    close: float
    volume: int
    open_interest: int = 0
    is_finalized: bool = False
    first_tick_time: datetime
    last_tick_time: datetime
    tick_count: int = 1


class LiveBarBuilder:
    """Constructs session-aware 1-minute bars from incoming ticks.

    Handles late, duplicate, and out-of-order ticks with grace window support.
    """

    def __init__(
        self,
        calendar: TradingCalendar | None = None,
        grace_period_sec: float = 15.0,
        enforce_session: bool = True,
        max_signatures_per_key: int = 500,
    ) -> None:
        self.calendar = calendar or TradingCalendar()
        self.grace_period_sec = grace_period_sec
        self.enforce_session = enforce_session
        self.max_signatures_per_key = max_signatures_per_key

        # Keyed by f"{segment}:{security_id}"
        self.active_bars: dict[str, LiveMinuteBar] = {}
        self.finalized_bars: dict[str, list[LiveMinuteBar]] = defaultdict(list)
        self.recent_signatures: dict[str, set[tuple[int, float, int, int | None]]] = defaultdict(
            set
        )

        # Telemetry metrics
        self.duplicate_ticks_count: int = 0
        self.out_of_order_ticks_count: int = 0
        self.dropped_late_ticks_count: int = 0
        self.processed_ticks_count: int = 0

    def _make_key(self, segment: str, security_id: str) -> str:
        return f"{segment}:{security_id}"

    def process_tick(self, tick: LiveTick) -> LiveMinuteBar | None:
        """Process a live tick and update or finalize 1-minute bars.

        Returns the updated bar (active or finalized).
        """
        # Ensure UTC tz
        ts = (
            tick.timestamp
            if tick.timestamp.tzinfo is not None
            else tick.timestamp.replace(tzinfo=UTC)
        )
        key = self._make_key(tick.segment, tick.security_id)

        # 1. Duplicate detection
        sig = (int(ts.timestamp() * 1000), tick.price, tick.volume, tick.sequence)
        if sig in self.recent_signatures[key]:
            self.duplicate_ticks_count += 1
            return self.active_bars.get(key)

        self.recent_signatures[key].add(sig)
        if len(self.recent_signatures[key]) > self.max_signatures_per_key:
            # Pop arbitrary to bound memory
            self.recent_signatures[key].pop()

        # 2. Session enforcement
        if self.enforce_session:
            dt_ist = to_ist(ts)
            bounds = self.calendar.get_session_bounds_utc(dt_ist.date(), segment=tick.segment)
            if bounds:
                session_start, session_end = bounds[0]
                if ts < session_start or ts >= session_end:
                    # Outside session
                    return None

        # 3. Bucket start timestamp (floor to minute)
        bucket_start = ts.replace(second=0, microsecond=0)
        self.processed_ticks_count += 1

        active = self.active_bars.get(key)

        # Case A: No active bar -> start a new one
        if active is None:
            new_bar = LiveMinuteBar(
                timestamp=bucket_start,
                segment=tick.segment,
                security_id=tick.security_id,
                symbol=tick.symbol,
                open=tick.price,
                high=tick.price,
                low=tick.price,
                close=tick.price,
                volume=tick.volume,
                open_interest=tick.open_interest,
                is_finalized=False,
                first_tick_time=ts,
                last_tick_time=ts,
                tick_count=1,
            )
            self.active_bars[key] = new_bar
            return new_bar

        # Case B: Tick belongs to current active minute bucket
        if bucket_start == active.timestamp:
            if ts < active.last_tick_time:
                self.out_of_order_ticks_count += 1

            active.high = max(active.high, tick.price)
            active.low = min(active.low, tick.price)
            active.volume += tick.volume
            active.tick_count += 1

            if ts <= active.first_tick_time:
                active.open = tick.price
                active.first_tick_time = ts

            if ts >= active.last_tick_time:
                active.close = tick.price
                active.last_tick_time = ts
                active.open_interest = tick.open_interest

            return active

        # Case C: Tick belongs to a future minute bucket -> finalize current and roll
        if bucket_start > active.timestamp:
            active.is_finalized = True
            self.finalized_bars[key].append(active)

            new_bar = LiveMinuteBar(
                timestamp=bucket_start,
                segment=tick.segment,
                security_id=tick.security_id,
                symbol=tick.symbol,
                open=tick.price,
                high=tick.price,
                low=tick.price,
                close=tick.price,
                volume=tick.volume,
                open_interest=tick.open_interest,
                is_finalized=False,
                first_tick_time=ts,
                last_tick_time=ts,
                tick_count=1,
            )
            self.active_bars[key] = new_bar
            return new_bar

        # Case D: Late tick belonging to a previous bucket (bucket_start < active.timestamp)
        # Check grace period against the closed bucket's end time
        bucket_end = bucket_start + timedelta(minutes=1)
        elapsed_late = (active.first_tick_time - bucket_end).total_seconds()
        if elapsed_late <= self.grace_period_sec and self.finalized_bars[key]:
            # Retroactively update matching finalized bar
            for finalized in reversed(self.finalized_bars[key]):
                if finalized.timestamp == bucket_start:
                    finalized.high = max(finalized.high, tick.price)
                    finalized.low = min(finalized.low, tick.price)
                    finalized.volume += tick.volume
                    finalized.tick_count += 1
                    if ts >= finalized.last_tick_time:
                        finalized.close = tick.price
                        finalized.last_tick_time = ts
                        finalized.open_interest = tick.open_interest
                    if ts <= finalized.first_tick_time:
                        finalized.open = tick.price
                        finalized.first_tick_time = ts
                    return finalized

        # Outside grace window or no matching finalized bar -> drop late tick
        self.dropped_late_ticks_count += 1
        return None

    def force_finalize_active(self, segment: str, security_id: str) -> LiveMinuteBar | None:
        """Force-finalize in-flight active bar (e.g. on market close or session end)."""
        key = self._make_key(segment, security_id)
        active = self.active_bars.pop(key, None)
        if active is not None:
            active.is_finalized = True
            self.finalized_bars[key].append(active)
        return active

    def get_completed_bars(self, segment: str, security_id: str) -> list[LiveMinuteBar]:
        """Return all finalized bars for the instrument."""
        key = self._make_key(segment, security_id)
        return list(self.finalized_bars[key])

    def get_active_bar(self, segment: str, security_id: str) -> LiveMinuteBar | None:
        """Return currently active in-flight bar for the instrument."""
        key = self._make_key(segment, security_id)
        return self.active_bars.get(key)


def merge_history_and_live(
    warehouse_bars: list[BarRecord],
    live_bars: list[LiveMinuteBar],
) -> list[BarRecord]:
    """Merge historical warehouse bars and live 1-minute bars into a continuous sequence.

    Invariants:
    1. Result is sorted strictly ascending by timestamp.
    2. Any overlapping timestamps are superseded by live bars.
    3. Volume and OHLC are preserved with no duplicates.
    """
    merged_map: dict[datetime, BarRecord] = {}

    for wb in warehouse_bars:
        ts = wb.timestamp if wb.timestamp.tzinfo is not None else wb.timestamp.replace(tzinfo=UTC)
        merged_map[ts] = wb

    for lb in live_bars:
        ts = lb.timestamp if lb.timestamp.tzinfo is not None else lb.timestamp.replace(tzinfo=UTC)
        # Live bar replaces historical record at same timestamp
        merged_map[ts] = BarRecord(
            timestamp=ts,
            exchange_segment=lb.segment,
            security_id=lb.security_id,
            symbol=lb.symbol,
            open=lb.open,
            high=lb.high,
            low=lb.low,
            close=lb.close,
            volume=lb.volume,
            open_interest=lb.open_interest,
        )

    # Return sorted by timestamp
    return sorted(merged_map.values(), key=lambda b: b.timestamp)
