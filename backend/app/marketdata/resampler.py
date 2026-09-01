"""Session-aware historical OHLCV bar resampler for Indian financial markets."""

from __future__ import annotations

import logging
from collections import defaultdict
from datetime import UTC, date, datetime, time, timedelta
from enum import StrEnum

import pyarrow as pa

from app.marketdata.calendar import (
    TradingCalendar,
    make_ist_datetime,
    to_ist,
    to_utc,
)
from app.warehouse.schema import BarRecord, bars_to_arrow_table

logger = logging.getLogger(__name__)


class Timeframe(StrEnum):
    """Supported bar timeframes."""

    M1 = "1m"
    M3 = "3m"
    M5 = "5m"
    M15 = "15m"
    M25 = "25m"
    M30 = "30m"
    H1 = "60m"
    D1 = "1d"
    W1 = "1w"


class PartialBarPolicy(StrEnum):
    """Handling strategy for incomplete end-of-session buckets."""

    EMIT_PARTIAL = "emit_partial"
    DROP_INCOMPLETE = "drop_incomplete"


def parse_timeframe(tf: str | Timeframe) -> Timeframe:
    """Normalize and validate timeframe string or enum."""
    if isinstance(tf, Timeframe):
        return tf

    clean = str(tf).strip().lower()
    mapping = {
        "1m": Timeframe.M1,
        "3m": Timeframe.M3,
        "5m": Timeframe.M5,
        "15m": Timeframe.M15,
        "25m": Timeframe.M25,
        "30m": Timeframe.M30,
        "60m": Timeframe.H1,
        "1h": Timeframe.H1,
        "1d": Timeframe.D1,
        "d": Timeframe.D1,
        "daily": Timeframe.D1,
        "1w": Timeframe.W1,
        "w": Timeframe.W1,
        "weekly": Timeframe.W1,
    }
    if clean in mapping:
        return mapping[clean]
    raise ValueError(f"Unsupported timeframe: {tf}")


