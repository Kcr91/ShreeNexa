"""Options analytics REST API for Black-76 pricing, Greeks, and IV solver."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.analytics.greeks import (
    DayCountConvention,
    ForwardSource,
    OptionConventions,
    OptionPricingResult,
    OptionType,
    price_black76_scalar,
    price_black76_vector,
    resolve_forward_price,
    solve_implied_volatility,
)

router = APIRouter(prefix="/api/v1/options", tags=["Options Analytics"])


class PriceOptionRequest(BaseModel):
    """Request payload for pricing a single option contract."""

    spot_ltp: float = Field(..., gt=0, description="Underlying spot LTP")
    strike: float = Field(..., gt=0, description="Contract strike price")
    t_years: float = Field(..., ge=0, description="Annualized time to expiry")
    rate: float = Field(default=0.07, description="Risk-free rate (e.g. 0.07 for 7%)")
    vol: float = Field(default=0.15, gt=0, description="Annualized volatility")
    option_type: OptionType = Field(default=OptionType.CALL, description="CALL or PUT")
    futures_ltp: float | None = Field(default=None, description="Futures LTP if available")
    atm_call_ltp: float | None = Field(default=None, description="ATM Call LTP for forward")
    atm_put_ltp: float | None = Field(default=None, description="ATM Put LTP for forward")
    day_count: DayCountConvention = Field(default=DayCountConvention.ACT_365)


class SolveIvRequest(BaseModel):
    """Request payload for solving implied volatility."""

    market_price: float = Field(..., gt=0, description="Observed market price/LTP of option")
    spot_ltp: float = Field(..., gt=0, description="Underlying spot LTP")
    strike: float = Field(..., gt=0, description="Contract strike price")
    t_years: float = Field(..., ge=0, description="Annualized time to expiry")
    rate: float = Field(default=0.07, description="Risk-free rate")
    option_type: OptionType = Field(default=OptionType.CALL, description="CALL or PUT")
    futures_ltp: float | None = Field(default=None, description="Futures LTP if available")
    atm_call_ltp: float | None = Field(default=None, description="ATM Call LTP for forward")
    atm_put_ltp: float | None = Field(default=None, description="ATM Put LTP for forward")


class SolveIvResponse(BaseModel):
    """Response from IV solver."""

    iv: float
    is_reliable: bool
    unreliable_reason: str | None
    forward_used: float
    forward_source: ForwardSource


class BatchPriceRequest(BaseModel):
    """Request payload for batch pricing option contracts."""

    forwards: list[float]
    strikes: list[float]
    t_years: list[float]
    rates: list[float]
    vols: list[float]
    is_call: list[bool]


class BatchPriceResponse(BaseModel):
    """Batch calculation results."""

    prices: list[float]
    deltas: list[float]
    gammas: list[float]
    thetas: list[float]
    vegas: list[float]


@router.post("/price", response_model=OptionPricingResult)
def price_option(req: PriceOptionRequest) -> OptionPricingResult:
    """Compute Black-76 theoretical price, Greeks, and forward price for an option."""
    f, src = resolve_forward_price(
        spot_ltp=req.spot_ltp,
        strike=req.strike,
        rate=req.rate,
        t_years=req.t_years,
        futures_ltp=req.futures_ltp,
        atm_call_ltp=req.atm_call_ltp,
        atm_put_ltp=req.atm_put_ltp,
    )
    conv = OptionConventions(
        day_count=req.day_count,
        risk_free_rate=req.rate,
        annualization_factor=365 if req.day_count == DayCountConvention.ACT_365 else 252,
    )
    return price_black76_scalar(
        forward=f,
        strike=req.strike,
        t_years=req.t_years,
        rate=req.rate,
        vol=req.vol,
        option_type=req.option_type,
        convention=conv,
        forward_source=src,
    )


@router.post("/solve-iv", response_model=SolveIvResponse)
def solve_iv(req: SolveIvRequest) -> SolveIvResponse:
    """Solve implied volatility using Brent's method with vega and intrinsic guards."""
    f, src = resolve_forward_price(
        spot_ltp=req.spot_ltp,
        strike=req.strike,
        rate=req.rate,
        t_years=req.t_years,
        futures_ltp=req.futures_ltp,
        atm_call_ltp=req.atm_call_ltp,
        atm_put_ltp=req.atm_put_ltp,
    )
    iv, reliable, reason = solve_implied_volatility(
        market_price=req.market_price,
        forward=f,
        strike=req.strike,
        t_years=req.t_years,
        rate=req.rate,
        option_type=req.option_type,
    )
    return SolveIvResponse(
        iv=iv,
        is_reliable=reliable,
        unreliable_reason=reason,
        forward_used=f,
        forward_source=src,
    )


@router.post("/price-batch", response_model=BatchPriceResponse)
def price_batch(req: BatchPriceRequest) -> BatchPriceResponse:
    """Compute batch Black-76 prices and Greeks for option contract arrays."""
    if not (
        len(req.forwards)
        == len(req.strikes)
        == len(req.t_years)
        == len(req.rates)
        == len(req.vols)
        == len(req.is_call)
    ):
        raise HTTPException(
            status_code=422,
            detail="All input lists in batch request must have identical lengths.",
        )
    res = price_black76_vector(
        forwards=req.forwards,
        strikes=req.strikes,
        t_years=req.t_years,
        rates=req.rates,
        vols=req.vols,
        is_call=req.is_call,
    )
    return BatchPriceResponse(
        prices=res["prices"],
        deltas=res["deltas"],
        gammas=res["gammas"],
        thetas=res["thetas"],
        vegas=res["vegas"],
    )
