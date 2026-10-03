"""DuckDB SQL-based multi-timeframe candle aggregator converting 1-min Parquet bars."""

from __future__ import annotations

import logging

import duckdb
import pandas as pd

logger = logging.getLogger(__name__)


TIMEFRAME_BUCKET_SQL: dict[str, str] = {
    "1min": "datetime_ist",
    "5min": "time_bucket(INTERVAL '5 minutes', datetime_ist)",
    "15min": "time_bucket(INTERVAL '15 minutes', datetime_ist)",
    "1h": "time_bucket(INTERVAL '1 hour', datetime_ist)",
    "4h": "time_bucket(INTERVAL '4 hours', datetime_ist)",
    "daily": "date_trunc('day', datetime_ist)",
    "weekly": "date_trunc('week', datetime_ist)",
    "monthly": "date_trunc('month', datetime_ist)",
}


class CandleAggregator:
    """Aggregates raw 1-minute OHLCV DataFrames or Parquet partitions into arbitrary timeframes."""

    def __init__(self) -> None:
        self.con = duckdb.connect(":memory:")

    def aggregate_df(
        self,
        df: pd.DataFrame,
        timeframe: str = "daily",
    ) -> pd.DataFrame:
        """Aggregate a pandas DataFrame of 1-minute candles to requested timeframe."""
        tf_lower = timeframe.lower()
        if tf_lower not in TIMEFRAME_BUCKET_SQL:
            supported = list(TIMEFRAME_BUCKET_SQL.keys())
            raise ValueError(f"Unsupported timeframe: {timeframe}. Supported: {supported}")

        if df.empty:
            cols = ["datetime_ist", "open", "high", "low", "close", "volume", "oi"]
            return pd.DataFrame(columns=cols)

        # Ensure datetime column is parsed
        if not pd.api.types.is_datetime64_any_dtype(df["datetime_ist"]):
            df["datetime_ist"] = pd.to_datetime(df["datetime_ist"])

        bucket_expr = TIMEFRAME_BUCKET_SQL[tf_lower]
        has_oi = "oi" in df.columns

        query = f"""
        SELECT
            {bucket_expr} AS datetime_ist,
            FIRST(open ORDER BY datetime_ist ASC) AS open,
            MAX(high) AS high,
            MIN(low) AS low,
            LAST(close ORDER BY datetime_ist ASC) AS close,
            SUM(volume) AS volume
            {", LAST(oi ORDER BY datetime_ist ASC) AS oi" if has_oi else ""}
        FROM df
        GROUP BY 1
        ORDER BY datetime_ist ASC
        """

        res_df = self.con.execute(query).df()
        return res_df

    def aggregate_parquet_glob(
        self,
        parquet_glob_path: str,
        timeframe: str = "daily",
    ) -> pd.DataFrame:
        """Aggregate directly from a Parquet path pattern via DuckDB."""
        tf_lower = timeframe.lower()
        bucket_expr = TIMEFRAME_BUCKET_SQL.get(tf_lower, "date_trunc('day', datetime_ist)")

        query = f"""
        SELECT
            {bucket_expr} AS datetime_ist,
            FIRST(open ORDER BY datetime_ist ASC) AS open,
            MAX(high) AS high,
            MIN(low) AS low,
            LAST(close ORDER BY datetime_ist ASC) AS close,
            SUM(volume) AS volume
        FROM read_parquet('{parquet_glob_path}')
        GROUP BY 1
        ORDER BY datetime_ist ASC
        """
        try:
            return self.con.execute(query).df()
        except Exception as exc:
            logger.warning("Error reading parquet %s: %s", parquet_glob_path, exc)
            return pd.DataFrame()
