"""Unit tests for Black-76 option pricing, closed-form Greeks, and Brent IV solver."""

from __future__ import annotations

import math
from datetime import date, datetime
from zoneinfo import ZoneInfo

import pytest
from app.analytics.greeks import (
    ExpiryTimeMode,
    ForwardSource,
    OptionConventions,
    OptionType,
    calculate_time_to_expiry,
    price_black76_scalar,
    price_black76_vector,
    resolve_forward_price,
    solve_implied_volatility,
)

IST = ZoneInfo("Asia/Kolkata")


def test_black76_known_reference_parity() -> None:
    # Benchmark ATM NIFTY contract: F = 25000, K = 25000, T = 30 / 365, r = 0.07, sigma = 0.15
    f = 25000.0
    k = 25000.0
    t = 30.0 / 365.0
    r = 0.07
    vol = 0.15

    call = price_black76_scalar(
        forward=f, strike=k, t_years=t, rate=r, vol=vol, option_type=OptionType.CALL
    )
    put = price_black76_scalar(
        forward=f, strike=k, t_years=t, rate=r, vol=vol, option_type=OptionType.PUT
    )

    assert call.is_valid
    assert put.is_valid

    # At-the-money forward F=K: Call theoretical price equals Put theoretical price
    assert call.price == pytest.approx(put.price, abs=0.01)
    assert call.price == pytest.approx(426.41, abs=0.05)

    # Greek checks
    assert 0.0 < call.delta < 1.0
    assert -1.0 < put.delta < 0.0
    assert call.gamma > 0.0
    assert put.gamma > 0.0
    assert call.gamma == pytest.approx(put.gamma, abs=1e-6)
    assert call.vega > 0.0
    assert put.vega > 0.0
    assert call.vega == pytest.approx(put.vega, abs=1e-4)
    assert call.theta < 0.0


def test_put_call_parity_exact_across_moneyness() -> None:
    f = 25200.0
    r = 0.07
    t = 45.0 / 365.0
    vol = 0.18

    strikes = [24000.0, 24500.0, 25000.0, 25200.0, 25500.0, 26000.0]
    df_r = math.exp(-r * t)

    for k in strikes:
        c = price_black76_scalar(
            forward=f, strike=k, t_years=t, rate=r, vol=vol, option_type=OptionType.CALL
        )
        p = price_black76_scalar(
            forward=f, strike=k, t_years=t, rate=r, vol=vol, option_type=OptionType.PUT
        )

        # Exact Put-Call Parity: Call - Put = e^(-rT) * (F - K)
        expected_diff = df_r * (f - k)
        actual_diff = c.price - p.price
        assert actual_diff == pytest.approx(expected_diff, abs=0.05)


def test_greek_bounds_and_properties() -> None:
    f = 52000.0
    r = 0.065
    t = 15.0 / 365.0
    vol = 0.16

    # ITM Call / OTM Put
    call_itm = price_black76_scalar(
        forward=f, strike=50000.0, t_years=t, rate=r, vol=vol, option_type=OptionType.CALL
    )
    assert call_itm.delta > 0.85
    assert call_itm.gamma > 0.0
    assert call_itm.vega > 0.0

    # OTM Call / ITM Put
    call_otm = price_black76_scalar(
        forward=f, strike=54000.0, t_years=t, rate=r, vol=vol, option_type=OptionType.CALL
    )
    put_itm = price_black76_scalar(
        forward=f, strike=54000.0, t_years=t, rate=r, vol=vol, option_type=OptionType.PUT
    )
    assert call_otm.delta < 0.20
    assert put_itm.delta < -0.80


def test_forward_selection_hierarchy() -> None:
    spot = 25000.0
    r = 0.07
    t = 20.0 / 365.0
    strike = 25000.0

    # 1. Actual futures LTP takes precedence
    f1, src1 = resolve_forward_price(
        spot_ltp=spot,
        strike=strike,
        rate=r,
        t_years=t,
        futures_ltp=25085.50,
    )
    assert f1 == 25085.50
    assert src1 == ForwardSource.FUTURES_LTP

    # 2. Synthetic forward derived from ATM Put-Call Parity
    f2, src2 = resolve_forward_price(
        spot_ltp=spot,
        strike=strike,
        rate=r,
        t_years=t,
        futures_ltp=None,
        atm_call_ltp=450.0,
        atm_put_ltp=360.0,
    )
    # F = 25000 + e^(0.07 * 20/365) * (450 - 360) = 25000 + 1.00384 * 90 = 25090.35
    assert src2 == ForwardSource.SYNTHETIC_PCP
    assert f2 > 25080.0

    # 3. Cost-of-carry spot fallback
    f3, src3 = resolve_forward_price(
        spot_ltp=spot,
        strike=strike,
        rate=r,
        t_years=t,
        futures_ltp=None,
        atm_call_ltp=None,
        atm_put_ltp=None,
    )
    assert src3 == ForwardSource.SPOT_COC
    assert f3 == pytest.approx(spot * math.exp(r * t), abs=0.01)


