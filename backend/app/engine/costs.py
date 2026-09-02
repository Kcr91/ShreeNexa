"""Effective-dated Indian market transaction cost model and regulatory fee calculation."""

from __future__ import annotations

from datetime import date, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, Field

from app.engine.contracts import OrderSide


class ProductType(StrEnum):
    """Trading product type for taxation and brokerage purposes."""

    DELIVERY = "DELIVERY"
    INTRADAY = "INTRADAY"
    FUTURES = "FUTURES"
    OPTIONS = "OPTIONS"


class TradeCostBreakdown(BaseModel):
    """Detailed itemized breakdown of Indian market transaction fees and taxes."""

    model_config = ConfigDict(extra="forbid")

    brokerage: float = Field(ge=0.0)
    stt_ctt: float = Field(ge=0.0)
    exchange_txn_charge: float = Field(ge=0.0)
    sebi_fee: float = Field(ge=0.0)
    stamp_duty: float = Field(ge=0.0)
    gst: float = Field(ge=0.0)
    total_cost: float = Field(ge=0.0)
    schedule_id: str


class IndianCostCalculator:
    """Calculates all Indian statutory taxes and broker fees with effective-date range support."""

    def __init__(self, config_path: str | Path | None = None) -> None:
        self.config_path = Path(config_path) if config_path else Path("config/costs.yaml")
        self._schedules: list[dict[str, Any]] = []
        self._load_config()

    def _load_config(self) -> None:
        if not self.config_path.exists():
            # Fallback default configuration if file missing
            self._schedules = [
                {
                    "id": "default_post_oct_2024",
                    "effective_from": "2024-10-01",
                    "effective_to": "2099-12-31",
                    "segments": {
                        "equity_delivery": {
                            "brokerage_flat": 0.0,
                            "brokerage_pct": 0.0,
                            "stt_buy_pct": 0.001,
                            "stt_sell_pct": 0.001,
                            "exchange_txn_pct": 0.0000297,
                            "sebi_fee_pct": 0.000001,
                            "stamp_duty_buy_pct": 0.00015,
                            "gst_pct": 0.18,
                        },
                        "equity_intraday": {
                            "brokerage_flat": 20.0,
                            "brokerage_pct": 0.0003,
                            "stt_buy_pct": 0.0,
                            "stt_sell_pct": 0.00025,
                            "exchange_txn_pct": 0.0000297,
                            "sebi_fee_pct": 0.000001,
                            "stamp_duty_buy_pct": 0.00003,
                            "gst_pct": 0.18,
                        },
                        "futures": {
                            "brokerage_flat": 20.0,
                            "brokerage_pct": 0.0003,
                            "stt_buy_pct": 0.0,
                            "stt_sell_pct": 0.00020,
                            "exchange_txn_pct": 0.0000173,
                            "sebi_fee_pct": 0.000001,
                            "stamp_duty_buy_pct": 0.00002,
                            "gst_pct": 0.18,
                        },
                        "options": {
                            "brokerage_flat": 20.0,
                            "brokerage_pct": 0.0,
                            "stt_buy_pct": 0.0,
                            "stt_sell_pct": 0.0010,
                            "exchange_txn_pct": 0.0003503,
                            "sebi_fee_pct": 0.000001,
                            "stamp_duty_buy_pct": 0.00003,
                            "gst_pct": 0.18,
                        },
                    },
                }
            ]
            return

        with open(self.config_path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
            self._schedules = data.get("schedules", [])

    def _resolve_schedule(self, trade_date: date) -> dict[str, Any]:
        """Find the cost schedule in effect on the specified trade date."""
        for schedule in self._schedules:
            eff_from = date.fromisoformat(schedule["effective_from"])
            eff_to = (
                date.fromisoformat(schedule["effective_to"])
                if schedule.get("effective_to")
                else date(2099, 12, 31)
            )
            if eff_from <= trade_date <= eff_to:
                return schedule

        # If no exact match, return last schedule
        if self._schedules:
            return self._schedules[-1]
        raise ValueError(f"No cost schedule configured for date {trade_date}")

    def calculate_cost(
        self,
        product_type: ProductType,
        side: OrderSide,
        quantity: int,
        price: float,
        timestamp: datetime,
    ) -> TradeCostBreakdown:
        """Calculate complete line-item transaction costs for an execution."""
        trade_date = timestamp.date() if isinstance(timestamp, datetime) else timestamp
        schedule = self._resolve_schedule(trade_date)
        seg_rules = schedule["segments"]

        # Map ProductType to schedule segment
        if product_type == ProductType.DELIVERY:
            rules = seg_rules["equity_delivery"]
        elif product_type == ProductType.INTRADAY:
            rules = seg_rules["equity_intraday"]
        elif product_type == ProductType.FUTURES:
            rules = seg_rules["futures"]
        else:  # OPTIONS
            rules = seg_rules["options"]

        turnover = quantity * price

        # 1. Brokerage: flat or percentage cap
        brokerage_flat = rules.get("brokerage_flat", 0.0)
        brokerage_pct = rules.get("brokerage_pct", 0.0)
        if brokerage_flat > 0.0 and brokerage_pct > 0.0:
            brokerage = min(brokerage_flat, turnover * brokerage_pct)
        elif brokerage_flat > 0.0:
            brokerage = brokerage_flat
        else:
            brokerage = turnover * brokerage_pct

        # 2. STT / CTT
        if side == OrderSide.BUY:
            stt = turnover * rules.get("stt_buy_pct", 0.0)
        else:
            stt = turnover * rules.get("stt_sell_pct", 0.0)

        # 3. Exchange Txn Charge
        exchange_txn = turnover * rules.get("exchange_txn_pct", 0.0)

        # 4. SEBI Turnover Fee
        sebi_fee = turnover * rules.get("sebi_fee_pct", 0.0)

        # 5. Stamp Duty (Buy side only)
        if side == OrderSide.BUY:
            stamp_duty = turnover * rules.get("stamp_duty_buy_pct", 0.0)
        else:
            stamp_duty = 0.0

        # 6. GST (18% on Brokerage + Exchange Txn + SEBI)
        gst = (brokerage + exchange_txn + sebi_fee) * rules.get("gst_pct", 0.18)

        total_cost = brokerage + stt + exchange_txn + sebi_fee + stamp_duty + gst

        return TradeCostBreakdown(
            brokerage=brokerage,
            stt_ctt=stt,
            exchange_txn_charge=exchange_txn,
            sebi_fee=sebi_fee,
            stamp_duty=stamp_duty,
            gst=gst,
            total_cost=total_cost,
            schedule_id=schedule["id"],
        )


# Global singleton instance
cost_calculator = IndianCostCalculator()
