"""Synthetic continuous option surface generator, BSM/Black-76 pricer, IV solver, and Greeks."""

from __future__ import annotations

import logging
import math
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict

logger = logging.getLogger(__name__)


def norm_cdf(x: float) -> float:
    """Standard normal cumulative distribution function."""
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def norm_pdf(x: float) -> float:
    """Standard normal probability density function."""
    return (1.0 / math.sqrt(2.0 * math.pi)) * math.exp(-0.5 * x * x)


class OptionType(StrEnum):
    """Option contract right."""

    CALL = "CALL"
    PUT = "PUT"


class OptionGreeks(BaseModel):
    """Calculated first and second-order option Greeks."""

    model_config = ConfigDict(frozen=True)

    delta: float
    gamma: float
    theta: float
    vega: float
    rho: float


class BlackScholesPricer:
    """European Black-Scholes-Merton option pricing, Greeks, and IV solver."""

    def price(
        self,
        spot: float,
        strike: float,
        t_years: float,
        rate: float,
        vol: float,
        option_type: OptionType = OptionType.CALL,
        div_yield: float = 0.0,
    ) -> float:
        """Compute theoretical European option price."""
        if t_years <= 0.0:
            if option_type == OptionType.CALL:
                return max(0.0, spot - strike)
            else:
                return max(0.0, strike - spot)

        if vol <= 0.0:
            vol = 0.0001

        sqrt_t = math.sqrt(t_years)
        d1 = (math.log(spot / strike) + (rate - div_yield + 0.5 * vol * vol) * t_years) / (
            vol * sqrt_t
        )
        d2 = d1 - vol * sqrt_t

        df_q = math.exp(-div_yield * t_years)
        df_r = math.exp(-rate * t_years)

        if option_type == OptionType.CALL:
            price_val = spot * df_q * norm_cdf(d1) - strike * df_r * norm_cdf(d2)
        else:
            price_val = strike * df_r * norm_cdf(-d2) - spot * df_q * norm_cdf(-d1)

        return max(0.0, price_val)

    def calculate_greeks(
        self,
        spot: float,
        strike: float,
        t_years: float,
        rate: float,
        vol: float,
        option_type: OptionType = OptionType.CALL,
        div_yield: float = 0.0,
    ) -> OptionGreeks:
        """Calculate Delta, Gamma, Theta (1-day), Vega (1%), and Rho (1%)."""
        if t_years <= 0.0:
            d = 1.0 if option_type == OptionType.CALL and spot >= strike else 0.0
            return OptionGreeks(delta=d, gamma=0.0, theta=0.0, vega=0.0, rho=0.0)

        vol = max(0.0001, vol)
        sqrt_t = math.sqrt(t_years)
        d1 = (math.log(spot / strike) + (rate - div_yield + 0.5 * vol * vol) * t_years) / (
            vol * sqrt_t
        )
        d2 = d1 - vol * sqrt_t

        df_q = math.exp(-div_yield * t_years)
        df_r = math.exp(-rate * t_years)
        n_d1 = norm_pdf(d1)

        # Delta
        if option_type == OptionType.CALL:
            delta = df_q * norm_cdf(d1)
        else:
            delta = -df_q * norm_cdf(-d1)

        # Gamma (identical for Call and Put)
        gamma = (df_q * n_d1) / (spot * vol * sqrt_t)

        # Vega (per 1% change in vol)
        vega = (spot * df_q * n_d1 * sqrt_t) / 100.0

        # Theta (1-day calendar theta decay)
        term1 = -(spot * df_q * n_d1 * vol) / (2.0 * sqrt_t)
        if option_type == OptionType.CALL:
            term2 = -rate * strike * df_r * norm_cdf(d2) + div_yield * spot * df_q * norm_cdf(d1)
        else:
            term2 = rate * strike * df_r * norm_cdf(-d2) - div_yield * spot * df_q * norm_cdf(-d1)
        theta_annual = term1 + term2
        theta_daily = theta_annual / 365.0

        # Rho (per 1% change in interest rate)
        if option_type == OptionType.CALL:
            rho = (strike * t_years * df_r * norm_cdf(d2)) / 100.0
        else:
            rho = (-strike * t_years * df_r * norm_cdf(-d2)) / 100.0

        return OptionGreeks(
            delta=delta,
            gamma=gamma,
            theta=theta_daily,
            vega=vega,
            rho=rho,
        )

    def calculate_iv(
        self,
        price: float,
        spot: float,
        strike: float,
        t_years: float,
        rate: float,
        option_type: OptionType = OptionType.CALL,
        div_yield: float = 0.0,
        max_iter: int = 100,
        tol: float = 1e-6,
    ) -> float | None:
        """Solve for implied volatility using Newton-Raphson with bisection fallback."""
        if t_years <= 0.0 or price <= 0.0:
            return None

        # Intrinsic value arbitrage bounds check
        df_q = math.exp(-div_yield * t_years)
        df_r = math.exp(-rate * t_years)
        if option_type == OptionType.CALL:
            intrinsic = max(0.0, spot * df_q - strike * df_r)
        else:
            intrinsic = max(0.0, strike * df_r - spot * df_q)

        if price < intrinsic - 1e-6:
            return None

        # Initial volatility estimate (Brenner-Subrahmanyam approximation)
        vol = math.sqrt(2.0 * math.pi / t_years) * (price / spot)
        vol = max(0.05, min(1.5, vol))

        low_vol = 0.001
        high_vol = 5.0

        for _ in range(max_iter):
            theo_price = self.price(
                spot, strike, t_years, rate, vol, option_type=option_type, div_yield=div_yield
            )
            diff = theo_price - price
            if abs(diff) < tol:
                return vol

            # Derivative w.r.t vol (Vega * 100)
            greeks = self.calculate_greeks(
                spot, strike, t_years, rate, vol, option_type=option_type, div_yield=div_yield
            )
            raw_vega = greeks.vega * 100.0

            if raw_vega > 1e-6:
                new_vol = vol - diff / raw_vega
                if low_vol <= new_vol <= high_vol:
                    vol = new_vol
                    continue

            # Bisection fallback step
            if diff > 0:
                high_vol = vol
            else:
                low_vol = vol
            vol = 0.5 * (low_vol + high_vol)

            if (high_vol - low_vol) < tol:
                return vol

        return vol


