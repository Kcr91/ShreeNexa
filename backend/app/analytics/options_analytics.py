"""Option analytics: ATM IV, IV Rank/Percentile, PCR, Max Pain, Skew/Smile, and Term Structure."""

from __future__ import annotations

import math
from datetime import date, datetime
from zoneinfo import ZoneInfo

from pydantic import BaseModel, ConfigDict, Field

IST = ZoneInfo("Asia/Kolkata")


class IVRankResult(BaseModel):
    """Historical Implied Volatility Rank and Percentile."""

    model_config = ConfigDict(frozen=True)

    current_iv: float
    iv_min_52w: float | None = None
    iv_max_52w: float | None = None
    iv_rank: float | None = None
    iv_percentile: float | None = None
    history_days_count: int = 0
    is_valid: bool = True
    unreliable_reason: str | None = None


class PCRResult(BaseModel):
    """Put-Call Open Interest and Volume Ratios."""

    model_config = ConfigDict(frozen=True)

    pcr_oi: float
    pcr_volume: float
    total_call_oi: int
    total_put_oi: int
    total_call_volume: int
    total_put_volume: int


class MaxPainResult(BaseModel):
    """Option Max Pain strike and expiration loss profile."""

    model_config = ConfigDict(frozen=True)

    max_pain_strike: float
    spot_price: float
    strike_distance_from_spot: float
    strike_distance_pct: float
    total_cash_loss_at_pain: float
    pain_curve: list[dict[str, float]] = Field(default_factory=list)


class SmilePoint(BaseModel):
    """Single strike point on the volatility smile curve."""

    model_config = ConfigDict(frozen=True)

    strike: float
    moneyness: float  # Strike / Forward
    call_iv: float
    put_iv: float
    blended_iv: float
    delta: float


class IVSkewResult(BaseModel):
    """Option volatility smile and 25-delta skew metrics."""

    model_config = ConfigDict(frozen=True)

    expiry_date: date
    atm_iv: float
    risk_reversal_25d: float  # 25D Put IV - 25D Call IV
    butterfly_25d: float  # (25D Call IV + 25D Put IV)/2 - ATM IV
    smile_points: list[SmilePoint] = Field(default_factory=list)


class TermStructurePoint(BaseModel):
    """ATM IV for an individual expiry in the term structure."""

    model_config = ConfigDict(frozen=True)

    expiry_date: date
    days_to_expiry: int
    atm_iv: float
    forward_price: float


class TermStructureResult(BaseModel):
    """Volatility term structure across multiple expiration dates."""

    model_config = ConfigDict(frozen=True)

    regime: str  # "CONTANGO", "BACKWARDATION", "FLAT"
    slope: float
    points: list[TermStructurePoint] = Field(default_factory=list)


class OptionsAnalyticsBundle(BaseModel):
    """Unified options analytics bundle for an underlying index/stock."""

    model_config = ConfigDict(frozen=True)

    underlying: str
    spot_price: float
    timestamp: datetime
    atm_iv: float
    iv_rank: IVRankResult
    pcr: PCRResult
    max_pain: MaxPainResult
    skew: IVSkewResult
    term_structure: TermStructureResult


def calculate_atm_iv(
    spot_price: float,
    strikes: list[float],
    call_ivs: list[float],
    put_ivs: list[float],
) -> float:
    """Derive blended ATM Implied Volatility via linear interpolation at spot/forward."""
    if not strikes or not call_ivs or not put_ivs:
        return 0.15

    # Find closest strikes surrounding spot
    sorted_pairs = sorted(zip(strikes, call_ivs, put_ivs, strict=False), key=lambda x: x[0])
    lower = None
    upper = None

    for s, c_iv, p_iv in sorted_pairs:
        blended = 0.5 * (c_iv + p_iv) if (c_iv > 0 and p_iv > 0) else max(c_iv, p_iv)
        if s <= spot_price:
            lower = (s, blended)
        if s >= spot_price and upper is None:
            upper = (s, blended)
            break

    if lower and upper and upper[0] != lower[0]:
        s_low, iv_low = lower
        s_up, iv_up = upper
        weight = (spot_price - s_low) / (s_up - s_low)
        return round(iv_low + weight * (iv_up - iv_low), 4)
    elif lower:
        return round(lower[1], 4)
    elif upper:
        return round(upper[1], 4)

    return 0.15


