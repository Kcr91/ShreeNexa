"""Dividend event ledger, matching engine, withholding/tax metadata, and income views."""

from __future__ import annotations

import calendar
import uuid
from datetime import date
from enum import StrEnum
from threading import RLock

from pydantic import BaseModel, ConfigDict, Field

from app.investing.ledger import HoldingsLedger, holdings_ledger


class DividendStatus(StrEnum):
    """Lifecycle status of a dividend payment."""

    DECLARED = "DECLARED"  # Declared by corporate, record date announced, payment pending
    MATCHED = "MATCHED"  # Successfully matched to an active ledger holding
    UNMATCHED = "UNMATCHED"  # Could not be matched to any holding on record date
    PAID = "PAID"  # Final cash credit confirmed in demat / bank


class DividendRecord(BaseModel):
    """Auditable record of a dividend event, withholding tax, and payment."""

    model_config = ConfigDict(frozen=True)

    dividend_id: str
    account_id: str
    security_id: str
    isin: str
    trading_symbol: str
    record_date: date
    ex_dividend_date: date
    payment_date: date
    rate_per_share: float = Field(ge=0.0)
    eligible_quantity: int = Field(ge=0)
    gross_amount: float = Field(ge=0.0)
    tds_rate_pct: float = Field(default=0.0, ge=0.0, le=100.0)
    tds_deducted: float = Field(default=0.0, ge=0.0)
    net_received: float = Field(ge=0.0)
    status: DividendStatus = DividendStatus.MATCHED
    notes: str = ""


class DividendPaymentImportItem(BaseModel):
    """External dividend payment entry imported from broker or bank statement."""

    model_config = ConfigDict(extra="ignore")

    isin: str | None = None
    trading_symbol: str | None = None
    payment_date: date
    net_amount: float = Field(gt=0.0)
    tds_deducted: float = Field(default=0.0, ge=0.0)
    gross_amount: float | None = None
    rate_per_share: float | None = None
    description: str = ""


class DividendMatchingResult(BaseModel):
    """Result of matching dividend payment items against holdings ledger."""

    model_config = ConfigDict(frozen=True)

    account_id: str
    matched_records: list[DividendRecord] = Field(default_factory=list)
    unmatched_items: list[DividendPaymentImportItem] = Field(default_factory=list)
    total_matched_gross: float = 0.0
    total_matched_net: float = 0.0
    total_tds_deducted: float = 0.0


class DividendIncomeCalendarMonth(BaseModel):
    """Monthly dividend income aggregation."""

    model_config = ConfigDict(frozen=True)

    year: int
    month: int
    month_name: str
    gross_dividend: float
    net_dividend: float
    tds_deducted: float
    payment_count: int


class DividendIncomeView(BaseModel):
    """Complete dividend income statement and yield metrics."""

    model_config = ConfigDict(frozen=True)

    account_id: str
    total_gross_income: float
    total_net_income: float
    total_tds: float
    annualized_yield_on_cost_pct: float
    annualized_current_yield_pct: float
    monthly_calendar: list[DividendIncomeCalendarMonth] = Field(default_factory=list)
    upcoming_dividends: list[DividendRecord] = Field(default_factory=list)
    recent_dividends: list[DividendRecord] = Field(default_factory=list)


