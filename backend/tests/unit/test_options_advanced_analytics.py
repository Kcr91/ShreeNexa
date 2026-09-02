"""Unit tests for Option Chain Analytics suite."""

from __future__ import annotations

from datetime import date
from zoneinfo import ZoneInfo

from app.analytics.options_analytics import (
    TermStructurePoint,
    calculate_atm_iv,
    calculate_iv_rank_and_percentile,
    calculate_iv_skew_and_smile,
    calculate_max_pain,
    calculate_put_call_ratios,
    calculate_term_structure,
)
from app.main import app
from fastapi.testclient import TestClient

IST = ZoneInfo("Asia/Kolkata")
client = TestClient(app)


def test_atm_iv_linear_interpolation() -> None:
    strikes = [24900.0, 25000.0, 25100.0]
    call_ivs = [0.150, 0.140, 0.130]
    put_ivs = [0.150, 0.140, 0.130]

    # Exact ATM
    atm_iv = calculate_atm_iv(25000.0, strikes, call_ivs, put_ivs)
    assert atm_iv == 0.140

    # Midpoint interpolation (25050 -> 0.135)
    mid_iv = calculate_atm_iv(25050.0, strikes, call_ivs, put_ivs)
    assert mid_iv == 0.135


def test_iv_rank_and_percentile_with_minimum_history() -> None:
    # 1. Standard valid 50-day history
    history = [0.10 + 0.002 * i for i in range(50)]  # range [0.10, 0.198]
    current = 0.149  # Near 50th percentile

    res = calculate_iv_rank_and_percentile(current, history, min_history_days=30)
    assert res.is_valid is True
    assert res.history_days_count == 50
    assert res.iv_min_52w == 0.10
    assert res.iv_max_52w == 0.198
    assert 48.0 <= (res.iv_rank or 0.0) <= 52.0
    assert 48.0 <= (res.iv_percentile or 0.0) <= 52.0

    # 2. Division-by-zero protection (min == max)
    flat_history = [0.14] * 40
    res_flat = calculate_iv_rank_and_percentile(0.14, flat_history, min_history_days=30)
    assert res_flat.is_valid is True
    assert res_flat.iv_rank == 50.0

    # 3. Insufficient history rule (< 30 days)
    short_history = [0.12, 0.13, 0.14]
    res_short = calculate_iv_rank_and_percentile(0.13, short_history, min_history_days=30)
    assert res_short.is_valid is False
    assert res_short.iv_rank is None
    assert res_short.iv_percentile is None
    assert "Insufficient historical IV observations" in (res_short.unreliable_reason or "")


def test_max_pain_independent_fixture() -> None:
    """Hand-calculated 3-strike Max Pain test vector:

    K=100: Call OI=1000, Put OI=0
    K=105: Call OI=500,  Put OI=500
    K=110: Call OI=0,    Put OI=1000
    Minimum cumulative buyer loss occurs at K=105.
    """
    strikes = [100.0, 105.0, 110.0]
    call_ois = [1000, 500, 0]
    put_ois = [0, 500, 1000]

    res = calculate_max_pain(strikes, call_ois, put_ois, spot_price=104.5)
    assert res.max_pain_strike == 105.0
    assert res.total_cash_loss_at_pain == 10000.0
    assert res.strike_distance_from_spot == 0.5


def test_pcr_calculation_and_guards() -> None:
    call_ois = [10000, 20000, 30000]
    put_ois = [15000, 25000, 35000]
    call_vols = [5000, 10000, 15000]
    put_vols = [6000, 12000, 18000]

    pcr = calculate_put_call_ratios(call_ois, put_ois, call_vols, put_vols)
    # Put OI = 75000, Call OI = 60000 -> PCR_OI = 1.25
    assert pcr.pcr_oi == 1.25
    # Put Vol = 36000, Call Vol = 30000 -> PCR_Vol = 1.20
    assert pcr.pcr_volume == 1.20

    # Zero-denominator guard
    zero_pcr = calculate_put_call_ratios([0], [100], [0], [50])
    assert zero_pcr.pcr_oi == 1.0


