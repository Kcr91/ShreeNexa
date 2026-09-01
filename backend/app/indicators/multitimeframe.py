"""Timeframe-aware multi-resolution technical indicator calculation pipeline."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from enum import StrEnum
from typing import Any

import pyarrow as pa

from app.indicators.graph import IndicatorDependencyGraph
from app.indicators.registry import registry
from app.marketdata.calendar import TradingCalendar
from app.marketdata.resampler import (
    BarResampler,
    Timeframe,
    parse_timeframe,
)
from app.warehouse.schema import BarRecord

logger = logging.getLogger(__name__)


class TimeframeAlignmentMode(StrEnum):
    """Alignment mode for higher-timeframe projections."""

    LOOKAHEAD_FREE = "lookahead_free"  # Available strictly after HTF bar interval close
    CONTEMPORANEOUS = "contemporaneous"  # As-of current open bucket (potential lookahead)


_TIMEFRAME_DELTAS: dict[Timeframe, timedelta] = {
    Timeframe.M1: timedelta(minutes=1),
    Timeframe.M3: timedelta(minutes=3),
    Timeframe.M5: timedelta(minutes=5),
    Timeframe.M15: timedelta(minutes=15),
    Timeframe.M25: timedelta(minutes=25),
    Timeframe.M30: timedelta(minutes=30),
    Timeframe.H1: timedelta(hours=1),
    Timeframe.D1: timedelta(days=1),
    Timeframe.W1: timedelta(weeks=1),
}


class MultiTimeframeIndicatorPipeline:
    """Calculates higher-timeframe indicators and projects onto base resolution series."""

    def __init__(self, calendar: TradingCalendar | None = None) -> None:
        self.calendar = calendar or TradingCalendar()
        self.resampler = BarResampler(self.calendar)

    def compute_indicator(
        self,
        base_bars: list[BarRecord] | pa.Table,
        target_tf: str | Timeframe,
        indicator_name: str,
        params: dict[str, Any] | None = None,
        alignment_mode: TimeframeAlignmentMode = TimeframeAlignmentMode.LOOKAHEAD_FREE,
    ) -> list[float | None] | dict[str, list[float | None]]:
        """Calculate indicator on resampled higher-timeframe bars and project back to base bars."""
        records = self._ensure_bar_records(base_bars)
        if not records:
            return []

        tf_enum = parse_timeframe(target_tf)
        htf_bars = self.resampler.resample_bars(records, tf_enum)
        if not htf_bars:
            n = len(records)
            return [None] * n

        htf_table = self._bars_to_dict(htf_bars)
        htf_indicator_out = registry.compute(indicator_name, htf_table, params=params)

        if isinstance(htf_indicator_out, list):
            return self._project_series(
                records, htf_bars, tf_enum, htf_indicator_out, alignment_mode
            )
        elif isinstance(htf_indicator_out, dict):
            out_dict: dict[str, list[float | None]] = {}
            for k, s in htf_indicator_out.items():
                out_dict[k] = self._project_series(records, htf_bars, tf_enum, s, alignment_mode)
            return out_dict

        raise TypeError(f"Unexpected indicator output type: {type(htf_indicator_out)}")

    def compute_graph(
        self,
        base_bars: list[BarRecord] | pa.Table,
        target_tf: str | Timeframe,
        graph: IndicatorDependencyGraph,
        alignment_mode: TimeframeAlignmentMode = TimeframeAlignmentMode.LOOKAHEAD_FREE,
    ) -> dict[str, list[Any]]:
        """Calculate compound dependency DAG on resampled HTF bars and project to base bars."""
        records = self._ensure_bar_records(base_bars)
        if not records:
            return {}

        tf_enum = parse_timeframe(target_tf)
        htf_bars = self.resampler.resample_bars(records, tf_enum)
        if not htf_bars:
            n = len(records)
            return {node: [None] * n for node in graph.nodes}

        htf_data = self._bars_to_dict(htf_bars)
        plan = graph.compile_plan()
        htf_results = plan.execute(htf_data)

        projected_results: dict[str, list[Any]] = {}
        for node_name, series in htf_results.items():
            projected_results[node_name] = self._project_series(
                records, htf_bars, tf_enum, series, alignment_mode
            )

        return projected_results

    def _project_series(
        self,
        base_bars: list[BarRecord],
        htf_bars: list[BarRecord],
        htf_tf: Timeframe,
        htf_series: list[Any],
        alignment_mode: TimeframeAlignmentMode,
    ) -> list[Any]:
        """Project HTF calculated values onto base bar timestamps without lookahead."""
        delta = _TIMEFRAME_DELTAS.get(htf_tf, timedelta(minutes=15))

        # Build list of (close_time, value) for HTF bars
        htf_events: list[tuple[datetime, Any]] = []
        for bar, val in zip(htf_bars, htf_series, strict=True):
            if alignment_mode == TimeframeAlignmentMode.LOOKAHEAD_FREE:
                # Available only at and after interval close
                avail_time = bar.timestamp + delta
            else:
                # Contemporaneous (open time)
                avail_time = bar.timestamp
            htf_events.append((avail_time, val))

        # Step through base bars and forward fill the latest available HTF event
        out: list[Any] = []
        event_idx = 0
        num_events = len(htf_events)
        current_val: Any = None

        for b in base_bars:
            b_ts = b.timestamp
            while event_idx < num_events and htf_events[event_idx][0] <= b_ts:
                current_val = htf_events[event_idx][1]
                event_idx += 1
            out.append(current_val)

        return out

    def _ensure_bar_records(self, data: list[BarRecord] | pa.Table) -> list[BarRecord]:
        """Convert PyArrow Table or list of BarRecords to list[BarRecord]."""
        if isinstance(data, list):
            return data
        elif isinstance(data, pa.Table):
            records: list[BarRecord] = []
            cols = {col: data[col].to_pylist() for col in data.column_names}
            n = data.num_rows
            for i in range(n):
                records.append(
                    BarRecord(
                        symbol=cols.get("symbol", ["RELIANCE"] * n)[i],
                        exchange_segment=cols.get("exchange_segment", ["NSE_EQ"] * n)[i],
                        security_id=str(cols.get("security_id", ["2885"] * n)[i]),
                        timestamp=cols["timestamp"][i],
                        open=float(cols["open"][i]),
                        high=float(cols["high"][i]),
                        low=float(cols["low"][i]),
                        close=float(cols["close"][i]),
                        volume=int(cols["volume"][i]),
                        open_interest=int(cols.get("open_interest", [0] * n)[i]),
                    )
                )
            return records
        else:
            raise TypeError(f"Unsupported input type {type(data)}")

    def _bars_to_dict(self, bars: list[BarRecord]) -> dict[str, Any]:
        """Convert list of BarRecords to columnar dictionary."""
        return {
            "open": [b.open for b in bars],
            "high": [b.high for b in bars],
            "low": [b.low for b in bars],
            "close": [b.close for b in bars],
            "volume": [b.volume for b in bars],
            "open_interest": [b.open_interest for b in bars],
        }