def calculate_iv_rank_and_percentile(
    current_iv: float,
    historical_daily_ivs: list[float],
    min_history_days: int = 30,
) -> IVRankResult:
    """Calculate IV Rank and IV Percentile with strict minimum-history rules."""
    # Filter valid positive numbers
    clean_history = [iv for iv in historical_daily_ivs if iv > 0.0]
    n = len(clean_history)

    if n < min_history_days:
        return IVRankResult(
            current_iv=round(current_iv, 4),
            history_days_count=n,
            is_valid=False,
            unreliable_reason=(
                f"Insufficient historical IV observations "
                f"(found {n}, requires >= {min_history_days})"
            ),
        )

    iv_min = min(clean_history)
    iv_max = max(clean_history)

    # Division-by-zero protection when min == max
    if math.isclose(iv_max, iv_min, abs_tol=1e-6):
        iv_rank = 50.0
    else:
        iv_rank = ((current_iv - iv_min) / (iv_max - iv_min)) * 100.0
        iv_rank = max(0.0, min(100.0, iv_rank))

    # Percentile: count of observations below current
    below_count = sum(1 for iv in clean_history if iv < current_iv)
    iv_percentile = (below_count / n) * 100.0

    return IVRankResult(
        current_iv=round(current_iv, 4),
        iv_min_52w=round(iv_min, 4),
        iv_max_52w=round(iv_max, 4),
        iv_rank=round(iv_rank, 2),
        iv_percentile=round(iv_percentile, 2),
        history_days_count=n,
        is_valid=True,
    )


def calculate_max_pain(
    strikes: list[float],
    call_ois: list[int],
    put_ois: list[int],
    spot_price: float,
) -> MaxPainResult:
    """Calculate the Max Pain strike where aggregate option buyers experience maximum cash loss."""
    if not strikes:
        return MaxPainResult(
            max_pain_strike=spot_price,
            spot_price=spot_price,
            strike_distance_from_spot=0.0,
            strike_distance_pct=0.0,
            total_cash_loss_at_pain=0.0,
        )

    min_loss = float("inf")
    best_strike = strikes[0]
    pain_curve: list[dict[str, float]] = []

    for test_k in strikes:
        total_loss = 0.0
        for k, c_oi, p_oi in zip(strikes, call_ois, put_ois, strict=False):
            # Call buyer payoff at test_k
            call_payoff = max(0.0, test_k - k) * c_oi
            # Put buyer payoff at test_k
            put_payoff = max(0.0, k - test_k) * p_oi
            total_loss += call_payoff + put_payoff

        pain_curve.append({"strike": test_k, "total_loss": total_loss})
        if total_loss < min_loss:
            min_loss = total_loss
            best_strike = test_k

    dist = best_strike - spot_price
    dist_pct = (dist / spot_price) * 100.0 if spot_price > 0 else 0.0

    return MaxPainResult(
        max_pain_strike=best_strike,
        spot_price=spot_price,
        strike_distance_from_spot=round(dist, 2),
        strike_distance_pct=round(dist_pct, 2),
        total_cash_loss_at_pain=round(min_loss, 2),
        pain_curve=pain_curve,
    )


