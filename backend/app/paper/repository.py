"""Persistence repository for paper trading accounts, orders, fills, and positions."""

from __future__ import annotations

from app.engine.contracts import EquityPoint
from app.paper.models import (
    PaperAccount,
    PaperFill,
    PaperOrder,
    PaperOrderStatus,
    PaperPosition,
)


class PaperRepository:
    """Thread-safe state repository for paper trading."""

    def __init__(self) -> None:
        self._accounts: dict[str, PaperAccount] = {}
        self._orders: dict[str, PaperOrder] = {}
        self._fills: dict[str, PaperFill] = {}
        self._positions: dict[tuple[str, str], PaperPosition] = {}  # (account_id, security_id)
        self._equity_curves: dict[str, list[EquityPoint]] = {}

    def save_account(self, account: PaperAccount) -> None:
        self._accounts[account.account_id] = account

    def get_account(self, account_id: str) -> PaperAccount | None:
        return self._accounts.get(account_id)

    def get_or_create_account(
        self,
        account_id: str,
        initial_capital: float = 1_000_000.0,
        name: str = "Default Paper Account",
    ) -> PaperAccount:
        if account_id not in self._accounts:
            acc = PaperAccount(
                account_id=account_id,
                name=name,
                initial_capital=initial_capital,
                cash_balance=initial_capital,
            )
            self._accounts[account_id] = acc
        return self._accounts[account_id]

    def save_order(self, order: PaperOrder) -> None:
        self._orders[order.order_id] = order

    def get_order(self, order_id: str) -> PaperOrder | None:
        return self._orders.get(order_id)

    def list_orders(
        self, account_id: str, status: PaperOrderStatus | None = None
    ) -> list[PaperOrder]:
        orders = [o for o in self._orders.values() if o.account_id == account_id]
        if status is not None:
            orders = [o for o in orders if o.status == status]
        return sorted(orders, key=lambda x: x.created_at, reverse=True)

    def save_fill(self, fill: PaperFill) -> None:
        self._fills[fill.fill_id] = fill

    def list_fills(self, account_id: str) -> list[PaperFill]:
        fills = [f for f in self._fills.values() if f.account_id == account_id]
        return sorted(fills, key=lambda x: x.timestamp, reverse=True)

    def save_position(self, position: PaperPosition) -> None:
        self._positions[(position.account_id, position.security_id)] = position

    def get_position(self, account_id: str, security_id: str) -> PaperPosition | None:
        return self._positions.get((account_id, security_id))

    def list_positions(self, account_id: str, open_only: bool = False) -> list[PaperPosition]:
        if open_only:
            return [
                p
                for p in self._positions.values()
                if p.account_id == account_id and p.quantity != 0
            ]
        return [p for p in self._positions.values() if p.account_id == account_id]

    def record_equity_point(self, account_id: str, point: EquityPoint) -> None:
        if account_id not in self._equity_curves:
            self._equity_curves[account_id] = []
        self._equity_curves[account_id].append(point)

    def get_equity_curve(self, account_id: str) -> list[EquityPoint]:
        return list(self._equity_curves.get(account_id, []))

    def clear(self) -> None:
        """Reset all in-memory paper states (used in tests or account resets)."""
        self._accounts.clear()
        self._orders.clear()
        self._fills.clear()
        self._positions.clear()
        self._equity_curves.clear()


paper_repository = PaperRepository()
