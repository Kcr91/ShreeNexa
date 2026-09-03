"""Typed models for DhanHQ REST API responses and payloads."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class DhanFundLimit(BaseModel):
    """Account fund and margin limits."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    client_id: str = Field(alias="dhanClientId", default="")
    available_balance: float = Field(alias="availabelBalance", default=0.0)
    sod_limit: float = Field(alias="sodLimit", default=0.0)
    collateral_amount: float = Field(alias="collateralAmount", default=0.0)
    receiveable_amount: float = Field(alias="receiveableAmount", default=0.0)
    utilized_amount: float = Field(alias="utilizedAmount", default=0.0)
    blocked_payout_amount: float = Field(alias="blockedPayoutAmount", default=0.0)
    withdrawable_balance: float = Field(alias="withdrawableBalance", default=0.0)


class DhanProfile(BaseModel):
    """User profile metadata."""

    model_config = ConfigDict(extra="ignore")

    client_id: str
    active: bool = True
    fund_limit: DhanFundLimit | None = None


class DhanHistoricalBar(BaseModel):
    """Single OHLCV bar with epoch timestamp."""

    model_config = ConfigDict(extra="ignore")

    timestamp: int
    open: float
    high: float
    low: float
    close: float
    volume: int


class DhanHistoricalData(BaseModel):
    """Collection of OHLCV bars returned by chart historical and intraday APIs."""

    model_config = ConfigDict(extra="ignore")

    open: list[float] = Field(default_factory=list)
    high: list[float] = Field(default_factory=list)
    low: list[float] = Field(default_factory=list)
    close: list[float] = Field(default_factory=list)
    volume: list[int] = Field(default_factory=list)
    start_time: list[int] = Field(alias="start_Time", default_factory=list)

    def to_bars(self) -> list[DhanHistoricalBar]:
        """Convert columnar arrays to row-oriented historical bar objects."""
        n = min(
            len(self.open),
            len(self.high),
            len(self.low),
            len(self.close),
            len(self.volume),
            len(self.start_time),
        )
        return [
            DhanHistoricalBar(
                timestamp=self.start_time[i],
                open=self.open[i],
                high=self.high[i],
                low=self.low[i],
                close=self.close[i],
                volume=self.volume[i],
            )
            for i in range(n)
        ]


class DhanQuote(BaseModel):
    """Snapshot market quote."""

    model_config = ConfigDict(extra="ignore")

    security_id: str
    exchange_segment: str
    last_price: float = 0.0
    volume: int = 0
    open: float = 0.0
    high: float = 0.0
    low: float = 0.0
    close: float = 0.0


class DhanHolding(BaseModel):
    """Account equity holding item."""

    model_config = ConfigDict(extra="ignore")

    security_id: str
    exchange_segment: str
    trading_symbol: str
    total_qty: int
    avg_cost_price: float
    current_price: float = 0.0


class DhanPosition(BaseModel):
    """Open or closed trading position item."""

    model_config = ConfigDict(extra="ignore")

    security_id: str
    exchange_segment: str
    position_type: str
    net_qty: int
    buy_avg: float = 0.0
    sell_avg: float = 0.0
    cost_price: float = 0.0
    realized_profit: float = 0.0
    unrealized_profit: float = 0.0


class DhanResponseEnvelope(BaseModel):
    """Standard Dhan v2 response container envelope."""

    model_config = ConfigDict(extra="ignore")

    status: str = Field(default="success")
    remarks: str | None = Field(default=None)
    error_type: str | None = Field(alias="errorType", default=None)
    error_code: str | None = Field(alias="errorCode", default=None)
    data: Any = Field(default=None)


class DhanTokenRenewalResponse(BaseModel):
    """Response payload for GET /v2/RenewToken."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    client_id: str = Field(alias="dhanClientId", default="")
    client_name: str = Field(alias="dhanClientName", default="")
    client_ucc: str = Field(alias="dhanClientUcc", default="")
    given_power_of_attorney: bool = Field(alias="givenPowerOfAttorney", default=False)
    access_token: str = Field(alias="accessToken", default="")
    expiry_time: str = Field(alias="expiryTime", default="")


class DhanIPConfig(BaseModel):
    """Configured static IP response from GET /v2/ip/getIP."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    primary_ip: str = Field(alias="primaryIP", default="")
    modify_date_primary: str = Field(alias="modifyDatePrimary", default="")
    secondary_ip: str = Field(alias="secondaryIP", default="")
    modify_date_secondary: str = Field(alias="modifyDateSecondary", default="")


class DhanMultiMarginScripItem(BaseModel):
    """Single order leg item for multi-order margin calculator."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    exchange_segment: str = Field(alias="exchangeSegment")
    transaction_type: str = Field(alias="transactionType")
    quantity: int = Field(alias="quantity")
    product_type: str = Field(alias="productType")
    security_id: str = Field(alias="securityId")
    price: float = Field(alias="price", default=0.0)
    trigger_price: float = Field(alias="triggerPrice", default=0.0)


class DhanMultiMarginRequest(BaseModel):
    """Request payload for POST /v2/margincalculator/multi."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    dhan_client_id: str = Field(alias="dhanClientId")
    include_position: bool = Field(alias="includePosition", default=False)
    include_order: bool = Field(alias="includeOrder", default=False)
    scrip_list: list[DhanMultiMarginScripItem] = Field(alias="scripList")


class DhanMultiMarginResponse(BaseModel):
    """Portfolio margin calculation with hedge benefits from POST /v2/margincalculator/multi."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    client_id: str = Field(alias="clientId", default="")
    total_margin: float = Field(alias="totalMargin", default=0.0)
    span_margin: float = Field(alias="spanMargin", default=0.0)
    exposure_margin: float = Field(alias="exposure", default=0.0)
    equity_margin: float = Field(alias="equityMargin", default=0.0)
    fo_margin: float = Field(alias="foMargin", default=0.0)
    commodity_margin: float = Field(alias="commodity", default=0.0)
    currency_margin: float = Field(alias="currency", default=0.0)


class DhanKillSwitchStatus(BaseModel):
    """Account kill switch status from GET or POST /v2/killswitch."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    client_id: str = Field(alias="dhanClientId", default="")
    kill_switch_status: str = Field(alias="killSwitchStatus", default="")
