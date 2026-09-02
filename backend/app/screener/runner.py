"""Point-in-Time Screener Execution Runner."""

from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import UTC, date, datetime
from typing import Any

from app.screener.models import (
    ScreenerDefinition,
    ScreenerMatch,
    ScreenerResult,
)
from app.strategy.compiler import VectorStrategyCompiler
from app.strategy.ir import (
    EntryRule,
    IndexUniverse,
    OrderSide,
    StaticUniverse,
    StrategyHorizon,
    StrategyIR,
    StrategyKind,
    StrategyType,
    WatchlistUniverse,
)
from app.warehouse.schema import BarRecord

logger = logging.getLogger(__name__)


class PointInTimeScreenerRunner:
    """Evaluates StrategyIR signal filters across historical universes at a point-in-time."""

    def __init__(
        self,
        bar_provider: Callable[[str, str, datetime, int], list[BarRecord]],
        index_resolver: Callable[[str, date], list[dict[str, str]]] | None = None,
    ) -> None:
        self.bar_provider = bar_provider
        self.index_resolver = index_resolver

    def run(self, screener: ScreenerDefinition) -> ScreenerResult:
        """Execute point-in-time screener against target universe as-of target timestamp."""
        as_of_dt = self._resolve_as_of_dt(screener.as_of)
        as_of_date = as_of_dt.date()

        warnings: list[str] = []
        instruments = self._resolve_universe(screener, as_of_date, warnings)

        # Build StrategyIR model for vector compilation
        strategy = StrategyIR(
            name=screener.name,
            kind=StrategyKind.STOCK,
            horizon=StrategyHorizon.SWING,
            strategy_type=StrategyType.TREND_FOLLOWING,
            universe=screener.universe,
            timeframe=screener.timeframe,
            indicators=screener.indicators,
            entries=[EntryRule(id="filter", side=OrderSide.BUY, when=screener.filter)],
            exits=[],
        )
        compiled = VectorStrategyCompiler.compile(strategy)

        matches: list[ScreenerMatch] = []
        evaluated_count = 0

        for inst in instruments:
            sec_id = inst.get("security_id", "")
            seg = inst.get("exchange_segment", inst.get("segment", "NSE_EQ"))
            symbol = inst.get("symbol", sec_id)

            # Load bars strictly <= as_of_dt to prevent lookahead
            bars = self.bar_provider(seg, sec_id, as_of_dt, screener.lookback_bars)
            if not bars:
                continue

            # Ensure sorted and strictly <= as_of_dt
            bars = [b for b in bars if b.timestamp <= as_of_dt]
            if not bars:
                continue

            evaluated_count += 1
            res = compiled.evaluate(bars)

            # Check if filter fired on the target as-of bar (last bar in point-in-time series)
            filter_signals = res.entry_signals.get("filter", [])
            if filter_signals and filter_signals[-1]:
                # Extract indicator values for the as-of bar
                last_ind_vals: dict[str, Any] = {}
                for k, v in res.indicator_values.items():
                    if isinstance(v, list) and v:
                        last_ind_vals[k] = v[-1]
                    else:
                        last_ind_vals[k] = v

                rank_val = self._compute_rank_value(screener, bars[-1], last_ind_vals)

                matches.append(
                    ScreenerMatch(
                        security_id=sec_id,
                        symbol=symbol,
                        exchange_segment=seg,
                        as_of=as_of_dt,
                        indicator_values=last_ind_vals,
                        rank_value=rank_val,
                    )
                )

        # Apply ranking if specified
        if screener.ranking:
            reverse = screener.ranking.direction == "desc"
            matches.sort(
                key=lambda m: (
                    m.rank_value
                    if m.rank_value is not None
                    else (float("-inf") if reverse else float("inf"))
                ),
                reverse=reverse,
            )

        # Apply limit if specified
        if screener.limit and screener.limit > 0:
            matches = matches[: screener.limit]

        return ScreenerResult(
            as_of=as_of_dt,
            matches=matches,
            total_universe_size=len(instruments),
            evaluated_count=evaluated_count,
            matched_count=len(matches),
            warnings=warnings,
        )

    def _resolve_as_of_dt(self, val: datetime | date | None) -> datetime:
        if isinstance(val, datetime):
            return val if val.tzinfo else val.replace(tzinfo=UTC)
        elif isinstance(val, date):
            return datetime(val.year, val.month, val.day, 15, 30, tzinfo=UTC)
        return datetime.now(tz=UTC)

    def _resolve_universe(
        self, screener: ScreenerDefinition, as_of_date: date, warnings: list[str]
    ) -> list[dict[str, str]]:
        universe = screener.universe
        if isinstance(universe, StaticUniverse):
            warnings.append(
                "Static universe evaluated: survivorship-bias may be present "
                "if constituent membership changed over historical periods."
            )
            return [
                {
                    "segment": inst.segment,
                    "security_id": inst.security_id,
                    "symbol": inst.security_id,
                }
                for inst in universe.instruments
            ]
        elif isinstance(universe, IndexUniverse):
            if self.index_resolver:
                try:
                    constituents = self.index_resolver(universe.index_name, as_of_date)
                    if not constituents:
                        warnings.append(
                            f"Survivorship-bias warning: Incomplete historical "
                            f"records for index '{universe.index_name}' as-of {as_of_date}."
                        )
                    return constituents
                except Exception as exc:
                    warnings.append(
                        f"Survivorship-bias warning: Failed resolving historical constituents "
                        f"for index '{universe.index_name}' as-of {as_of_date}: {exc}"
                    )
                    return []
            else:
                warnings.append(
                    f"Survivorship-bias warning: No historical index constituent resolver "
                    f"attached for '{universe.index_name}'."
                )
                return []
        elif isinstance(universe, WatchlistUniverse):
            warnings.append(
                f"Watchlist universe '{universe.watchlist_id}' evaluated: "
                f"historical point-in-time composition may vary."
            )
            return []
        return []

    def _compute_rank_value(
        self, screener: ScreenerDefinition, last_bar: BarRecord, last_ind_vals: dict[str, Any]
    ) -> float | None:
        if not screener.ranking:
            return None
        target = screener.ranking.by.lower()
        if target in last_ind_vals and isinstance(last_ind_vals[target], (int, float)):
            return float(last_ind_vals[target])
        if hasattr(last_bar, target):
            val = getattr(last_bar, target)
            if isinstance(val, (int, float)):
                return float(val)
        return None
