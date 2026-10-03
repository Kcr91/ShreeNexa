"""Options Strike and Expiry Resolver Module for Indian Markets."""

from __future__ import annotations

import math
from typing import Literal

# Standard Strike Intervals for major Indian Indices
INDEX_STRIKE_INTERVALS: dict[str, float] = {
    "NIFTY": 50.0,
    "BANKNIFTY": 100.0,
    "FINNIFTY": 50.0,
    "MIDCPNIFTY": 25.0,
    "SENSEX": 100.0,
    "BANKEX": 100.0,
}


def get_strike_interval(underlying: str, spot_price: float | None = None) -> float:
    """Get the standard strike interval for an underlying index or stock."""
    clean = underlying.upper().strip()
    if clean in INDEX_STRIKE_INTERVALS:
        return INDEX_STRIKE_INTERVALS[clean]

    # For equity stocks, estimate interval based on stock price level
    if spot_price is not None:
        if spot_price > 5000:
            return 100.0
        elif spot_price > 2000:
            return 50.0
        elif spot_price > 1000:
            return 20.0
        elif spot_price > 500:
            return 10.0
        elif spot_price > 250:
            return 5.0
        elif spot_price > 100:
            return 2.5
        else:
            return 1.0

    return 50.0


def calculate_atm_strike(spot_price: float, strike_interval: float) -> float:
    """Calculate the exact At-The-Money (ATM) strike price rounded to the nearest interval."""
    if strike_interval <= 0:
        return spot_price
    return round(spot_price / strike_interval) * strike_interval


def resolve_strike(
    underlying: str,
    spot_price: float,
    mode: Literal["ATM_OFFSET", "DELTA", "PREMIUM_RANGE"] = "ATM_OFFSET",
    offset: int = 0,
    option_right: Literal["CE", "PE"] = "CE",
) -> float:
    """Resolve the selected strike price based on ATM offset or selection mode.

    For CE (Call):
      offset > 0 => OTM (higher strike, e.g. +1 => ATM + interval)
      offset < 0 => ITM (lower strike, e.g. -1 => ATM - interval)

    For PE (Put):
      offset > 0 => OTM (lower strike, e.g. +1 => ATM - interval)
      offset < 0 => ITM (higher strike, e.g. -1 => ATM + interval)
    """
    interval = get_strike_interval(underlying, spot_price)
    atm = calculate_atm_strike(spot_price, interval)

    if mode == "ATM_OFFSET":
        if option_right.upper() == "CE":
            return atm + (offset * interval)
        else:  # PE
            return atm - (offset * interval)

    return atm


def format_option_symbol(
    underlying: str,
    expiry_date_str: str,
    strike: float,
    option_right: Literal["CE", "PE"],
) -> str:
    """Format canonical option symbol string (e.g. NIFTY_2026-10-29_25000_CE)."""
    strike_int = int(strike) if math.isclose(strike, int(strike)) else strike
    return f"{underlying.upper()}_{expiry_date_str}_{strike_int}_{option_right.upper()}"
