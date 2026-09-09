"""Expand the agreed backfill tiers into concrete queue jobs.

The tier order encodes what becomes back-testable first, not just what is cheapest:
indices and index options land within days, while the F&O stock-option tier - roughly
85% of the total API spend - runs last and in the background.

    1  index spot            1-minute, 5 years            ~1,100 calls
    2  index options         ATM+/-10, CE+PE, week+month  ~10,300 calls
    3  index futures         active contracts only        ~40 calls
    4  F&O stocks (cash)     1-minute, 5 years            ~4,600 calls
    5  F&O stock options     ATM+/-5, CE+PE, monthly      ~99,000 calls
    6  F&O stock futures     active contracts only        ~1,300 calls
    7  MCX commodities       active futures contracts     ~150 calls
    8  all other stocks      daily EOD only               ~4,000 calls (separate budget)

Tier 8 uses charts/historical, which has its own 7,000/day allowance, so it costs
nothing against the intraday grind and can run concurrently from day one.

Two limits are inherent to the vendor rather than choices made here: expired futures
contracts leave the scrip master, so only currently-listed contracts can be back-filled;
and charts/rollingoption serves NSE_FNO and BSE_FNO only, so MCX options have no history
at all. Both gaps are filled going forward by live capture (F1.11).
"""

from __future__ import annotations

import calendar
import logging
from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.engine import Engine

from app.dhan.instruments import instrument_table
from app.worker.backfill_queue import JobSpec
from app.worker.minute_backfill import MAX_INTRADAY_WINDOW_DAYS
from app.worker.options_backfill import (
    INDEX_MAX_STRIKES,
    MAX_OPTIONS_WINDOW_DAYS,
    STOCK_MAX_STRIKES,
)

logger = logging.getLogger(__name__)

# Per-dataset history depth. The published docs say "last 5 years" for both
# charts/intraday and charts/rollingoption, but probing the live API shows 1-minute
# NIFTY data going back to roughly 2017-07 (2017-01 returns nothing, 2017-07 returns a
# full 7,875-bar month). charts/historical serves daily data from inception - 2010
# returns a full 251-session year.
#
# Intraday is therefore requested for the full depth rather than the documented five
# years. Months before a symbol's history begins come back empty, which is recorded as
# a terminal "empty" window and shown in the Historic Data Report - so the report ends
# up stating exactly where each symbol's history actually starts, instead of that being
# a guess.
DAILY_HISTORY_YEARS = 10
INTRADAY_HISTORY_YEARS = 10
OPTIONS_HISTORY_YEARS = 5

# Kept for callers that want a single default.
HISTORY_YEARS = INTRADAY_HISTORY_YEARS

TIER_INDEX_SPOT = 1
TIER_INDEX_OPTIONS = 2
TIER_INDEX_FUTURES = 3
TIER_FNO_STOCKS = 4
TIER_STOCK_OPTIONS = 5
TIER_STOCK_FUTURES = 6
TIER_MCX = 7
TIER_OTHER_STOCKS_DAILY = 8

# Underlyings with a listed option chain deep enough for ATM+/-10.
INDEX_OPTION_UNDERLYINGS: tuple[tuple[str, str], ...] = (
    ("NIFTY", "NSE_FNO"),
    ("BANKNIFTY", "NSE_FNO"),
    ("FINNIFTY", "NSE_FNO"),
    ("MIDCPNIFTY", "NSE_FNO"),
    ("SENSEX", "BSE_FNO"),
    ("BANKEX", "BSE_FNO"),
)

# Weeklies exist for index chains; single-stock options are monthly only.
# charts/rollingoption requires drvOptionType and returns only that leg, so each
# strike costs one call per side rather than one call for the pair.
OPTION_TYPES: tuple[str, ...] = ("CALL", "PUT")

INDEX_EXPIRY_FLAGS: tuple[str, ...] = ("WEEK", "MONTH")
STOCK_EXPIRY_FLAGS: tuple[str, ...] = ("MONTH",)


@dataclass(frozen=True)
class UniverseCounts:
    """How many jobs each tier expanded into, for cost estimation before enqueueing."""

    jobs_by_tier: dict[int, int]

    @property
    def total_jobs(self) -> int:
        return sum(self.jobs_by_tier.values())


def history_years_for(dataset: str) -> int:
    """How far back to request for a dataset."""
    if dataset == "daily":
        return DAILY_HISTORY_YEARS
    if dataset == "options":
        return OPTIONS_HISTORY_YEARS
    return INTRADAY_HISTORY_YEARS


