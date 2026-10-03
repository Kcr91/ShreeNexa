"""Real-Time Shadow Variant Tracker running in-memory variations alongside baseline."""

from __future__ import annotations

from typing import Any


class ShadowVariantState:
    """In-memory tracking state for a single shadow variation."""

    def __init__(
        self, name: str, is_baseline: bool = False, overrides: dict[str, Any] | None = None
    ) -> None:
        self.name = name
        self.is_baseline = is_baseline
        self.overrides = overrides or {}
        self.realized_pnl: float = 0.0
        self.open_pnl: float = 0.0
        self.trade_count: int = 0
        self.win_count: int = 0

    def record_trade(self, pnl: float) -> None:
        """Update shadow metrics when a trade completes."""
        self.realized_pnl += pnl
        self.trade_count += 1
        if pnl > 0:
            self.win_count += 1

    def to_dict(self) -> dict[str, Any]:
        win_rate = (self.win_count / self.trade_count * 100.0) if self.trade_count > 0 else 0.0
        return {
            "variant_name": self.name,
            "is_baseline": self.is_baseline,
            "realized_pnl": round(self.realized_pnl, 2),
            "open_pnl": round(self.open_pnl, 2),
            "total_pnl": round(self.realized_pnl + self.open_pnl, 2),
            "trades_count": self.trade_count,
            "win_rate_pct": round(win_rate, 2),
            "outperforming_baseline": False,
        }


class ShadowVariantTracker:
    """Manages concurrent shadow variant simulations in memory."""

    def __init__(self, strategy_id: int) -> None:
        self.strategy_id = strategy_id
        self.variants: dict[str, ShadowVariantState] = {
            "Variant 0 (Baseline Default)": ShadowVariantState(
                "Variant 0 (Baseline Default)", is_baseline=True
            ),
            "Variant 1 (Multi-Target Grid)": ShadowVariantState(
                "Variant 1 (Multi-Target Grid)",
                is_baseline=False,
                overrides={"target_1": 30.0, "target_2": 60.0},
            ),
            "Variant 2 (Trailing SL Grid)": ShadowVariantState(
                "Variant 2 (Trailing SL Grid)",
                is_baseline=False,
                overrides={"trail_step_pct": 10.0},
            ),
        }

    def update_tick(self, symbol: str, ltp: float) -> None:
        """Simulate tick update across shadow positions."""
        # Update open pnl based on current LTP
        pass

    def get_leaderboard(self) -> list[dict[str, Any]]:
        """Return sorted leaderboard comparing baseline against shadow variants."""
        results = [v.to_dict() for v in self.variants.values()]
        baseline_pnl = next((r["total_pnl"] for r in results if r["is_baseline"]), 0.0)

        for r in results:
            if not r["is_baseline"] and r["total_pnl"] > baseline_pnl:
                r["outperforming_baseline"] = True

        results.sort(key=lambda x: x["total_pnl"], reverse=True)
        return results