class DividendLedger:
    """Thread-safe ledger managing dividend events, payment matching, and income analytics."""

    def __init__(self) -> None:
        self._lock = RLock()
        # account_id -> list[DividendRecord]
        self._records: dict[str, list[DividendRecord]] = {}

    def record_dividend(self, record: DividendRecord) -> DividendRecord:
        """Store a verified dividend record in the ledger."""
        with self._lock:
            acc_list = self._records.setdefault(record.account_id, [])
            acc_list.append(record)
            acc_list.sort(key=lambda r: r.payment_date)
        return record

    def list_dividends(
        self,
        account_id: str,
        *,
        from_date: date | None = None,
        to_date: date | None = None,
        status: DividendStatus | None = None,
    ) -> list[DividendRecord]:
        """Query recorded dividends with optional date range and status filters."""
        with self._lock:
            records = list(self._records.get(account_id, []))

        filtered: list[DividendRecord] = []
        for r in records:
            if from_date and r.payment_date < from_date:
                continue
            if to_date and r.payment_date > to_date:
                continue
            if status and r.status != status:
                continue
            filtered.append(r)
        return filtered

    def match_dividend_payments(
        self,
        account_id: str,
        imports: list[DividendPaymentImportItem],
        *,
        ledger: HoldingsLedger = holdings_ledger,
    ) -> DividendMatchingResult:
        """Match imported dividend payments against ledger holdings.

        Invariant: Unmatched payments are explicitly isolated into unmatched_items
        and are NEVER erroneously attributed to another holding.
        """
        matched_records: list[DividendRecord] = []
        unmatched_items: list[DividendPaymentImportItem] = []

        with ledger._lock:
            acc_lots = ledger._lots.get(account_id, {})

        for item in imports:
            matched_sec_id: str | None = None
            matched_isin: str | None = None
            matched_symbol: str | None = None

            # 1. Search for matching security in account lots by ISIN or trading symbol
            for sec_id, lots in acc_lots.items():
                if not lots:
                    continue
                first_lot = lots[0]
                if item.isin and first_lot.isin.upper() == item.isin.upper():
                    matched_sec_id = sec_id
                    matched_isin = first_lot.isin
                    matched_symbol = first_lot.trading_symbol
                    break
                if (
                    item.trading_symbol
                    and first_lot.trading_symbol.upper() == item.trading_symbol.upper()
                ):
                    matched_sec_id = sec_id
                    matched_isin = first_lot.isin
                    matched_symbol = first_lot.trading_symbol
                    break

            if not matched_sec_id or not matched_isin or not matched_symbol:
                # Critical proof invariant: Report as unmatched rather than guessing wrong holding
                unmatched_items.append(item)
                continue

            # 2. Check eligible quantity held on or before payment date
            target_lots = acc_lots.get(matched_sec_id, [])
            eligible_qty = sum(
                lot.quantity for lot in target_lots if lot.acquisition_date <= item.payment_date
            )

            if eligible_qty <= 0:
                # Security known, but zero shares acquired on or before payment date
                unmatched_items.append(item)
                continue

            # 3. Calculate gross amount and rate per share
            gross = (
                item.gross_amount
                if item.gross_amount is not None
                else round(item.net_amount + item.tds_deducted, 2)
            )
            rate = (
                item.rate_per_share
                if item.rate_per_share is not None
                else round(gross / eligible_qty, 4)
            )
            tds_rate = (
                round((item.tds_deducted / gross) * 100.0, 2)
                if gross > 0 and item.tds_deducted > 0
                else 0.0
            )

            record = DividendRecord(
                dividend_id=f"div-{uuid.uuid4().hex[:10]}",
                account_id=account_id,
                security_id=matched_sec_id,
                isin=matched_isin,
                trading_symbol=matched_symbol,
                record_date=item.payment_date,
                ex_dividend_date=item.payment_date,
                payment_date=item.payment_date,
                rate_per_share=rate,
                eligible_quantity=eligible_qty,
                gross_amount=gross,
                tds_rate_pct=tds_rate,
                tds_deducted=item.tds_deducted,
                net_received=item.net_amount,
                status=DividendStatus.MATCHED,
                notes=item.description or "Matched against active holding",
            )
            self.record_dividend(record)
            matched_records.append(record)

        tot_gross = round(sum(r.gross_amount for r in matched_records), 2)
        tot_net = round(sum(r.net_received for r in matched_records), 2)
        tot_tds = round(sum(r.tds_deducted for r in matched_records), 2)

        return DividendMatchingResult(
            account_id=account_id,
            matched_records=matched_records,
            unmatched_items=unmatched_items,
            total_matched_gross=tot_gross,
            total_matched_net=tot_net,
            total_tds_deducted=tot_tds,
        )

    def generate_income_view(
        self,
        account_id: str,
        *,
        ledger: HoldingsLedger = holdings_ledger,
        current_prices: dict[str, float] | None = None,
        as_of_date: date | None = None,
    ) -> DividendIncomeView:
        """Compute calendar breakdown, upcoming dividends, and dividend yields."""
        target_date = as_of_date or date.today()
        records = self.list_dividends(account_id)
        portfolio_report = ledger.generate_portfolio_report(
            account_id, current_prices=current_prices
        )

        monthly_map: dict[tuple[int, int], dict[str, float]] = {}
        upcoming: list[DividendRecord] = []
        recent: list[DividendRecord] = []

        tot_gross = 0.0
        tot_net = 0.0
        tot_tds = 0.0

        for r in records:
            if r.payment_date > target_date:
                upcoming.append(r)
                continue

            recent.append(r)
            tot_gross += r.gross_amount
            tot_net += r.net_received
            tot_tds += r.tds_deducted

            m_key = (r.payment_date.year, r.payment_date.month)
            if m_key not in monthly_map:
                monthly_map[m_key] = {"gross": 0.0, "net": 0.0, "tds": 0.0, "count": 0.0}
            monthly_map[m_key]["gross"] += r.gross_amount
            monthly_map[m_key]["net"] += r.net_received
            monthly_map[m_key]["tds"] += r.tds_deducted
            monthly_map[m_key]["count"] += 1.0

        calendar_months: list[DividendIncomeCalendarMonth] = []
        for (yr, mo), data_m in sorted(monthly_map.items()):
            calendar_months.append(
                DividendIncomeCalendarMonth(
                    year=yr,
                    month=mo,
                    month_name=calendar.month_abbr[mo],
                    gross_dividend=round(data_m["gross"], 2),
                    net_dividend=round(data_m["net"], 2),
                    tds_deducted=round(data_m["tds"], 2),
                    payment_count=int(data_m["count"]),
                )
            )

        # Yield on Cost & Current Yield
        invested = portfolio_report.total_invested or 1.0
        current_val = portfolio_report.total_current_value or invested
        yoc_pct = round((tot_gross / invested) * 100.0, 2)
        curr_yield_pct = round((tot_gross / current_val) * 100.0, 2)

        return DividendIncomeView(
            account_id=account_id,
            total_gross_income=round(tot_gross, 2),
            total_net_income=round(tot_net, 2),
            total_tds=round(tot_tds, 2),
            annualized_yield_on_cost_pct=yoc_pct,
            annualized_current_yield_pct=curr_yield_pct,
            monthly_calendar=calendar_months,
            upcoming_dividends=upcoming,
            recent_dividends=sorted(recent, key=lambda x: x.payment_date, reverse=True)[:10],
        )


# Global singleton instance
dividend_ledger = DividendLedger()
