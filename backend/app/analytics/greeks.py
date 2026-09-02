"""Black-76 pricing model, forward price resolver, Brent IV solver, and closed-form Greeks."""

from __future__ import annotations

import math
from datetime import date, datetime, time
from enum import StrEnum
from zoneinfo import ZoneInfo

from pydantic import BaseModel, ConfigDict

IST = ZoneInfo("Asia/Kolkata")
MARKET_CLOSE_TIME = time(15, 30)  # 15:30 IST


class OptionType(StrEnum):
    """Option contract right."""

    CALL = "CALL"
    PUT = "PUT"


class ForwardSource(StrEnum):
    """Source used to determine the underlying forward price F."""

    FUTURES_LTP = "FUTURES_LTP"
    SYNTHETIC_PCP = "SYNTHETIC_PCP"
    SPOT_COC = "SPOT_COC"


class DayCountConvention(StrEnum):
    """Annual day-count convention."""

    ACT_365 = "ACT_365"
    ACT_252 = "ACT_252"


class ExpiryTimeMode(StrEnum):
    """Time-to-expiry measurement mode."""

    CALENDAR_HOURS_TO_CLOSE = "CALENDAR_HOURS_TO_CLOSE"
    CALENDAR_DAYS = "CALENDAR_DAYS"


class OptionConventions(BaseModel):
    """Option calculation conventions matching Indian market standards."""

    model_config = ConfigDict(frozen=True)

    day_count: DayCountConvention = DayCountConvention.ACT_365
    time_mode: ExpiryTimeMode = ExpiryTimeMode.CALENDAR_HOURS_TO_CLOSE
    risk_free_rate: float = 0.07  # 7.0% default Indian risk-free rate / MIBOR
    annualization_factor: int = 365


DEFAULT_OPTION_CONVENTIONS = OptionConventions()


class OptionGreeks(BaseModel):
    """First and second-order option Greeks."""

    model_config = ConfigDict(frozen=True)

    delta: float
    gamma: float
    theta: float
    vega: float
    rho: float


class OptionPricingResult(BaseModel):
    """Comprehensive theoretical pricing, IV, Greeks, and reliability flags."""

    model_config = ConfigDict(frozen=True)

    price: float
    delta: float
    gamma: float
    theta: float  # 1-day calendar decay
    vega: float  # per 1 vol point change (0.01)
    rho: float  # per 1 rate point change (0.01)
    iv: float
    is_valid: bool = True
    is_iv_reliable: bool = True
    unreliable_reason: str | None = None
    forward_used: float = 0.0
    forward_source: ForwardSource = ForwardSource.SPOT_COC


def norm_cdf(x: float) -> float:
    """Standard normal cumulative distribution function."""
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def norm_pdf(x: float) -> float:
    """Standard normal probability density function."""
    return (1.0 / math.sqrt(2.0 * math.pi)) * math.exp(-0.5 * x * x)


def calculate_time_to_expiry(
    current_time: datetime,
    expiry_date: date,
    convention: OptionConventions = DEFAULT_OPTION_CONVENTIONS,
) -> float:
    """Calculate annualized time to expiry T based on convention."""
    if current_time.tzinfo is None:
        current_time = current_time.replace(tzinfo=IST)
    else:
        current_time = current_time.astimezone(IST)

    expiry_dt = datetime.combine(expiry_date, MARKET_CLOSE_TIME, tzinfo=IST)

    diff_seconds = (expiry_dt - current_time).total_seconds()
    if diff_seconds <= 0:
        return 0.0

    annual_seconds = convention.annualization_factor * 86400.0
    return diff_seconds / annual_seconds


def resolve_forward_price(
    spot_ltp: float,
    strike: float,
    rate: float,
    t_years: float,
    futures_ltp: float | None = None,
    atm_call_ltp: float | None = None,
    atm_put_ltp: float | None = None,
    div_yield: float = 0.0,
) -> tuple[float, ForwardSource]:
    """Resolve underlying forward price F using the hierarchy specified in §11.3."""
    # 1. Actual Futures LTP if liquid
    if futures_ltp is not None and futures_ltp > 0.0:
        return futures_ltp, ForwardSource.FUTURES_LTP

    # 2. Synthetic forward derived from ATM Put-Call Parity: F = K + e^(rT) * (Call - Put)
    if (
        atm_call_ltp is not None
        and atm_put_ltp is not None
        and atm_call_ltp > 0.0
        and atm_put_ltp > 0.0
        and t_years > 0.0
    ):
        df_r = math.exp(rate * t_years)
        synth_forward = strike + df_r * (atm_call_ltp - atm_put_ltp)
        if synth_forward > 0.0:
            return round(synth_forward, 4), ForwardSource.SYNTHETIC_PCP

    # 3. Cost of carry forward from spot: F = S * e^((r - q) * T)
    f_coc = spot_ltp * math.exp((rate - div_yield) * t_years)
    return round(f_coc, 4), ForwardSource.SPOT_COC