class ContinuousOptionSurface:
    """Generates synthetic continuous option surfaces across moneyness and constant maturity."""

    def __init__(self, pricer: BlackScholesPricer | None = None) -> None:
        self.pricer = pricer or BlackScholesPricer()

    def generate_constant_moneyness_surface(
        self,
        spot: float,
        dte_days: float,
        atm_vol: float,
        rate: float = 0.065,
        div_yield: float = 0.0,
        moneyness_levels: list[float] | None = None,
        skew_slope: float = 0.0,
    ) -> list[dict[str, Any]]:
        """Generate constant moneyness surface slices (ATM, OTM, ITM) with Greeks."""
        levels = moneyness_levels or [0.90, 0.95, 0.975, 1.0, 1.025, 1.05, 1.10]
        t_years = max(0.0001, dte_days / 365.0)

        rows: list[dict[str, Any]] = []
        for m in levels:
            strike = round(spot * m, 2)
            # Apply quadratic or linear skew if slope is provided
            vol_m = max(0.01, atm_vol + skew_slope * (1.0 - m))

            # Call
            call_p = self.pricer.price(
                spot, strike, t_years, rate, vol_m, option_type=OptionType.CALL, div_yield=div_yield
            )
            call_g = self.pricer.calculate_greeks(
                spot, strike, t_years, rate, vol_m, option_type=OptionType.CALL, div_yield=div_yield
            )

            # Put
            put_p = self.pricer.price(
                spot, strike, t_years, rate, vol_m, option_type=OptionType.PUT, div_yield=div_yield
            )
            put_g = self.pricer.calculate_greeks(
                spot, strike, t_years, rate, vol_m, option_type=OptionType.PUT, div_yield=div_yield
            )

            rows.append(
                {
                    "moneyness": m,
                    "strike": strike,
                    "dte_days": dte_days,
                    "volatility": vol_m,
                    "call_price": round(call_p, 4),
                    "call_delta": round(call_g.delta, 4),
                    "call_theta": round(call_g.theta, 4),
                    "put_price": round(put_p, 4),
                    "put_delta": round(put_g.delta, 4),
                    "put_theta": round(put_g.theta, 4),
                    "gamma": round(call_g.gamma, 6),
                    "vega": round(call_g.vega, 4),
                }
            )

        return rows
