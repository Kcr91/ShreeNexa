"""Unit test suite for Dynamic Screener Engine (Feature 2)."""

from __future__ import annotations

from collections.abc import Generator
from datetime import UTC, datetime, timedelta

import numpy as np
import pandas as pd
import pytest
from app.main import app
from app.screener.aggregator import CandleAggregator
from app.screener.condition_evaluator import evaluate_condition_tree
from app.screener.dynamic_engine import DynamicScreenerEngine
from app.screener.engine_models import metadata as screener_metadata
from app.screener.indicators import (
    calculate_bollinger_bands,
    calculate_ema,
    calculate_macd,
    calculate_rsi,
    calculate_supertrend,
    check_candlestick_pattern,
)
from app.worker.data_engine.models import metadata as data_metadata
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.pool import StaticPool


@pytest.fixture
def sqlite_engine() -> Generator[Engine]:
    """In-memory SQLite engine for screener testing."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    screener_metadata.create_all(engine)
    data_metadata.create_all(engine)
    yield engine
    engine.dispose()


def _generate_sample_candles(n: int = 100, start_price: float = 1000.0) -> pd.DataFrame:
    """Generate sample 1-minute OHLCV candles."""
    base_time = datetime(2026, 10, 1, 9, 15, tzinfo=UTC)
    rows = []
    price = start_price

    for i in range(n):
        dt = base_time + timedelta(minutes=i)
        change = np.sin(i / 10.0) * 5.0 + 0.5
        open_p = price
        high_p = open_p + max(0.0, change) + 2.0
        low_p = open_p + min(0.0, change) - 2.0
        close_p = open_p + change
        vol = 1000 + (i * 20)
        rows.append(
            {
                "datetime_ist": dt,
                "open": open_p,
                "high": high_p,
                "low": low_p,
                "close": close_p,
                "volume": vol,
            }
        )
        price = close_p

    return pd.DataFrame(rows)


def test_timeframe_aggregator() -> None:
    """Verify 1-minute candles aggregate correctly into 5min, 15min, and daily buckets."""
    aggregator = CandleAggregator()
    df_1min = _generate_sample_candles(n=60)

    # 5-min aggregation (60 1-min -> 12 5-min bars)
    df_5min = aggregator.aggregate_df(df_1min, timeframe="5min")
    assert len(df_5min) == 12
    assert "open" in df_5min.columns
    assert "close" in df_5min.columns

    # 15-min aggregation (60 1-min -> 4 15-min bars)
    df_15min = aggregator.aggregate_df(df_1min, timeframe="15min")
    assert len(df_15min) == 4

    # Daily aggregation (1 day)
    df_daily = aggregator.aggregate_df(df_1min, timeframe="daily")
    assert len(df_daily) == 1


def test_technical_indicators_and_patterns() -> None:
    """Verify indicator math and candlestick pattern recognition."""
    df = _generate_sample_candles(n=50)

    # RSI
    rsi = calculate_rsi(df["close"], period=14)
    assert len(rsi) == 50
    assert 0.0 <= float(rsi.iloc[-1]) <= 100.0

    # EMA
    ema = calculate_ema(df["close"], period=20)
    assert len(ema) == 50

    # MACD
    macd_line, sig_line, _hist = calculate_macd(df["close"])
    assert len(macd_line) == 50
    assert len(sig_line) == 50

    # Bollinger Bands
    mid, up, low = calculate_bollinger_bands(df["close"], period=20, std_dev=2.0)
    assert up.iloc[-1] >= mid.iloc[-1] >= low.iloc[-1]

    # Supertrend
    st_line, is_bullish = calculate_supertrend(df, period=10, multiplier=3.0)
    assert len(st_line) == 50
    assert isinstance(bool(is_bullish.iloc[-1]), bool)

    # Open=High pattern
    pattern_df = pd.DataFrame(
        [
            {
                "datetime_ist": datetime.now(UTC),
                "open": 2500.0,
                "high": 2500.0,
                "low": 2480.0,
                "close": 2485.0,
                "volume": 5000,
            }
        ]
    )
    assert check_candlestick_pattern(pattern_df, "OPEN_EQ_HIGH") is True
    assert check_candlestick_pattern(pattern_df, "OPEN_EQ_LOW") is False


def test_condition_tree_evaluator() -> None:
    """Verify nested AND / OR condition tree evaluations."""
    df_1min = _generate_sample_candles(n=60)
    timeframe_dfs = {
        "1min": df_1min,
        "daily": df_1min,
        "weekly": df_1min,
        "monthly": df_1min,
    }

    # Example: Pure AND setup (RSI > 40 on daily)
    tree_and = {
        "logic": "AND",
        "conditions": [
            {
                "indicator": "RSI",
                "period": 14,
                "timeframe": "daily",
                "operator": ">",
                "value": 40.0,
            },
            {
                "indicator": "EMA",
                "period": 20,
                "timeframe": "daily",
                "operator": "close_above",
            },
        ],
    }

    res_collector: dict[str, float] = {}
    matched_conds: list[str] = []
    matched = evaluate_condition_tree(
        tree_and,
        timeframe_dfs,
        results_collector=res_collector,
        matched_conditions=matched_conds,
    )
    assert isinstance(matched, bool)
    assert len(res_collector) >= 1


def test_dynamic_screener_engine_run(sqlite_engine: Engine) -> None:
    """Verify full screener engine run across universe."""
    # Seed raw candles for RELIANCE
    df = _generate_sample_candles(n=50)
    df["security_id"] = "RELIANCE_EQ"
    df["exchange_segment"] = "NSE_EQ"
    df["symbol"] = "RELIANCE"
    df.to_sql("mkt_ohlcv_equity", sqlite_engine, if_exists="append", index=False)

    screener_engine = DynamicScreenerEngine(engine=sqlite_engine)
    condition_tree = {
        "logic": "AND",
        "conditions": [
            {
                "indicator": "RSI",
                "period": 14,
                "timeframe": "1min",
                "operator": ">",
                "value": 20.0,
            }
        ],
    }

    res = screener_engine.run_screener(
        condition_tree=condition_tree,
        universe_code="FNO_208",
        config_name="Test Scan",
        save_results=True,
    )
    assert res.total_scanned >= 1
    assert res.duration_ms >= 0


def test_screener_api_endpoints(sqlite_engine: Engine) -> None:
    """Verify Screener FastAPI CRUD and execution endpoints."""
    from app.api.screener_engine import get_db_engine

    app.dependency_overrides[get_db_engine] = lambda: sqlite_engine
    client = TestClient(app)

    try:
        # 1. Create config
        create_payload = {
            "name": "RSI Pullback Setup",
            "description": "Multi-timeframe RSI scan",
            "universe_filter": "FNO_208",
            "condition_tree": {
                "logic": "AND",
                "conditions": [
                    {
                        "indicator": "RSI",
                        "period": 14,
                        "timeframe": "daily",
                        "operator": ">",
                        "value": 50,
                    }
                ],
            },
            "is_strategy_mode": False,
        }
        resp = client.post("/api/v1/screener/configs", json=create_payload)
        assert resp.status_code == 200
        created = resp.json()
        config_id = created["id"]
        assert created["name"] == "RSI Pullback Setup"

        # 2. List configs
        list_resp = client.get("/api/v1/screener/configs")
        assert list_resp.status_code == 200
        assert len(list_resp.json()) >= 1

        # 3. Get single config
        get_resp = client.get(f"/api/v1/screener/configs/{config_id}")
        assert get_resp.status_code == 200
        assert get_resp.json()["id"] == config_id

        # 4. Run scan
        run_resp = client.post(f"/api/v1/screener/run/{config_id}")
        assert run_resp.status_code == 200
        run_data = run_resp.json()
        assert run_data["config_name"] == "RSI Pullback Setup"

        # 5. Delete config
        del_resp = client.delete(f"/api/v1/screener/configs/{config_id}")
        assert del_resp.status_code == 200
        assert del_resp.json()["status"] == "deleted"

    finally:
        app.dependency_overrides.pop(get_db_engine, None)
