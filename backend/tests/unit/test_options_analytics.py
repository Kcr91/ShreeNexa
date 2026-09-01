"""Unit tests for Black-Scholes-Merton pricing, IV inversion, Greeks, and option surfaces."""

from __future__ import annotations

import json
import math
from pathlib import Path

from app.marketdata.options_analytics import (
    BlackScholesPricer,
    ContinuousOptionSurface,
    OptionType,
)

FIXTURE_PATH = Path(__file__).parents[1] / "fixtures" / "sample_option_surface_greeks.json"


def test_black_scholes_pricing_against_reference_fixture() -> None:
    """Verify BSM pricing and Greeks against independent reference fixture."""
    data = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    tc = data["test_cases"][0]

    pricer = BlackScholesPricer()
    t_years = tc["dte_days"] / 365.0

    call_price = pricer.price(
        spot=tc["spot"],
        strike=tc["strike"],
        t_years=t_years,
        rate=tc["rate"],
        vol=tc["volatility"],
        option_type=OptionType.CALL,
        div_yield=tc["dividend_yield"],
    )
    put_price = pricer.price(
        spot=tc["spot"],
        strike=tc["strike"],
        t_years=t_years,
        rate=tc["rate"],
        vol=tc["volatility"],
        option_type=OptionType.PUT,
        div_yield=tc["dividend_yield"],
    )

    assert round(call_price, 2) == tc["expected_call_price"]
    assert round(put_price, 2) == tc["expected_put_price"]

    call_greeks = pricer.calculate_greeks(
        spot=tc["spot"],
        strike=tc["strike"],
        t_years=t_years,
        rate=tc["rate"],
        vol=tc["volatility"],
        option_type=OptionType.CALL,
        div_yield=tc["dividend_yield"],
    )
    put_greeks = pricer.calculate_greeks(
        spot=tc["spot"],
        strike=tc["strike"],
        t_years=t_years,
        rate=tc["rate"],
        vol=tc["volatility"],
        option_type=OptionType.PUT,
        div_yield=tc["dividend_yield"],
    )

    assert round(call_greeks.delta, 4) == tc["expected_call_delta"]
    assert round(put_greeks.delta, 4) == tc["expected_put_delta"]
    assert round(call_greeks.gamma, 6) == tc["expected_gamma"]
    assert round(call_greeks.vega, 2) == tc["expected_vega"]
    assert round(call_greeks.theta, 2) == tc["expected_call_theta"]
    assert round(put_greeks.theta, 2) == tc["expected_put_theta"]


def test_put_call_parity_exact() -> None:
    """Verify exact put-call parity: C - P = S * exp(-q*T) - K * exp(-r*T)."""
    pricer = BlackScholesPricer()
    spot = 24500.0
    strike = 25000.0
    t_years = 45.0 / 365.0
    rate = 0.065
    div_yield = 0.012
    vol = 0.18

    call = pricer.price(
        spot, strike, t_years, rate, vol, option_type=OptionType.CALL, div_yield=div_yield
    )
    put = pricer.price(
        spot, strike, t_years, rate, vol, option_type=OptionType.PUT, div_yield=div_yield
    )

    lhs = call - put
    rhs = spot * math.exp(-div_yield * t_years) - strike * math.exp(-rate * t_years)
    assert abs(lhs - rhs) < 1e-4


def test_iv_inversion_high_precision() -> None:
    """Verify recovering exact target volatility from market price using IV solver."""
    pricer = BlackScholesPricer()
    spot = 25000.0
    strike = 25200.0
    t_years = 15.0 / 365.0
    rate = 0.065
    target_vol = 0.2345

    market_call_price = pricer.price(
        spot, strike, t_years, rate, target_vol, option_type=OptionType.CALL
    )
    recovered_iv = pricer.calculate_iv(
        price=market_call_price,
        spot=spot,
        strike=strike,
        t_years=t_years,
        rate=rate,
        option_type=OptionType.CALL,
    )

    assert recovered_iv is not None
    assert abs(recovered_iv - target_vol) < 1e-5


def test_constant_moneyness_surface_generation() -> None:
    """Verify generating constant moneyness grid with skew and Greeks."""
    surface = ContinuousOptionSurface()
    grid = surface.generate_constant_moneyness_surface(
        spot=25000.0,
        dte_days=30.0,
        atm_vol=0.15,
        skew_slope=0.05,
    )

    assert len(grid) == 7  # 0.90, 0.95, 0.975, 1.0, 1.025, 1.05, 1.10
    atm_row = next(r for r in grid if r["moneyness"] == 1.0)
    assert atm_row["strike"] == 25000.0
    assert atm_row["volatility"] == 0.15
    assert 0.45 < atm_row["call_delta"] < 0.60
    assert -0.60 < atm_row["put_delta"] < -0.40
    assert atm_row["gamma"] > 0
    assert atm_row["vega"] > 0
    assert atm_row["call_theta"] < 0
