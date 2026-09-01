"""Continuous synthetic futures series generator with calendar, volume, and OI roll rules."""

from __future__ import annotations

import logging
from collections import defaultdict
from datetime import date, timedelta
from enum import StrEnum

import pyarrow as pa
from pydantic import BaseModel, ConfigDict

from app.marketdata.calendar import to_ist
from app.warehouse.schema import BarRecord, bars_to_arrow_table

logger = logging.getLogger(__name__)


class RollTrigger(StrEnum):
    """Supported trigger criteria for contract rolls."""

    CALENDAR = "CALENDAR"
    VOLUME = "VOLUME"
    OPEN_INTEREST = "OPEN_INTEREST"


class AdjustmentMethod(StrEnum):
    """Continuous price series adjustment policies."""

    UNADJUSTED = "UNADJUSTED"
    DIFFERENCE = "DIFFERENCE"
    RATIO = "RATIO"


class ContractMetadata(BaseModel):
    """Container for individual futures contract specifications and bars."""

    model_config = ConfigDict(frozen=True)

    symbol: str
    expiry_date: date
    bars: list[BarRecord]


class RollEvent(BaseModel):
    """Audit record capturing contract roll parameters and price reconciliation."""

    model_config = ConfigDict(frozen=True)

    roll_date: date
    from_symbol: str
    to_symbol: str
    old_close: float
    new_close: float
    spread: float
    ratio: float
    trigger_reason: str


