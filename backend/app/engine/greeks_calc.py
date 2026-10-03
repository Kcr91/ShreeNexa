"""Black-Scholes Options Pricing, Implied Volatility Solver, and Greeks Calculator."""

from __future__ import annotations

import math
from typing import NamedTuple


class Greeks(NamedTuple):
    """Calculated Black-Scholes Greeks."""

    price: float
    iv: float  # As percentage (e.g. 24.5 for 24.5%)
    delta: float
    gamma: float
    theta: float  # 1-day theta decay (₹ per lot or per share)
    vega: float  # Per 1% IV change
    rho: float


def norm_cdf(x: float) -> float:
    """Standard normal cumulative distribution function."""
    return (1.0 + math.erf(x / math.sqrt(2.0))) / 2.0


def norm_pdf(x: float) -> float:
    """Standard normal probability density function."""
    return (1.0 / math.sqrt(2.0 * math.pi)) * math.exp(-0.5 * x * x)


def black_scholes_price(
    spot: float,
    strike: float,
    tte_years: float,
    iv_pct: float,
    rate: float = 0.07,  # RBI 91-day T-bill benchmark ~7%
    option_right: str = "CE",
) -> float:
    """Calculate Black-Scholes option theoretical price."""
    if tte_years <= 0 or iv_pct <= 0 or spot <= 0 or strike <= 0:
        if option_right.upper() == "CE":
            return max(0.0, spot - strike)
        return max(0.0, strike - spot)

    sigma = iv_pct / 100.0
    d1 = (math.log(spot / strike) + (rate + 0.5 * sigma * sigma) * tte_years) / (
        sigma * math.sqrt(tte_years)
    )
    d2 = d1 - sigma * math.sqrt(tte_years)

    if option_right.upper() == "CE":
        price = spot * norm_cdf(d1) - strike * math.exp(-rate * tte_years) * norm_cdf(d2)
    else:
        price = strike * math.exp(-rate * tte_years) * norm_cdf(-d2) - spot * norm_cdf(-d1)

    return max(0.0, price)


def calculate_implied_volatility(
    market_price: float,
    spot: float,
    strike: float,
    tte_years: float,
    rate: float = 0.07,
    option_right: str = "CE",
    max_iter: int = 50,
    tolerance: float = 1e-4,
) -> float:
    """Calculate Implied Volatility (%) using Newton-Raphson with bisection fallback."""
    intrinsic = max(0.0, spot - strike) if option_right.upper() == "CE" else max(0.0, strike - spot)
    if market_price <= intrinsic:
        return 5.0  # Baseline floor

    if tte_years <= 1e-5:
        return 20.0

    # Initial guess
    sigma = 0.25  # 25%

    for _ in range(max_iter):
        price = black_scholes_price(spot, strike, tte_years, sigma * 100.0, rate, option_right)
        diff = price - market_price

        if abs(diff) < tolerance:
            return round(sigma * 100.0, 2)

        # Vega calculation
        d1 = (math.log(spot / strike) + (rate + 0.5 * sigma * sigma) * tte_years) / (
            sigma * math.sqrt(tte_years)
        )
        vega = spot * math.sqrt(tte_years) * norm_pdf(d1)

        if vega < 1e-6:
            break

        sigma = sigma - (diff / vega)
        if sigma <= 0.01:
            sigma = 0.01
        elif sigma > 5.0:  # 500%
            sigma = 5.0

    # Bisection fallback
    low = 0.01
    high = 3.0
    for _ in range(30):
        mid = (low + high) / 2.0
        p = black_scholes_price(spot, strike, tte_years, mid * 100.0, rate, option_right)
        if abs(p - market_price) < tolerance:
            return round(mid * 100.0, 2)
        if p < market_price:
            low = mid
        else:
            high = mid

    return round(mid * 100.0, 2)


def calculate_greeks(
    spot: float,
    strike: float,
    tte_years: float,
    iv_pct: float,
    rate: float = 0.07,
    option_right: str = "CE",
) -> Greeks:
    """Calculate option theoretical price and all 5 Greeks."""
    is_call = option_right.upper() == "CE"
    tte = max(1e-5, tte_years)
    sigma = max(0.01, iv_pct / 100.0)

    d1 = (math.log(spot / strike) + (rate + 0.5 * sigma * sigma) * tte) / (sigma * math.sqrt(tte))
    d2 = d1 - sigma * math.sqrt(tte)

    nd1 = norm_cdf(d1)
    nd2 = norm_cdf(d2)
    np_d1 = norm_pdf(d1)

    # Price
    if is_call:
        price = spot * nd1 - strike * math.exp(-rate * tte) * nd2
        delta = nd1
        theta_annual = (
            -(spot * np_d1 * sigma) / (2.0 * math.sqrt(tte))
            - rate * strike * math.exp(-rate * tte) * nd2
        )
        rho = strike * tte * math.exp(-rate * tte) * nd2 / 100.0
    else:
        price = strike * math.exp(-rate * tte) * norm_cdf(-d2) - spot * norm_cdf(-d1)
        delta = nd1 - 1.0
        theta_annual = -(spot * np_d1 * sigma) / (2.0 * math.sqrt(tte)) + rate * strike * math.exp(
            -rate * tte
        ) * norm_cdf(-d2)
        rho = -strike * tte * math.exp(-rate * tte) * norm_cdf(-d2) / 100.0

    gamma = np_d1 / (spot * sigma * math.sqrt(tte))
    vega = (spot * math.sqrt(tte) * np_d1) / 100.0  # Per 1% change
    theta_day = theta_annual / 365.0

    return Greeks(
        price=round(max(0.0, price), 4),
        iv=round(iv_pct, 2),
        delta=round(delta, 4),
        gamma=round(gamma, 6),
        theta=round(theta_day, 4),
        vega=round(vega, 4),
        rho=round(rho, 4),
    )