def price_black76_scalar(
    forward: float,
    strike: float,
    t_years: float,
    rate: float,
    vol: float,
    option_type: OptionType = OptionType.CALL,
    convention: OptionConventions = DEFAULT_OPTION_CONVENTIONS,
    forward_source: ForwardSource = ForwardSource.SPOT_COC,
) -> OptionPricingResult:
    """Calculate theoretical Black-76 price and closed-form Greeks for a single contract."""
    if forward <= 0.0 or strike <= 0.0:
        return OptionPricingResult(
            price=0.0,
            delta=0.0,
            gamma=0.0,
            theta=0.0,
            vega=0.0,
            rho=0.0,
            iv=vol,
            is_valid=False,
            is_iv_reliable=False,
            unreliable_reason="Forward or strike price is non-positive",
            forward_used=forward,
            forward_source=forward_source,
        )

    # Expiry case (T <= 0)
    if t_years <= 0.0:
        if option_type == OptionType.CALL:
            intrinsic = max(0.0, forward - strike)
            delta = 1.0 if forward > strike else 0.0
        else:
            intrinsic = max(0.0, strike - forward)
            delta = -1.0 if strike > forward else 0.0

        return OptionPricingResult(
            price=round(intrinsic, 4),
            delta=delta,
            gamma=0.0,
            theta=0.0,
            vega=0.0,
            rho=0.0,
            iv=vol,
            is_valid=True,
            is_iv_reliable=False,
            unreliable_reason="Contract has expired (T <= 0)",
            forward_used=forward,
            forward_source=forward_source,
        )

    safe_vol = max(0.0001, vol)
    sqrt_t = math.sqrt(t_years)
    df_r = math.exp(-rate * t_years)

    d1 = (math.log(forward / strike) + 0.5 * safe_vol * safe_vol * t_years) / (
        safe_vol * sqrt_t
    )
    d2 = d1 - safe_vol * sqrt_t

    pdf_d1 = norm_pdf(d1)

    if option_type == OptionType.CALL:
        nd1 = norm_cdf(d1)
        nd2 = norm_cdf(d2)
        price_val = df_r * (forward * nd1 - strike * nd2)
        delta = df_r * nd1
        # Theta per calendar day
        theta_annual = -(forward * df_r * pdf_d1 * safe_vol) / (2.0 * sqrt_t) - (
            rate * df_r * strike * nd2
        ) + (rate * df_r * forward * nd1)
        # Rho per 1% change
        rho = -t_years * df_r * (forward * nd1 - strike * nd2) * 0.01
    else:
        n_neg_d1 = norm_cdf(-d1)
        n_neg_d2 = norm_cdf(-d2)
        price_val = df_r * (strike * n_neg_d2 - forward * n_neg_d1)
        delta = -df_r * n_neg_d1
        # Theta per calendar day
        theta_annual = -(forward * df_r * pdf_d1 * safe_vol) / (2.0 * sqrt_t) + (
            rate * df_r * strike * n_neg_d2
        ) - (rate * df_r * forward * n_neg_d1)
        # Rho per 1% change
        rho = -t_years * df_r * (strike * n_neg_d2 - forward * n_neg_d1) * 0.01

    gamma = (df_r * pdf_d1) / (forward * safe_vol * sqrt_t)
    # Vega per 1% volatility change (0.01)
    vega = forward * df_r * sqrt_t * pdf_d1 * 0.01
    theta_1d = theta_annual / convention.annualization_factor

    return OptionPricingResult(
        price=round(max(0.0, price_val), 4),
        delta=round(delta, 6),
        gamma=round(gamma, 6),
        theta=round(theta_1d, 4),
        vega=round(vega, 4),
        rho=round(rho, 4),
        iv=vol,
        is_valid=True,
        is_iv_reliable=True,
        unreliable_reason=None,
        forward_used=forward,
        forward_source=forward_source,
    )


