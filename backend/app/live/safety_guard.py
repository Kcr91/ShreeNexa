"""Multi-Layer Risk Guardrails & Emergency Auto-Kill Switch Engine."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any


@dataclass
class RiskGuardrailCheckResult:
    passed: bool
    guard_name: str
    rejection_reason: str | None = None
    trigger_auto_kill: bool = False
    details: dict[str, Any] | None = None


class SafetyGuardEngine:
    """Evaluates the 4 core safety guardrails before live order routing."""

    def __init__(
        self,
        total_capital: float = 500000.0,
        max_daily_loss_pct: float = 3.0,
        max_trade_exposure_pct: float = 10.0,
        max_concurrent_trades: int = 5,
        circuit_buffer_pct: float = 0.5,
    ) -> None:
        self.total_capital = total_capital
        self.max_daily_loss_pct = max_daily_loss_pct
        self.max_trade_exposure_pct = max_trade_exposure_pct
        self.max_concurrent_trades = max_concurrent_trades
        self.circuit_buffer_pct = circuit_buffer_pct
        self.kill_switch_active = False

    def check_kill_switch_status(self) -> RiskGuardrailCheckResult:
        """Verify if global kill switch is currently active."""
        if self.kill_switch_active:
            return RiskGuardrailCheckResult(
                passed=False,
                guard_name="GLOBAL_KILL_SWITCH",
                rejection_reason="Emergency Kill Switch is ACTIVE. Trading is locked.",
                trigger_auto_kill=False,
            )
        return RiskGuardrailCheckResult(passed=True, guard_name="GLOBAL_KILL_SWITCH")

    def check_daily_loss_limit(
        self, current_realized_pnl: float, current_unrealized_pnl: float
    ) -> RiskGuardrailCheckResult:
        """Guard 1: Max Daily Loss Auto-Kill Switch.

        Trigger: Realized + Unrealized Loss >= max_daily_loss_pct (e.g. 3%) of Total Capital.
        """
        total_daily_pnl = current_realized_pnl + current_unrealized_pnl
        max_allowed_loss = -(self.total_capital * (self.max_daily_loss_pct / 100.0))

        if total_daily_pnl <= max_allowed_loss:
            self.kill_switch_active = True
            return RiskGuardrailCheckResult(
                passed=False,
                guard_name="MAX_DAILY_LOSS_GUARD",
                rejection_reason=(
                    f"Daily PnL (₹{total_daily_pnl:,.2f}) breached max daily loss limit "
                    f"(₹{max_allowed_loss:,.2f} / -{self.max_daily_loss_pct}%). "
                    "Auto-Kill Switch triggered!"
                ),
                trigger_auto_kill=True,
                details={
                    "total_daily_pnl": total_daily_pnl,
                    "max_allowed_loss": max_allowed_loss,
                    "loss_pct": round(abs(total_daily_pnl) / self.total_capital * 100.0, 2),
                },
            )

        return RiskGuardrailCheckResult(
            passed=True,
            guard_name="MAX_DAILY_LOSS_GUARD",
            details={"current_loss_headroom": total_daily_pnl - max_allowed_loss},
        )

    def check_trade_exposure(self, required_margin_or_premium: float) -> RiskGuardrailCheckResult:
        """Guard 2: Single Trade Exposure Cap (e.g. max 10% of total capital per trade)."""
        max_allowed_trade_capital = self.total_capital * (self.max_trade_exposure_pct / 100.0)
        if required_margin_or_premium > max_allowed_trade_capital:
            return RiskGuardrailCheckResult(
                passed=False,
                guard_name="TRADE_EXPOSURE_CAP_GUARD",
                rejection_reason=(
                    f"Trade capital required (₹{required_margin_or_premium:,.2f}) exceeds "
                    f"max single trade exposure cap of {self.max_trade_exposure_pct}% "
                    f"(₹{max_allowed_trade_capital:,.2f})."
                ),
                details={
                    "required_capital": required_margin_or_premium,
                    "max_allowed": max_allowed_trade_capital,
                },
            )

        return RiskGuardrailCheckResult(passed=True, guard_name="TRADE_EXPOSURE_CAP_GUARD")

    def check_concurrent_positions(
        self, current_open_positions_count: int
    ) -> RiskGuardrailCheckResult:
        """Guard 3: Max Concurrent Positions Limit (e.g. max 5 concurrent positions)."""
        if current_open_positions_count >= self.max_concurrent_trades:
            return RiskGuardrailCheckResult(
                passed=False,
                guard_name="CONCURRENT_POSITIONS_LIMIT_GUARD",
                rejection_reason=(
                    f"Max concurrent open positions limit ({self.max_concurrent_trades}) reached. "
                    f"Current open: {current_open_positions_count}."
                ),
                details={
                    "current_open": current_open_positions_count,
                    "max_limit": self.max_concurrent_trades,
                },
            )

        return RiskGuardrailCheckResult(passed=True, guard_name="CONCURRENT_POSITIONS_LIMIT_GUARD")

    def check_circuit_breaker(
        self,
        current_ltp: float,
        upper_circuit_limit: float | None = None,
        lower_circuit_limit: float | None = None,
    ) -> RiskGuardrailCheckResult:
        """Guard 4: Circuit Breaker & Freeze Check (rejects orders within buffer % of circuit)."""
        if upper_circuit_limit is not None and upper_circuit_limit > 0:
            upper_threshold = upper_circuit_limit * (1.0 - (self.circuit_buffer_pct / 100.0))
            if current_ltp >= upper_threshold:
                return RiskGuardrailCheckResult(
                    passed=False,
                    guard_name="CIRCUIT_BREAKER_GUARD",
                    rejection_reason=(
                        f"LTP (₹{current_ltp:.2f}) is within {self.circuit_buffer_pct}% "
                        f"of Upper Circuit (₹{upper_circuit_limit:.2f}). Order blocked."
                    ),
                    details={"ltp": current_ltp, "upper_circuit": upper_circuit_limit},
                )

        if lower_circuit_limit is not None and lower_circuit_limit > 0:
            lower_threshold = lower_circuit_limit * (1.0 + (self.circuit_buffer_pct / 100.0))
            if current_ltp <= lower_threshold:
                return RiskGuardrailCheckResult(
                    passed=False,
                    guard_name="CIRCUIT_BREAKER_GUARD",
                    rejection_reason=(
                        f"LTP (₹{current_ltp:.2f}) is within {self.circuit_buffer_pct}% "
                        f"of Lower Circuit (₹{lower_circuit_limit:.2f}). Order blocked."
                    ),
                    details={"ltp": current_ltp, "lower_circuit": lower_circuit_limit},
                )

        return RiskGuardrailCheckResult(passed=True, guard_name="CIRCUIT_BREAKER_GUARD")

    def validate_pre_order_all_guards(
        self,
        current_realized_pnl: float,
        current_unrealized_pnl: float,
        required_trade_capital: float,
        current_open_positions_count: int,
        current_ltp: float,
        upper_circuit: float | None = None,
        lower_circuit: float | None = None,
    ) -> tuple[bool, list[RiskGuardrailCheckResult]]:
        """Run all 4 guardrails sequentially in fail-fast order."""
        results: list[RiskGuardrailCheckResult] = []

        # 0. Global Kill Switch Check
        res_ks = self.check_kill_switch_status()
        results.append(res_ks)
        if not res_ks.passed:
            return False, results

        # 1. Daily Loss Check
        res_dl = self.check_daily_loss_limit(current_realized_pnl, current_unrealized_pnl)
        results.append(res_dl)
        if not res_dl.passed:
            return False, results

        # 2. Concurrent Positions Check
        res_cp = self.check_concurrent_positions(current_open_positions_count)
        results.append(res_cp)
        if not res_cp.passed:
            return False, results

        # 3. Trade Exposure Cap Check
        res_te = self.check_trade_exposure(required_trade_capital)
        results.append(res_te)
        if not res_te.passed:
            return False, results

        # 4. Circuit Breaker Check
        res_cb = self.check_circuit_breaker(current_ltp, upper_circuit, lower_circuit)
        results.append(res_cb)
        if not res_cb.passed:
            return False, results

        return True, results

    def trigger_emergency_kill_switch(self, reason: str = "Manual Trigger") -> dict[str, Any]:
        """Trigger emergency kill switch and lock trading."""
        self.kill_switch_active = True
        return {
            "kill_switch_active": True,
            "reason": reason,
            "timestamp": datetime.now(UTC),
            "status": "HALTED",
        }
