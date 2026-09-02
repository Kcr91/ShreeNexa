"""REST API endpoints for StrategyIR Schema, Validation, and Template Generation."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.strategy.compiler import CompiledStrategy
from app.strategy.ir import (
    StrategyHorizon,
    StrategyIR,
    StrategyKind,
    StrategyType,
    export_strategy_ir_json_schema,
)

router = APIRouter(prefix="/api/v1/strategy", tags=["Strategy IR"])


class ValidateStrategyRequest(BaseModel):
    """Payload to validate a StrategyIR instance."""

    strategy_ir: dict[str, Any]


class ValidateStrategyResponse(BaseModel):
    """Response detailing validation status and AST complexity."""

    is_valid: bool
    strategy_id: str | None = None
    name: str | None = None
    indicator_count: int = 0
    entry_rules_count: int = 0
    exit_rules_count: int = 0
    errors: list[str] = Field(default_factory=list)


@router.post("/validate", response_model=ValidateStrategyResponse)
def validate_strategy_ir(req: ValidateStrategyRequest) -> ValidateStrategyResponse:
    """Validate a StrategyIR dictionary against the Pydantic schema and graph compiler."""
    try:
        ir = StrategyIR.from_dict(req.strategy_ir)
        # Verify it compiles cleanly into execution graph
        CompiledStrategy(ir)

        return ValidateStrategyResponse(
            is_valid=True,
            strategy_id=ir.name.lower().replace(" ", "-"),
            name=ir.name,
            indicator_count=len(ir.indicators),
            entry_rules_count=len(ir.entries),
            exit_rules_count=len(ir.exits),
            errors=[],
        )
    except Exception as e:
        return ValidateStrategyResponse(
            is_valid=False,
            errors=[str(e)],
        )


@router.get("/schema")
def get_strategy_ir_schema() -> dict[str, Any]:
    """Get the full OpenAPI/JSON schema for StrategyIR."""
    return export_strategy_ir_json_schema()


@router.get("/templates")
def get_strategy_templates() -> list[dict[str, Any]]:
    """Return pre-built standard stock strategy templates in canonical StrategyIR format."""
    dual_ema: dict[str, Any] = {
        "ir_version": 1,
        "name": "Dual EMA Crossover",
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

    rsi_pullback: dict[str, Any] = {
        "ir_version": 1,
        "name": "RSI Mean Reversion",
        "kind": StrategyKind.STOCK.value,
        "horizon": StrategyHorizon.INTRADAY.value,
        "strategy_type": StrategyType.MEAN_REVERSION.value,
        "universe": {"type": "index", "index_name": "NIFTY 50"},
        "timeframe": "15m",
        "session": {"segment": "NSE_EQ"},
        "indicators": {
            "rsi_14": {"fn": "RSI", "params": {"length": 14}, "source": "close"},
            "sma_200": {"fn": "SMA", "params": {"length": 200}, "source": "close"},
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

    return [dual_ema, rsi_pullback]
