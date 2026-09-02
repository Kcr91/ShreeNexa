"""Unit tests for Dhan option chain calibration, convention fitting, and drift detection."""

from __future__ import annotations

from datetime import date, datetime
from zoneinfo import ZoneInfo

from app.analytics.calibration import (
    DhanOptionContractGreeks,
    DhanOptionQuote,
    DriftStatus,
    ExclusionReason,
    calibrate_option_chain,
)
from app.analytics.greeks import OptionType, price_black76_scalar
from app.main import app
from fastapi.testclient import TestClient

IST = ZoneInfo("Asia/Kolkata")
client = TestClient(app)


def _build_test_quotes(
    spot: float = 25000.0,
    strikes_count: int = 15,
    strike_step: float = 50.0,
    theta_noise: float = 0.0,
    t_years: float = 14.0 / 365.0,
) -> list[DhanOptionQuote]:
    """Generate sample Dhan-like option chain quotes for testing."""
    quotes: list[DhanOptionQuote] = []
    atm_strike = round(spot / strike_step) * strike_step
    r = 0.07
    vol = 0.15
    f = spot * 1.003

    for i in range(-strikes_count, strikes_count + 1):
        strike = atm_strike + i * strike_step

        # Call
        res_c = price_black76_scalar(
            forward=f, strike=strike, t_years=t_years, rate=r, vol=vol, option_type=OptionType.CALL
        )
        quotes.append(
            DhanOptionQuote(
                strike=strike,
                option_type=OptionType.CALL,
                last_price=res_c.price,
                bid=max(0.05, round(res_c.price - 0.20, 2)),
                ask=round(res_c.price + 0.20, 2),
                iv=vol,
                oi=200000,
                volume=150000,
                greeks=DhanOptionContractGreeks(
                    delta=res_c.delta,
                    gamma=res_c.gamma,
                    theta=res_c.theta + theta_noise,
                    vega=res_c.vega,
                    rho=res_c.rho,
                ),
            )
        )

        # Put
        res_p = price_black76_scalar(
            forward=f, strike=strike, t_years=t_years, rate=r, vol=vol, option_type=OptionType.PUT
        )
        quotes.append(
            DhanOptionQuote(
                strike=strike,
                option_type=OptionType.PUT,
                last_price=res_p.price,
                bid=max(0.05, round(res_p.price - 0.20, 2)),
                ask=round(res_p.price + 0.20, 2),
                iv=vol,
                oi=190000,
                volume=140000,
                greeks=DhanOptionContractGreeks(
                    delta=res_p.delta,
                    gamma=res_p.gamma,
                    theta=res_p.theta + theta_noise,
                    vega=res_p.vega,
                    rho=res_p.rho,
                ),
            )
        )

    return quotes


def test_dhan_chain_calibration_reconciles_at_least_20_strikes() -> None:
    spot = 25000.0
    exp = date(2026, 9, 17)
    curr_time = datetime(2026, 9, 3, 10, 0, tzinfo=IST)
    quotes = _build_test_quotes(spot=spot, strikes_count=15, strike_step=50.0)

    report = calibrate_option_chain(
        underlying="NIFTY",
        spot_price=spot,
        expiry_date=exp,
        quotes=quotes,
        futures_price=spot * 1.003,
        current_time=curr_time,
    )

    # Acceptance requirement: At least 20 strikes reconcile
    assert report.reconciled_strikes_count >= 20
    assert report.status == DriftStatus.CALIBRATED
    assert "🟢 Calibrated" in report.drift_badge_text
    assert report.theta_rmse < 0.20
    assert report.theta_mae < 0.20
    assert report.delta_mae < 0.05
    assert report.iv_mae < 0.02


def test_theta_convention_explicit_validation() -> None:
    from app.analytics.greeks import calculate_time_to_expiry

    spot = 52000.0
    exp = date(2026, 9, 24)
    curr_time = datetime(2026, 9, 3, 11, 30, tzinfo=IST)
    t_years = calculate_time_to_expiry(curr_time, exp)
    quotes = _build_test_quotes(
        spot=spot, strikes_count=12, strike_step=100.0, t_years=t_years
    )

    report = calibrate_option_chain(
        underlying="BANKNIFTY",
        spot_price=spot,
        expiry_date=exp,
        quotes=quotes,
        futures_price=spot * 1.0025,
        current_time=curr_time,
    )

    # Validate theta error specifically
    assert report.theta_rmse <= 0.50
    assert report.theta_mae <= 0.50
    assert report.best_convention.annualization_factor in {365, 252}


