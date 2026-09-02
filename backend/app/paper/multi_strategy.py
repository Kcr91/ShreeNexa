"""Multi-strategy paper execution coordinator with isolated capital and shared account caps."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from app.paper.broker import PaperBroker
from app.paper.models import (
    PaperFill,
    PaperOrder,
    PaperOrderStatus,
)
from app.paper.repository import PaperRepository, paper_repository
from app.warehouse.schema import BarRecord


class SharedAccountCaps(BaseModel):
    """Global portfolio risk caps enforced across all concurrent paper strategies."""

    model_config = ConfigDict(extra="ignore")

    max_single_stock_exposure_pct: float = Field(
        default=0.30,
        description="Max gross exposure in a single stock across all strategies (default 30%).",
    )
    max_account_leverage: float = Field(
        default=2.0,
        description="Max gross leverage (positions / equity) allowed across all strategies.",
    )
    max_account_drawdown_pct: float = Field(
        default=0.15,
        description="Max account-level drawdown allowed before halting new orders (default 15%).",
    )
    kill_switch_active: bool = Field(
        default=False,
        description="Global emergency kill switch halting orders across all strategies.",
    )


class StrategyAllocationConfig(BaseModel):
    """Capital allocation for an individual paper strategy."""

    model_config = ConfigDict(extra="ignore")

    strategy_id: str
    strategy_name: str
    allocated_capital: float


class StrategyBookSummary(BaseModel):
    """Summary of an isolated strategy paper trading book."""

    model_config = ConfigDict(extra="ignore")

    strategy_id: str
    strategy_name: str
    allocated_capital: float
    cash_balance: float
    realized_pnl: float
    unrealized_pnl: float
    total_equity: float
    positions_count: int
    working_orders_count: int


class MultiStrategyStatus(BaseModel):
    """Aggregated status of the multi-strategy paper trading portfolio."""

    model_config = ConfigDict(extra="ignore")

    account_id: str
    initial_total_capital: float
    total_account_equity: float
    total_cash_balance: float
    total_realized_pnl: float
    total_unrealized_pnl: float
    shared_caps: SharedAccountCaps
    strategies: dict[str, StrategyBookSummary]


class MultiStrategyPaperCoordinator:
    """Coordinates multiple concurrent paper strategies with isolated capital and shared caps."""

    def __init__(
        self,
        account_id: str,
        total_capital: float,
        allocations: list[StrategyAllocationConfig],
        shared_caps: SharedAccountCaps | None = None,
        repository: PaperRepository | None = None,
    ) -> None:
        self.account_id = account_id
        self.total_capital = total_capital
        self.shared_caps = shared_caps or SharedAccountCaps()
        self.repo = repository or paper_repository
        self.peak_equity = total_capital

        # Validate allocations sum does not exceed total capital
        allocated_sum = sum(a.allocated_capital for a in allocations)
        if allocated_sum > total_capital + 0.01:
            raise ValueError(
                f"Sum of allocated capital ({allocated_sum}) exceeds total ({total_capital})"
            )

        self.strategy_configs: dict[str, StrategyAllocationConfig] = {}
        self.strategy_brokers: dict[str, PaperBroker] = {}

        # Set up isolated sub-accounts and brokers
        for alloc in allocations:
            self.strategy_configs[alloc.strategy_id] = alloc
            sub_account_id = f"{account_id}:{alloc.strategy_id}"
            self.repo.get_or_create_account(
                account_id=sub_account_id,
                name=f"{alloc.strategy_name} (Paper)",
                initial_capital=alloc.allocated_capital,
            )
            self.strategy_brokers[alloc.strategy_id] = PaperBroker(repository=self.repo)

    def trigger_kill_switch(self, reason: str = "Manual emergency halt") -> None:
        """Activate the global kill switch and cancel all working orders across all strategies."""
        self.shared_caps.kill_switch_active = True
        for s_id in self.strategy_brokers:
            sub_acc = f"{self.account_id}:{s_id}"
            working_orders = [
                o
                for o in self.repo.list_orders(sub_acc)
                if o.status in (PaperOrderStatus.ACCEPTED, PaperOrderStatus.PARTIALLY_FILLED)
            ]
            for o in working_orders:
                self.strategy_brokers[s_id].cancel_order(o.order_id)

    def reset_kill_switch(self) -> None:
        """Deactivate the global kill switch."""
        self.shared_caps.kill_switch_active = False

    def get_total_account_equity(self) -> float:
        """Calculate aggregate equity across all isolated strategy books."""
        total = 0.0
        for s_id in self.strategy_brokers:
            sub_acc = f"{self.account_id}:{s_id}"
            acc = self.repo.get_or_create_account(sub_acc)
            positions = self.repo.list_positions(sub_acc)
            pos_val = sum(
                p.quantity * (p.current_price if p.current_price > 0 else p.avg_entry_price)
                for p in positions
            )
            total += acc.cash_balance + acc.blocked_margin + pos_val
        return round(total, 2)

    def get_symbol_gross_exposure(self, security_id: str) -> float:
        """Calculate total gross market exposure to a security across all strategies."""
        exposure = 0.0
        for s_id in self.strategy_brokers:
            sub_acc = f"{self.account_id}:{s_id}"
            pos = self.repo.get_position(sub_acc, security_id)
            if pos and pos.quantity != 0:
                price = pos.current_price if pos.current_price > 0 else pos.avg_entry_price
                exposure += abs(pos.quantity * price)
        return round(exposure, 2)

    def get_total_gross_exposure(self) -> float:
        """Calculate total gross market exposure across all securities and strategies."""
        total_exp = 0.0
        for s_id in self.strategy_brokers:
            sub_acc = f"{self.account_id}:{s_id}"
            positions = self.repo.list_positions(sub_acc)
            for p in positions:
                if p.quantity != 0:
                    price = p.current_price if p.current_price > 0 else p.avg_entry_price
                    total_exp += abs(p.quantity * price)
        return round(total_exp, 2)

    def submit_strategy_order(self, strategy_id: str, order: PaperOrder) -> PaperOrder:
        """Validate against shared account caps and route to the isolated strategy broker."""
        sub_account_id = f"{self.account_id}:{strategy_id}"
        order.account_id = sub_account_id

        # 1. Global Kill Switch check
        if self.shared_caps.kill_switch_active:
            order.status = PaperOrderStatus.REJECTED
            order.reject_reason = "Global kill switch is active across all strategies"
            self.repo.save_order(order)
            return order

        # 2. Strategy existence check
        broker = self.strategy_brokers.get(strategy_id)
        if not broker:
            order.status = PaperOrderStatus.REJECTED
            order.reject_reason = f"Strategy '{strategy_id}' not found in paper coordinator"
            self.repo.save_order(order)
            return order

        # Calculate current global portfolio stats
        total_equity = self.get_total_account_equity()
        if total_equity > self.peak_equity:
            self.peak_equity = total_equity

        # 3. Shared Account Drawdown Cap check
        drawdown_pct = (
            (self.peak_equity - total_equity) / self.peak_equity if self.peak_equity > 0 else 0.0
        )
        if drawdown_pct > self.shared_caps.max_account_drawdown_pct:
            order.status = PaperOrderStatus.REJECTED
            max_dd = self.shared_caps.max_account_drawdown_pct * 100
            curr_dd = drawdown_pct * 100
            order.reject_reason = (
                f"Shared account cap breached: max account drawdown {max_dd:.1f}% "
                f"exceeded (current {curr_dd:.1f}%)"
            )
            self.repo.save_order(order)
            return order

        # Estimate order value
        order_price = order.price if order.price and order.price > 0 else 1.0
        order_val = order.quantity * order_price

        # 4. Shared Single-Stock Exposure Cap check
        current_sec_exposure = self.get_symbol_gross_exposure(order.security_id)
        if total_equity > 0:
            projected_pct = (current_sec_exposure + order_val) / total_equity
            if projected_pct > self.shared_caps.max_single_stock_exposure_pct:
                order.status = PaperOrderStatus.REJECTED
                max_stock_pct = self.shared_caps.max_single_stock_exposure_pct * 100
                curr_stock_pct = projected_pct * 100
                order.reject_reason = (
                    f"Shared account cap breached: single stock exposure for {order.symbol} "
                    f"({curr_stock_pct:.1f}%) exceeds {max_stock_pct:.1f}% limit"
                )
                self.repo.save_order(order)
                return order

        # 5. Shared Account Leverage Cap check
        current_gross_exp = self.get_total_gross_exposure()
        if total_equity > 0:
            projected_leverage = (current_gross_exp + order_val) / total_equity
            if projected_leverage > self.shared_caps.max_account_leverage:
                order.status = PaperOrderStatus.REJECTED
                max_lev = self.shared_caps.max_account_leverage
                order.reject_reason = (
                    f"Shared account cap breached: aggregate leverage ({projected_leverage:.2f}x) "
                    f"exceeds {max_lev:.2f}x limit"
                )
                self.repo.save_order(order)
                return order

        # 6. Route to isolated strategy broker (enforcing isolated strategy capital)
        broker.submit_orders([order])
        return order

    def process_price_update(
        self,
        security_id: str,
        current_price: float,
        low_price: float | None = None,
        high_price: float | None = None,
    ) -> list[PaperFill]:
        """Fan out market price updates to all concurrent strategy brokers."""
        fills: list[PaperFill] = []
        for broker in self.strategy_brokers.values():
            fills.extend(
                broker.process_price_update(
                    security_id=security_id,
                    current_price=current_price,
                    low_price=low_price,
                    high_price=high_price,
                )
            )
        return fills

    def on_bar(self, bar: BarRecord) -> list[PaperFill]:
        """Fan out BarRecord events to all concurrent strategy brokers."""
        fills: list[PaperFill] = []
        for broker in self.strategy_brokers.values():
            fills.extend(broker.on_bar(bar))
        return fills

    def get_status(self) -> MultiStrategyStatus:
        """Generate comprehensive status report of all strategy books and shared caps."""
        tot_equity = 0.0
        tot_cash = 0.0
        tot_realized = 0.0
        tot_unrealized = 0.0
        strategies_summary: dict[str, StrategyBookSummary] = {}

        for s_id, cfg in self.strategy_configs.items():
            sub_acc = f"{self.account_id}:{s_id}"
            acc = self.repo.get_or_create_account(sub_acc)
            positions = self.repo.list_positions(sub_acc)
            orders = self.repo.list_orders(sub_acc)
            unrealized = sum(p.unrealized_pnl for p in positions)
            pos_val = sum(
                p.quantity * (p.current_price if p.current_price > 0 else p.avg_entry_price)
                for p in positions
            )
            equity = acc.cash_balance + acc.blocked_margin + pos_val

            tot_equity += equity
            tot_cash += acc.cash_balance
            tot_realized += acc.realized_pnl
            tot_unrealized += unrealized

            working_count = len(
                [
                    o
                    for o in orders
                    if o.status in (PaperOrderStatus.ACCEPTED, PaperOrderStatus.PARTIALLY_FILLED)
                ]
            )

            strategies_summary[s_id] = StrategyBookSummary(
                strategy_id=s_id,
                strategy_name=cfg.strategy_name,
                allocated_capital=round(cfg.allocated_capital, 2),
                cash_balance=round(acc.cash_balance, 2),
                realized_pnl=round(acc.realized_pnl, 2),
                unrealized_pnl=round(unrealized, 2),
                total_equity=round(equity, 2),
                positions_count=len([p for p in positions if p.quantity != 0]),
                working_orders_count=working_count,
            )

        return MultiStrategyStatus(
            account_id=self.account_id,
            initial_total_capital=round(self.total_capital, 2),
            total_account_equity=round(tot_equity, 2),
            total_cash_balance=round(tot_cash, 2),
            total_realized_pnl=round(tot_realized, 2),
            total_unrealized_pnl=round(tot_unrealized, 2),
            shared_caps=self.shared_caps,
            strategies=strategies_summary,
        )
