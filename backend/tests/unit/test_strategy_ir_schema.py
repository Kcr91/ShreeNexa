"""Unit tests for StrategyIR Pydantic schemas, validation, migration, and JSON Schema export."""

from __future__ import annotations

import json
from typing import Any

import pytest
from app.strategy.ir import (
    AndNode,
    OptionLegsUniverse,
    SequenceNode,
    StrategyHorizon,
    StrategyIR,
    StrategyKind,
    StrategyType,
    export_strategy_ir_json_schema,
)
from app.strategy.migration import MigrationError, migrate_strategy_ir
from pydantic import ValidationError


def test_strategy_ir_worked_example_roundtrip() -> None:
    """Test full round-trip serialization of the canonical worked example from Spec §6.6."""
    raw: dict[str, Any] = {
        "ir_version": 1,
        "name": "ORB long with trend and momentum filter",
        "kind": "stock",
        "horizon": "swing",
        "strategy_type": "trend_following",
        "universe": {"type": "screener", "screener_id": 2, "refresh": "daily"},
        "timeframe": "5m",
        "session": {"segment": "NSE_EQ"},
        "indicators": {
            "rsi14": {"fn": "RSI", "params": {"length": 14}, "source": "close"},
            "ema200": {"fn": "EMA", "params": {"length": 200}, "source": "close"},
            "orh": {"fn": "OPENING_RANGE_HIGH", "params": {"minutes": 15}},
        },
        "entries": [
            {
                "id": "long",
                "side": "BUY",
                "when": {
                    "node": "And",
                    "children": [
                        {"node": "TimeWindow", "mode": "clock", "from": "09:30", "to": "14:30"},
                        {
                            "node": "PriceLevelBreak",
                            "level": {"ref": "orh"},
                            "direction": "above",
                            "after": {
                                "node": "And",
                                "children": [
                                    {
                                        "node": "IndicatorCompare",
                                        "left": {"ref": "rsi14"},
                                        "op": "<",
                                        "right": {"const": 60},
                                    },
                                    {
                                        "node": "IndicatorCompare",
                                        "left": {"field": "close"},
                                        "op": ">",
                                        "right": {"ref": "ema200"},
                                    },
                                ],
                            },
                        },
                    ],
                },
            }
        ],
        "exits": [
            {"id": "tp", "type": "target", "pct": 2.0},
            {"id": "sl", "type": "stop", "pct": 1.0},
            {"id": "eod", "type": "time", "at": "15:15"},
        ],
        "sizing": {"type": "risk_pct", "risk_pct": 1.0, "stop_ref": "sl"},
        "risk": {"max_positions": 5, "max_daily_loss_pct": 3.0},
    }

    strategy = StrategyIR.from_dict(raw)
    assert strategy.name == "ORB long with trend and momentum filter"
    assert strategy.kind == StrategyKind.STOCK
    assert strategy.horizon == StrategyHorizon.SWING
    assert strategy.strategy_type == StrategyType.TREND_FOLLOWING
    assert len(strategy.entries) == 1
    assert len(strategy.exits) == 3

    # Check serialization round-trip
    json_str = strategy.to_json()
    reloaded = StrategyIR.from_json(json_str)
    assert reloaded.name == strategy.name
    assert reloaded.horizon == strategy.horizon
    assert reloaded.strategy_type == strategy.strategy_type
    assert len(reloaded.entries) == 1
    assert isinstance(reloaded.entries[0].when, AndNode)


def test_option_legs_universe_and_strikes() -> None:
    """Validate option legs universe with ATM, Delta, Premium, and Absolute strike selectors."""
    option_ir_dict: dict[str, Any] = {
        "ir_version": 1,
        "name": "Nifty Short Straddle & Wings",
        "kind": "option",
        "horizon": "intraday",
        "strategy_type": "option_selling",
        "universe": {
            "type": "option_legs",
            "underlying": {"segment": "IDX_I", "security_id": "13", "symbol": "NIFTY"},
            "expiry_rule": {"type": "weekly", "offset": 0},
            "legs": [
                {
                    "id": "ce_short",
                    "option_type": "CE",
                    "strike": {"type": "atm", "offset": 0},
                    "side": "SELL",
                    "lots": 2,
                },
                {
                    "id": "pe_short",
                    "option_type": "PE",
                    "strike": {"type": "atm", "offset": 0},
                    "side": "SELL",
                    "lots": 2,
                },
                {
                    "id": "ce_wing",
                    "option_type": "CE",
                    "strike": {"type": "delta", "target": 0.15},
                    "side": "BUY",
                    "lots": 2,
                },
                {
                    "id": "pe_wing",
                    "option_type": "PE",
                    "strike": {"type": "premium", "target": 25.0},
                    "side": "BUY",
                    "lots": 2,
                },
                {
                    "id": "fixed_hedge",
                    "option_type": "PE",
                    "strike": {"type": "absolute", "strike": 24000.0},
                    "side": "BUY",
                    "lots": 1,
                },
            ],
        },
        "timeframe": "1m",
        "entries": [],
        "exits": [{"id": "sl", "type": "stop", "pct": 25.0}],
    }

    strategy = StrategyIR.from_dict(option_ir_dict)
    assert strategy.kind == StrategyKind.OPTION
    assert isinstance(strategy.universe, OptionLegsUniverse)
    assert len(strategy.universe.legs) == 5
    assert strategy.universe.legs[0].strike.type == "atm"
    assert strategy.universe.legs[2].strike.type == "delta"
    assert strategy.universe.legs[3].strike.type == "premium"
    assert strategy.universe.legs[4].strike.type == "absolute"


