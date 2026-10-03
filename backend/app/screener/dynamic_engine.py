"""Dynamic Screener Engine orchestrating universe loading and execution."""

from __future__ import annotations

import logging
import time
from datetime import UTC, datetime
from typing import Any

import pandas as pd
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.engine import Engine

from app.screener.aggregator import CandleAggregator
from app.screener.condition_evaluator import evaluate_condition_tree
from app.screener.engine_models import (
    DynamicScreenerRunResponse,
    MatchedStockDetail,
    screener_results_table,
)
from app.worker.data_engine.models import (
    mkt_ohlcv_equity_table,
    mkt_segment_constituent_table,
)

logger = logging.getLogger(__name__)


def extract_required_timeframes(node: dict[str, Any]) -> set[str]:
    """Recursively collect all unique timeframes referenced in the condition tree."""
    timeframes: set[str] = set()
    if "logic" in node:
        for c in node.get("conditions", []):
            timeframes.update(extract_required_timeframes(c))
    else:
        tf = node.get("timeframe", "daily").lower()
        timeframes.add(tf)
    return timeframes or {"daily"}


class DynamicScreenerEngine:
    """Orchestrates dynamic screener execution in both Strategy Mode and Live Scan Mode."""

    def __init__(
        self,
        engine: Engine,
        aggregator: CandleAggregator | None = None,
    ) -> None:
        self.engine = engine
        self.aggregator = aggregator or CandleAggregator()

    def get_universe_symbols(self, universe_code: str) -> list[str]:
        """Fetch all constituent symbols for the requested segment / universe."""
        with self.engine.connect() as conn:
            stmt = select(mkt_segment_constituent_table.c.symbol).where(
                mkt_segment_constituent_table.c.segment_code == universe_code.upper()
            )
            rows = conn.execute(stmt).fetchall()
            if rows:
                return [r[0] for r in rows]

        # Fallback list if segment table not yet populated
        return [
            "RELIANCE",
            "TCS",
            "INFY",
            "HDFCBANK",
            "ICICIBANK",
            "SBIN",
            "BHARTIARTL",
            "ITC",
            "LT",
            "KOTAKBANK",
        ]

    def load_symbol_raw_candles(self, symbol: str) -> pd.DataFrame:
        """Fetch 1-minute historical candles for a symbol from PostgreSQL."""
        with self.engine.connect() as conn:
            stmt = (
                select(
                    mkt_ohlcv_equity_table.c.datetime_ist,
                    mkt_ohlcv_equity_table.c.open,
                    mkt_ohlcv_equity_table.c.high,
                    mkt_ohlcv_equity_table.c.low,
                    mkt_ohlcv_equity_table.c.close,
                    mkt_ohlcv_equity_table.c.volume,
                )
                .where(mkt_ohlcv_equity_table.c.symbol == symbol.upper())
                .order_by(mkt_ohlcv_equity_table.c.datetime_ist.asc())
            )
            rows = conn.execute(stmt).fetchall()
            if not rows:
                return pd.DataFrame(
                    columns=["datetime_ist", "open", "high", "low", "close", "volume"]
                )

            return pd.DataFrame(
                [dict(r._mapping) for r in rows],
                columns=["datetime_ist", "open", "high", "low", "close", "volume"],
            )

    def run_screener(
        self,
        condition_tree: dict[str, Any],
        universe_code: str = "FNO_208",
        config_id: int | None = None,
        config_name: str = "Live Screener Scan",
        save_results: bool = True,
    ) -> DynamicScreenerRunResponse:
        """Execute the screener against target universe and return full matched results."""
        start_time = time.perf_counter()
        run_at = datetime.now(UTC)

        symbols = self.get_universe_symbols(universe_code)
        required_tfs = extract_required_timeframes(condition_tree)

        matched_details: list[MatchedStockDetail] = []
        matched_symbols: list[str] = []

        for sym in symbols:
            raw_df = self.load_symbol_raw_candles(sym)
            if raw_df.empty or len(raw_df) < 5:
                continue

            # Build aggregated timeframes for this symbol
            timeframe_dfs: dict[str, pd.DataFrame] = {}
            for tf in required_tfs:
                if tf == "1min":
                    timeframe_dfs[tf] = raw_df
                else:
                    timeframe_dfs[tf] = self.aggregator.aggregate_df(raw_df, timeframe=tf)

            indicator_vals: dict[str, Any] = {}
            conditions_met: list[str] = []

            is_matched = evaluate_condition_tree(
                condition_tree,
                timeframe_dfs,
                results_collector=indicator_vals,
                matched_conditions=conditions_met,
            )

            if is_matched:
                last_c = float(raw_df["close"].iloc[-1])
                prev_c = float(raw_df["close"].iloc[-2]) if len(raw_df) >= 2 else last_c
                chg_pct = round(((last_c - prev_c) / prev_c) * 100.0, 2)
                vol = int(raw_df["volume"].iloc[-1])

                detail = MatchedStockDetail(
                    symbol=sym,
                    display_name=sym,
                    segments=[universe_code],
                    last_close=last_c,
                    change_pct=chg_pct,
                    volume=vol,
                    indicator_values=indicator_vals,
                    conditions_met=conditions_met,
                )
                matched_details.append(detail)
                matched_symbols.append(sym)

        duration_ms = int((time.perf_counter() - start_time) * 1000)

        # Persist results to DB
        run_id = None
        if save_results:
            try:
                with self.engine.begin() as conn:
                    ins_stmt = (
                        pg_insert(screener_results_table)
                        .values(
                            config_id=config_id,
                            run_at=run_at,
                            matched_symbols=matched_symbols,
                            total_scanned=len(symbols),
                            total_matched=len(matched_symbols),
                            run_duration_ms=duration_ms,
                            result_snapshot=[d.model_dump() for d in matched_details],
                        )
                        .returning(screener_results_table.c.id)
                    )
                    run_id = conn.execute(ins_stmt).scalar()
            except Exception as exc:
                logger.warning("Could not persist screener run result: %s", exc)

        return DynamicScreenerRunResponse(
            run_id=run_id,
            config_id=config_id,
            config_name=config_name,
            universe=universe_code,
            total_scanned=len(symbols),
            total_matched=len(matched_symbols),
            duration_ms=duration_ms,
            run_at=run_at,
            results=matched_details,
        )
