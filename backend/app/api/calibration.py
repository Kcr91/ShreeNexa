"""REST API endpoints for Dhan option-chain calibration and drift monitoring."""

from __future__ import annotations

from datetime import date, datetime

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.analytics.calibration import (
    IST,
    CalibrationReport,
    DhanOptionContractGreeks,
    DhanOptionQuote,
    TolerancePolicy,
    calibrate_option_chain,
)
from app.analytics.calibration_store import get_calibration_store
from app.analytics.greeks import (
    DEFAULT_OPTION_CONVENTIONS,
    OptionType,
    calculate_time_to_expiry,
    price_black76_scalar,
)

router = APIRouter(prefix="/api/v1/options/calibration", tags=["Options Calibration"])


class CalibrateRequest(BaseModel):
    """Payload for submitting option quotes for calibration fitting."""

    underlying: str = Field(..., description="Underlying symbol, e.g. NIFTY")
    spot_price: float = Field(..., gt=0, description="Underlying spot price")
    expiry_date: date = Field(..., description="Option expiry date")
    quotes: list[DhanOptionQuote] = Field(..., min_length=1)
    futures_price: float | None = Field(default=None)
    tolerance_policy: TolerancePolicy = Field(default_factory=TolerancePolicy)


def _generate_synthetic_benchmark_chain(
    underlying: str,
    spot_price: float,
    expiry_date: date,
    current_time: datetime,
) -> list[DhanOptionQuote]:
    """Generate a high-fidelity synthetic benchmark chain with 30 strikes for testing/fallback."""
    step = 50.0 if "NIFTY" in underlying else 100.0
    atm_strike = round(spot_price / step) * step
    t_years = calculate_time_to_expiry(current_time, expiry_date, DEFAULT_OPTION_CONVENTIONS)
    quotes: list[DhanOptionQuote] = []

    for i in range(-15, 16):
        strike = atm_strike + i * step
        # Call
        res_c = price_black76_scalar(
            forward=spot_price * 1.003,
            strike=strike,
            t_years=t_years,
            rate=0.07,
            vol=0.145,
            option_type=OptionType.CALL,
        )
        quotes.append(
            DhanOptionQuote(
                strike=strike,
                option_type=OptionType.CALL,
                last_price=res_c.price,
                bid=max(0.05, round(res_c.price - 0.20, 2)),
                ask=round(res_c.price + 0.20, 2),
                iv=0.145,
                oi=250000,
                volume=180000,
                greeks=DhanOptionContractGreeks(
                    delta=res_c.delta,
                    gamma=res_c.gamma,
                    theta=res_c.theta,
                    vega=res_c.vega,
                    rho=res_c.rho,
                ),
            )
        )
        # Put
        res_p = price_black76_scalar(
            forward=spot_price * 1.003,
            strike=strike,
            t_years=t_years,
            rate=0.07,
            vol=0.145,
            option_type=OptionType.PUT,
        )
        quotes.append(
            DhanOptionQuote(
                strike=strike,
                option_type=OptionType.PUT,
                last_price=res_p.price,
                bid=max(0.05, round(res_p.price - 0.20, 2)),
                ask=round(res_p.price + 0.20, 2),
                iv=0.145,
                oi=240000,
                volume=175000,
                greeks=DhanOptionContractGreeks(
                    delta=res_p.delta,
                    gamma=res_p.gamma,
                    theta=res_p.theta,
                    vega=res_p.vega,
                    rho=res_p.rho,
                ),
            )
        )

    return quotes


@router.get("/{underlying}", response_model=CalibrationReport)
def get_calibration(underlying: str) -> CalibrationReport:
    """Retrieve current calibration status, fitted conventions, and drift metrics."""
    store = get_calibration_store()
    report = store.get(underlying)
    if report is not None:
        return report

    # Generate default initial calibrated state for common underlyings
    spot = 25000.0 if underlying.upper() == "NIFTY" else 52000.0
    now = datetime.now(tz=IST)
    exp = date.fromordinal(date.today().toordinal() + 14)
    quotes = _generate_synthetic_benchmark_chain(underlying.upper(), spot, exp, now)
    fresh_report = calibrate_option_chain(
        underlying=underlying.upper(),
        spot_price=spot,
        expiry_date=exp,
        quotes=quotes,
        futures_price=spot * 1.003,
        current_time=now,
    )
    store.save(underlying.upper(), fresh_report)
    return fresh_report


@router.post("/calibrate", response_model=CalibrationReport)
def run_calibration(req: CalibrateRequest) -> CalibrationReport:
    """Execute convention fitting against supplied Dhan option chain quotes and store report."""
    report = calibrate_option_chain(
        underlying=req.underlying.upper(),
        spot_price=req.spot_price,
        expiry_date=req.expiry_date,
        quotes=req.quotes,
        futures_price=req.futures_price,
        tolerance_policy=req.tolerance_policy,
    )
    store = get_calibration_store()
    store.save(req.underlying.upper(), report)
    return report
