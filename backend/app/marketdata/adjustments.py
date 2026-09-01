"""Corporate action adjustment pipeline with point-in-time preservation."""

from __future__ import annotations

import logging
from datetime import UTC, date, datetime
from enum import StrEnum

import pyarrow as pa
from pydantic import BaseModel, ConfigDict

from app.marketdata.calendar import to_ist
from app.warehouse.schema import BarRecord, bars_to_arrow_table

logger = logging.getLogger(__name__)


class ActionType(StrEnum):
    """Supported corporate action categories."""

    SPLIT = "SPLIT"
    BONUS = "BONUS"
    DIVIDEND = "DIVIDEND"
    RIGHTS = "RIGHTS"


class CorporateAction(BaseModel):
    """Specification of an Indian market corporate action event."""

    model_config = ConfigDict(frozen=True)

    symbol: str
    action_type: ActionType
    ex_date: date
    record_date: date | None = None
    ratio_numerator: float | None = None
    ratio_denominator: float | None = None
    dividend_amount: float | None = None
    announced_date: date | None = None

    def calculate_factor(self, reference_close: float | None = None) -> float:
        """Calculate the price multiplier adjustment factor for data prior to ex-date."""
        if self.action_type == ActionType.SPLIT:
            num = self.ratio_numerator or 1.0
            den = self.ratio_denominator or 1.0
            if den <= 0:
                raise ValueError(f"Split ratio denominator must be positive: {den}")
            return float(num / den)

        elif self.action_type == ActionType.BONUS:
            bonus = self.ratio_numerator or 1.0
            existing = self.ratio_denominator or 1.0
            total = bonus + existing
            if total <= 0:
                raise ValueError(f"Bonus ratio total must be positive: {total}")
            return float(existing / total)

        elif self.action_type == ActionType.DIVIDEND:
            div = self.dividend_amount or 0.0
            if div <= 0:
                return 1.0
            if reference_close is None or reference_close <= 0:
                logger.warning(
                    "Dividend adjustment for %s on %s missing reference close; factor default 1.0",
                    self.symbol,
                    self.ex_date,
                )
                return 1.0
            factor = (reference_close - div) / reference_close
            return float(max(0.0001, factor))

        elif self.action_type == ActionType.RIGHTS:
            # Rights issue theoretical ex-rights factor
            num = self.ratio_numerator or 1.0
            den = self.ratio_denominator or 1.0
            return float(den / (num + den))

        return 1.0


class AdjustmentPipeline:
    """Computes point-in-time cumulative factors and transforms OHLCV bar series."""

    def __init__(self, actions: list[CorporateAction] | None = None) -> None:
        self._actions_by_symbol: dict[str, list[CorporateAction]] = {}
        if actions:
            for act in actions:
                self.add_action(act)

    def add_action(self, action: CorporateAction) -> None:
        """Register a corporate action event."""
        sym = action.symbol.upper()
        self._actions_by_symbol.setdefault(sym, []).append(action)
        # Keep actions sorted by ex_date
        self._actions_by_symbol[sym].sort(key=lambda a: a.ex_date)

    def get_actions(self, symbol: str) -> list[CorporateAction]:
        """Return all registered corporate actions for a symbol."""
        return list(self._actions_by_symbol.get(symbol.upper(), []))

    def get_cumulative_factor(
        self,
        symbol: str,
        target_date: date,
        reference_prices: dict[date, float] | None = None,
    ) -> float:
        """Calculate compounded adjustment factor for corporate actions after target_date."""
        sym = symbol.upper()
        actions = self._actions_by_symbol.get(sym, [])
        if not actions:
            return 1.0

        cum_factor = 1.0
        ref_prices = reference_prices or {}

        for act in actions:
            if act.ex_date > target_date:
                ref_close = ref_prices.get(act.ex_date)
                f = act.calculate_factor(reference_close=ref_close)
                cum_factor *= f

        return cum_factor

    def adjust_bars(
        self,
        bars: list[BarRecord],
        reference_prices: dict[date, float] | None = None,
    ) -> list[BarRecord]:
        """Apply corporate action adjustments to BarRecord models without mutating source."""
        if not bars:
            return []

        adjusted_bars: list[BarRecord] = []
        ref_prices = reference_prices or {}

        for b in bars:
            b_date = to_ist(b.timestamp).date()
            factor = self.get_cumulative_factor(
                symbol=b.symbol,
                target_date=b_date,
                reference_prices=ref_prices,
            )

            if abs(factor - 1.0) < 1e-9:
                adjusted_bars.append(b)
                continue

            adj_open = round(b.open * factor, 4)
            adj_high = round(b.high * factor, 4)
            adj_low = round(b.low * factor, 4)
            adj_close = round(b.close * factor, 4)

            # Volume and open interest are inversely scaled (divided by factor)
            adj_volume = round(b.volume / factor)
            adj_oi = round(b.open_interest / factor) if b.open_interest > 0 else 0

            # Ensure high is at least max(open, close) and low is at most min(open, close)
            adj_high = max(adj_high, adj_open, adj_close)
            adj_low = min(adj_low, adj_open, adj_close)

            adjusted_bars.append(
                BarRecord(
                    timestamp=b.timestamp,
                    exchange_segment=b.exchange_segment,
                    security_id=b.security_id,
                    symbol=b.symbol,
                    open=adj_open,
                    high=adj_high,
                    low=adj_low,
                    close=adj_close,
                    volume=adj_volume,
                    open_interest=adj_oi,
                )
            )

        return adjusted_bars

    def adjust_table(
        self,
        table: pa.Table,
        reference_prices: dict[date, float] | None = None,
    ) -> pa.Table:
        """Apply corporate action adjustments to a PyArrow Table."""
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

        adjusted = self.adjust_bars(bars, reference_prices=reference_prices)
        return bars_to_arrow_table(adjusted)
