"""Portfolio analytics: XIRR, sector allocation, asset classes, and benchmark performance."""

from __future__ import annotations

from datetime import date
from typing import Any

from app.investing.ledger import HoldingsLedger, holdings_ledger
from app.investing.models import (
    AssetAllocationItem,
    BenchmarkComparisonResult,
    CashFlowItem,
    PortfolioAllocationReport,
    SectorAllocationItem,
    XIRRCalculationResponse,
)
from app.investing.xirr import calculate_xirr

# Standard NSE sector taxonomy for major equities
NSE_SECTOR_MAP: dict[str, str] = {
    "RELIANCE": "Oil, Gas & Energy",
    "ONGC": "Oil, Gas & Energy",
    "BPCL": "Oil, Gas & Energy",
    "TCS": "Information Technology",
    "INFY": "Information Technology",
    "WIPRO": "Information Technology",
    "HCLTECH": "Information Technology",
    "TECHM": "Information Technology",
    "HDFCBANK": "Banking & Financial Services",
    "ICICIBANK": "Banking & Financial Services",
    "SBIN": "Banking & Financial Services",
    "KOTAKBANK": "Banking & Financial Services",
    "AXISBANK": "Banking & Financial Services",
    "BAJFINANCE": "Banking & Financial Services",
    "TATAMOTORS": "Automobiles",
    "MARUTI": "Automobiles",
    "M&M": "Automobiles",
    "BAJAJ-AUTO": "Automobiles",
    "ITC": "Fast Moving Consumer Goods",
    "HINDUNILVR": "Fast Moving Consumer Goods",
    "NESTLEIND": "Fast Moving Consumer Goods",
    "SUNPHARMA": "Healthcare & Pharmaceuticals",
    "DRREDDY": "Healthcare & Pharmaceuticals",
    "CIPLA": "Healthcare & Pharmaceuticals",
    "LT": "Construction & Capital Goods",
    "BHARTIARTL": "Telecommunication",
    "TATASTEEL": "Metals & Mining",
    "JSWSTEEL": "Metals & Mining",
}


def get_security_sector(symbol: str) -> str:
    """Lookup sector for an equity ticker symbol."""
    clean = symbol.upper().replace("-EQ", "").strip()
    return NSE_SECTOR_MAP.get(clean, "Diversified Industrials")


def generate_portfolio_cashflows(
    account_id: str,
    *,
    ledger: HoldingsLedger = holdings_ledger,
    current_prices: dict[str, float] | None = None,
    as_of_date: date | None = None,
) -> list[CashFlowItem]:
    """Generate chronological cash flow series from lots, disposals, and terminal value."""
    report = ledger.generate_portfolio_report(account_id, current_prices=current_prices)
    target_date = as_of_date or date.today()

    cashflows: list[CashFlowItem] = []

    # 1. Negative cashflows: Initial acquisitions
    with ledger._lock:
        acc_dict = ledger._lots.get(account_id, {})
        account_lots = [lot for sec_lots in acc_dict.values() for lot in sec_lots]
        account_disposals = list(ledger._disposals.get(account_id, []))

    for lot in account_lots:
        cost = lot.quantity * lot.acquisition_price
        if cost > 0:
            cashflows.append(
                CashFlowItem(
                    date=lot.acquisition_date,
                    amount=-cost,
                    description=(
                        f"Buy {lot.quantity} {lot.trading_symbol} @ {lot.acquisition_price}"
                    ),
                )
            )

    # 2. Positive cashflows: Disposals (sales)
    for disp in account_disposals:
        proceeds = disp.quantity * disp.disposal_price
        if proceeds > 0:
            cashflows.append(
                CashFlowItem(
                    date=disp.disposal_date,
                    amount=proceeds,
                    description=(
                        f"Sell {disp.quantity} {disp.trading_symbol} @ {disp.disposal_price}"
                    ),
                )
            )

    # 3. Terminal value: Current market value of remaining open positions
    terminal_val = (
        report.total_current_value if report.total_current_value > 0 else report.total_invested
    )
    if terminal_val > 0:
        cashflows.append(
            CashFlowItem(
                date=target_date,
                amount=terminal_val,
                description=f"Current Portfolio Valuation as of {target_date}",
            )
        )

    # Sort chronologically
    cashflows.sort(key=lambda x: x.date)
    return cashflows


def compute_account_xirr(
    account_id: str,
    *,
    ledger: HoldingsLedger = holdings_ledger,
    current_prices: dict[str, float] | None = None,
    as_of_date: date | None = None,
) -> XIRRCalculationResponse:
    """Compute XIRR for a specific investing account based on its trading cash flows."""
    cashflows = generate_portfolio_cashflows(
        account_id,
        ledger=ledger,
        current_prices=current_prices,
        as_of_date=as_of_date,
    )
    report = ledger.generate_portfolio_report(account_id, current_prices=current_prices)

    raw_flows = [(cf.date, cf.amount) for cf in cashflows]
    xirr_val = calculate_xirr(raw_flows)

    return XIRRCalculationResponse(
        account_id=account_id,
        xirr=xirr_val,
        xirr_pct=round(xirr_val * 100.0, 2),
        total_invested=report.total_invested,
        current_value=report.total_current_value or report.total_invested,
        cashflow_count=len(cashflows),
    )


