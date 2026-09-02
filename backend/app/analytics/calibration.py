"""Continuous Dhan option-chain calibration, convention fitting, and drift detection."""

from __future__ import annotations

import math
from datetime import date, datetime
from enum import StrEnum
from zoneinfo import ZoneInfo

from pydantic import BaseModel, ConfigDict, Field

from app.analytics.greeks import (
    DEFAULT_OPTION_CONVENTIONS,
    DayCountConvention,
    ExpiryTimeMode,
    ForwardSource,
    OptionConventions,
    OptionType,
    calculate_time_to_expiry,
    price_black76_scalar,
    resolve_forward_price,
    solve_implied_volatility,
)

IST = ZoneInfo("Asia/Kolkata")


class DriftStatus(StrEnum):
    """Option chain calibration health status."""

    CALIBRATED = "CALIBRATED"
    WARNING = "WARNING"
    DRIFT_DETECTED = "DRIFT_DETECTED"


class ExclusionReason(StrEnum):
    """Reason why an option quote is excluded from convention fitting."""

    VEGA_NEAR_ZERO = "VEGA_NEAR_ZERO"
    WIDE_SPREAD = "WIDE_SPREAD"
    ZERO_LIQUIDITY = "ZERO_LIQUIDITY"
    BELOW_INTRINSIC = "BELOW_INTRINSIC"
    DEEP_OTM_ITM = "DEEP_OTM_ITM"
    ZERO_PRICE = "ZERO_PRICE"


class DhanOptionContractGreeks(BaseModel):
    """Published option Greeks from broker snapshot."""

    model_config = ConfigDict(frozen=True)

    delta: float
    gamma: float
    theta: float
    vega: float
    rho: float = 0.0


class DhanOptionQuote(BaseModel):
    """Standardized option quote from Dhan option chain."""

    model_config = ConfigDict(frozen=True)

    strike: float
    option_type: OptionType
    last_price: float
    bid: float
    ask: float
    iv: float  # broker published IV as decimal (e.g. 0.14)
    oi: int = 0
    volume: int = 0
    greeks: DhanOptionContractGreeks


class StrikeCalibrationComparison(BaseModel):
    """Per-strike reconciliation between local Black-76 values and Dhan published numbers."""

    model_config = ConfigDict(frozen=True)

    strike: float
    option_type: OptionType
    market_price: float
    dhan_iv: float
    local_iv: float
    iv_error: float
    dhan_theta: float
    local_theta: float
    theta_error: float
    dhan_delta: float
    local_delta: float
    delta_error: float
    dhan_gamma: float
    local_gamma: float
    dhan_vega: float
    local_vega: float
    is_reconciled: bool
    is_excluded: bool
    exclusion_reason: str | None = None


class TolerancePolicy(BaseModel):
    """Tolerance thresholds for option chain calibration and drift detection."""

    model_config = ConfigDict(frozen=True)

    theta_rel_tol: float = 0.08  # 8% relative theta error threshold
    theta_abs_tol: float = 0.50  # 0.50 INR absolute theta tolerance
    delta_abs_tol: float = 0.05  # 0.05 absolute delta tolerance
    iv_abs_tol: float = 0.02  # 2.0% volatility absolute tolerance
    min_reconciled_strikes: int = 20  # Minimum 20 strikes to guarantee calibrated status


DEFAULT_TOLERANCE_POLICY = TolerancePolicy()


class CalibrationReport(BaseModel):
    """Comprehensive calibration result and drift badge metadata."""

    model_config = ConfigDict(frozen=True)

    underlying: str
    expiry_date: date
    timestamp: datetime
    status: DriftStatus
    best_convention: OptionConventions
    forward_source_fitted: ForwardSource
    forward_price_used: float
    total_strikes_evaluated: int
    reconciled_strikes_count: int
    excluded_strikes_count: int
    theta_rmse: float
    theta_mae: float
    delta_mae: float
    iv_mae: float
    max_theta_drift_pct: float
    drift_badge_text: str
    strike_comparisons: list[StrikeCalibrationComparison] = Field(default_factory=list)
    exclusion_summary: dict[str, int] = Field(default_factory=dict)


def evaluate_quote_exclusion(
    quote: DhanOptionQuote,
    spot_price: float,
    t_years: float,
) -> tuple[bool, ExclusionReason | None]:
    """Determine whether an option quote should be excluded from calibration fitting."""
    # 1. Zero or negative price
    if quote.last_price <= 0.05:
        return True, ExclusionReason.ZERO_PRICE

    # 2. Zero volume / OI
    if quote.oi <= 0 and quote.volume <= 0:
        return True, ExclusionReason.ZERO_LIQUIDITY

    # 3. Deep OTM / ITM
    moneyness = abs(math.log(spot_price / quote.strike))
    if moneyness > 0.18:  # >18% away from spot
        return True, ExclusionReason.DEEP_OTM_ITM

    # 4. Wide bid-ask spread
    if quote.bid <= 0.0:
        return True, ExclusionReason.WIDE_SPREAD

    mid = 0.5 * (quote.bid + quote.ask)
    if mid > 0:
        spread_pct = (quote.ask - quote.bid) / mid
        if spread_pct > 0.35:  # >35% spread
            return True, ExclusionReason.WIDE_SPREAD

    # 5. Near-zero vega / expiry
    if t_years <= 1.0 / 365.0 and quote.last_price < 2.0:
        return True, ExclusionReason.VEGA_NEAR_ZERO

    return False, None