def test_iv_skew_and_smile() -> None:
    spot = 25000.0
    forward = 25080.0
    strikes = [24600.0, 24800.0, 25000.0, 25200.0, 25400.0]
    call_ivs = [0.155, 0.145, 0.140, 0.135, 0.130]
    put_ivs = [0.170, 0.155, 0.140, 0.130, 0.125]
    call_deltas = [0.80, 0.65, 0.50, 0.35, 0.20]
    put_deltas = [-0.20, -0.35, -0.50, -0.65, -0.80]

    skew = calculate_iv_skew_and_smile(
        spot_price=spot,
        strikes=strikes,
        call_ivs=call_ivs,
        put_ivs=put_ivs,
        call_deltas=call_deltas,
        put_deltas=put_deltas,
        expiry_date=date(2026, 9, 24),
        forward_price=forward,
    )

    assert skew.atm_iv == 0.140
    assert len(skew.smile_points) == 5
    # 25d Put is ~24600 (put_delta=-0.20) -> IV=0.170
    # 25d Call is ~25400 (call_delta=0.20) -> IV=0.130
    # Risk Reversal = 0.170 - 0.130 = +0.040
    assert skew.risk_reversal_25d > 0.0


def test_term_structure_regime() -> None:
    # Contango: Longer expiries have higher IV
    contango_pts = [
        TermStructurePoint(
            expiry_date=date(2026, 9, 10), days_to_expiry=7, atm_iv=0.130, forward_price=25000
        ),
        TermStructurePoint(
            expiry_date=date(2026, 9, 17), days_to_expiry=14, atm_iv=0.138, forward_price=25020
        ),
        TermStructurePoint(
            expiry_date=date(2026, 9, 24), days_to_expiry=21, atm_iv=0.145, forward_price=25040
        ),
    ]
    res_contango = calculate_term_structure(contango_pts)
    assert res_contango.regime == "CONTANGO"
    assert res_contango.slope > 0.0

    # Backwardation: Shorter expiries have higher IV (e.g. event spike)
    backward_pts = [
        TermStructurePoint(
            expiry_date=date(2026, 9, 10), days_to_expiry=7, atm_iv=0.220, forward_price=25000
        ),
        TermStructurePoint(
            expiry_date=date(2026, 9, 17), days_to_expiry=14, atm_iv=0.180, forward_price=25020
        ),
        TermStructurePoint(
            expiry_date=date(2026, 9, 24), days_to_expiry=21, atm_iv=0.150, forward_price=25040
        ),
    ]
    res_backward = calculate_term_structure(backward_pts)
    assert res_backward.regime == "BACKWARDATION"
    assert res_backward.slope < 0.0


def test_options_analytics_rest_api() -> None:
    # 1. GET analytics bundle
    resp = client.get("/api/v1/options/analytics/NIFTY")
    assert resp.status_code == 200
    data = resp.json()
    assert data["underlying"] == "NIFTY"
    assert data["atm_iv"] > 0
    assert data["pcr"]["pcr_oi"] > 0
    assert data["max_pain"]["max_pain_strike"] > 0
    assert len(data["skew"]["smile_points"]) > 0
    assert len(data["term_structure"]["points"]) > 0

    # 2. POST custom compute
    payload = {
        "underlying": "NIFTY",
        "spot_price": 25000.0,
        "expiry_date": "2026-09-24",
        "strikes": [24800.0, 25000.0, 25200.0],
        "call_ivs": [0.145, 0.140, 0.135],
        "put_ivs": [0.155, 0.140, 0.130],
        "call_ois": [100000, 200000, 300000],
        "put_ois": [300000, 200000, 100000],
        "call_vols": [50000, 100000, 150000],
        "put_vols": [150000, 100000, 50000],
        "call_deltas": [0.65, 0.50, 0.35],
        "put_deltas": [-0.35, -0.50, -0.65],
        "historical_daily_ivs": [0.12 + 0.001 * i for i in range(40)],
        "term_structure_points": [
            {
                "expiry_date": "2026-09-17",
                "days_to_expiry": 7,
                "atm_iv": 0.135,
                "forward_price": 25020.0,
            },
            {
                "expiry_date": "2026-09-24",
                "days_to_expiry": 14,
                "atm_iv": 0.140,
                "forward_price": 25040.0,
            },
        ],
    }
    resp_post = client.post("/api/v1/options/analytics/compute", json=payload)
    assert resp_post.status_code == 200
    post_data = resp_post.json()
    assert post_data["underlying"] == "NIFTY"
    assert post_data["iv_rank"]["is_valid"] is True
    assert post_data["term_structure"]["regime"] == "CONTANGO"