def generate_portfolio_allocation(
    account_id: str,
    *,
    ledger: HoldingsLedger = holdings_ledger,
    current_prices: dict[str, float] | None = None,
) -> PortfolioAllocationReport:
    """Aggregate portfolio holdings into sector and asset-class allocations."""
    report = ledger.generate_portfolio_report(account_id, current_prices=current_prices)
    total_val = report.total_current_value or report.total_invested or 1.0

    # Sector aggregation
    sector_buckets: dict[str, dict[str, Any]] = {}
    for h in report.holdings:
        sec = get_security_sector(h.trading_symbol)
        if sec not in sector_buckets:
            sector_buckets[sec] = {
                "invested": 0.0,
                "current": 0.0,
                "count": 0,
            }
        val = h.current_value if h.current_value > 0 else h.total_invested_capital
        sector_buckets[sec]["invested"] += h.total_invested_capital
        sector_buckets[sec]["current"] += val
        sector_buckets[sec]["count"] += 1

    sectors: list[SectorAllocationItem] = []
    warnings: list[str] = []

    for s_name, data_s in sector_buckets.items():
        weight = round((data_s["current"] / total_val) * 100.0, 2)
        sectors.append(
            SectorAllocationItem(
                sector=s_name,
                invested_amount=round(data_s["invested"], 2),
                current_value=round(data_s["current"], 2),
                weight_pct=weight,
                holding_count=data_s["count"],
            )
        )
        if weight > 35.0:
            warnings.append(
                f"Concentration warning: Sector '{s_name}' constitutes {weight}% of portfolio."
            )

    sectors.sort(key=lambda x: x.current_value, reverse=True)

    # Asset class aggregation (Equities by default, ETF if marked)
    asset_buckets: dict[str, dict[str, float]] = {
        "Equity": {"invested": 0.0, "current": 0.0},
    }
    for h in report.holdings:
        ac = (
            "ETF"
            if "BEES" in h.trading_symbol.upper() or "ETF" in h.trading_symbol.upper()
            else "Equity"
        )
        if ac not in asset_buckets:
            asset_buckets[ac] = {"invested": 0.0, "current": 0.0}
        val = h.current_value if h.current_value > 0 else h.total_invested_capital
        asset_buckets[ac]["invested"] += h.total_invested_capital
        asset_buckets[ac]["current"] += val

    asset_classes: list[AssetAllocationItem] = []
    for ac_name, ac_data in asset_buckets.items():
        weight = round((ac_data["current"] / total_val) * 100.0, 2)
        asset_classes.append(
            AssetAllocationItem(
                asset_class=ac_name,
                invested_amount=round(ac_data["invested"], 2),
                current_value=round(ac_data["current"], 2),
                weight_pct=weight,
            )
        )

    # Check individual position concentration
    for h in report.holdings:
        h_val = h.current_value if h.current_value > 0 else h.total_invested_capital
        h_weight = round((h_val / total_val) * 100.0, 2)
        if h_weight > 25.0:
            warnings.append(
                f"Concentration warning: Position '{h.trading_symbol}' constitutes "
                f"{h_weight}% of portfolio."
            )

    return PortfolioAllocationReport(
        account_id=account_id,
        total_invested=report.total_invested,
        total_current_value=report.total_current_value or report.total_invested,
        sectors=sectors,
        asset_classes=asset_classes,
        concentration_warnings=warnings,
    )


def compare_portfolio_to_benchmark(
    account_id: str,
    *,
    benchmark_symbol: str = "NIFTY 50",
    benchmark_annual_return_pct: float = 14.5,
    ledger: HoldingsLedger = holdings_ledger,
    current_prices: dict[str, float] | None = None,
    as_of_date: date | None = None,
) -> BenchmarkComparisonResult:
    """Compare portfolio XIRR against a market benchmark annual rate."""
    xirr_res = compute_account_xirr(
        account_id,
        ledger=ledger,
        current_prices=current_prices,
        as_of_date=as_of_date,
    )
    port_xirr = xirr_res.xirr_pct
    alpha = round(port_xirr - benchmark_annual_return_pct, 2)

    return BenchmarkComparisonResult(
        account_id=account_id,
        portfolio_xirr_pct=port_xirr,
        benchmark_symbol=benchmark_symbol,
        benchmark_xirr_pct=benchmark_annual_return_pct,
        alpha_pct=alpha,
        outperforming=alpha >= 0.0,
        as_of_date=as_of_date or date.today(),
    )