class BarResampler:
    """Resamples 1m historical OHLCV bars into session-aligned higher timeframes."""

    def __init__(self, calendar: TradingCalendar | None = None) -> None:
        self.calendar = calendar or TradingCalendar()

    def resample_bars(
        self,
        bars: list[BarRecord],
        timeframe: str | Timeframe,
        policy: PartialBarPolicy = PartialBarPolicy.EMIT_PARTIAL,
        segment: str = "NSE_EQ",
    ) -> list[BarRecord]:
        """Resample a chronological list of 1m BarRecord models into the target timeframe."""
        if not bars:
            return []

        tf = parse_timeframe(timeframe)
        if tf == Timeframe.M1:
            return sorted(bars, key=lambda b: b.timestamp)

        sorted_bars = sorted(bars, key=lambda b: b.timestamp)

        if tf == Timeframe.D1:
            return self._resample_daily(sorted_bars, segment=segment)
        elif tf == Timeframe.W1:
            return self._resample_weekly(sorted_bars, segment=segment)
        else:
            minutes = self._timeframe_to_minutes(tf)
            return self._resample_intraday(
                sorted_bars,
                interval_minutes=minutes,
                policy=policy,
                segment=segment,
            )

    def _timeframe_to_minutes(self, tf: Timeframe) -> int:
        """Convert intraday timeframe to integer minutes."""
        mapping = {
            Timeframe.M3: 3,
            Timeframe.M5: 5,
            Timeframe.M15: 15,
            Timeframe.M25: 25,
            Timeframe.M30: 30,
            Timeframe.H1: 60,
        }
        if tf not in mapping:
            raise ValueError(f"Timeframe {tf} is not an intraday minute timeframe")
        return mapping[tf]

    def _resample_intraday(
        self,
        bars: list[BarRecord],
        interval_minutes: int,
        policy: PartialBarPolicy,
        segment: str,
    ) -> list[BarRecord]:
        """Resample 1m bars aligned to the session opening time (e.g. 09:15 IST)."""
        # Group bars by date in IST
        days_map: dict[date, list[BarRecord]] = defaultdict(list)
        for b in bars:
            dt_ist = to_ist(b.timestamp)
            days_map[dt_ist.date()].append(b)

        result: list[BarRecord] = []

        for d, day_bars in sorted(days_map.items()):
            session_bounds = self.calendar.get_session_bounds_utc(d, segment=segment)
            if not session_bounds:
                # Fallback to standard 09:15 IST opening
                sess_start_utc = make_ist_datetime(d, time(9, 15))
                sess_end_utc = make_ist_datetime(d, time(15, 30))
            else:
                sess_start_utc, sess_end_utc = session_bounds[0]

            # Map bars into discrete session-relative buckets
            bucket_map: dict[int, list[BarRecord]] = defaultdict(list)
            for b in day_bars:
                ts_utc = to_utc(b.timestamp)
                if ts_utc < sess_start_utc or ts_utc > sess_end_utc:
                    continue
                diff_minutes = int((ts_utc - sess_start_utc).total_seconds() // 60)
                bucket_index = diff_minutes // interval_minutes
                bucket_map[bucket_index].append(b)

            for b_idx in sorted(bucket_map.keys()):
                b_bars = bucket_map[b_idx]
                if not b_bars:
                    continue

                bucket_start_utc = sess_start_utc + timedelta(minutes=b_idx * interval_minutes)
                bucket_end_utc = bucket_start_utc + timedelta(minutes=interval_minutes)

                # Check partial bar policy for final bucket
                if bucket_end_utc > sess_end_utc:
                    if (
                        policy == PartialBarPolicy.DROP_INCOMPLETE
                        and len(b_bars) < interval_minutes
                    ):
                        continue

                b_bars.sort(key=lambda b: b.timestamp)
                agg_bar = BarRecord(
                    timestamp=bucket_start_utc,
                    exchange_segment=b_bars[0].exchange_segment,
                    security_id=b_bars[0].security_id,
                    symbol=b_bars[0].symbol,
                    open=b_bars[0].open,
                    high=max(b.high for b in b_bars),
                    low=min(b.low for b in b_bars),
                    close=b_bars[-1].close,
                    volume=sum(b.volume for b in b_bars),
                    open_interest=b_bars[-1].open_interest,
                )
                result.append(agg_bar)

        return result

    def _resample_daily(self, bars: list[BarRecord], segment: str) -> list[BarRecord]:
        """Aggregate 1m intraday bars into 1-day daily bars."""
        days_map: dict[date, list[BarRecord]] = defaultdict(list)
        for b in bars:
            dt_ist = to_ist(b.timestamp)
            days_map[dt_ist.date()].append(b)

        result: list[BarRecord] = []
        for d, day_bars in sorted(days_map.items()):
            if not day_bars:
                continue

            day_bars.sort(key=lambda b: b.timestamp)
            session_bounds = self.calendar.get_session_bounds_utc(d, segment=segment)
            ts_start = session_bounds[0][0] if session_bounds else day_bars[0].timestamp

            agg_bar = BarRecord(
                timestamp=ts_start,
                exchange_segment=day_bars[0].exchange_segment,
                security_id=day_bars[0].security_id,
                symbol=day_bars[0].symbol,
                open=day_bars[0].open,
                high=max(b.high for b in day_bars),
                low=min(b.low for b in day_bars),
                close=day_bars[-1].close,
                volume=sum(b.volume for b in day_bars),
                open_interest=day_bars[-1].open_interest,
            )
            result.append(agg_bar)

        return result

    def _resample_weekly(self, bars: list[BarRecord], segment: str) -> list[BarRecord]:
        """Aggregate 1m intraday bars into 1-week bars."""
        week_map: dict[tuple[int, int], list[BarRecord]] = defaultdict(list)
        for b in bars:
            dt_ist = to_ist(b.timestamp)
            iso_year, iso_week, _ = dt_ist.isocalendar()
            week_map[(iso_year, iso_week)].append(b)

        result: list[BarRecord] = []
        for _, week_bars in sorted(week_map.items()):
            if not week_bars:
                continue

            week_bars.sort(key=lambda b: b.timestamp)
            first_day = to_ist(week_bars[0].timestamp).date()
            session_bounds = self.calendar.get_session_bounds_utc(first_day, segment=segment)
            ts_start = session_bounds[0][0] if session_bounds else week_bars[0].timestamp

            agg_bar = BarRecord(
                timestamp=ts_start,
                exchange_segment=week_bars[0].exchange_segment,
                security_id=week_bars[0].security_id,
                symbol=week_bars[0].symbol,
                open=week_bars[0].open,
                high=max(b.high for b in week_bars),
                low=min(b.low for b in week_bars),
                close=week_bars[-1].close,
                volume=sum(b.volume for b in week_bars),
                open_interest=week_bars[-1].open_interest,
            )
            result.append(agg_bar)

        return result

    def resample_table(
        self,
        table: pa.Table,
        timeframe: str | Timeframe,
        policy: PartialBarPolicy = PartialBarPolicy.EMIT_PARTIAL,
        segment: str = "NSE_EQ",
    ) -> pa.Table:
        """Convenience method to resample a PyArrow Table into a resampled PyArrow Table."""
        if table.num_rows == 0:
            return table

        bars: list[BarRecord] = []
        pydict = table.to_pydict()
        timestamps = pydict["timestamp"]
        segments = pydict["exchange_segment"]
        security_ids = pydict["security_id"]
        symbols = pydict["symbol"]
        opens = pydict["open"]
        highs = pydict["high"]
        lows = pydict["low"]
        closes = pydict["close"]
        volumes = pydict["volume"]
        open_interests = pydict["open_interest"]

        for i in range(table.num_rows):
            ts = timestamps[i]
            if isinstance(ts, (int, float)):
                ts_dt = datetime.fromtimestamp(ts / 1000.0, tz=UTC)
            elif isinstance(ts, datetime):
                ts_dt = ts if ts.tzinfo is not None else ts.replace(tzinfo=UTC)
            else:
                ts_dt = datetime.now(UTC)

            bars.append(
                BarRecord(
                    timestamp=ts_dt,
                    exchange_segment=str(segments[i]),
                    security_id=str(security_ids[i]),
                    symbol=str(symbols[i]),
                    open=float(opens[i]),
                    high=float(highs[i]),
                    low=float(lows[i]),
                    close=float(closes[i]),
                    volume=int(volumes[i]),
                    open_interest=int(open_interests[i]),
                )
            )

        resampled = self.resample_bars(
            bars=bars,
            timeframe=timeframe,
            policy=policy,
            segment=segment,
        )
        return bars_to_arrow_table(resampled)
