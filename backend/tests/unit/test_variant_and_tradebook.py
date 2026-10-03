"""Unit test suite for Feature 4: Multi-Variant Engine, Volatility Context & Live Tradebook."""

from __future__ import annotations

from collections.abc import Generator
from datetime import UTC, datetime, timedelta
from typing import Any

import pandas as pd
import pytest
from app.api.deps import require_csrf, require_non_demo_session, require_session
from app.api.variant_engine import get_db_engine
from app.engine.cost_simulator import calculate_trade_costs
from app.engine.greeks_calc import (
    black_scholes_price,
    calculate_greeks,
    calculate_implied_volatility,
)
from app.engine.multi_variant_loop import MultiVariantSimulator
from app.engine.variant_models import SelectedVariantOverride
from app.engine.vix_analytics import generate_vix_iv_heatmap
from app.main import app
from app.strategy.models import metadata, strategy_configs_table
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, insert
from sqlalchemy.engine import Engine
from sqlalchemy.pool import StaticPool


@pytest.fixture
def sqlite_engine() -> Generator[Engine]:
    """In-memory SQLite engine for variant and tradebook testing."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture
def client(sqlite_engine: Engine) -> Generator[TestClient]:
    """TestClient with database dependency and auth overrides."""
    app.dependency_overrides[get_db_engine] = lambda: sqlite_engine
    app.dependency_overrides[require_session] = lambda: {"user_id": "test_user"}
    app.dependency_overrides[require_non_demo_session] = lambda: {"user_id": "test_user"}
    app.dependency_overrides[require_csrf] = lambda: None

    tc = TestClient(app, raise_server_exceptions=True)
    yield tc

    app.dependency_overrides.clear()


def sample_options_strategy_dict() -> dict[str, Any]:
    """Sample option strategy definition for multi-variant testing."""
    return {
        "strategy_type": "OPTION",
        "name": "Nifty Open-High Put Multi-Variant",
        "version": 1,
        "part_1_scope": {
            "source_type": "INDEX_OPTION",
            "underlying_symbol": "NIFTY",
            "option_right": "PE",
            "expiry_type": "CURRENT_WEEK",
            "strike_selection": {"mode": "ATM_OFFSET", "offset": 0},
        },
        "part_2_entry": {
            "direction": "LONG",
            "trigger_timeframe": "1min",
            "logic": "AND",
            "conditions": [
                {
                    "price_reference": "SPOT",
                    "timeframe": "1min",
                    "pattern": "OPEN_EQ_HIGH",
                }
            ],
        },
        "part_3_stoploss": {
            "sl_reference": "OPTION_PREMIUM",
            "sl_type": "PERCENTAGE",
            "percentage_val": 20.0,
        },
        "part_4_exit": {
            "exit_reference": "OPTION_PREMIUM",
            "targets": [
                {
                    "target_number": 1,
                    "percentage_gain": 40.0,
                    "exit_lots_percentage": 100.0,
                }
            ],
            "trailing_sl": {
                "enabled": False,
            },
        },
    }


def test_black_scholes_pricing_and_greeks() -> None:
    """Verify Black-Scholes formula, IV inversion, and Greeks calculations."""
    spot = 24500.0
    strike = 24500.0
    tte = 7.0 / 365.0
    iv = 25.0
    rate = 0.07

    # 1. Price calculation
    call_p = black_scholes_price(spot, strike, tte, iv, rate, "CE")
    put_p = black_scholes_price(spot, strike, tte, iv, rate, "PE")
    assert call_p > 50.0
    assert put_p > 50.0

    # 2. Implied Volatility Solver
    solved_iv = calculate_implied_volatility(call_p, spot, strike, tte, rate, "CE")
    assert abs(solved_iv - iv) < 0.5

    # 3. Greeks calculation
    greeks_call = calculate_greeks(spot, strike, tte, iv, rate, "CE")
    assert 0.45 <= greeks_call.delta <= 0.55  # ATM Delta ~0.50
    assert greeks_call.gamma > 0.0
    assert greeks_call.theta < 0.0  # Theta decay is negative
    assert greeks_call.vega > 0.0  # Vega is positive

    greeks_put = calculate_greeks(spot, strike, tte, iv, rate, "PE")
    assert -0.55 <= greeks_put.delta <= -0.45  # ATM Put Delta ~ -0.50


def test_cost_simulator_breakdown() -> None:
    """Verify Indian market brokerage, STT, turnover charges, and tax math."""
    # Options Trade: Buy at 150, Sell at 200, 50 qty (1 Nifty lot)
    breakdown = calculate_trade_costs(
        instrument_type="OPTION",
        buy_price=150.0,
        sell_price=200.0,
        quantity=50,
        brokerage_per_order=20.0,
        slippage_per_unit=0.10,
    )

    # Buy turnover = 7,500; Sell turnover = 10,000; Gross = 2,500
    assert breakdown.gross_pnl == 2500.00
    assert breakdown.brokerage == 40.00  # ₹20 buy + ₹20 sell
    assert breakdown.stt_tax == 12.50  # 0.125% of 10,000 = ₹12.50
    assert breakdown.gst > 7.0  # 18% on brokerage + turnover
    assert breakdown.total_costs > 50.0
    assert breakdown.net_pnl == round(breakdown.gross_pnl - breakdown.total_costs, 2)


def test_multi_variant_simulator_execution() -> None:
    """Verify single-pass MultiVariantSimulator with baseline and partial exits."""
    strat = sample_options_strategy_dict()

    # Generate candles with trigger at bar 20
    base_time = datetime(2026, 9, 1, 9, 15, tzinfo=UTC)
    spot_rows = []
    opt_rows = []
    for idx in range(60):
        dt = base_time + timedelta(minutes=idx)
        if idx == 20:
            # Trigger Open == High
            s_open, s_high, s_low, s_close = 24500.0, 24500.0, 24470.0, 24475.0
            o_open, o_high, o_low, o_close = 150.0, 180.0, 145.0, 175.0
        else:
            s_open, s_high, s_low, s_close = 24500.0, 24510.0, 24490.0, 24505.0
            o_open, o_high, o_low, o_close = 150.0, 155.0, 148.0, 152.0

        spot_rows.append(
            {
                "datetime_ist": dt,
                "open": s_open,
                "high": s_high,
                "low": s_low,
                "close": s_close,
                "volume": 1000,
            }
        )
        opt_rows.append(
            {
                "datetime_ist": dt,
                "open": o_open,
                "high": o_high,
                "low": o_low,
                "close": o_close,
                "volume": 500,
            }
        )

    spot_df = pd.DataFrame(spot_rows)
    opt_df = pd.DataFrame(opt_rows)

    simulator = MultiVariantSimulator()
    selected_vars = [
        SelectedVariantOverride(
            name="Variant 1: Partial Exits",
            override_params={"target_1": 15.0, "target_2": 30.0},
        )
    ]

    rankings, trades = simulator.run_simulation(
        strategy_config=strat,
        spot_candles=spot_df,
        option_candles=opt_df,
        selected_variations=selected_vars,
    )

    assert len(rankings) == 2  # Baseline + Variant 1
    assert any(r.is_baseline for r in rankings)
    assert len(trades) >= 2

    # Check volatility snapshots in trades
    for t in trades:
        assert t.entry_india_vix is not None
        assert t.entry_option_iv is not None
        assert t.exit_reason != ""


def test_vix_iv_heatmap_analytics() -> None:
    """Verify performance aggregation into 2D VIX vs IV grid."""
    trades = [
        {"entry_india_vix": 13.5, "entry_option_iv": 24.0, "realized_pnl": 1500.0},
        {"entry_india_vix": 14.0, "entry_option_iv": 28.0, "realized_pnl": 2000.0},
        {"entry_india_vix": 19.5, "entry_option_iv": 35.0, "realized_pnl": -500.0},
        {"entry_india_vix": 23.0, "entry_option_iv": 45.0, "realized_pnl": -1200.0},
    ]

    heatmap = generate_vix_iv_heatmap(trades)
    assert len(heatmap.cells) == 20  # 5 VIX buckets x 4 IV buckets
    assert "12-15" in heatmap.profitable_vix_range
    assert "20-30%" in heatmap.profitable_iv_zone


def test_variant_and_tradebook_api(client: TestClient, sqlite_engine: Engine) -> None:
    """Test full FastAPI REST endpoints for Variant Library, Multi-Variant Run & Live Tradebook."""
    now = datetime.now(UTC)

    # 1. Insert a mock strategy config in SQLite
    strat_dict = sample_options_strategy_dict()
    with sqlite_engine.begin() as conn:
        res = conn.execute(
            insert(strategy_configs_table).values(
                name="API Test Option Strategy",
                description="Strategy for multi-variant testing",
                strategy_type="OPTION",
                current_version=1,
                is_active=True,
                config_json=strat_dict,
                created_at=now,
                updated_at=now,
            )
        )
        strat_id = res.inserted_primary_key[0]  # type: ignore[index]

    # 2. List library conditions (triggers auto-seeding)
    lib_resp = client.get("/api/v1/variant/library")
    assert lib_resp.status_code == 200
    lib_items = lib_resp.json()
    assert len(lib_items) >= 4

    # 3. Create custom library condition
    custom_cond = {
        "name": "Supertrend Exit on 5min",
        "description": "Exit if 5min Supertrend flips Bearish",
        "category": "INDICATOR_EXIT",
        "condition_config": {"indicator": "SUPERTREND", "period": 10, "multiplier": 3.0},
        "is_built_in": False,
    }
    create_resp = client.post("/api/v1/variant/library", json=custom_cond)
    assert create_resp.status_code == 201
    cond_id = create_resp.json()["id"]

    # 4. Update custom library condition
    up_resp = client.put(
        f"/api/v1/variant/library/{cond_id}",
        json={"description": "Updated Supertrend exit rule"},
    )
    assert up_resp.status_code == 200
    assert up_resp.json()["description"] == "Updated Supertrend exit rule"

    # 5. Run Multi-Variant Backtest
    run_req = {
        "strategy_id": strat_id,
        "run_name": "API Multi-Variant Backtest",
        "start_date": "2026-09-01",
        "end_date": "2026-09-30",
        "capital": 500000.0,
        "selected_variations": [
            {
                "condition_id": cond_id,
                "name": "Custom Variation 1",
                "override_params": {"target_1": 25.0},
            }
        ],
    }
    run_resp = client.post("/api/v1/variant/run", json=run_req)
    assert run_resp.status_code == 200
    run_data = run_resp.json()
    assert run_data["strategy_id"] == strat_id
    assert len(run_data["rankings"]) >= 2
    assert "trades" in run_data

    # 6. Fetch VIX/IV Heatmap Analytics
    heatmap_resp = client.get("/api/v1/variant/analytics/vix-heatmap")
    assert heatmap_resp.status_code == 200
    h_data = heatmap_resp.json()
    assert "cells" in h_data
    assert len(h_data["cells"]) == 20

    # 7. Log live trade to live tradebook
    live_trade = {
        "dhan_order_id": "DHAN_ORD_987654",
        "strategy_id": strat_id,
        "symbol": "NIFTY26OCT25000PE",
        "signal_type": "BUY",
        "fill_time": now.isoformat(),
        "buy_price": 160.0,
        "sell_price": 210.0,
        "quantity": 50,
        "entry_vix": 14.25,
        "exit_vix": 14.90,
        "entry_iv": 26.50,
        "exit_iv": 28.20,
        "exit_reason": "TARGET_1",
        "realized_pnl": 2420.0,
        "brokerage_charges": 40.0,
        "stt_taxes": 13.12,
        "slippage_amount": 10.0,
    }
    log_resp = client.post("/api/v1/tradebook/live", json=live_trade)
    assert log_resp.status_code == 201
    assert log_resp.json()["dhan_order_id"] == "DHAN_ORD_987654"

    # 8. List live tradebook entries
    tb_list_resp = client.get("/api/v1/tradebook/live")
    assert tb_list_resp.status_code == 200
    assert len(tb_list_resp.json()) >= 1

    # 9. Delete custom library condition
    del_resp = client.delete(f"/api/v1/variant/library/{cond_id}")
    assert del_resp.status_code == 204
