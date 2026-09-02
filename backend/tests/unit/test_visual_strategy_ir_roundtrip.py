"""Unit tests for Visual Strategy Builder StrategyIR validation, templates, and compilation."""

from __future__ import annotations

from typing import Any
from zoneinfo import ZoneInfo

from fastapi.testclient import TestClient

from app.main import app
from app.strategy.compiler import CompiledStrategy
from app.strategy.ir import (
    StrategyHorizon,
    StrategyIR,
    StrategyKind,
    StrategyType,
)

IST = ZoneInfo("Asia/Kolkata")
client = TestClient(app)


def test_canonical_strategy_ir_schema_and_compile() -> None:
    raw: dict[str, Any] = {
        "ir_version": 1,
        "name": "Trend Surfer",
        "kind": StrategyKind.STOCK.value,
        "horizon": StrategyHorizon.INTRADAY.value,
        "strategy_type": StrategyType.TREND_FOLLOWING.value,
        "universe": {"type": "index", "index_name": "NIFTY 50"},
        "timeframe": "5m",
        "session": {"segment": "NSE_EQ"},
        "indicators": {
            "ema_fast": {"fn": "EMA", "params": {"length": 9}, "source": "close"},
            "ema_slow": {"fn": "EMA", "params": {"length": 21}, "source": "close"},
        },
        "entries": [
            {
                "id": "entry_1",
                "side": "BUY",
                "when": {
                    "node": "CrossOver",
                    "left": {"ref": "ema_fast"},
                    "right": {"ref": "ema_slow"},
                },
            }
        ],
        "exits": [
            {"id": "tp", "type": "target", "pct": 3.0},
            {"id": "sl", "type": "stop", "pct": 1.5},
        ],
        "sizing": {"type": "fixed_value", "value": 50000.0},
        "risk": {"max_positions": 5, "max_daily_loss_pct": 3.0},
    }

    ir = StrategyIR.from_dict(raw)

    # Validate serialization round-trip
    d = ir.to_dict()
    reconstructed = StrategyIR.from_dict(d)
    assert reconstructed.name == "Trend Surfer"
    assert len(reconstructed.indicators) == 2
    assert len(reconstructed.entries) == 1

    # Verify compilation into executable graph
    compiled = CompiledStrategy(ir)
    assert compiled.strategy.name == "Trend Surfer"


def test_strategy_ir_validate_api_endpoint() -> None:
    payload = {
        "strategy_ir": {
            "ir_version": 1,
            "name": "RSI Pullback",
            "kind": "stock",
            "horizon": "intraday",
            "strategy_type": "mean_reversion",
            "universe": {"type": "index", "index_name": "NIFTY 50"},
            "timeframe": "15m",
            "session": {"segment": "NSE_EQ"},
            "indicators": {
                "rsi_14": {"fn": "RSI", "params": {"length": 14}, "source": "close"},
            },
            "entries": [
                {
                    "id": "entry_1",
                    "side": "BUY",
                    "when": {
                        "node": "IndicatorCompare",
                        "left": {"ref": "rsi_14"},
                        "op": "<",
                        "right": {"const": 30.0},
                    },
                }
            ],
            "exits": [
                {"id": "tp", "type": "target", "pct": 4.0},
                {"id": "sl", "type": "stop", "pct": 2.0},
            ],
            "sizing": {"type": "fixed_value", "value": 50000.0},
            "risk": {"max_positions": 5, "max_daily_loss_pct": 3.0},
        }
    }

    resp = client.post("/api/v1/strategy/validate", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["is_valid"] is True
    assert data["name"] == "RSI Pullback"
    assert data["indicator_count"] == 1
    assert data["entry_rules_count"] == 1


def test_strategy_ir_schema_and_templates_api() -> None:
    # Test schema
    resp_schema = client.get("/api/v1/strategy/schema")
    assert resp_schema.status_code == 200
    assert "properties" in resp_schema.json()

    # Test templates
    resp_templates = client.get("/api/v1/strategy/templates")
    assert resp_templates.status_code == 200
    templates = resp_templates.json()
    assert len(templates) >= 2
    assert templates[0]["name"] == "Dual EMA Crossover"
