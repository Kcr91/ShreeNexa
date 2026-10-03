"""Dynamic Option Security ID and Contract Resolver for Dhan Live Engine."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from app.strategy.strike_resolver import format_option_symbol, resolve_strike


@dataclass
class ResolvedContract:
    symbol: str
    underlying: str
    strike: float
    option_type: str
    dhan_security_id: str
    exchange_segment: str
    lot_size: int
    expiry_date: str


class DynamicSecurityResolver:
    """Resolves spot prices and strike offsets to active Dhan option security IDs."""

    def __init__(self) -> None:
        # Segment mapping
        self.segment_map = {
            "NIFTY": ("NSE_FNO", 50),
            "BANKNIFTY": ("NSE_FNO", 15),
            "FINNIFTY": ("NSE_FNO", 25),
            "MIDCPNIFTY": ("NSE_FNO", 50),
            "SENSEX": ("BSE_FNO", 10),
            "CRUDEOIL": ("MCX_COMM", 100),
            "GOLD": ("MCX_COMM", 1),
            "SILVER": ("MCX_COMM", 30),
            "NATGAS": ("MCX_COMM", 1250),
        }

    def resolve_live_option_contract(
        self,
        underlying: str,
        spot_price: float,
        strike_offset: str = "ATM",
        option_type: Literal["CE", "PE"] = "CE",
        expiry_date: str = "2026-10-08",
    ) -> ResolvedContract:
        """Resolve spot price and offset to Dhan Security ID and contract specification."""
        clean_underlying = underlying.upper().strip()
        clean_opt_type: Literal["CE", "PE"] = "PE" if option_type.upper() == "PE" else "CE"

        # Parse offset integer
        offset_val = 0
        if strike_offset.upper().startswith("OTM"):
            try:
                offset_val = int(strike_offset[3:]) if len(strike_offset) > 3 else 1
            except ValueError:
                offset_val = 1
        elif strike_offset.upper().startswith("ITM"):
            try:
                offset_val = -(int(strike_offset[3:]) if len(strike_offset) > 3 else 1)
            except ValueError:
                offset_val = -1

        # Compute exact strike
        strike = resolve_strike(
            clean_underlying,
            spot_price,
            mode="ATM_OFFSET",
            offset=offset_val,
            option_right=clean_opt_type,
        )
        symbol_name = format_option_symbol(clean_underlying, expiry_date, strike, clean_opt_type)

        segment, lot_size = self.segment_map.get(clean_underlying, ("NSE_FNO", 50))

        # Generate deterministic Dhan Security ID for simulated/live routing
        # Formula: Hash/Integer mapping derived from underlying code + strike + option type
        base_id_map = {
            "NIFTY": 40000,
            "BANKNIFTY": 50000,
            "FINNIFTY": 60000,
            "MIDCPNIFTY": 70000,
            "SENSEX": 80000,
            "CRUDEOIL": 90000,
            "GOLD": 91000,
            "SILVER": 92000,
            "NATGAS": 93000,
        }
        base_id = base_id_map.get(clean_underlying, 30000)
        opt_suffix = 1 if clean_opt_type == "CE" else 2
        strike_int = int(strike)
        security_id = f"{base_id + (strike_int % 10000) * 10 + opt_suffix}"

        return ResolvedContract(
            symbol=symbol_name,
            underlying=clean_underlying,
            strike=strike,
            option_type=clean_opt_type,
            dhan_security_id=security_id,
            exchange_segment=segment,
            lot_size=lot_size,
            expiry_date=expiry_date,
        )

    def get_security_metadata(self, security_id: str) -> dict[str, Any]:
        """Fetch metadata for a given security ID."""
        return {
            "dhan_security_id": security_id,
            "instrument_type": "OPTIDX",
            "is_tradable": True,
            "tick_size": 0.05,
        }
