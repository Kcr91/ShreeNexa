"""Telegram & Emergency Alert Notification Dispatcher."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

logger = logging.getLogger(__name__)


class TelegramAlertDispatcher:
    """Dispatches trade alerts, target hits, stop-loss hits, and emergency kill-switch events."""

    def __init__(
        self,
        bot_token: str | None = None,
        chat_id: str | None = None,
        enabled: bool = False,
    ) -> None:
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.enabled = enabled and bool(bot_token and chat_id)
        self.dispatched_messages: list[dict[str, Any]] = []

    def send_order_fill_alert(
        self,
        symbol: str,
        transaction_type: str,
        quantity: int,
        executed_price: float,
        dhan_order_id: str,
        strategy_name: str = "Momentum F&O",
    ) -> dict[str, Any]:
        """Send Trade Entry / Fill alert."""
        text = (
            f"🔔 *TRADE EXECUTED (Dhan API)*\n"
            f"• Strategy: `{strategy_name}`\n"
            f"• Symbol: *{symbol}*\n"
            f"• Side: *{transaction_type.upper()}* | Qty: `{quantity}`\n"
            f"• Price: `₹{executed_price:,.2f}`\n"
            f"• Dhan Order ID: `{dhan_order_id}`\n"
            f"• Time: `{datetime.now(UTC).strftime('%H:%M:%S UTC')}`"
        )
        return self._dispatch(event_type="ORDER_FILLED", text=text)

    def send_stoploss_hit_alert(
        self,
        symbol: str,
        exit_price: float,
        realized_pnl: float,
        strategy_name: str = "Momentum F&O",
    ) -> dict[str, Any]:
        """Send Stop-Loss Hit alert."""
        text = (
            f"🛑 *STOP-LOSS TRIGGERED*\n"
            f"• Strategy: `{strategy_name}`\n"
            f"• Symbol: *{symbol}*\n"
            f"• Exit Price: `₹{exit_price:,.2f}`\n"
            f"• Realized PnL: `₹{realized_pnl:,.2f}`\n"
            f"• Time: `{datetime.now(UTC).strftime('%H:%M:%S UTC')}`"
        )
        return self._dispatch(event_type="STOPLOSS_HIT", text=text)

    def send_target_hit_alert(
        self,
        symbol: str,
        exit_price: float,
        realized_pnl: float,
        target_stage: str = "T1",
        strategy_name: str = "Momentum F&O",
    ) -> dict[str, Any]:
        """Send Target Hit alert."""
        text = (
            f"🎯 *TARGET HIT ({target_stage})*\n"
            f"• Strategy: `{strategy_name}`\n"
            f"• Symbol: *{symbol}*\n"
            f"• Exit Price: `₹{exit_price:,.2f}`\n"
            f"• Realized PnL: `+₹{realized_pnl:,.2f}`\n"
            f"• Time: `{datetime.now(UTC).strftime('%H:%M:%S UTC')}`"
        )
        return self._dispatch(event_type="TARGET_HIT", text=text)

    def send_kill_switch_alert(
        self,
        reason: str,
        daily_pnl: float,
        positions_closed: int,
    ) -> dict[str, Any]:
        """Send Emergency Kill Switch Alert."""
        text = (
            f"🚨🚨 *EMERGENCY KILL SWITCH ACTIVATED* 🚨🚨\n"
            f"• Reason: *{reason}*\n"
            f"• Daily PnL: `₹{daily_pnl:,.2f}`\n"
            f"• Open Positions Squared Off: `{positions_closed}`\n"
            f"• Trading Status: *HALTED / LOCKED*\n"
            f"• Time: `{datetime.now(UTC).strftime('%H:%M:%S UTC')}`"
        )
        return self._dispatch(event_type="KILL_SWITCH_HALT", text=text)

    def _dispatch(self, event_type: str, text: str) -> dict[str, Any]:
        """Record and dispatch alert message."""
        payload = {
            "event_type": event_type,
            "text": text,
            "timestamp": datetime.now(UTC),
            "dispatched": self.enabled,
        }
        self.dispatched_messages.append(payload)
        logger.info("Dispatched Alert [%s]: %s", event_type, text)
        return payload
