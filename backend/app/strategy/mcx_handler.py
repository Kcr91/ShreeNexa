"""MCX Commodity contract specifications and session constraints handler."""

from __future__ import annotations

from datetime import time
from typing import Any, NamedTuple


class CommoditySpec(NamedTuple):
    """MCX Commodity Contract Specifications."""

    symbol: str
    display_name: str
    lot_size: int
    tick_size: float
    multiplier: float
    session_start: str = "09:00:00"
    session_end: str = "23:30:00"
    winter_session_end: str = "23:55:00"


MCX_COMMODITY_SPECS: dict[str, CommoditySpec] = {
    "GOLD": CommoditySpec(
        symbol="GOLD",
        display_name="Gold 1kg",
        lot_size=100,
        tick_size=1.00,
        multiplier=100.0,
    ),
    "GOLDM": CommoditySpec(
        symbol="GOLDM",
        display_name="Gold Mini 100g",
        lot_size=10,
        tick_size=1.00,
        multiplier=10.0,
    ),
    "SILVER": CommoditySpec(
        symbol="SILVER",
        display_name="Silver 30kg",
        lot_size=30,
        tick_size=1.00,
        multiplier=30.0,
    ),
    "SILVERM": CommoditySpec(
        symbol="SILVERM",
        display_name="Silver Mini 5kg",
        lot_size=5,
        tick_size=1.00,
        multiplier=5.0,
    ),
    "CRUDEOIL": CommoditySpec(
        symbol="CRUDEOIL",
        display_name="Crude Oil 100 BBL",
        lot_size=100,
        tick_size=1.00,
        multiplier=100.0,
    ),
    "NATURALGAS": CommoditySpec(
        symbol="NATURALGAS",
        display_name="Natural Gas 1250 mmBtu",
        lot_size=1250,
        tick_size=0.10,
        multiplier=1250.0,
    ),
    "COPPER": CommoditySpec(
        symbol="COPPER",
        display_name="Copper 2500 kg",
        lot_size=2500,
        tick_size=0.05,
        multiplier=2500.0,
    ),
}


def get_commodity_specs(symbol: str) -> CommoditySpec | None:
    """Retrieve specifications for a given MCX commodity."""
    clean_sym = symbol.upper().replace("-MCX", "").strip()
    return MCX_COMMODITY_SPECS.get(clean_sym)


def parse_time_str(t_str: str) -> time:
    """Parse HH:MM:SS or HH:MM into a datetime.time object."""
    parts = [int(p) for p in t_str.split(":")]
    if len(parts) == 2:
        return time(hour=parts[0], minute=parts[1], second=0)
    elif len(parts) == 3:
        return time(hour=parts[0], minute=parts[1], second=parts[2])
    msg = f"Invalid time string: {t_str}"
    raise ValueError(msg)


def is_within_session(
    current_time: time,
    start_str: str = "09:00:00",
    end_str: str = "23:30:00",
) -> bool:
    """Check if the current time falls within the allowed session window."""
    start = parse_time_str(start_str)
    end = parse_time_str(end_str)
    return start <= current_time <= end


def validate_mcx_quantity(symbol: str, quantity: int) -> dict[str, Any]:
    """Validate if the quantity is a valid multiple of the MCX contract lot size."""
    specs = get_commodity_specs(symbol)
    if not specs:
        return {"valid": False, "error": f"Unknown MCX commodity: {symbol}"}

    if quantity <= 0 or quantity % specs.lot_size != 0:
        return {
            "valid": False,
            "error": (
                f"Quantity {quantity} must be a positive multiple of lot size {specs.lot_size}"
            ),
            "lot_size": specs.lot_size,
        }

    lots = quantity // specs.lot_size
    return {"valid": True, "lots": lots, "lot_size": specs.lot_size, "symbol": specs.symbol}