def calculate_put_call_ratios(
    call_ois: list[int],
    put_ois: list[int],
    call_vols: list[int],
    put_vols: list[int],
) -> PCRResult:
    """Calculate PCR by Open Interest and Volume with zero-denominator safety."""
    total_c_oi = sum(call_ois)
    total_p_oi = sum(put_ois)
    total_c_vol = sum(call_vols)
    total_p_vol = sum(put_vols)

    pcr_oi = (total_p_oi / total_c_oi) if total_c_oi > 0 else 1.0
    pcr_vol = (total_p_vol / total_c_vol) if total_c_vol > 0 else 1.0

    return PCRResult(
        pcr_oi=round(pcr_oi, 3),
        pcr_volume=round(pcr_vol, 3),
        total_call_oi=total_c_oi,
        total_put_oi=total_p_oi,
        total_call_volume=total_c_vol,
        total_put_volume=total_p_vol,
    )


def calculate_iv_skew_and_smile(
    spot_price: float,
    strikes: list[float],
    call_ivs: list[float],
    put_ivs: list[float],
    call_deltas: list[float],
    put_deltas: list[float],
    expiry_date: date,
    forward_price: float,
) -> IVSkewResult:
    """Compute volatility smile points and 25-delta Risk Reversal / Butterfly metrics."""
    smile_points: list[SmilePoint] = []
    atm_iv = calculate_atm_iv(spot_price, strikes, call_ivs, put_ivs)

    iv_25d_call = atm_iv
    iv_25d_put = atm_iv
    min_call_delta_diff = float("inf")
    min_put_delta_diff = float("inf")

    for s, c_iv, p_iv, c_del, p_del in zip(
        strikes, call_ivs, put_ivs, call_deltas, put_deltas, strict=False
    ):
        moneyness = s / forward_price if forward_price > 0 else 1.0
        blended = p_iv if s < spot_price else (c_iv if s > spot_price else 0.5 * (c_iv + p_iv))
        if blended <= 0:
            blended = max(c_iv, p_iv, atm_iv)

        smile_points.append(
            SmilePoint(
                strike=s,
                moneyness=round(moneyness, 4),
                call_iv=round(c_iv, 4),
                put_iv=round(p_iv, 4),
                blended_iv=round(blended, 4),
                delta=round(c_del if s >= spot_price else p_del, 4),
            )
        )

        # Track 25-delta call (delta ~ +0.25)
        diff_c = abs(c_del - 0.25)
        if diff_c < min_call_delta_diff and c_iv > 0:
            min_call_delta_diff = diff_c
            iv_25d_call = c_iv

        # Track 25-delta put (delta ~ -0.25)
        diff_p = abs(p_del - (-0.25))
        if diff_p < min_put_delta_diff and p_iv > 0:
            min_put_delta_diff = diff_p
            iv_25d_put = p_iv

    # 25-delta Risk Reversal: Put IV - Call IV (positive indicates downside put demand)
    risk_reversal = iv_25d_put - iv_25d_call
    # 25-delta Butterfly: Average(Wings) - ATM
    butterfly = 0.5 * (iv_25d_call + iv_25d_put) - atm_iv

    return IVSkewResult(
        expiry_date=expiry_date,
        atm_iv=round(atm_iv, 4),
        risk_reversal_25d=round(risk_reversal, 4),
        butterfly_25d=round(butterfly, 4),
        smile_points=smile_points,
    )


def calculate_term_structure(points: list[TermStructurePoint]) -> TermStructureResult:
    """Determine volatility term structure regime (Contango / Backwardation) and slope."""
    if len(points) < 2:
        return TermStructureResult(regime="FLAT", slope=0.0, points=points)

    sorted_pts = sorted(points, key=lambda p: p.days_to_expiry)
    first_pt = sorted_pts[0]
    last_pt = sorted_pts[-1]

    dte_diff = last_pt.days_to_expiry - first_pt.days_to_expiry
    iv_diff = last_pt.atm_iv - first_pt.atm_iv

    slope = (iv_diff / dte_diff) * 365.0 if dte_diff > 0 else 0.0

    if slope > 0.02:
        regime = "CONTANGO"
    elif slope < -0.02:
        regime = "BACKWARDATION"
    else:
        regime = "FLAT"

    return TermStructureResult(
        regime=regime,
        slope=round(slope, 4),
        points=sorted_pts,
    )
