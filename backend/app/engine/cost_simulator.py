"""Indian Market Transaction Cost, Taxation & Slippage Simulator."""

from __future__ import annotations

from typing import NamedTuple


class TradeCostBreakdown(NamedTuple):
    """Detailed breakdown of all regulatory and brokerage charges."""

    brokerage: float
    stt_tax: float
    exchange_turnover_fee: float
    sebi_charges: float
    stamp_duty: float
    gst: float
    slippage_cost: float
    total_costs: float
    gross_pnl: float
    net_pnl: float


def calculate_trade_costs(
    instrument_type: str,  # "OPTION", "FUTURE", "EQUITY"
    buy_price: float,
    sell_price: float,
    quantity: int,
    brokerage_per_order: float = 20.0,
    slippage_per_unit: float = 0.10,
) -> TradeCostBreakdown:
    """Calculate exact regulatory costs, taxes, brokerage, and net PnL."""
    buy_turnover = buy_price * quantity
    sell_turnover = sell_price * quantity
    gross_pnl = (sell_price - buy_price) * quantity

    # 1. Brokerage (Dhan ₹20 per executed trade on F&O, ₹0 for Equity Delivery)
    if instrument_type.upper() == "EQUITY":
        brokerage = 0.0
    else:
        brokerage = brokerage_per_order * 2.0  # Buy order + Sell order

    # 2. Securities Transaction Tax (STT)
    # Options: 0.125% on sell premium
    # Futures: 0.0125% on sell turnover
    # Equity: 0.1% on both buy & sell
    if instrument_type.upper() == "OPTION":
        stt = sell_turnover * 0.00125
    elif instrument_type.upper() == "FUTURE":
        stt = sell_turnover * 0.000125
    else:  # Equity
        stt = (buy_turnover + sell_turnover) * 0.001

    # 3. Exchange Turnover Fee (NSE)
    # Options: 0.0355% on premium turnover
    # Futures: 0.0019% on turnover
    # Equity: 0.00297%
    if instrument_type.upper() == "OPTION":
        exch_fee = (buy_turnover + sell_turnover) * 0.000355
    elif instrument_type.upper() == "FUTURE":
        exch_fee = (buy_turnover + sell_turnover) * 0.000019
    else:
        exch_fee = (buy_turnover + sell_turnover) * 0.0000297

    # 4. SEBI Charges (₹10 per crore = 0.0001%)
    sebi = (buy_turnover + sell_turnover) * 0.000001

    # 5. Stamp Duty (Buy side only: Options 0.003%, Futures 0.002%, Equity 0.015%)
    if instrument_type.upper() == "OPTION":
        stamp = buy_turnover * 0.00003
    elif instrument_type.upper() == "FUTURE":
        stamp = buy_turnover * 0.00002
    else:
        stamp = buy_turnover * 0.00015

    # 6. GST (18% on Brokerage + Exchange Fee + SEBI)
    gst = (brokerage + exch_fee + sebi) * 0.18

    # 7. Slippage
    slippage_cost = slippage_per_unit * quantity * 2.0  # Buy entry slippage + Sell exit slippage

    total_costs = brokerage + stt + exch_fee + sebi + stamp + gst + slippage_cost
    net_pnl = gross_pnl - total_costs

    return TradeCostBreakdown(
        brokerage=round(brokerage, 2),
        stt_tax=round(stt, 2),
        exchange_turnover_fee=round(exch_fee, 2),
        sebi_charges=round(sebi, 2),
        stamp_duty=round(stamp, 2),
        gst=round(gst, 2),
        slippage_cost=round(slippage_cost, 2),
        total_costs=round(total_costs, 2),
        gross_pnl=round(gross_pnl, 2),
        net_pnl=round(net_pnl, 2),
    )