def default_history_start(today: date | None = None, dataset: str = "intraday") -> date:
    """Earliest date to request for a dataset."""
    ref = today or date.today()
    return ref - timedelta(days=365 * history_years_for(dataset))


def month_windows(start: date, end: date) -> list[tuple[date, date]]:
    """Split a range into calendar months, clipped to the requested bounds.

    Calendar months rather than maximal 90/45-day windows, for two reasons.

    The warehouse managers write one Parquet file per (symbol, year, month). Two
    windows landing in the same month therefore collide on the same partition path,
    and the later one supersedes the earlier - silently losing bars. A month-sized
    window maps to exactly one file, so that cannot happen.

    It also makes coverage reportable: "2022-03 downloaded, 2022-04 missing" is a
    fact about a window, not an interval that has to be reconstructed. Dhan's own
    archive is corrupt for roughly 2021-10 to 2022-05, so per-month status is how a
    usable range gets established at all.

    The cost is more calls - a month is under both the 90-day intraday and 45-day
    rolling-option maxima - which the 100,000/day Data API budget absorbs.
    """
    if start > end:
        raise ValueError(f"start_date ({start}) cannot be after end_date ({end})")

    windows: list[tuple[date, date]] = []
    cursor = date(start.year, start.month, 1)
    while cursor <= end:
        last_day = calendar.monthrange(cursor.year, cursor.month)[1]
        month_end = date(cursor.year, cursor.month, last_day)
        windows.append((max(cursor, start), min(month_end, end)))
        cursor = month_end + timedelta(days=1)
    return windows


def intraday_windows(spec: JobSpec) -> list[tuple[date, date]]:
    """One window per calendar month; well inside the 90-day API maximum."""
    assert MAX_INTRADAY_WINDOW_DAYS >= 31
    return month_windows(spec.start_date, spec.end_date)


def option_windows(spec: JobSpec) -> list[tuple[date, date]]:
    """One window per calendar month; well inside the 45-day API maximum."""
    assert MAX_OPTIONS_WINDOW_DAYS >= 31
    return month_windows(spec.start_date, spec.end_date)


def daily_windows(spec: JobSpec) -> list[tuple[date, date]]:
    """Daily history is unwindowed: charts/historical serves since inception."""
    return [(spec.start_date, spec.end_date)]


def windows_for(spec: JobSpec) -> list[tuple[date, date]]:
    """Pick the window size that matches the endpoint this job will use."""
    if spec.dataset == "options":
        return option_windows(spec)
    if spec.dataset == "daily":
        return daily_windows(spec)
    return intraday_windows(spec)


def _split(start: date, end: date, max_days: int) -> list[tuple[date, date]]:
    if start > end:
        raise ValueError(f"start_date ({start}) cannot be after end_date ({end})")
    windows: list[tuple[date, date]] = []
    cursor = start
    while cursor <= end:
        stop = min(cursor + timedelta(days=max_days - 1), end)
        windows.append((cursor, stop))
        cursor = stop + timedelta(days=1)
    return windows


def strike_offsets(is_index: bool) -> list[int]:
    """ATM-relative offsets to collect, per the F1.4 coverage band."""
    limit = INDEX_MAX_STRIKES if is_index else STOCK_MAX_STRIKES
    return list(range(-limit, limit + 1))