class ContinuousFuturesGenerator:
    """Constructs stitched synthetic continuous futures curves with configurable roll rules."""

    def __init__(
        self,
        roll_trigger: RollTrigger = RollTrigger.CALENDAR,
        days_before_expiry: int = 0,
        adjustment_method: AdjustmentMethod = AdjustmentMethod.UNADJUSTED,
    ) -> None:
        self.roll_trigger = roll_trigger
        self.days_before_expiry = max(0, days_before_expiry)
        self.adjustment_method = adjustment_method

    def build_continuous_series(
        self,
        contracts: list[ContractMetadata],
        continuous_symbol: str = "NIFTY_F1",
    ) -> tuple[list[BarRecord], list[RollEvent]]:
        """Build continuous futures series and return stitched bars along with roll event audit."""
        if not contracts:
            return [], []

        # Sort contracts by expiry date
        sorted_contracts = sorted(contracts, key=lambda c: c.expiry_date)
        if len(sorted_contracts) == 1:
            # Single contract, no roll needed
            single_bars = [
                self._clone_bar_with_symbol(b, continuous_symbol) for b in sorted_contracts[0].bars
            ]
            return single_bars, []

        # Index bars by contract symbol and date
        bars_by_contract_and_date: dict[str, dict[date, list[BarRecord]]] = defaultdict(
            lambda: defaultdict(list)
        )
        all_dates_set: set[date] = set()

        for c in sorted_contracts:
            for b in c.bars:
                d = to_ist(b.timestamp).date()
                bars_by_contract_and_date[c.symbol][d].append(b)
                all_dates_set.add(d)

        all_dates = sorted(all_dates_set)
        roll_events: list[RollEvent] = []

        # Track active contract index
        active_idx = 0
        active_contract = sorted_contracts[active_idx]

        # Segments: list of (contract_symbol, list[BarRecord], date_start, date_end)
        stitched_raw: list[tuple[str, BarRecord, date]] = []

        for d in all_dates:
            # Check if we should roll to next contract
            if active_idx < len(sorted_contracts) - 1:
                next_contract = sorted_contracts[active_idx + 1]
                should_roll = False
                reason = ""

                if self.roll_trigger == RollTrigger.CALENDAR:
                    roll_deadline = active_contract.expiry_date - timedelta(
                        days=self.days_before_expiry
                    )
                    if d >= roll_deadline:
                        should_roll = True
                        reason = (
                            f"Calendar roll {self.days_before_expiry}d prior to expiry "
                            f"{active_contract.expiry_date}"
                        )

                elif self.roll_trigger == RollTrigger.VOLUME:
                    curr_day_bars = bars_by_contract_and_date[active_contract.symbol].get(d, [])
                    next_day_bars = bars_by_contract_and_date[next_contract.symbol].get(d, [])
                    curr_vol = sum(b.volume for b in curr_day_bars)
                    next_vol = sum(b.volume for b in next_day_bars)
                    if next_vol > curr_vol and next_vol > 0:
                        should_roll = True
                        reason = f"Volume roll: next contract vol ({next_vol}) > curr ({curr_vol})"

                elif self.roll_trigger == RollTrigger.OPEN_INTEREST:
                    curr_day_bars = bars_by_contract_and_date[active_contract.symbol].get(d, [])
                    next_day_bars = bars_by_contract_and_date[next_contract.symbol].get(d, [])
                    curr_oi = curr_day_bars[-1].open_interest if curr_day_bars else 0
                    next_oi = next_day_bars[-1].open_interest if next_day_bars else 0
                    if next_oi > curr_oi and next_oi > 0:
                        should_roll = True
                        reason = f"OI roll: next contract OI ({next_oi}) > curr ({curr_oi})"

                if should_roll:
                    # Calculate roll spread and ratio
                    curr_day_bars = bars_by_contract_and_date[active_contract.symbol].get(d, [])
                    next_day_bars = bars_by_contract_and_date[next_contract.symbol].get(d, [])

                    old_close = curr_day_bars[-1].close if curr_day_bars else 0.0
                    new_close = next_day_bars[-1].close if next_day_bars else 0.0
                    spread = new_close - old_close
                    ratio = (new_close / old_close) if old_close > 0 else 1.0

                    event = RollEvent(
                        roll_date=d,
                        from_symbol=active_contract.symbol,
                        to_symbol=next_contract.symbol,
                        old_close=old_close,
                        new_close=new_close,
                        spread=spread,
                        ratio=ratio,
                        trigger_reason=reason,
                    )
                    roll_events.append(event)

                    # Switch to next contract
                    active_idx += 1
                    active_contract = next_contract

            # Append bars from active contract for date d
            active_day_bars = bars_by_contract_and_date[active_contract.symbol].get(d, [])
            for b in active_day_bars:
                stitched_raw.append((active_contract.symbol, b, d))

        # Apply continuous adjustment method
        final_bars = self._apply_adjustments(
            stitched_raw=stitched_raw,
            roll_events=roll_events,
            continuous_symbol=continuous_symbol,
        )
        return final_bars, roll_events

    def _clone_bar_with_symbol(self, bar: BarRecord, new_symbol: str) -> BarRecord:
        """Helper to create a copy of a BarRecord with a synthetic continuous symbol."""
        return BarRecord(
            timestamp=bar.timestamp,
            exchange_segment=bar.exchange_segment,
            security_id=bar.security_id,
            symbol=new_symbol,
            open=bar.open,
            high=bar.high,
            low=bar.low,
            close=bar.close,
            volume=bar.volume,
            open_interest=bar.open_interest,
        )

    def _apply_adjustments(
        self,
        stitched_raw: list[tuple[str, BarRecord, date]],
        roll_events: list[RollEvent],
        continuous_symbol: str,
    ) -> list[BarRecord]:
        """Apply UNADJUSTED, DIFFERENCE, or RATIO adjustment across roll boundaries."""
        if not stitched_raw:
            return []

        if self.adjustment_method == AdjustmentMethod.UNADJUSTED or not roll_events:
            return [self._clone_bar_with_symbol(b, continuous_symbol) for _, b, _ in stitched_raw]

        # Calculate backward cumulative shifts or multipliers for each date
        # Rolls are applied backwards from future to past
        sorted_events = sorted(roll_events, key=lambda e: e.roll_date)

        adjusted_bars: list[BarRecord] = []
        for _contract_sym, b, d in stitched_raw:
            if self.adjustment_method == AdjustmentMethod.DIFFERENCE:
                # Cumulative additive spread: sum(spread_i) for all rolls occurring after date d
                cum_spread = sum(e.spread for e in sorted_events if e.roll_date > d)
                adj_open = round(b.open + cum_spread, 4)
                adj_high = round(b.high + cum_spread, 4)
                adj_low = round(b.low + cum_spread, 4)
                adj_close = round(b.close + cum_spread, 4)
            elif self.adjustment_method == AdjustmentMethod.RATIO:
                # Cumulative multiplicative ratio: prod(ratio_i) for all rolls after date d
                cum_ratio = 1.0
                for e in sorted_events:
                    if e.roll_date > d:
                        cum_ratio *= e.ratio
                adj_open = round(b.open * cum_ratio, 4)
                adj_high = round(b.high * cum_ratio, 4)
                adj_low = round(b.low * cum_ratio, 4)
                adj_close = round(b.close * cum_ratio, 4)
            else:
                adj_open, adj_high, adj_low, adj_close = b.open, b.high, b.low, b.close

            adj_high = max(adj_high, adj_open, adj_close)
            adj_low = min(adj_low, adj_open, adj_close)

            adjusted_bars.append(
                BarRecord(
                    timestamp=b.timestamp,
                    exchange_segment=b.exchange_segment,
                    security_id=b.security_id,
                    symbol=continuous_symbol,
                    open=adj_open,
                    high=adj_high,
                    low=adj_low,
                    close=adj_close,
                    volume=b.volume,
                    open_interest=b.open_interest,
                )
            )

        return adjusted_bars

    def build_continuous_table(
        self,
        contracts: list[ContractMetadata],
        continuous_symbol: str = "NIFTY_F1",
    ) -> tuple[pa.Table, list[RollEvent]]:
        """Convenience method returning continuous PyArrow Table and roll events."""
        bars, events = self.build_continuous_series(
            contracts=contracts,
            continuous_symbol=continuous_symbol,
        )
        return bars_to_arrow_table(bars), events
