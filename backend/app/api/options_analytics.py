"""REST API endpoints for Option Chain Analytics."""

from __future__ import annotations

import math
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.analytics.greeks import OptionType, price_black76_scalar
from app.analytics.options_analytics import (
    OptionsAnalyticsBundle,
    TermStructurePoint,
    calculate_atm_iv,
    calculate_iv_rank_and_percentile,
    calculate_iv_skew_and_smile,
    calculate_max_pain,
    calculate_put_call_ratios,
    calculate_term_structure,
)

IST = ZoneInfo("Asia/Kolkata")
router = APIRouter(prefix="/api/v1/options/analytics", tags=["Options Analytics"])


class ComputeAnalyticsRequest(BaseModel):
    """Payload for on-demand options analytics computation."""

    underlying: str
    spot_price: float = Field(..., gt=0)
    expiry_date: date
    strikes: list[float] = Field(..., min_length=1)
    call_ivs: list[float]
    put_ivs: list[float]
    call_ois: list[int]
    put_ois: list[int]
    call_vols: list[int]
    put_vols: list[int]
    call_deltas: list[float]
    put_deltas: list[float]
    historical_daily_ivs: list[float] = Field(default_factory=list)
    term_structure_points: list[TermStructurePoint] = Field(default_factory=list)


def _build_synthetic_analytics_bundle(underlying: str) -> OptionsAnalyticsBundle:
    """Generate high-fidelity synthetic analytics bundle for testing/dashboard demo."""
    spot = 25000.0 if underlying.upper() == "NIFTY" else 52000.0
    step = 50.0 if "NIFTY" in underlying.upper() else 100.0
    atm_strike = round(spot / step) * step
    now = datetime.now(tz=IST)
    exp = date.fromordinal(date.today().toordinal() + 7)

    strikes: list[float] = []
    call_ivs: list[float] = []
    put_ivs: list[float] = []
    call_ois: list[int] = []
    put_ois: list[int] = []
    call_vols: list[int] = []
    put_vols: list[int] = []
    call_deltas: list[float] = []
    put_deltas: list[float] = []

    for i in range(-10, 11):
        k = atm_strike + i * step
        strikes.append(k)

        # Skewed IV: OTM puts higher IV, OTM calls lower IV
        skew_factor = (atm_strike - k) / spot
        c_iv = max(0.08, 0.14 - 0.05 * skew_factor + 0.001 * (i**2))
        p_iv = max(0.08, 0.14 + 0.12 * skew_factor + 0.001 * (i**2))
        call_ivs.append(round(c_iv, 4))
        put_ivs.append(round(p_iv, 4))

        # OI distributions peaking near ATM / immediate OTM
        c_oi = int(max(10000, 450000 - abs(i) * 35000 + (10000 if i == 2 else 0)))
        p_oi = int(max(10000, 520000 - abs(i) * 38000 + (25000 if i == -2 else 0)))
        call_ois.append(c_oi)
        put_ois.append(p_oi)

        call_vols.append(int(c_oi * 0.75))
        put_vols.append(int(p_oi * 0.85))

        res_c = price_black76_scalar(
            forward=spot * 1.003,
            strike=k,
            t_years=7.0 / 365.0,
            rate=0.07,
            vol=c_iv,
            option_type=OptionType.CALL,
        )
        res_p = price_black76_scalar(
            forward=spot * 1.003,
            strike=k,
            t_years=7.0 / 365.0,
            rate=0.07,
            vol=p_iv,
            option_type=OptionType.PUT,
        )
        call_deltas.append(res_c.delta)
        put_deltas.append(res_p.delta)

    # 1. ATM IV
    atm_iv = calculate_atm_iv(spot, strikes, call_ivs, put_ivs)

    # 2. IV Rank & Percentile (with 252 historical daily samples)
    hist_ivs = [0.11 + 0.08 * (math.sin(d / 15.0) ** 2) for d in range(252)]
    iv_rank = calculate_iv_rank_and_percentile(atm_iv, hist_ivs, min_history_days=30)

    # 3. PCR
    pcr = calculate_put_call_ratios(call_ois, put_ois, call_vols, put_vols)

    # 4. Max Pain
    max_pain = calculate_max_pain(strikes, call_ois, put_ois, spot)

    # 5. Skew & Smile
    skew = calculate_iv_skew_and_smile(
        spot, strikes, call_ivs, put_ivs, call_deltas, put_deltas, exp, spot * 1.003
    )

    # 6. Term Structure
    term_pts = [
        TermStructurePoint(
            expiry_date=date.today() + timedelta(days=d),
            days_to_expiry=d,
            atm_iv=round(0.135 + 0.005 * math.log(d / 7.0 + 1.0), 4),
            forward_price=round(spot * (1.0 + 0.07 * (d / 365.0)), 2),
        )
        for d in [7, 14, 21, 28, 56, 84]
    ]
    term_structure = calculate_term_structure(term_pts)

    return OptionsAnalyticsBundle(
        underlying=underlying.upper(),
        spot_price=spot,
        timestamp=now,
        atm_iv=atm_iv,
        iv_rank=iv_rank,
        pcr=pcr,
        max_pain=max_pain,
        skew=skew,
        term_structure=term_structure,
    )


@router.get("/{underlying}", response_model=OptionsAnalyticsBundle)
def get_options_analytics(underlying: str) -> OptionsAnalyticsBundle:
    """Retrieve comprehensive option analytics bundle."""
    return _build_synthetic_analytics_bundle(underlying)


@router.post("/compute", response_model=OptionsAnalyticsBundle)
def compute_options_analytics(req: ComputeAnalyticsRequest) -> OptionsAnalyticsBundle:
    """Compute customized analytics bundle from provided option chain arrays."""
    now = datetime.now(tz=IST)
    forward = req.spot_price * 1.003

    atm_iv = calculate_atm_iv(req.spot_price, req.strikes, req.call_ivs, req.put_ivs)
    iv_rank = calculate_iv_rank_and_percentile(
        atm_iv, req.historical_daily_ivs, min_history_days=30
    )
    pcr = calculate_put_call_ratios(req.call_ois, req.put_ois, req.call_vols, req.put_vols)
    max_pain = calculate_max_pain(req.strikes, req.call_ois, req.put_ois, req.spot_price)
    skew = calculate_iv_skew_and_smile(
        req.spot_price,
        req.strikes,
        req.call_ivs,
        req.put_ivs,
        req.call_deltas,
        req.put_deltas,
        req.expiry_date,
        forward,
    )
    term_structure = calculate_term_structure(req.term_structure_points)

    return OptionsAnalyticsBundle(
        underlying=req.underlying.upper(),
        spot_price=req.spot_price,
        timestamp=now,
        atm_iv=atm_iv,
        iv_rank=iv_rank,
        pcr=pcr,
        max_pain=max_pain,
        skew=skew,
        term_structure=term_structure,
    )