class UniverseBuilder:
    """Turns the instrument master into tiered job specifications."""

    def __init__(
        self,
        engine: Engine,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> None:
        self.engine = engine
        self.end_date = end_date or date.today()
        # An explicit start_date pins every dataset; otherwise each gets its own depth.
        self.explicit_start = start_date
        self.start_date = start_date or default_history_start(self.end_date, "intraday")

    def start_for(self, dataset: str) -> date:
        """Start date for a dataset, honouring an explicit override."""
        if self.explicit_start is not None:
            return self.explicit_start
        return default_history_start(self.end_date, dataset)

    # ------------------------------------------------------------------ tiers

    def build(self, tiers: Sequence[int] | None = None) -> list[JobSpec]:
        """Expand the requested tiers (all of them by default) into job specs."""
        wanted = set(tiers) if tiers else set(range(1, 9))
        specs: list[JobSpec] = []

        builders = {
            TIER_INDEX_SPOT: self.tier_index_spot,
            TIER_INDEX_OPTIONS: self.tier_index_options,
            TIER_INDEX_FUTURES: self.tier_index_futures,
            TIER_FNO_STOCKS: self.tier_fno_stocks,
            TIER_STOCK_OPTIONS: self.tier_stock_options,
            TIER_STOCK_FUTURES: self.tier_stock_futures,
            TIER_MCX: self.tier_mcx,
            TIER_OTHER_STOCKS_DAILY: self.tier_other_stocks_daily,
        }
        for tier in sorted(wanted):
            builder = builders.get(tier)
            if builder is None:
                raise ValueError(f"Unknown backfill tier: {tier}")
            specs.extend(builder())

        return specs

    def tier_index_spot(self) -> list[JobSpec]:
        """1-minute history for every index, plus its daily series."""
        specs: list[JobSpec] = []
        for row in self._instruments(segments=["IDX_I"]):
            specs.append(
                self._spec(
                    TIER_INDEX_SPOT,
                    "intraday",
                    row,
                    interval="1",
                    instrument_type="INDEX",
                    priority=10,
                )
            )
            specs.append(
                self._spec(
                    TIER_INDEX_SPOT,
                    "daily",
                    row,
                    interval="D",
                    instrument_type="INDEX",
                    priority=10,
                )
            )
        return specs

    def tier_index_options(self) -> list[JobSpec]:
        """ATM+/-10 for each index chain, both expiry cadences. One job per offset."""
        known = {(r["symbol"], r["exchange_segment"]): r for r in self._instruments()}
        specs: list[JobSpec] = []

        for symbol, segment in INDEX_OPTION_UNDERLYINGS:
            row = known.get((symbol, segment)) or self._lookup_underlying(symbol)
            if row is None:
                logger.warning(
                    "Index option underlying %s not in instrument master; skipping. "
                    "Sync the scrip master first (python -m app.dhan.sync_master).",
                    symbol,
                )
                continue

            for flag in INDEX_EXPIRY_FLAGS:
                for offset in strike_offsets(is_index=True):
                    for option_type in OPTION_TYPES:
                        specs.append(
                            self._spec(
                                TIER_INDEX_OPTIONS,
                                "options",
                                row,
                                interval="1",
                                instrument_type="OPTIDX",
                                exchange_segment=segment,
                                underlying_symbol=symbol,
                                expiry_flag=flag,
                                expiry_code=1,
                                strike_offset=offset,
                                option_type=option_type,
                                # Collect ATM outwards; near-the-money matters most.
                                priority=20 + abs(offset),
                            )
                        )
        return specs

    def tier_index_futures(self) -> list[JobSpec]:
        """Currently-listed index futures. Expired contracts are unobtainable."""
        return [
            self._spec(TIER_INDEX_FUTURES, "intraday", row, interval="1", priority=30)
            for row in self._instruments(segments=["NSE_FNO", "BSE_FNO"], types=["FUTIDX"])
        ]

    def tier_fno_stocks(self) -> list[JobSpec]:
        """1-minute cash history for underlyings that have a derivatives chain."""
        return [
            self._spec(
                TIER_FNO_STOCKS,
                "intraday",
                row,
                interval="1",
                instrument_type="EQUITY",
                priority=40,
            )
            for row in self._fno_underlyings()
        ]

    def tier_stock_options(self) -> list[JobSpec]:
        """ATM+/-5 monthly chains for every F&O stock. The bulk of the API spend."""
        specs: list[JobSpec] = []
        for row in self._fno_underlyings():
            for flag in STOCK_EXPIRY_FLAGS:
                for offset in strike_offsets(is_index=False):
                    for option_type in OPTION_TYPES:
                        specs.append(
                            self._spec(
                                TIER_STOCK_OPTIONS,
                                "options",
                                row,
                                interval="1",
                                instrument_type="OPTSTK",
                                exchange_segment="NSE_FNO",
                                underlying_symbol=str(row["symbol"]),
                                expiry_flag=flag,
                                expiry_code=1,
                                strike_offset=offset,
                                option_type=option_type,
                                priority=50 + abs(offset),
                            )
                        )
        return specs

    def tier_stock_futures(self) -> list[JobSpec]:
        """Currently-listed stock futures; the rest accumulates from live capture."""
        return [
            self._spec(TIER_STOCK_FUTURES, "intraday", row, interval="1", priority=60)
            for row in self._instruments(segments=["NSE_FNO"], types=["FUTSTK"])
        ]

    def tier_mcx(self) -> list[JobSpec]:
        """Active MCX futures. MCX options have no rollingoption support at all."""
        specs: list[JobSpec] = []
        for row in self._instruments(segments=["MCX_COMM"]):
            specs.append(self._spec(TIER_MCX, "intraday", row, interval="1", priority=70))
            specs.append(self._spec(TIER_MCX, "daily", row, interval="D", priority=70))
        return specs

    def tier_other_stocks_daily(self) -> list[JobSpec]:
        """Daily EOD for every listed stock. Separate budget, so effectively free."""
        return [
            self._spec(
                TIER_OTHER_STOCKS_DAILY,
                "daily",
                row,
                interval="D",
                instrument_type="EQUITY",
                priority=80,
            )
            for row in self._instruments(segments=["NSE_EQ", "BSE_EQ"])
        ]

    # ---------------------------------------------------------------- helpers

    def estimate(self, tiers: Sequence[int] | None = None) -> UniverseCounts:
        """Count jobs per tier without enqueueing, for a cost check before committing."""
        counts: dict[int, int] = {}
        for spec in self.build(tiers):
            counts[spec.tier] = counts.get(spec.tier, 0) + 1
        return UniverseCounts(jobs_by_tier=counts)

    def estimate_calls(self, tiers: Sequence[int] | None = None) -> int:
        """Total API calls the requested tiers would cost, counting every window."""
        return sum(len(windows_for(spec)) for spec in self.build(tiers))

    def _spec(
        self,
        tier: int,
        dataset: str,
        row: dict[str, object],
        *,
        interval: str,
        instrument_type: str | None = None,
        exchange_segment: str | None = None,
        underlying_symbol: str | None = None,
        expiry_flag: str | None = None,
        expiry_code: int | None = None,
        strike_offset: int | None = None,
        option_type: str | None = None,
        priority: int = 100,
    ) -> JobSpec:
        return JobSpec(
            tier=tier,
            dataset=dataset,
            exchange_segment=exchange_segment or str(row["exchange_segment"]),
            security_id=str(row["security_id"]),
            symbol=str(row["symbol"]),
            interval=interval,
            start_date=self.start_for(dataset),
            end_date=self.end_date,
            underlying_symbol=underlying_symbol,
            instrument_type=instrument_type or str(row.get("instrument_type") or "EQUITY"),
            expiry_flag=expiry_flag,
            expiry_code=expiry_code,
            strike_offset=strike_offset,
            option_type=option_type,
            priority=priority,
        )

    def _instruments(
        self,
        segments: Sequence[str] | None = None,
        types: Sequence[str] | None = None,
    ) -> list[dict[str, object]]:
        """Distinct tradable series from the instrument master."""
        t = instrument_table
        stmt = select(
            t.c.security_id,
            t.c.exchange_segment,
            t.c.symbol,
            t.c.instrument_type,
            t.c.underlying_id,
        ).where(t.c.is_active.is_(True))
        if segments:
            stmt = stmt.where(t.c.exchange_segment.in_(list(segments)))
        if types:
            stmt = stmt.where(t.c.instrument_type.in_(list(types)))

        with self.engine.connect() as conn:
            rows = [dict(r) for r in conn.execute(stmt).mappings()]

        # One job per symbol; the master lists a row per contract for derivatives.
        seen: set[tuple[str, str]] = set()
        unique: list[dict[str, object]] = []
        for row in rows:
            key = (str(row["symbol"]), str(row["exchange_segment"]))
            if key in seen:
                continue
            seen.add(key)
            unique.append(row)
        return unique

    def _fno_underlyings(self) -> list[dict[str, object]]:
        """Cash-segment rows for symbols that also have a derivatives contract."""
        derivative_symbols = {
            str(r["symbol"])
            for r in self._instruments(segments=["NSE_FNO"], types=["FUTSTK", "OPTSTK"])
        }
        if not derivative_symbols:
            return []
        return [
            row
            for row in self._instruments(segments=["NSE_EQ"])
            if str(row["symbol"]) in derivative_symbols
        ]

    def _lookup_underlying(self, symbol: str) -> dict[str, object] | None:
        for row in self._instruments():
            if str(row["symbol"]).upper() == symbol.upper():
                return row
        return None


def iter_specs(specs: Sequence[JobSpec]) -> Iterator[JobSpec]:
    """Yield specs in claim order, so a partial enqueue still front-loads tier 1."""
    yield from sorted(specs, key=lambda s: (s.tier, s.priority, s.symbol))
