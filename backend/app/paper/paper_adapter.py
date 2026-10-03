"""Unified Execution Engine Paper Trading Adapter with Fill Delay Simulation."""

from __future__ import annotations

import time
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import delete, insert, select, update
from sqlalchemy.engine import Engine

from app.engine.cost_simulator import calculate_trade_costs
from app.paper.paper_models import (
    paper_positions_table,
    paper_sessions_table,
    paper_tradebook_table,
)


class PaperExecutionAdapter:
    """Executes paper orders with realistic latency and cost deduction."""

    def __init__(self, engine: Engine, simulated_latency_ms: int = 150) -> None:
        self.engine = engine
        self.latency_ms = simulated_latency_ms

    def open_position(
        self,
        session_id: int,
        symbol: str,
        signal_type: str,
        price: float,
        quantity: int,
        active_sl: float | None = None,
        active_target: float | None = None,
    ) -> dict[str, Any]:
        """Simulate order entry with fill delay."""
        # Simulated execution delay (100-200ms)
        time.sleep(self.latency_ms / 1000.0)

        now = datetime.now(UTC)
        with self.engine.begin() as conn:
            res = conn.execute(
                insert(paper_positions_table).values(
                    session_id=session_id,
                    symbol=symbol,
                    signal_type=signal_type,
                    entry_time=now,
                    entry_price=price,
                    current_price=price,
                    quantity=quantity,
                    unrealized_pnl=0.00,
                    active_sl=active_sl,
                    active_target=active_target,
                    updated_at=now,
                )
            )
            pos_id = res.inserted_primary_key[0]  # type: ignore[index]

        return {
            "status": "OPENED",
            "position_id": pos_id,
            "symbol": symbol,
            "entry_price": price,
            "quantity": quantity,
        }

    def square_off_position(
        self,
        position_id: int,
        exit_price: float,
        exit_reason: str = "MANUAL_SQUARE_OFF",
    ) -> dict[str, Any]:
        """Square off open paper position and log into paper_tradebook."""
        now = datetime.now(UTC)
        with self.engine.begin() as conn:
            pos = (
                conn.execute(
                    select(paper_positions_table).where(
                        paper_positions_table.c.position_id == position_id
                    )
                )
                .mappings()
                .first()
            )

            if not pos:
                return {"status": "ERROR", "message": f"Position {position_id} not found"}

            session_id = pos["session_id"]
            symbol = pos["symbol"]
            qty = pos["quantity"]
            entry_p = float(pos["entry_price"])
            signal_type = pos["signal_type"]
            entry_t = pos["entry_time"]

            cost = calculate_trade_costs(
                instrument_type="OPTION" if "PE" in symbol or "CE" in symbol else "EQUITY",
                buy_price=entry_p,
                sell_price=exit_price,
                quantity=qty,
            )

            # Insert into tradebook
            conn.execute(
                insert(paper_tradebook_table).values(
                    session_id=session_id,
                    symbol=symbol,
                    signal_type=signal_type,
                    entry_time=entry_t,
                    exit_time=now,
                    entry_price=entry_p,
                    exit_price=exit_price,
                    quantity=qty,
                    realized_pnl=cost.net_pnl,
                    exit_reason=exit_reason,
                    entry_vix=14.50,
                    exit_vix=14.80,
                    entry_iv=25.0,
                    exit_iv=26.5,
                    simulated_slippage=cost.slippage_cost,
                    simulated_brokerage=cost.brokerage,
                )
            )

            # Update session capital
            conn.execute(
                update(paper_sessions_table)
                .where(paper_sessions_table.c.session_id == session_id)
                .values(current_capital=paper_sessions_table.c.current_capital + cost.net_pnl)
            )

            # Delete open position
            conn.execute(
                delete(paper_positions_table).where(
                    paper_positions_table.c.position_id == position_id
                )
            )

        return {
            "status": "CLOSED",
            "position_id": position_id,
            "realized_pnl": cost.net_pnl,
            "exit_price": exit_price,
            "exit_reason": exit_reason,
        }
