"""Data models for Paper Trading: Accounts, Orders, Fills, and Positions."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class PaperOrderSide(StrEnum):
    """Side of order trade."""

    BUY = "BUY"
    SELL = "SELL"


class PaperOrderType(StrEnum):
    """Execution type of paper order."""

    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP_LOSS_MARKET = "STOP_LOSS_MARKET"
    STOP_LOSS_LIMIT = "STOP_LOSS_LIMIT"


class PaperOrderStatus(StrEnum):
    """Lifecycle status of paper order."""

    SUBMITTED = "SUBMITTED"
    ACCEPTED = "ACCEPTED"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    FILLED = "FILLED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"


class PaperAccount(BaseModel):
    """Paper trading virtual capital account."""

    model_config = ConfigDict(extra="ignore")

    account_id: str
    name: str = "Default Paper Account"
    initial_capital: float = 1_000_000.0
    cash_balance: float = 1_000_000.0
    blocked_margin: float = 0.0
    realized_pnl: float = 0.0
    unrealized_pnl: float = 0.0
    is_active: bool = True
    created_at: datetime = Field(default_factory=lambda: datetime.now(tz=UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(tz=UTC))

    @property
    def total_equity(self) -> float:
        """Total current account equity."""
        return self.cash_balance + self.blocked_margin + self.unrealized_pnl


class PaperOrder(BaseModel):
    """Persisted paper trading order."""

    model_config = ConfigDict(extra="ignore")

    order_id: str
    account_id: str = "default"
    strategy_id: str | None = None
    symbol: str
    segment: str = "NSE_EQ"
    security_id: str
    side: PaperOrderSide
    order_type: PaperOrderType
    quantity: int = Field(gt=0)
    filled_quantity: int = 0
    price: float | None = None
    trigger_price: float | None = None
    status: PaperOrderStatus = PaperOrderStatus.SUBMITTED
    reject_reason: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(tz=UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(tz=UTC))


class PaperFill(BaseModel):
    """Executed paper trade fill event."""

    model_config = ConfigDict(extra="ignore")

    fill_id: str
    order_id: str
    account_id: str = "default"
    symbol: str
    segment: str = "NSE_EQ"
    security_id: str
    side: PaperOrderSide
    quantity: int = Field(gt=0)
    price: float = Field(gt=0.0)
    slippage: float = 0.0
    transaction_cost: float = 0.0
    timestamp: datetime = Field(default_factory=lambda: datetime.now(tz=UTC))


class PaperPosition(BaseModel):
    """Active open position in paper portfolio."""

    model_config = ConfigDict(extra="ignore")

    position_id: str
    account_id: str = "default"
    symbol: str
    segment: str = "NSE_EQ"
    security_id: str
    quantity: int = 0
    avg_entry_price: float = 0.0
    current_price: float = 0.0
    realized_pnl: float = 0.0
    unrealized_pnl: float = 0.0
    updated_at: datetime = Field(default_factory=lambda: datetime.now(tz=UTC))
