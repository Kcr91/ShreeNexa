"""Production-grade PaperBroker with state machine lifecycle and restart recovery."""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from app.engine.contracts import OrderResult, OrderStatus
from app.paper.fill_policy import PaperFillPolicy
from app.paper.models import (
    PaperAccount,
    PaperFill,
    PaperOrder,
    PaperOrderSide,
    PaperOrderStatus,
    PaperPosition,
)
from app.paper.repository import PaperRepository, paper_repository
from app.warehouse.schema import BarRecord

logger = logging.getLogger(__name__)


class PaperBroker:
    """Simulated execution broker listening to market feed and persisting state."""

    def __init__(
        self,
        repository: PaperRepository | None = None,
        fill_policy: PaperFillPolicy | None = None,
    ) -> None:
        self.repository = repository or paper_repository
        self.fill_policy = fill_policy or PaperFillPolicy()
        self._processed_fill_ids: set[str] = set()

    def submit_orders(self, orders: list[PaperOrder]) -> list[OrderResult]:
        """Submit paper orders into the broker state machine."""
        results: list[OrderResult] = []
        now = datetime.now(tz=UTC)

        for order in orders:
            acc = self.repository.get_or_create_account(order.account_id)

            # Pre-trade cash check for BUY orders
            if order.side == PaperOrderSide.BUY:
                est_cost = (order.price or 100.0) * order.quantity
                if acc.cash_balance < est_cost:
                    order.status = PaperOrderStatus.REJECTED
                    order.reject_reason = (
                        f"Insufficient funds: required ₹{est_cost:.2f}, "
                        f"available ₹{acc.cash_balance:.2f}"
                    )
                    self.repository.save_order(order)
                    results.append(
                        OrderResult(
                            order_id=order.order_id,
                            status=OrderStatus.REJECTED,
                            reason=order.reject_reason,
                            submitted_at=now,
                        )
                    )
                    continue

            order.status = PaperOrderStatus.ACCEPTED
            order.updated_at = now
            self.repository.save_order(order)
            results.append(
                OrderResult(
                    order_id=order.order_id,
                    status=OrderStatus.ACCEPTED,
                    submitted_at=now,
                )
            )

        return results

    def cancel_order(self, order_id: str) -> bool:
        """Cancel an accepted active paper order."""
        order = self.repository.get_order(order_id)
        if order is None:
            return False

        if order.status in (PaperOrderStatus.ACCEPTED, PaperOrderStatus.PARTIALLY_FILLED):
            order.status = PaperOrderStatus.CANCELLED
            order.updated_at = datetime.now(tz=UTC)
            self.repository.save_order(order)
            return True
        return False

    def process_price_update(
        self,
        security_id: str,
        current_price: float,
        high_price: float | None = None,
        low_price: float | None = None,
        timestamp: datetime | None = None,
    ) -> list[PaperFill]:
        """Process incoming tick or bar update across all accounts."""
        fills: list[PaperFill] = []
        now = timestamp or datetime.now(tz=UTC)

        # Retrieve all active pending orders
        all_accounts = list(self.repository._accounts.keys()) or ["default"]
        for acc_id in all_accounts:
            pending_orders = self.repository.list_orders(
                account_id=acc_id, status=PaperOrderStatus.ACCEPTED
            )
            matching_orders = [o for o in pending_orders if o.security_id == security_id]

            for order in matching_orders:
                fill = self.fill_policy.match_order(
                    order=order,
                    current_price=current_price,
                    high_price=high_price,
                    low_price=low_price,
                    timestamp=now,
                )
                if fill is not None:
                    self.apply_fill(fill)
                    fills.append(fill)

            # Update mark-to-market on open positions for this security
            pos = self.repository.get_position(acc_id, security_id)
            if pos and pos.quantity != 0:
                pos.current_price = current_price
                if pos.quantity > 0:
                    pos.unrealized_pnl = (current_price - pos.avg_entry_price) * pos.quantity
                else:
                    pos.unrealized_pnl = (pos.avg_entry_price - current_price) * abs(pos.quantity)
                pos.updated_at = now
                self.repository.save_position(pos)

        return fills

    def on_bar(self, bar: BarRecord) -> list[PaperFill]:
        """Process single historical or live BarRecord."""
        return self.process_price_update(
            security_id=bar.security_id,
            current_price=bar.close,
            high_price=bar.high,
            low_price=bar.low,
            timestamp=bar.timestamp,
        )

    def apply_fill(self, fill: PaperFill) -> bool:
        """Apply fill to portfolio balance and position with strict idempotency guard."""
        # 1. Idempotency Check: reject duplicate fill IDs
        if fill.fill_id in self._processed_fill_ids:
            logger.warning("Rejecting duplicate fill ID %s", fill.fill_id)
            return False

        self._processed_fill_ids.add(fill.fill_id)
        self.repository.save_fill(fill)

        # 2. Update Order status
        order = self.repository.get_order(fill.order_id)
        if order is not None:
            order.filled_quantity += fill.quantity
            if order.filled_quantity >= order.quantity:
                order.status = PaperOrderStatus.FILLED
            else:
                order.status = PaperOrderStatus.PARTIALLY_FILLED
            order.updated_at = fill.timestamp
            self.repository.save_order(order)

        # 3. Update Position & Cash
        acc = self.repository.get_or_create_account(fill.account_id)
        pos = self.repository.get_position(fill.account_id, fill.security_id)

        if pos is None:
            pos = PaperPosition(
                position_id=f"pos-{fill.account_id}-{fill.security_id}",
                account_id=fill.account_id,
                symbol=fill.symbol,
                segment=fill.segment,
                security_id=fill.security_id,
                quantity=0,
                avg_entry_price=0.0,
                current_price=fill.price,
            )

        if fill.side == PaperOrderSide.BUY:
            outlay = (fill.quantity * fill.price) + fill.transaction_cost
            acc.cash_balance -= outlay

            if pos.quantity >= 0:
                total_qty = pos.quantity + fill.quantity
                pos.avg_entry_price = (
                    (pos.quantity * pos.avg_entry_price) + (fill.quantity * fill.price)
                ) / total_qty
                pos.quantity = total_qty
            else:  # Covering short
                cover_qty = min(abs(pos.quantity), fill.quantity)
                pnl = (pos.avg_entry_price - fill.price) * cover_qty - fill.transaction_cost
                pos.realized_pnl += pnl
                acc.realized_pnl += pnl
                pos.quantity += fill.quantity
                if pos.quantity > 0:
                    pos.avg_entry_price = fill.price
        else:  # SELL
            proceeds = (fill.quantity * fill.price) - fill.transaction_cost
            acc.cash_balance += proceeds

            if pos.quantity > 0:  # Closing / trimming long
                sell_qty = min(pos.quantity, fill.quantity)
                pnl = (fill.price - pos.avg_entry_price) * sell_qty - fill.transaction_cost
                pos.realized_pnl += pnl
                acc.realized_pnl += pnl
                pos.quantity -= fill.quantity
                if pos.quantity < 0:
                    pos.avg_entry_price = fill.price
            else:  # Opening / adding short
                total_qty = abs(pos.quantity) + fill.quantity
                pos.avg_entry_price = (
                    (abs(pos.quantity) * pos.avg_entry_price) + (fill.quantity * fill.price)
                ) / total_qty
                pos.quantity -= fill.quantity

        pos.current_price = fill.price
        pos.updated_at = fill.timestamp
        self.repository.save_position(pos)
        self.repository.save_account(acc)

        return True

    def recover(self, account_id: str) -> PaperAccount:
        """Reconcile and recover active portfolio state from persisted store."""
        acc = self.repository.get_or_create_account(account_id)
        # Ensure processed fill IDs are loaded
        fills = self.repository.list_fills(account_id)
        for f in fills:
            self._processed_fill_ids.add(f.fill_id)

        return acc


paper_broker = PaperBroker()