def test_unreliable_quote_exclusion_with_reasons() -> None:
    spot = 25000.0
    exp = date(2026, 9, 17)
    curr_time = datetime(2026, 9, 3, 10, 0, tzinfo=IST)
    quotes = _build_test_quotes(spot=spot, strikes_count=10, strike_step=50.0)

    # Inject unreliable quotes
    # 1. Zero liquidity
    quotes.append(
        DhanOptionQuote(
            strike=27000.0,
            option_type=OptionType.CALL,
            last_price=10.0,
            bid=9.0,
            ask=11.0,
            iv=0.15,
            oi=0,
            volume=0,
            greeks=DhanOptionContractGreeks(delta=0.01, gamma=0.0001, theta=-1.0, vega=0.5),
        )
    )
    # 2. Wide spread
    quotes.append(
        DhanOptionQuote(
            strike=24000.0,
            option_type=OptionType.PUT,
            last_price=20.0,
            bid=5.0,
            ask=35.0,
            iv=0.15,
            oi=10000,
            volume=5000,
            greeks=DhanOptionContractGreeks(delta=-0.1, gamma=0.0001, theta=-2.0, vega=1.0),
        )
    )
    # 3. Deep OTM (>18% away from spot)
    quotes.append(
        DhanOptionQuote(
            strike=31000.0,
            option_type=OptionType.CALL,
            last_price=0.5,
            bid=0.4,
            ask=0.6,
            iv=0.15,
            oi=50000,
            volume=20000,
            greeks=DhanOptionContractGreeks(delta=0.001, gamma=0.00001, theta=-0.1, vega=0.05),
        )
    )

    report = calibrate_option_chain(
        underlying="NIFTY",
        spot_price=spot,
        expiry_date=exp,
        quotes=quotes,
        futures_price=spot * 1.003,
        current_time=curr_time,
    )

    assert report.excluded_strikes_count >= 3
    assert ExclusionReason.ZERO_LIQUIDITY.value in report.exclusion_summary
    assert ExclusionReason.WIDE_SPREAD.value in report.exclusion_summary
    assert ExclusionReason.DEEP_OTM_ITM.value in report.exclusion_summary


def test_drift_detection_warning_and_critical() -> None:
    spot = 25000.0
    exp = date(2026, 9, 17)
    curr_time = datetime(2026, 9, 3, 10, 0, tzinfo=IST)

    # Distort theta significantly (+8.0 INR offset on theta)
    distorted_quotes = _build_test_quotes(
        spot=spot, strikes_count=15, strike_step=50.0, theta_noise=8.0
    )

    report = calibrate_option_chain(
        underlying="NIFTY",
        spot_price=spot,
        expiry_date=exp,
        quotes=distorted_quotes,
        futures_price=spot * 1.003,
        current_time=curr_time,
    )

    assert report.status in {DriftStatus.DRIFT_DETECTED, DriftStatus.WARNING}
    assert "Drift" in report.drift_badge_text


def test_calibration_api_endpoints() -> None:
    # 1. GET initial calibration for NIFTY
    resp = client.get("/api/v1/options/calibration/NIFTY")
    assert resp.status_code == 200
    data = resp.json()
    assert data["underlying"] == "NIFTY"
    assert data["status"] in ["CALIBRATED", "WARNING", "DRIFT_DETECTED"]
    assert data["reconciled_strikes_count"] >= 20
    assert len(data["strike_comparisons"]) >= 20

    # 2. POST custom calibration
    quotes = _build_test_quotes(spot=25000.0, strikes_count=12)
    payload = {
        "underlying": "NIFTY",
        "spot_price": 25000.0,
        "expiry_date": "2026-09-17",
        "quotes": [q.model_dump() for q in quotes],
        "futures_price": 25080.0,
    }
    resp_post = client.post("/api/v1/options/calibration/calibrate", json=payload)
    assert resp_post.status_code == 200
    post_data = resp_post.json()
    assert post_data["reconciled_strikes_count"] >= 20
    assert post_data["status"] == "CALIBRATED"
