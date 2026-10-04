"""Unit test suite for Feature 3: Strategy Builder & Python Code Exporter."""

from __future__ import annotations

import ast
from collections.abc import Generator
from datetime import time
from typing import Any

import pandas as pd
import pytest
from app.api.deps import require_csrf, require_non_demo_session, require_session
from app.api.strategy_engine import get_db_engine
from app.main import app
from app.strategy.code_generator import export_strategy_python_script
from app.strategy.evaluator import StrategyEvaluator
from app.strategy.mcx_handler import (
    get_commodity_specs,
    is_within_session,
    validate_mcx_quantity,
)
from app.strategy.models import (
    Part2Entry,
    Part3Stoploss,
    Part4Exit,
    StrategyCondition,
    StrategyDefinition,
    TargetRule,
    TrailingSLRule,
)
from app.strategy.models import (
    metadata as strategy_metadata,
)
from app.strategy.parser import parse_and_validate_strategy
from app.strategy.strike_resolver import (
    calculate_atm_strike,
    get_strike_interval,
    resolve_strike,
)
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.pool import StaticPool


@pytest.fixture
def sqlite_engine() -> Generator[Engine]:
    """In-memory SQLite engine for strategy testing."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    strategy_metadata.create_all(engine)
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


def sample_stock_strategy() -> dict[str, Any]:
    """Return a valid Stock Strategy JSON definition."""
    return {
        "strategy_type": "STOCK",
        "name": "Intraday Breakout Strategy",
        "version": 1,
        "part_1_scope": {
            "source_type": "WATCHLIST",
            "fallback_watchlist": ["RELIANCE", "TCS", "INFY"],
            "trading_session": {
                "start_time": "09:16:00",
                "no_new_entries_after": "14:30:00",
                "force_square_off": "15:15:00",
            },
        },
        "part_2_entry": {
            "direction": "LONG",
            "trigger_timeframe": "15min",
            "logic": "AND",
            "conditions": [
                {
                    "price_reference": "SPOT",
                    "timeframe": "15min",
                    "indicator": "RSI",
                    "period": 14,
                    "operator": ">",
                    "value": 55,
                }
            ],
        },
        "part_3_stoploss": {
            "sl_reference": "SPOT",
            "sl_type": "PERCENTAGE",
            "percentage_val": 2.0,
        },
        "part_4_exit": {
            "exit_reference": "SPOT",
            "targets": [
                {
                    "target_number": 1,
                    "percentage_gain": 4.0,
                    "exit_lots_percentage": 50.0,
                },
                {
                    "target_number": 2,
                    "percentage_gain": 8.0,
                    "exit_lots_percentage": 50.0,
                },
            ],
            "trailing_sl": {
                "enabled": True,
                "mode": "SPOT_PERCENTAGE",
                "trail_after_target": 1,
                "step_percentage": 1.0,
            },
        },
    }


def sample_options_dual_price_strategy() -> dict[str, Any]:
    """Return a valid Options Strategy with Dual-Price Reference."""
    return {
        "strategy_type": "OPTION",
        "name": "Nifty Open-High Put Buying",
        "version": 1,
        "part_1_scope": {
            "source_type": "INDEX_OPTION",
            "underlying_symbol": "NIFTY",
            "option_right": "PE",
            "expiry_type": "CURRENT_WEEK",
            "strike_selection": {"mode": "ATM_OFFSET", "offset": 0},
            "trading_session": {
                "start_time": "09:16:00",
                "no_new_entries_after": "14:30:00",
                "force_square_off": "15:15:00",
            },
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
                },
                {
                    "price_reference": "OPTION_PREMIUM",
                    "timeframe": "1min",
                    "indicator": "RSI",
                    "period": 14,
                    "operator": ">",
                    "value": 50,
                },
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
                    "percentage_gain": 30.0,
                    "exit_lots_percentage": 50.0,
                },
                {
                    "target_number": 2,
                    "percentage_gain": 60.0,
                    "exit_lots_percentage": 50.0,
                },
            ],
            "trailing_sl": {
                "enabled": True,
                "mode": "OPTION_PERCENTAGE",
                "trail_after_target": 1,
                "step_percentage": 10.0,
            },
        },
    }


def test_strategy_parser_and_validation() -> None:
    """Test strategy configuration validation."""
    valid_strat = sample_stock_strategy()
    res = parse_and_validate_strategy(valid_strat)
    assert res["valid"] is True
    assert res["strategy"] is not None
    assert isinstance(res["strategy"], StrategyDefinition)
    assert len(res["errors"]) == 0

    # Invalid Stop-Loss
    invalid_strat = sample_stock_strategy()
    invalid_strat["part_3_stoploss"]["percentage_val"] = -5.0
    res_invalid = parse_and_validate_strategy(invalid_strat)
    assert res_invalid["valid"] is False
    assert len(res_invalid["errors"]) > 0

    # Invalid Target percentages (> 100%)
    invalid_target_strat = sample_stock_strategy()
    invalid_target_strat["part_4_exit"]["targets"] = [
        {"target_number": 1, "percentage_gain": 5.0, "exit_lots_percentage": 60.0},
        {"target_number": 2, "percentage_gain": 10.0, "exit_lots_percentage": 60.0},
    ]
    res_tgt = parse_and_validate_strategy(invalid_target_strat)
    assert res_tgt["valid"] is False
    assert any("exceeds 100%" in err for err in res_tgt["errors"])


def test_dual_price_evaluator() -> None:
    """Test Dual-Price Reference evaluator on Spot and Option DataFrames."""
    spot_df = pd.DataFrame(
        {
            "open": [24500.0, 24500.0],
            "high": [24550.0, 24500.0],  # Open == High on second bar
            "low": [24480.0, 24400.0],
            "close": [24520.0, 24420.0],
            "volume": [10000, 20000],
        }
    )

    opt_df = pd.DataFrame(
        {
            "open": [150.0, 160.0, 170.0, 180.0, 190.0],
            "high": [165.0, 175.0, 185.0, 195.0, 205.0],
            "low": [145.0, 155.0, 165.0, 175.0, 185.0],
            "close": [160.0, 170.0, 180.0, 190.0, 200.0],
            "volume": [5000, 6000, 7000, 8000, 9000],
        }
    )

    entry_rules = Part2Entry(
        direction="LONG",
        trigger_timeframe="1min",
        logic="AND",
        conditions=[
            StrategyCondition(
                price_reference="SPOT",
                timeframe="1min",
                pattern="OPEN_EQ_HIGH",
            ),
            StrategyCondition(
                price_reference="OPTION_PREMIUM",
                timeframe="1min",
                indicator="RSI",
                period=2,
                operator=">",
                value=50.0,
            ),
        ],
    )

    signal = StrategyEvaluator.evaluate_entry(entry_rules, spot_df, opt_df)
    assert signal is True

    # Test exit calculation
    sl_config = Part3Stoploss(
        sl_reference="OPTION_PREMIUM", sl_type="PERCENTAGE", percentage_val=20.0
    )
    exit_config = Part4Exit(
        exit_reference="OPTION_PREMIUM",
        targets=[
            TargetRule(target_number=1, percentage_gain=30.0, exit_lots_percentage=50.0),
            TargetRule(target_number=2, percentage_gain=60.0, exit_lots_percentage=50.0),
        ],
        trailing_sl=TrailingSLRule(
            enabled=True,
            mode="OPTION_PERCENTAGE",
            trail_after_target=1,
            step_percentage=10.0,
        ),
    )

    exit_levels = StrategyEvaluator.calculate_exit_levels(
        entry_price=200.0,
        direction="LONG",
        stoploss=sl_config,
        exit_rules=exit_config,
    )

    assert exit_levels["entry_price"] == 200.0
    assert exit_levels["stop_loss_price"] == 160.0  # 20% SL below 200
    assert exit_levels["targets"][0]["target_price"] == 260.0  # 30% above 200
    assert exit_levels["targets"][1]["target_price"] == 320.0  # 60% above 200


def test_options_strike_resolver() -> None:
    """Test options strike interval and ATM offset calculation."""
    assert get_strike_interval("NIFTY") == 50.0
    assert get_strike_interval("BANKNIFTY") == 100.0
    assert get_strike_interval("FINNIFTY") == 50.0

    # NIFTY Spot at 24520 -> ATM is 24500
    atm = calculate_atm_strike(24520.0, 50.0)
    assert atm == 24500.0

    # Call OTM +1 -> 24550
    ce_otm_1 = resolve_strike("NIFTY", 24520.0, mode="ATM_OFFSET", offset=1, option_right="CE")
    assert ce_otm_1 == 24550.0

    # Put OTM +1 -> 24450
    pe_otm_1 = resolve_strike("NIFTY", 24520.0, mode="ATM_OFFSET", offset=1, option_right="PE")
    assert pe_otm_1 == 24450.0


def test_mcx_commodity_specs_and_session() -> None:
    """Test MCX commodity specifications and trading session rules."""
    gold_specs = get_commodity_specs("GOLD")
    assert gold_specs is not None
    assert gold_specs.lot_size == 100
    assert gold_specs.tick_size == 1.0

    crude_specs = get_commodity_specs("CRUDEOIL")
    assert crude_specs is not None
    assert crude_specs.lot_size == 100

    # Validate quantities
    valid_q = validate_mcx_quantity("CRUDEOIL", 200)
    assert valid_q["valid"] is True
    assert valid_q["lots"] == 2

    invalid_q = validate_mcx_quantity("CRUDEOIL", 150)
    assert invalid_q["valid"] is False

    # Session window test
    assert is_within_session(time(14, 0, 0), "09:00:00", "23:30:00") is True
    assert is_within_session(time(8, 30, 0), "09:00:00", "23:30:00") is False


def test_python_code_generator_syntax() -> None:
    """Test that standalone Python code generator produces syntactically valid Python code."""
    opt_strat = sample_options_dual_price_strategy()
    code = export_strategy_python_script(opt_strat)

    assert "import pandas as pd" in code
    assert "from dhanhq import dhanhq" in code
    assert "Nifty Open-High Put Buying" in code
    assert "def check_entry_signals" in code
    assert "def run_strategy" in code

    # Verify python syntax using AST parser
    parsed_ast = ast.parse(code)
    assert parsed_ast is not None


def test_strategy_api_crud_and_versions(client: TestClient) -> None:
    """Test full FastAPI REST endpoints for Strategy Builder."""
    strat_payload = sample_stock_strategy()

    # 1. Validate endpoint
    val_resp = client.post("/api/v1/strategy/config/validate", json=strat_payload)
    assert val_resp.status_code == 200
    assert val_resp.json()["valid"] is True

    # 2. Create strategy
    create_resp = client.post(
        "/api/v1/strategy/configs",
        json={
            "name": strat_payload["name"],
            "description": "Test Stock Strategy",
            "strategy_type": strat_payload["strategy_type"],
            "config_json": strat_payload,
            "is_active": True,
        },
    )
    assert create_resp.status_code == 201
    created = create_resp.json()
    strat_id = created["id"]
    assert created["name"] == "Intraday Breakout Strategy"
    assert created["current_version"] == 1

    # 3. Get strategy detail
    get_resp = client.get(f"/api/v1/strategy/configs/{strat_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == strat_id

    # 4. Update strategy (triggers version increment)
    updated_config = dict(strat_payload)
    updated_config["part_3_stoploss"]["percentage_val"] = 2.5
    update_resp = client.put(
        f"/api/v1/strategy/configs/{strat_id}",
        json={
            "config_json": updated_config,
            "change_summary": "Adjusted SL to 2.5%",
        },
    )
    assert update_resp.status_code == 200
    updated = update_resp.json()
    assert updated["current_version"] == 2

    # 5. Version history
    ver_resp = client.get(f"/api/v1/strategy/configs/{strat_id}/versions")
    assert ver_resp.status_code == 200
    versions = ver_resp.json()
    assert len(versions) == 2
    assert versions[0]["version"] == 2
    assert versions[1]["version"] == 1

    # 6. Export Python script
    export_resp = client.post(f"/api/v1/strategy/configs/{strat_id}/export-python")
    assert export_resp.status_code == 200
    export_data = export_resp.json()
    assert "code_content" in export_data
    assert "filename" in export_data
    assert export_data["filename"].endswith(".py")
    assert "dhanhq" in export_data["code_content"]

    # 7. Import strategy JSON
    import_payload = sample_options_dual_price_strategy()
    import_resp = client.post("/api/v1/strategy/configs/import", json=import_payload)
    assert import_resp.status_code == 201
    imported = import_resp.json()
    assert imported["strategy_type"] == "OPTION"
    assert imported["name"] == "Nifty Open-High Put Buying"

    # 8. List strategies
    list_resp = client.get("/api/v1/strategy/configs")
    assert list_resp.status_code == 200
    all_strats = list_resp.json()
    assert len(all_strats) == 2

    # 9. Delete strategy
    del_resp = client.delete(f"/api/v1/strategy/configs/{strat_id}")
    assert del_resp.status_code == 204