def test_brent_iv_inversion_and_accuracy() -> None:
    f = 25200.0
    k = 25000.0
    t = 25.0 / 365.0
    r = 0.07
    true_vol = 0.185

    # Compute reference market price with known vol
    ref = price_black76_scalar(
        forward=f, strike=k, t_years=t, rate=r, vol=true_vol, option_type=OptionType.CALL
    )
    mkt_price = ref.price

    # Invert IV using Brent's method
    solved_iv, reliable, reason = solve_implied_volatility(
        market_price=mkt_price,
        forward=f,
        strike=k,
        t_years=t,
        rate=r,
        option_type=OptionType.CALL,
    )

    assert reliable
    assert reason is None
    assert solved_iv == pytest.approx(true_vol, abs=1e-3)


def test_near_zero_vega_and_intrinsic_guards() -> None:
    f = 25000.0
    r = 0.07
    t = 1.0 / 365.0  # 1 day to expiry

    # Deep OTM Strike (50000) with 1 day to expiry -> near-zero vega
    _, reliable, reason = solve_implied_volatility(
        market_price=0.05,
        forward=f,
        strike=50000.0,
        t_years=t,
        rate=r,
        option_type=OptionType.CALL,
    )
    assert not reliable
    assert "Vega near zero" in (reason or "")

    # Below discounted intrinsic value
    _, reliable2, reason2 = solve_implied_volatility(
        market_price=4000.0,  # Below intrinsic
        forward=f,
        strike=20000.0,
        t_years=0.1,
        rate=r,
        option_type=OptionType.CALL,
    )
    assert not reliable2
    assert "below discounted intrinsic" in (reason2 or "")


def test_calculate_time_to_expiry_conventions() -> None:
    curr = datetime(2026, 9, 3, 10, 0, tzinfo=IST)
    exp = date(2026, 9, 3)

    conv = OptionConventions(
        time_mode=ExpiryTimeMode.CALENDAR_HOURS_TO_CLOSE,
        annualization_factor=365,
    )
    t = calculate_time_to_expiry(curr, exp, conv)

    # 10:00 to 15:30 is 5.5 hours = 5.5 / 24 / 365 = 0.0006278
    assert t == pytest.approx(5.5 / (24.0 * 365.0), rel=1e-3)


def test_vectorized_black76_parity() -> None:
    n = 20
    forwards = [25000.0] * n
    strikes = [24000.0 + i * 100.0 for i in range(n)]
    t_years = [30.0 / 365.0] * n
    rates = [0.07] * n
    vols = [0.16] * n
    is_call = [True] * n

    vec_res = price_black76_vector(
        forwards=forwards,
        strikes=strikes,
        t_years=t_years,
        rates=rates,
        vols=vols,
        is_call=is_call,
    )

    for i in range(n):
        scalar_res = price_black76_scalar(
            forward=forwards[i],
            strike=strikes[i],
            t_years=t_years[i],
            rate=rates[i],
            vol=vols[i],
            option_type=OptionType.CALL,
        )
        assert vec_res["prices"][i] == pytest.approx(scalar_res.price, abs=0.01)
        assert vec_res["deltas"][i] == pytest.approx(scalar_res.delta, abs=1e-5)
        assert vec_res["gammas"][i] == pytest.approx(scalar_res.gamma, abs=1e-5)
        assert vec_res["vegas"][i] == pytest.approx(scalar_res.vega, abs=1e-3)


def test_api_options_endpoints() -> None:
    from app.main import app
    from fastapi.testclient import TestClient

    client = TestClient(app)

    # 1. Price single option
    resp = client.post(
        "/api/v1/options/price",
        json={
            "spot_ltp": 25000.0,
            "strike": 25000.0,
            "t_years": 30.0 / 365.0,
            "rate": 0.07,
            "vol": 0.15,
            "option_type": "CALL",
            "futures_ltp": 25080.0,
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["price"] > 0
    assert data["delta"] > 0
    assert data["forward_source"] == "FUTURES_LTP"
    assert data["forward_used"] == 25080.0

    # 2. Solve IV
    resp_iv = client.post(
        "/api/v1/options/solve-iv",
        json={
            "market_price": 450.0,
            "spot_ltp": 25000.0,
            "strike": 25000.0,
            "t_years": 30.0 / 365.0,
            "rate": 0.07,
            "option_type": "CALL",
        },
    )
    assert resp_iv.status_code == 200
    data_iv = resp_iv.json()
    assert data_iv["is_reliable"] is True
    assert data_iv["iv"] > 0

    # 3. Batch price
    resp_batch = client.post(
        "/api/v1/options/price-batch",
        json={
            "forwards": [25000.0, 25000.0],
            "strikes": [24500.0, 25500.0],
            "t_years": [0.1, 0.1],
            "rates": [0.07, 0.07],
            "vols": [0.15, 0.15],
            "is_call": [True, False],
        },
    )
    assert resp_batch.status_code == 200
    data_batch = resp_batch.json()
    assert len(data_batch["prices"]) == 2
    assert len(data_batch["deltas"]) == 2
