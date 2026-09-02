"""REST API endpoints for Option Strategy Margin Calculation and Hedging Relief."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.analytics.options_margin import BasketMarginResult
from app.analytics.strategy_builder import OptionLeg
from app.dhan.margin_adapter import dhan_margin_adapter

router = APIRouter(prefix="/api/v1/options/margin", tags=["Option Margin"])


class CalculateMarginRequest(BaseModel):
    """Payload for basket margin and hedging relief calculation."""

    underlying: str
    spot_price: float = Field(..., gt=0)
    legs: list[OptionLeg] = Field(default_factory=list)
    broker_response_override: dict[str, Any] | None = None


@router.post("/calculate", response_model=BasketMarginResult)
def calculate_margin(req: CalculateMarginRequest) -> BasketMarginResult:
    """Calculate SPAN, Exposure, Gross Margin, Net Required Margin, and Hedging Relief."""
    return dhan_margin_adapter.calculate_basket_margin(
        underlying=req.underlying,
        spot_price=req.spot_price,
        legs=req.legs,
        broker_response_override=req.broker_response_override,
    )