def calibrate_option_chain(
    underlying: str,
    spot_price: float,
    expiry_date: date,
    quotes: list[DhanOptionQuote],
    futures_price: float | None = None,
    current_time: datetime | None = None,
    tolerance_policy: TolerancePolicy = DEFAULT_TOLERANCE_POLICY,
) -> CalibrationReport:
    """Fit convention parameters against Dhan published Greeks and evaluate drift."""
    if current_time is None:
        current_time = datetime.now(tz=IST)
    elif current_time.tzinfo is None:
        current_time = current_time.replace(tzinfo=IST)
    else:
        current_time = current_time.astimezone(IST)

    # Candidate grid for fitting
    day_counts = [DayCountConvention.ACT_365, DayCountConvention.ACT_252]
    time_modes = [
        ExpiryTimeMode.CALENDAR_HOURS_TO_CLOSE,
        ExpiryTimeMode.CALENDAR_DAYS,
    ]
    rates = [0.060, 0.065, 0.070, 0.075]

    # Find ATM Call and Put for synthetic forward
    atm_call = next(
        (
            q
            for q in quotes
            if q.option_type == OptionType.CALL
            and abs(q.strike - spot_price) < 100.0
            and q.last_price > 0
        ),
        None,
    )
    atm_put = next(
        (
            q
            for q in quotes
            if q.option_type == OptionType.PUT
            and abs(q.strike - spot_price) < 100.0
            and q.last_price > 0
        ),
        None,
    )

    # Initial time calculation
    t_initial = calculate_time_to_expiry(current_time, expiry_date, DEFAULT_OPTION_CONVENTIONS)

    # Categorize exclusions
    valid_quotes: list[DhanOptionQuote] = []
    excluded_quotes: list[tuple[DhanOptionQuote, ExclusionReason]] = []
    exclusion_counts: dict[str, int] = {}

    for q in quotes:
        is_ex, reason = evaluate_quote_exclusion(q, spot_price, t_initial)
        if is_ex and reason is not None:
            excluded_quotes.append((q, reason))
            exclusion_counts[reason.value] = exclusion_counts.get(reason.value, 0) + 1
        else:
            valid_quotes.append(q)

    # Grid search for best convention minimizing Theta RMSE
    best_conv = DEFAULT_OPTION_CONVENTIONS
    best_f_src = ForwardSource.SPOT_COC
    best_f_price = spot_price
    min_theta_rmse = float("inf")

    # If valid quotes exist, run grid search
    target_quotes = valid_quotes if len(valid_quotes) >= 10 else quotes

    for dc in day_counts:
        ann_factor = 365 if dc == DayCountConvention.ACT_365 else 252
        for tm in time_modes:
            for r in rates:
                candidate_conv = OptionConventions(
                    day_count=dc,
                    time_mode=tm,
                    risk_free_rate=r,
                    annualization_factor=ann_factor,
                )
                t_cand = calculate_time_to_expiry(current_time, expiry_date, candidate_conv)

                for f_src_choice in [
                    ForwardSource.FUTURES_LTP,
                    ForwardSource.SYNTHETIC_PCP,
                    ForwardSource.SPOT_COC,
                ]:
                    cand_fut = futures_price if f_src_choice == ForwardSource.FUTURES_LTP else None
                    cand_call = (
                        atm_call.last_price
                        if atm_call and f_src_choice == ForwardSource.SYNTHETIC_PCP
                        else None
                    )
                    cand_put = (
                        atm_put.last_price
                        if atm_put and f_src_choice == ForwardSource.SYNTHETIC_PCP
                        else None
                    )
                    f_cand, actual_src = resolve_forward_price(
                        spot_ltp=spot_price,
                        strike=spot_price,
                        rate=r,
                        t_years=t_cand,
                        futures_ltp=cand_fut,
                        atm_call_ltp=cand_call,
                        atm_put_ltp=cand_put,
                    )

                    # Compute Theta squared error over target quotes
                    sq_err_sum = 0.0
                    evaluated_count = 0

                    for q in target_quotes:
                        res = price_black76_scalar(
                            forward=f_cand,
                            strike=q.strike,
                            t_years=t_cand,
                            rate=r,
                            vol=q.iv if q.iv > 0 else 0.15,
                            option_type=q.option_type,
                            convention=candidate_conv,
                            forward_source=actual_src,
                        )
                        if res.is_valid:
                            diff = res.theta - q.greeks.theta
                            sq_err_sum += diff * diff
                            evaluated_count += 1

                    if evaluated_count > 0:
                        rmse = math.sqrt(sq_err_sum / evaluated_count)
                        if rmse < min_theta_rmse:
                            min_theta_rmse = rmse
                            best_conv = candidate_conv
                            best_f_src = actual_src
                            best_f_price = f_cand

    # Perform detailed comparison for all quotes using best fitted convention
    t_best = calculate_time_to_expiry(current_time, expiry_date, best_conv)
    comparisons: list[StrikeCalibrationComparison] = []
    reconciled_count = 0
    theta_errors: list[float] = []
    delta_errors: list[float] = []
    iv_errors: list[float] = []
    max_theta_drift_pct = 0.0

    for q in quotes:
        is_ex, reason = evaluate_quote_exclusion(q, spot_price, t_best)
        res = price_black76_scalar(
            forward=best_f_price,
            strike=q.strike,
            t_years=t_best,
            rate=best_conv.risk_free_rate,
            vol=q.iv if q.iv > 0 else 0.15,
            option_type=q.option_type,
            convention=best_conv,
            forward_source=best_f_src,
        )

        solved_iv, reliable, _ = solve_implied_volatility(
            market_price=q.last_price,
            forward=best_f_price,
            strike=q.strike,
            t_years=t_best,
            rate=best_conv.risk_free_rate,
            option_type=q.option_type,
        )
        local_iv = solved_iv if reliable else q.iv

        theta_err = abs(res.theta - q.greeks.theta)
        delta_err = abs(res.delta - q.greeks.delta)
        iv_err = abs(local_iv - q.iv)

        # Check reconciliation criteria on non-excluded strikes
        is_reconciled = False
        if not is_ex and res.is_valid:
            # Theta tolerance check
            theta_rel_err = (
                theta_err / abs(q.greeks.theta) if abs(q.greeks.theta) > 0.5 else theta_err
            )
            theta_ok = (
                theta_rel_err <= tolerance_policy.theta_rel_tol
                or theta_err <= tolerance_policy.theta_abs_tol
            )
            delta_ok = delta_err <= tolerance_policy.delta_abs_tol
            iv_ok = iv_err <= tolerance_policy.iv_abs_tol

            if theta_ok and delta_ok and iv_ok:
                is_reconciled = True
                reconciled_count += 1

            theta_errors.append(theta_err)
            delta_errors.append(delta_err)
            iv_errors.append(iv_err)
            max_theta_drift_pct = max(max_theta_drift_pct, theta_rel_err * 100.0)

        comparisons.append(
            StrikeCalibrationComparison(
                strike=q.strike,
                option_type=q.option_type,
                market_price=q.last_price,
                dhan_iv=round(q.iv, 4),
                local_iv=round(local_iv, 4),
                iv_error=round(iv_err, 4),
                dhan_theta=round(q.greeks.theta, 4),
                local_theta=round(res.theta, 4),
                theta_error=round(theta_err, 4),
                dhan_delta=round(q.greeks.delta, 4),
                local_delta=round(res.delta, 4),
                delta_error=round(delta_err, 4),
                dhan_gamma=round(q.greeks.gamma, 6),
                local_gamma=round(res.gamma, 6),
                dhan_vega=round(q.greeks.vega, 4),
                local_vega=round(res.vega, 4),
                is_reconciled=is_reconciled,
                is_excluded=is_ex,
                exclusion_reason=reason.value if reason else None,
            )
        )

    # Compute aggregate metrics
    theta_mae = round(sum(theta_errors) / len(theta_errors), 4) if theta_errors else 0.0
    delta_mae = round(sum(delta_errors) / len(delta_errors), 4) if delta_errors else 0.0
    iv_mae = round(sum(iv_errors) / len(iv_errors), 4) if iv_errors else 0.0
    theta_rmse = (
        round(math.sqrt(sum(e * e for e in theta_errors) / len(theta_errors)), 4)
        if theta_errors
        else 0.0
    )

    # Determine drift status
    if (
        reconciled_count >= tolerance_policy.min_reconciled_strikes
        and theta_rmse <= tolerance_policy.theta_abs_tol
        and max_theta_drift_pct < 10.0
    ):
        status = DriftStatus.CALIBRATED
        badge_text = f"🟢 Calibrated (Theta Error {theta_mae:.2f})"
    elif theta_rmse <= tolerance_policy.theta_abs_tol * 2.0 and max_theta_drift_pct < 18.0:
        status = DriftStatus.WARNING
        badge_text = f"🟡 Minor Drift (Theta Error {theta_mae:.2f})"
    else:
        status = DriftStatus.DRIFT_DETECTED
        badge_text = f"🔴 Drift Detected (Theta Drift {max_theta_drift_pct:.1f}%)"

    return CalibrationReport(
        underlying=underlying,
        expiry_date=expiry_date,
        timestamp=current_time,
        status=status,
        best_convention=best_conv,
        forward_source_fitted=best_f_src,
        forward_price_used=best_f_price,
        total_strikes_evaluated=len(quotes),
        reconciled_strikes_count=reconciled_count,
        excluded_strikes_count=len(excluded_quotes),
        theta_rmse=theta_rmse,
        theta_mae=theta_mae,
        delta_mae=delta_mae,
        iv_mae=iv_mae,
        max_theta_drift_pct=round(max_theta_drift_pct, 2),
        drift_badge_text=badge_text,
        strike_comparisons=comparisons,
        exclusion_summary=exclusion_counts,
    )
