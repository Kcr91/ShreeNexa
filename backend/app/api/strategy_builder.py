"""REST API endpoints for Multi-Leg Option Strategy Builder (payoffs, breakevens, net Greeks)."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Literal

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

from app.analytics.strategy_builder import (
    MultiLegStrategy,
    StrategyAnalyticsResult,
    calculate_strategy_payoff_and_greeks,
    create_standard_strategy,
)

router = APIRouter(prefix="/api/v1/options/strategy", tags=["Option Strategy Builder"])


class AnalyzeStrategyRequest(BaseModel):
    """Payload for analyzing a custom multi-leg option strategy."""

    strategy: MultiLegStrategy
    target_days_forward: int = Field(default=0, ge=0)
    price_range_pct: float = Field(default=0.10, gt=0, le=0.50)
    num_points: int = Field(default=41, ge=11, le=101)


@router.post("/analyze", response_model=StrategyAnalyticsResult)
def analyze_strategy(req: AnalyzeStrategyRequest) -> StrategyAnalyticsResult:
    """Compute payoff profile, breakevens, extrema, and net Greeks for a multi-leg strategy."""
    return calculate_strategy_payoff_and_greeks(
        strategy=req.strategy,
        target_days_forward=req.target_days_forward,
        price_range_pct=req.price_range_pct,
        num_points=req.num_points,
    )


@router.get("/template", response_model=MultiLegStrategy)
def get_strategy_template(
    strategy_type: Literal[
        "BULL_CALL_SPREAD",
        "BEAR_PUT_SPREAD",
        "STRADDLE",
        "STRANGLE",
        "IRON_CONDOR",
        "IRON_BUTTERFLY",
    ] = Query(..., description="Standard strategy template identifier"),
    underlying: str = Query(default="NIFTY", description="Underlying symbol"),
    spot_price: float | None = Query(default=None, description="Optional custom spot price"),
) -> MultiLegStrategy:
    """Retrieve pre-built standard multi-leg option strategy."""
    spot = spot_price or (25000.0 if underlying.upper() == "NIFTY" else 52000.0)
    step = 50.0 if "NIFTY" in underlying.upper() else 100.0
    lot_size = 25 if "NIFTY" in underlying.upper() else 15
    atm_strike = round(spot / step) * step
    expiry = date.today() + timedelta(days=7)

    return create_standard_strategy(
        strategy_type=strategy_type,
        underlying=underlying.upper(),
        spot_price=spot,
        atm_strike=atm_strike,
        step=step,
        lot_size=lot_size,
        expiry_date=expiry,
    )
