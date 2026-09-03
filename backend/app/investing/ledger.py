"""Holdings ledger managing discrete tax lots, FIFO depletion, and corporate actions."""

from __future__ import annotations

import uuid
from datetime import date
from threading import RLock

from app.investing.models import (
    CapitalGainsCategory,
    CorporateAction,
    CorporateActionType,
    DisposalAllocation,
    DisposalRecord,
    HoldingSummary,
    PortfolioHoldingsReport,
    TaxLot,
)


class HoldingsLedger:
    """Thread-safe portfolio holdings ledger supporting FIFO lot depletion and tax accounting."""

    def __init__(self) -> None:
        self._lock = RLock()
        # account_id -> security_id -> list[TaxLot]
        self._lots: dict[str, dict[str, list[TaxLot]]] = {}
        # account_id -> list[DisposalRecord]
        self._disposals: dict[str, list[DisposalRecord]] = {}
        # account_id -> list[CorporateAction]
        self._corporate_actions: dict[str, list[CorporateAction]] = {}

    def add_lot(
        self,
        account_id: str,
        security_id: str,
        isin: str,
        trading_symbol: str,
        acquisition_date: date,
        acquisition_price: float,
        quantity: int,
        lot_id: str | None = None,
    ) -> TaxLot:
        """Add a new purchase tax lot to the ledger."""
        if quantity <= 0:
            raise ValueError(f"Quantity must be positive, got {quantity}")
        if acquisition_price < 0:
            raise ValueError(f"Acquisition price cannot be negative, got {acquisition_price}")

        lot = TaxLot(
            lot_id=lot_id or f"lot-{uuid.uuid4().hex[:10]}",
            security_id=security_id,
            isin=isin,
            trading_symbol=trading_symbol,
            acquisition_date=acquisition_date,
            acquisition_price=round(acquisition_price, 4),
            quantity=quantity,
            remaining_quantity=quantity,
        )

        with self._lock:
            acc_lots = self._lots.setdefault(account_id, {})
            sec_lots = acc_lots.setdefault(security_id, [])
            sec_lots.append(lot)
            # Maintain chronological ordering by acquisition_date
            sec_lots.sort(key=lambda item: item.acquisition_date)

        return lot

    def record_disposal(
        self,
        account_id: str,
        security_id: str,
        disposal_date: date,
        disposal_price: float,
        quantity: int,
        transaction_costs: float = 0.0,
        disposal_id: str | None = None,
    ) -> DisposalRecord:
        """Deplete active lots in strict First-In-First-Out (FIFO) order and compute STCG/LTCG."""
        if quantity <= 0:
            raise ValueError(f"Disposal quantity must be positive, got {quantity}")
        if disposal_price <= 0:
            raise ValueError(f"Disposal price must be positive, got {disposal_price}")

        with self._lock:
            acc_lots = self._lots.get(account_id, {})
            sec_lots = acc_lots.get(security_id, [])
            total_available = sum(item.remaining_quantity for item in sec_lots)
            if quantity > total_available:
                raise ValueError(
                    f"Insufficient quantity for {security_id}: requested {quantity}, "
                    f"available {total_available}"
                )

            remaining_to_sell = quantity
            allocations: list[DisposalAllocation] = []
            updated_lots: list[TaxLot] = []

            for lot in sec_lots:
                if remaining_to_sell == 0 or lot.remaining_quantity == 0:
                    updated_lots.append(lot)
                    continue

                deplete = min(lot.remaining_quantity, remaining_to_sell)
                holding_period = (disposal_date - lot.acquisition_date).days
                gains_cat = (
                    CapitalGainsCategory.LTCG
                    if holding_period >= 365
                    else CapitalGainsCategory.STCG
                )
                gross_pnl = round((disposal_price - lot.acquisition_price) * deplete, 2)

                alloc = DisposalAllocation(
                    lot_id=lot.lot_id,
                    depleted_quantity=deplete,
                    acquisition_price=lot.acquisition_price,
                    acquisition_date=lot.acquisition_date,
                    disposal_price=disposal_price,
                    disposal_date=disposal_date,
                    holding_period_days=holding_period,
                    gains_category=gains_cat,
                    gross_pnl=gross_pnl,
                )
                allocations.append(alloc)
                remaining_to_sell -= deplete

                updated_lots.append(
                    TaxLot(
                        lot_id=lot.lot_id,
                        security_id=lot.security_id,
                        isin=lot.isin,
                        trading_symbol=lot.trading_symbol,
                        acquisition_date=lot.acquisition_date,
                        acquisition_price=lot.acquisition_price,
                        quantity=lot.quantity,
                        remaining_quantity=lot.remaining_quantity - deplete,
                    )
                )

            acc_lots[security_id] = updated_lots

            # Aggregate gross PnL, STCG, and LTCG
            total_gross = round(sum(a.gross_pnl for a in allocations), 2)
            net_pnl = round(total_gross - transaction_costs, 2)
            stcg = round(
                sum(
                    a.gross_pnl
                    for a in allocations
                    if a.gains_category == CapitalGainsCategory.STCG
                ),
                2,
            )
            ltcg = round(
                sum(
                    a.gross_pnl
                    for a in allocations
                    if a.gains_category == CapitalGainsCategory.LTCG
                ),
                2,
            )

            # Extract metadata from first depleted lot
            isin = sec_lots[0].isin if sec_lots else ""
            symbol = sec_lots[0].trading_symbol if sec_lots else security_id

            record = DisposalRecord(
                disposal_id=disposal_id or f"disp-{uuid.uuid4().hex[:10]}",
                security_id=security_id,
                isin=isin,
                trading_symbol=symbol,
                disposal_date=disposal_date,
                disposal_price=round(disposal_price, 4),
                quantity=quantity,
                transaction_costs=round(transaction_costs, 2),
                gross_realized_pnl=total_gross,
                net_realized_pnl=net_pnl,
                stcg_pnl=stcg,
                ltcg_pnl=ltcg,
                allocations=allocations,
            )

            self._disposals.setdefault(account_id, []).append(record)
            return record

    def apply_corporate_action(
        self,
        account_id: str,
        action: CorporateAction,
    ) -> list[TaxLot]:
        """Apply corporate action (split, bonus, consolidation) preserving invested capital."""
        with self._lock:
            acc_lots = self._lots.get(account_id, {})
            sec_lots = acc_lots.get(action.security_id, [])
            if not sec_lots:
                return []

            if action.action_type == CorporateActionType.STOCK_SPLIT:
                # E.g. 2 for 1 split (numerator=2, denominator=1)
                factor = action.ratio_numerator / action.ratio_denominator
                updated: list[TaxLot] = []
                for lot in sec_lots:
                    new_qty = int(lot.quantity * factor)
                    new_rem = int(lot.remaining_quantity * factor)
                    new_price = round(lot.acquisition_price / factor, 4)
                    updated.append(
                        TaxLot(
                            lot_id=lot.lot_id,
                            security_id=lot.security_id,
                            isin=lot.isin,
                            trading_symbol=lot.trading_symbol,
                            acquisition_date=lot.acquisition_date,
                            acquisition_price=new_price,
                            quantity=new_qty,
                            remaining_quantity=new_rem,
                        )
                    )
                acc_lots[action.security_id] = updated

            elif action.action_type == CorporateActionType.BONUS_ISSUE:
                # E.g. 1:1 bonus adds 1 new share for each holding share at 0 cost per share
                bonus_ratio = action.ratio_numerator / action.ratio_denominator
                total_remaining = sum(lot.remaining_quantity for lot in sec_lots)
                bonus_shares = int(total_remaining * bonus_ratio)

                if bonus_shares > 0:
                    first = sec_lots[0]
                    bonus_lot = TaxLot(
                        lot_id=f"lot-bonus-{uuid.uuid4().hex[:8]}",
                        security_id=first.security_id,
                        isin=first.isin,
                        trading_symbol=first.trading_symbol,
                        acquisition_date=action.effective_date,
                        acquisition_price=0.0,
                        quantity=bonus_shares,
                        remaining_quantity=bonus_shares,
                    )
                    sec_lots.append(bonus_lot)
                    sec_lots.sort(key=lambda item: item.acquisition_date)

            elif action.action_type == CorporateActionType.CONSOLIDATION:
                # E.g. 1 for 2 reverse split (numerator=1, denominator=2)
                factor = action.ratio_numerator / action.ratio_denominator
                updated = []
                for lot in sec_lots:
                    new_qty = max(1, int(lot.quantity * factor))
                    new_rem = max(0, int(lot.remaining_quantity * factor))
                    new_price = round(lot.acquisition_price / factor, 4)
                    updated.append(
                        TaxLot(
                            lot_id=lot.lot_id,
                            security_id=lot.security_id,
                            isin=lot.isin,
                            trading_symbol=lot.trading_symbol,
                            acquisition_date=lot.acquisition_date,
                            acquisition_price=new_price,
                            quantity=new_qty,
                            remaining_quantity=new_rem,
                        )
                    )
                acc_lots[action.security_id] = updated

            self._corporate_actions.setdefault(account_id, []).append(action)
            return list(acc_lots.get(action.security_id, []))

    def get_holding_summary(
        self,
        account_id: str,
        security_id: str,
        current_market_price: float = 0.0,
    ) -> HoldingSummary | None:
        """Compute holding summary including weighted-average cost and unrealised P&L."""
        with self._lock:
            acc_lots = self._lots.get(account_id, {})
            sec_lots = acc_lots.get(security_id, [])
            active_lots = [lot for lot in sec_lots if lot.remaining_quantity > 0]
            if not active_lots:
                return None

            first = active_lots[0]
            total_qty = sum(lot.remaining_quantity for lot in active_lots)
            total_invested = round(
                sum(lot.remaining_quantity * lot.acquisition_price for lot in active_lots), 2
            )
            avg_cost = round(total_invested / total_qty, 4) if total_qty > 0 else 0.0

            current_val = round(total_qty * current_market_price, 2)
            unrealized = (
                round(current_val - total_invested, 2) if current_market_price > 0 else 0.0
            )
            unrealized_pct = (
                round((unrealized / total_invested) * 100.0, 2) if total_invested > 0 else 0.0
            )

            return HoldingSummary(
                security_id=first.security_id,
                isin=first.isin,
                trading_symbol=first.trading_symbol,
                total_quantity=total_qty,
                available_quantity=total_qty,
                dp_quantity=total_qty,
                t1_quantity=0,
                weighted_average_cost=avg_cost,
                total_invested_capital=total_invested,
                current_market_price=round(current_market_price, 2),
                current_value=current_val,
                unrealized_pnl=unrealized,
                unrealized_pnl_pct=unrealized_pct,
                active_lots=active_lots,
            )

    def generate_portfolio_report(
        self,
        account_id: str,
        current_prices: dict[str, float] | None = None,
        as_of_date: date | None = None,
    ) -> PortfolioHoldingsReport:
        """Generate comprehensive portfolio report across all active holdings."""
        prices = current_prices or {}
        with self._lock:
            acc_lots = self._lots.get(account_id, {})
            holdings: list[HoldingSummary] = []
            for sec_id in acc_lots:
                cmp = prices.get(sec_id, 0.0)
                summary = self.get_holding_summary(account_id, sec_id, current_market_price=cmp)
                if summary:
                    holdings.append(summary)

            total_invested = round(sum(h.total_invested_capital for h in holdings), 2)
            total_current_val = round(sum(h.current_value for h in holdings), 2)
            total_unrealized = round(sum(h.unrealized_pnl for h in holdings), 2)

            disposals = self._disposals.get(account_id, [])
            total_realized = round(sum(d.net_realized_pnl for d in disposals), 2)
            total_stcg = round(sum(d.stcg_pnl for d in disposals), 2)
            total_ltcg = round(sum(d.ltcg_pnl for d in disposals), 2)

            return PortfolioHoldingsReport(
                account_id=account_id,
                as_of_date=as_of_date or date.today(),
                holdings=holdings,
                total_invested=total_invested,
                total_current_value=total_current_val,
                total_unrealized_pnl=total_unrealized,
                total_realized_pnl=total_realized,
                total_stcg=total_stcg,
                total_ltcg=total_ltcg,
            )

    def clear(self) -> None:
        """Reset ledger for testing."""
        with self._lock:
            self._lots.clear()
            self._disposals.clear()
            self._corporate_actions.clear()


holdings_ledger = HoldingsLedger()