def solve_implied_volatility(
    market_price: float,
    forward: float,
    strike: float,
    t_years: float,
    rate: float,
    option_type: OptionType = OptionType.CALL,
    tol: float = 1e-6,
    max_iter: int = 100,
) -> tuple[float, bool, str | None]:
    """Solve Black-76 implied volatility using Brent's method with vega and intrinsic guards."""
    if market_price <= 0.0:
        return 0.0, False, "Market price is zero or negative"

    if t_years <= 0.0:
        return 0.0, False, "Contract has expired (T <= 0)"

    if forward <= 0.0 or strike <= 0.0:
        return 0.0, False, "Forward or strike price is non-positive"

    df_r = math.exp(-rate * t_years)
    sqrt_t = math.sqrt(t_years)

    # 1. Intrinsic lower bound check
    if option_type == OptionType.CALL:
        intrinsic = df_r * max(0.0, forward - strike)
    else:
        intrinsic = df_r * max(0.0, strike - forward)

    if market_price < intrinsic - 1e-4:
        return 0.0, False, "Market price is below discounted intrinsic value"

    # 2. Near-zero vega guard (§11.3)
    # Check vega at benchmark volatility 20%
    d1_ref = (math.log(forward / strike) + 0.5 * 0.20 * 0.20 * t_years) / (0.20 * sqrt_t)
    ref_vega = forward * df_r * sqrt_t * norm_pdf(d1_ref) * 0.01
    if ref_vega < 1e-5:
        return 0.0, False, "Vega near zero: IV numerically unreliable"

    # Objective function
    def obj_func(vol_candidate: float) -> float:
        res = price_black76_scalar(
            forward=forward,
            strike=strike,
            t_years=t_years,
            rate=rate,
            vol=vol_candidate,
            option_type=option_type,
        )
        return res.price - market_price

    # Bracket search on [0.001, 5.0] (0.1% to 500% IV)
    a = 0.001
    b = 5.0
    fa = obj_func(a)
    fb = obj_func(b)

    if fa * fb > 0.0:
        if abs(fa) < 0.05:
            return a, True, None
        if abs(fb) < 0.05:
            return b, True, None
        return 0.0, False, "IV root not bracketed in [0.001, 5.0]"

    # Pure Python Brent's Root Finding Method
    c = a
    fc = fa
    d = e = b - a

    for _ in range(max_iter):
        if (fb > 0.0 and fc > 0.0) or (fb < 0.0 and fc < 0.0):
            c = a
            fc = fa
            d = e = b - a

        if abs(fc) < abs(fb):
            a = b
            b = c
            c = a
            fa = fb
            fb = fc
            fc = fa

        tol1 = 2.0 * 1e-15 * abs(b) + 0.5 * tol
        xm = 0.5 * (c - b)

        if abs(xm) <= tol1 or abs(fb) <= tol:
            return round(b, 4), True, None

        if abs(e) >= tol1 and abs(fa) > abs(fb):
            s = fb / fa
            if a == c:
                p = 2.0 * xm * s
                q = 1.0 - s
            else:
                q = fa / fc
                r_ratio = fb / fc
                p = s * (2.0 * xm * q * (q - r_ratio) - (b - a) * (r_ratio - 1.0))
                q = (q - 1.0) * (r_ratio - 1.0) * (s - 1.0)

            if p > 0.0:
                q = -q
            p = abs(p)

            if 2.0 * p < min(3.0 * xm * q - abs(tol1 * q), abs(e * q)):
                e = d
                d = p / q
            else:
                d = xm
                e = d
        else:
            d = xm
            e = d

        a = b
        fa = fb
        if abs(d) > tol1:
            b += d
        else:
            b += math.copysign(tol1, xm)
        fb = obj_func(b)

    return round(b, 4), True, None


def price_black76_vector(
    forwards: list[float] | tuple[float, ...],
    strikes: list[float] | tuple[float, ...],
    t_years: list[float] | tuple[float, ...],
    rates: list[float] | tuple[float, ...],
    vols: list[float] | tuple[float, ...],
    is_call: list[bool] | tuple[bool, ...],
    convention: OptionConventions = DEFAULT_OPTION_CONVENTIONS,
) -> dict[str, list[float]]:
    """Batch Black-76 pricing and Greeks computation over contract sequences."""
    n = len(forwards)
    prices: list[float] = []
    deltas: list[float] = []
    gammas: list[float] = []
    thetas: list[float] = []
    vegas: list[float] = []

    for i in range(n):
        f = forwards[i]
        k = strikes[i]
        t = t_years[i]
        r = rates[i]
        v = vols[i]
        opt_type = OptionType.CALL if is_call[i] else OptionType.PUT

        res = price_black76_scalar(
            forward=f,
            strike=k,
            t_years=t,
            rate=r,
            vol=v,
            option_type=opt_type,
            convention=convention,
        )
        prices.append(res.price)
        deltas.append(res.delta)
        gammas.append(res.gamma)
        thetas.append(res.theta)
        vegas.append(res.vega)

    return {
        "prices": prices,
        "deltas": deltas,
        "gammas": gammas,
        "thetas": thetas,
        "vegas": vegas,
    }