def test_signal_node_grammar_variants() -> None:
    """Test all signal node types including Sequence, Persist, CrossOver, and Regime."""
    signal_tree: dict[str, Any] = {
        "node": "And",
        "children": [
            {
                "node": "Sequence",
                "within": 10,
                "steps": [
                    {
                        "node": "IndicatorCompare",
                        "left": {"ref": "rsi"},
                        "op": "<",
                        "right": {"const": 30},
                    },
                    {
                        "node": "CrossOver",
                        "left": {"ref": "macd_line"},
                        "right": {"ref": "macd_signal"},
                    },
                ],
            },
            {
                "node": "Persist",
                "bars": 3,
                "child": {
                    "node": "IndicatorCompare",
                    "left": {"field": "close"},
                    "op": ">",
                    "right": {"ref": "vwap"},
                },
            },
            {
                "node": "PctChange",
                "source": "close",
                "lookback": 5,
                "op": ">",
                "value": 1.5,
            },
            {
                "node": "Regime",
                "detector": "adx_trend",
                "state": "trending_bullish",
            },
        ],
    }

    raw_ir: dict[str, Any] = {
        "name": "Grammar Test",
        "kind": "stock",
        "horizon": "intraday",
        "strategy_type": "mean_reversion",
        "universe": {
            "type": "static",
            "instruments": [{"segment": "NSE_EQ", "security_id": "RELIANCE"}],
        },
        "entries": [{"id": "entry_1", "side": "BUY", "when": signal_tree}],
    }

    strategy = StrategyIR.from_dict(raw_ir)
    entry_when = strategy.entries[0].when
    assert isinstance(entry_when, AndNode)
    assert len(entry_when.children) == 4
    assert isinstance(entry_when.children[0], SequenceNode)


def test_invalid_strategy_rejections() -> None:
    """Verify schema rejects invalid nodes, missing required fields, and malformed types."""
    # 1. Missing required horizon
    with pytest.raises(ValidationError):
        StrategyIR.model_validate(
            {
                "name": "Invalid IR",
                "kind": "stock",
                "strategy_type": "trend_following",
                "universe": {
                    "type": "static",
                    "instruments": [{"segment": "NSE_EQ", "security_id": "1"}],
                },
            }
        )

    # 2. Missing required strategy_type
    with pytest.raises(ValidationError):
        StrategyIR.model_validate(
            {
                "name": "Invalid IR",
                "kind": "stock",
                "horizon": "swing",
                "universe": {
                    "type": "static",
                    "instruments": [{"segment": "NSE_EQ", "security_id": "1"}],
                },
            }
        )

    # 3. Invalid enum values
    with pytest.raises(ValidationError):
        StrategyIR.model_validate(
            {
                "name": "Invalid IR",
                "kind": "crypto_unknown",
                "horizon": "swing",
                "strategy_type": "trend_following",
                "universe": {
                    "type": "static",
                    "instruments": [{"segment": "NSE_EQ", "security_id": "1"}],
                },
            }
        )

    # 4. Empty static instruments list
    with pytest.raises(ValidationError):
        StrategyIR.model_validate(
            {
                "name": "Invalid IR",
                "kind": "stock",
                "horizon": "swing",
                "strategy_type": "trend_following",
                "universe": {"type": "static", "instruments": []},
            }
        )


def test_strategy_ir_migration() -> None:
    """Test legacy dictionary migration to target StrategyIR schema."""
    legacy_dict: dict[str, Any] = {
        "name": "Legacy V0 Strategy",
        "universe": ["1333", "2885"],  # Legacy bare list of string security IDs
        "sizing": 50.0,  # Legacy scalar sizing percentage
        "entries": [],
    }

    migrated = migrate_strategy_ir(legacy_dict, target_version=1)
    assert migrated.ir_version == 1
    assert migrated.horizon == StrategyHorizon.SWING
    assert migrated.strategy_type == StrategyType.TREND_FOLLOWING
    assert migrated.kind == StrategyKind.STOCK
    assert migrated.universe.type == "static"
    assert len(migrated.universe.instruments) == 2
    assert migrated.sizing.pct == 50.0

    # Test rejection of incompatible or non-dict payloads
    with pytest.raises(MigrationError):
        migrate_strategy_ir("not_a_dict")  # type: ignore[arg-type]


def test_json_schema_export() -> None:
    """Test JSON Schema export compliance."""
    schema = export_strategy_ir_json_schema()
    assert isinstance(schema, dict)
    assert "properties" in schema
    assert "horizon" in schema["properties"]
    assert "strategy_type" in schema["properties"]
    assert "universe" in schema["properties"]
    assert "$defs" in schema
    assert "OptionLegDef" in schema["$defs"]

    # Verify JSON serializability
    schema_json = json.dumps(schema)
    assert len(schema_json) > 1000
