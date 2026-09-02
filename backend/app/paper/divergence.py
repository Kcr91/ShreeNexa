"""Same-session paper-vs-backtest divergence report engine.

Compares live/paper execution against replay backtests across signals,
timestamps, execution prices, fills, costs, and P&L, providing automated
classification and root-cause localization.
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field

from app.engine.contracts import FillEvent, OrderSide, Portfolio
from app.paper.adapter import paper_account_to_portfolio
from app.paper.models import PaperFill, PaperOrderSide
from app.paper.repository import PaperRepository, paper_repository


class DivergenceSeverity(StrEnum):
    """Overall classification of session divergence."""

    PERFECT_MATCH = "PERFECT_MATCH"
    ACCEPTABLE_DRIFT = "ACCEPTABLE_DRIFT"
    DIVERGENCE_DETECTED = "DIVERGENCE_DETECTED"
    CRITICAL_MISMATCH = "CRITICAL_MISMATCH"


class DiscrepancyType(StrEnum):
    """Specific categories for localizing execution differences."""

    MISSED_SIGNAL = "MISSED_SIGNAL"
    UNEXPECTED_SIGNAL = "UNEXPECTED_SIGNAL"
    SIGNAL_DIRECTION_MISMATCH = "SIGNAL_DIRECTION_MISMATCH"
    LATENCY_DELAY = "LATENCY_DELAY"
    SLIPPAGE_DISCREPANCY = "SLIPPAGE_DISCREPANCY"
    FILL_QUANTITY_MISMATCH = "FILL_QUANTITY_MISMATCH"
    DROPPED_FILL = "DROPPED_FILL"
    UNEXPECTED_FILL = "UNEXPECTED_FILL"
    COST_MODEL_DRIFT = "COST_MODEL_DRIFT"
    PNL_DISCREPANCY = "PNL_DISCREPANCY"


class DivergenceTolerances(BaseModel):
    """Configurable tolerances for divergence classification."""

    max_price_drift_pct: float = Field(
        default=0.1,
        description="Maximum acceptable percentage price difference (e.g. 0.1%).",
    )
    max_latency_seconds: float = Field(
        default=2.0,
        description="Maximum execution timestamp delta in seconds (e.g. 2.0s).",
    )
    max_cost_drift_pct: float = Field(
        default=5.0,
        description="Maximum acceptable transaction cost drift percentage (e.g. 5.0%).",
    )
    max_pnl_drift_pct: float = Field(
        default=0.5,
        description="Maximum acceptable portfolio P&L drift percentage (e.g. 0.5%).",
    )
    allow_partial_fills: bool = Field(
        default=False,
        description="Whether partial fills without backtest counterpart are tolerated.",
    )


class DiscrepancyItem(BaseModel):
    """Individual flagged discrepancy with root-cause attribution."""

    discrepancy_type: DiscrepancyType
    severity: DivergenceSeverity
    entity_id: str
    symbol: str
    paper_value: Any
    backtest_value: Any
    delta: Any
    explanation: str


class SignalComparisonItem(BaseModel):
    """Comparative evaluation of a single strategy signal."""

    signal_id: str
    symbol: str
    side: str
    timestamp_paper: datetime | None = None
    timestamp_backtest: datetime | None = None
    latency_ms: float | None = None
    status: str
    explanation: str = ""


class ExecutionComparisonItem(BaseModel):
    """Comparative evaluation of an individual order fill."""

    order_id: str
    symbol: str
    side: str
    paper_price: float | None = None
    backtest_price: float | None = None
    price_delta: float | None = None
    price_delta_pct: float | None = None
    paper_qty: int = 0
    backtest_qty: int = 0
    paper_cost: float = 0.0
    backtest_cost: float = 0.0
    latency_seconds: float | None = None
    status: str
    explanation: str = ""


class PnLComparisonSummary(BaseModel):
    """Comparative portfolio performance summary."""

    paper_realized_pnl: float
    backtest_realized_pnl: float
    pnl_delta: float
    pnl_delta_pct: float
    paper_total_costs: float
    backtest_total_costs: float
    costs_delta: float
    paper_final_equity: float
    backtest_final_equity: float
    equity_delta: float


class SessionDivergenceReport(BaseModel):
    """Comprehensive divergence report across signals, execution, and P&L."""

    session_id: str
    strategy_name: str
    generated_at: datetime
    verdict: DivergenceSeverity
    is_deployable: bool
    tolerances: DivergenceTolerances
    signals_summary: dict[str, int]
    executions_summary: dict[str, int]
    pnl_summary: PnLComparisonSummary
    discrepancies: list[DiscrepancyItem]
    signals: list[SignalComparisonItem] = Field(default_factory=list)
    executions: list[ExecutionComparisonItem] = Field(default_factory=list)


def compare_signals(
    paper_signals: list[dict[str, Any]],
    backtest_signals: list[dict[str, Any]],
    tolerances: DivergenceTolerances,
) -> tuple[list[SignalComparisonItem], list[DiscrepancyItem]]:
    """Compare signals generated in paper session vs replay backtest."""
    signal_items: list[SignalComparisonItem] = []
    discrepancies: list[DiscrepancyItem] = []

    # Map signals by (symbol, side, sequence_index)
    bt_consumed: set[int] = set()

    for idx, p_sig in enumerate(paper_signals):
        symbol = str(p_sig.get("symbol", ""))
        side = str(p_sig.get("side", "")).upper()
        p_ts = p_sig.get("timestamp")
        if isinstance(p_ts, str):
            p_ts = datetime.fromisoformat(p_ts)

        # Look for best matching backtest signal
        match_idx: int | None = None
        for b_idx, b_sig in enumerate(backtest_signals):
            if b_idx in bt_consumed:
                continue
            if b_sig.get("symbol") == symbol and str(b_sig.get("side", "")).upper() == side:
                match_idx = b_idx
                break

        if match_idx is not None:
            bt_consumed.add(match_idx)
            b_sig = backtest_signals[match_idx]
            b_ts = b_sig.get("timestamp")
            if isinstance(b_ts, str):
                b_ts = datetime.fromisoformat(b_ts)

            latency_ms = None
            if p_ts and b_ts:
                latency_ms = abs((p_ts - b_ts).total_seconds()) * 1000.0

            status = "MATCHED"
            explanation = "Signal matched backtest trigger"

            if latency_ms is not None and latency_ms > (tolerances.max_latency_seconds * 1000.0):
                status = "TIMING_DRIFT"
                explanation = (
                    f"Signal latency ({latency_ms:.1f}ms) exceeded threshold "
                    f"({tolerances.max_latency_seconds * 1000.0}ms)"
                )
                discrepancies.append(
                    DiscrepancyItem(
                        discrepancy_type=DiscrepancyType.LATENCY_DELAY,
                        severity=DivergenceSeverity.DIVERGENCE_DETECTED,
                        entity_id=str(p_sig.get("signal_id", f"sig-{idx}")),
                        symbol=symbol,
                        paper_value=latency_ms,
                        backtest_value=0.0,
                        delta=latency_ms,
                        explanation=explanation,
                    )
                )

            signal_items.append(
                SignalComparisonItem(
                    signal_id=str(p_sig.get("signal_id", f"sig-p-{idx}")),
                    symbol=symbol,
                    side=side,
                    timestamp_paper=p_ts,
                    timestamp_backtest=b_ts,
                    latency_ms=latency_ms,
                    status=status,
                    explanation=explanation,
                )
            )
        else:
            # Paper signal not found in backtest
            explanation = "Signal occurred in paper session but not reproduced in backtest"
            discrepancies.append(
                DiscrepancyItem(
                    discrepancy_type=DiscrepancyType.UNEXPECTED_SIGNAL,
                    severity=DivergenceSeverity.DIVERGENCE_DETECTED,
                    entity_id=str(p_sig.get("signal_id", f"sig-p-{idx}")),
                    symbol=symbol,
                    paper_value=side,
                    backtest_value=None,
                    delta=None,
                    explanation=explanation,
                )
            )
            signal_items.append(
                SignalComparisonItem(
                    signal_id=str(p_sig.get("signal_id", f"sig-p-{idx}")),
                    symbol=symbol,
                    side=side,
                    timestamp_paper=p_ts,
                    status="UNEXPECTED_IN_PAPER",
                    explanation=explanation,
                )
            )

    # Check for backtest signals missed in paper
    for b_idx, b_sig in enumerate(backtest_signals):
        if b_idx not in bt_consumed:
            symbol = str(b_sig.get("symbol", ""))
            side = str(b_sig.get("side", "")).upper()
            b_ts = b_sig.get("timestamp")
            if isinstance(b_ts, str):
                b_ts = datetime.fromisoformat(b_ts)
            explanation = "Signal generated in backtest was dropped or not triggered in paper"
            discrepancies.append(
                DiscrepancyItem(
                    discrepancy_type=DiscrepancyType.MISSED_SIGNAL,
                    severity=DivergenceSeverity.CRITICAL_MISMATCH,
                    entity_id=str(b_sig.get("signal_id", f"sig-bt-{b_idx}")),
                    symbol=symbol,
                    paper_value=None,
                    backtest_value=side,
                    delta=None,
                    explanation=explanation,
                )
            )
            signal_items.append(
                SignalComparisonItem(
                    signal_id=str(b_sig.get("signal_id", f"sig-bt-{b_idx}")),
                    symbol=symbol,
                    side=side,
                    timestamp_backtest=b_ts,
                    status="MISSED_IN_PAPER",
                    explanation=explanation,
                )
            )

    return signal_items, discrepancies


def compare_executions(
    paper_fills: list[PaperFill],
    backtest_fills: list[FillEvent],
    tolerances: DivergenceTolerances,
) -> tuple[list[ExecutionComparisonItem], list[DiscrepancyItem]]:
    """Compare fill prices, timestamps, quantities, and costs."""
    exec_items: list[ExecutionComparisonItem] = []
    discrepancies: list[DiscrepancyItem] = []

    # Sort fills chronologically
    sorted_paper = sorted(paper_fills, key=lambda f: f.timestamp)
    sorted_bt = sorted(backtest_fills, key=lambda f: f.timestamp)

    bt_consumed: set[int] = set()

    for p_fill in sorted_paper:
        p_side_str = "BUY" if p_fill.side == PaperOrderSide.BUY else "SELL"
        symbol = p_fill.symbol or p_fill.security_id

        # Match by order_id or (security_id, side)
        match_idx: int | None = None
        for b_idx, b_fill in enumerate(sorted_bt):
            if b_idx in bt_consumed:
                continue
            b_side_str = "BUY" if b_fill.side == OrderSide.BUY else "SELL"
            # Primary: match order_id if identical
            if p_fill.order_id and b_fill.order_id and p_fill.order_id == b_fill.order_id:
                match_idx = b_idx
                break
            # Secondary: match security_id and side
            if b_fill.security_id == p_fill.security_id and b_side_str == p_side_str:
                match_idx = b_idx
                break

        if match_idx is not None:
            bt_consumed.add(match_idx)
            b_fill = sorted_bt[match_idx]

            price_delta = round(p_fill.price - b_fill.price, 4)
            price_delta_pct = (
                round((abs(price_delta) / b_fill.price) * 100.0, 4) if b_fill.price > 0 else 0.0
            )
            latency_sec = round(abs((p_fill.timestamp - b_fill.timestamp).total_seconds()), 4)

            # Check quantity
            qty_match = p_fill.quantity == b_fill.quantity
            # Check price
            price_match = price_delta_pct <= tolerances.max_price_drift_pct
            # Check latency
            latency_match = latency_sec <= tolerances.max_latency_seconds

            status = "MATCHED"
            explanations: list[str] = []

            if not qty_match:
                status = "QUANTITY_MISMATCH"
                exp = (
                    f"Executed quantity mismatch: paper={p_fill.quantity} "
                    f"vs backtest={b_fill.quantity}"
                )
                explanations.append(exp)
                discrepancies.append(
                    DiscrepancyItem(
                        discrepancy_type=DiscrepancyType.FILL_QUANTITY_MISMATCH,
                        severity=DivergenceSeverity.CRITICAL_MISMATCH,
                        entity_id=p_fill.order_id,
                        symbol=symbol,
                        paper_value=p_fill.quantity,
                        backtest_value=b_fill.quantity,
                        delta=p_fill.quantity - b_fill.quantity,
                        explanation=exp,
                    )
                )

            if not price_match:
                status = "SLIPPAGE_DRIFT" if status == "MATCHED" else status
                exp = (
                    f"Fill price drifted by {price_delta_pct:.2f}% "
                    f"(paper={p_fill.price:.2f}, bt={b_fill.price:.2f})"
                )
                explanations.append(exp)
                discrepancies.append(
                    DiscrepancyItem(
                        discrepancy_type=DiscrepancyType.SLIPPAGE_DISCREPANCY,
                        severity=DivergenceSeverity.DIVERGENCE_DETECTED,
                        entity_id=p_fill.order_id,
                        symbol=symbol,
                        paper_value=p_fill.price,
                        backtest_value=b_fill.price,
                        delta=price_delta,
                        explanation=exp,
                    )
                )

            if not latency_match:
                status = "LATENCY_EXCEEDED" if status == "MATCHED" else status
                exp = (
                    f"Execution latency delta {latency_sec:.2f}s exceeded threshold "
                    f"({tolerances.max_latency_seconds:.1f}s)"
                )
                explanations.append(exp)
                discrepancies.append(
                    DiscrepancyItem(
                        discrepancy_type=DiscrepancyType.LATENCY_DELAY,
                        severity=DivergenceSeverity.DIVERGENCE_DETECTED,
                        entity_id=p_fill.order_id,
                        symbol=symbol,
                        paper_value=latency_sec,
                        backtest_value=0.0,
                        delta=latency_sec,
                        explanation=exp,
                    )
                )

            # Check transaction costs
            p_cost = p_fill.transaction_cost
            b_cost = b_fill.total_cost
            if b_cost > 0:
                cost_drift_pct = (abs(p_cost - b_cost) / b_cost) * 100.0
                if cost_drift_pct > tolerances.max_cost_drift_pct:
                    exp = (
                        f"Cost model drift: paper={p_cost:.2f} vs backtest={b_cost:.2f} "
                        f"({cost_drift_pct:.1f}% drift)"
                    )
                    explanations.append(exp)
                    discrepancies.append(
                        DiscrepancyItem(
                            discrepancy_type=DiscrepancyType.COST_MODEL_DRIFT,
                            severity=DivergenceSeverity.ACCEPTABLE_DRIFT
                            if cost_drift_pct < 15.0
                            else DivergenceSeverity.DIVERGENCE_DETECTED,
                            entity_id=p_fill.order_id,
                            symbol=symbol,
                            paper_value=p_cost,
                            backtest_value=b_cost,
                            delta=round(p_cost - b_cost, 2),
                            explanation=exp,
                        )
                    )

            exec_items.append(
                ExecutionComparisonItem(
                    order_id=p_fill.order_id,
                    symbol=symbol,
                    side=p_side_str,
                    paper_price=p_fill.price,
                    backtest_price=b_fill.price,
                    price_delta=price_delta,
                    price_delta_pct=price_delta_pct,
                    paper_qty=p_fill.quantity,
                    backtest_qty=b_fill.quantity,
                    paper_cost=p_cost,
                    backtest_cost=b_cost,
                    latency_seconds=latency_sec,
                    status=status,
                    explanation="; ".join(explanations)
                    if explanations
                    else "Fill reconciled within declared tolerances",
                )
            )
        else:
            # Paper fill with no backtest match
            exp = "Paper executed fill with no corresponding backtest order"
            discrepancies.append(
                DiscrepancyItem(
                    discrepancy_type=DiscrepancyType.UNEXPECTED_FILL,
                    severity=DivergenceSeverity.CRITICAL_MISMATCH,
                    entity_id=p_fill.order_id,
                    symbol=symbol,
                    paper_value=p_fill.quantity,
                    backtest_value=0,
                    delta=p_fill.quantity,
                    explanation=exp,
                )
            )
            exec_items.append(
                ExecutionComparisonItem(
                    order_id=p_fill.order_id,
                    symbol=symbol,
                    side=p_side_str,
                    paper_price=p_fill.price,
                    paper_qty=p_fill.quantity,
                    paper_cost=p_fill.transaction_cost,
                    status="UNEXPECTED_IN_PAPER",
                    explanation=exp,
                )
            )

    # Check for backtest fills not executed in paper
    for b_idx, b_fill in enumerate(sorted_bt):
        if b_idx not in bt_consumed:
            b_side_str = "BUY" if b_fill.side == OrderSide.BUY else "SELL"
            exp = "Backtest fill failed to execute or was dropped in paper trading"
            discrepancies.append(
                DiscrepancyItem(
                    discrepancy_type=DiscrepancyType.DROPPED_FILL,
                    severity=DivergenceSeverity.CRITICAL_MISMATCH,
                    entity_id=b_fill.order_id,
                    symbol=b_fill.security_id,
                    paper_value=0,
                    backtest_value=b_fill.quantity,
                    delta=-b_fill.quantity,
                    explanation=exp,
                )
            )
            exec_items.append(
                ExecutionComparisonItem(
                    order_id=b_fill.order_id,
                    symbol=b_fill.security_id,
                    side=b_side_str,
                    backtest_price=b_fill.price,
                    backtest_qty=b_fill.quantity,
                    backtest_cost=b_fill.total_cost,
                    status="DROPPED_FILL",
                    explanation=exp,
                )
            )

    return exec_items, discrepancies


def generate_divergence_report(
    session_id: str,
    strategy_name: str,
    paper_fills: list[PaperFill],
    backtest_fills: list[FillEvent],
    paper_portfolio: Portfolio | None = None,
    backtest_portfolio: Portfolio | None = None,
    paper_signals: list[dict[str, Any]] | None = None,
    backtest_signals: list[dict[str, Any]] | None = None,
    tolerances: DivergenceTolerances | None = None,
) -> SessionDivergenceReport:
    """Generate a multi-dimensional divergence report between paper and backtest runs."""
    cfg = tolerances or DivergenceTolerances()
    all_discrepancies: list[DiscrepancyItem] = []

    # 1. Compare Signals
    p_signals = paper_signals or []
    bt_signals = backtest_signals or []
    signal_items, sig_disc = compare_signals(p_signals, bt_signals, cfg)
    all_discrepancies.extend(sig_disc)

    # 2. Compare Executions (fills, prices, slippage, costs)
    exec_items, exec_disc = compare_executions(paper_fills, backtest_fills, cfg)
    all_discrepancies.extend(exec_disc)

    # 3. Compare P&L and Returns
    from app.engine.contracts import Position

    if backtest_portfolio is None and backtest_fills:
        init_c = paper_portfolio.initial_cash if paper_portfolio else 1_000_000.0
        c_bal = paper_portfolio.cash if paper_portfolio else 1_000_000.0
        bt_pos_map: dict[str, Position] = {}
        for bf in backtest_fills:
            if bf.security_id not in bt_pos_map:
                bt_pos_map[bf.security_id] = Position(
                    security_id=bf.security_id,
                    exchange_segment=bf.exchange_segment,
                )
            bt_pos_map[bf.security_id].apply_fill(bf.side, bf.quantity, bf.price)
        backtest_portfolio = Portfolio(
            initial_cash=init_c,
            cash=c_bal,
            positions=bt_pos_map,
            fills=backtest_fills,
        )

    if paper_portfolio is None and paper_fills:
        init_c = 1_000_000.0
        p_pos_map: dict[str, Position] = {}
        p_fill_events: list[FillEvent] = []
        for pf in paper_fills:
            side = OrderSide.BUY if pf.side == PaperOrderSide.BUY else OrderSide.SELL
            if pf.security_id not in p_pos_map:
                p_pos_map[pf.security_id] = Position(
                    security_id=pf.security_id,
                    exchange_segment=pf.segment,
                )
            p_pos_map[pf.security_id].apply_fill(side, pf.quantity, pf.price)
            p_fill_events.append(
                FillEvent(
                    order_id=pf.order_id,
                    security_id=pf.security_id,
                    exchange_segment=pf.segment,
                    side=side,
                    quantity=pf.quantity,
                    price=pf.price,
                    timestamp=pf.timestamp,
                    brokerage=0.0,
                    taxes=pf.transaction_cost,
                    slippage=pf.slippage,
                )
            )
        paper_portfolio = Portfolio(
            initial_cash=init_c,
            cash=init_c,
            positions=p_pos_map,
            fills=p_fill_events,
        )

    p_realized = (
        sum(p.realized_pnl for p in paper_portfolio.positions.values()) if paper_portfolio else 0.0
    )
    bt_realized = (
        sum(p.realized_pnl for p in backtest_portfolio.positions.values())
        if backtest_portfolio
        else 0.0
    )

    p_costs = sum(f.transaction_cost for f in paper_fills)
    bt_costs = sum(f.total_cost for f in backtest_fills)

    p_final_eq = paper_portfolio.total_equity() if paper_portfolio else 1_000_000.0 + p_realized
    bt_final_eq = (
        backtest_portfolio.total_equity() if backtest_portfolio else 1_000_000.0 + bt_realized
    )

    pnl_delta = round(p_realized - bt_realized, 2)
    base_pnl = abs(bt_realized) if abs(bt_realized) > 1e-4 else 1.0
    pnl_delta_pct = round((abs(pnl_delta) / base_pnl) * 100.0, 4)

    pnl_summary = PnLComparisonSummary(
        paper_realized_pnl=round(p_realized, 2),
        backtest_realized_pnl=round(bt_realized, 2),
        pnl_delta=pnl_delta,
        pnl_delta_pct=pnl_delta_pct,
        paper_total_costs=round(p_costs, 2),
        backtest_total_costs=round(bt_costs, 2),
        costs_delta=round(p_costs - bt_costs, 2),
        paper_final_equity=round(p_final_eq, 2),
        backtest_final_equity=round(bt_final_eq, 2),
        equity_delta=round(p_final_eq - bt_final_eq, 2),
    )

    # Flag PnL divergence if delta exceeds tolerance
    if abs(pnl_delta) > 10.0 and pnl_delta_pct > cfg.max_pnl_drift_pct:
        severity = (
            DivergenceSeverity.CRITICAL_MISMATCH
            if pnl_delta_pct > 2.0
            else DivergenceSeverity.DIVERGENCE_DETECTED
        )
        all_discrepancies.append(
            DiscrepancyItem(
                discrepancy_type=DiscrepancyType.PNL_DISCREPANCY,
                severity=severity,
                entity_id=session_id,
                symbol="PORTFOLIO",
                paper_value=round(p_realized, 2),
                backtest_value=round(bt_realized, 2),
                delta=pnl_delta,
                explanation=(
                    f"Portfolio realized P&L drifted by {pnl_delta_pct:.2f}% "
                    f"(paper={p_realized:.2f}, bt={bt_realized:.2f})"
                ),
            )
        )

    # 4. Summaries & Verdict Determination
    matched_sig = sum(1 for s in signal_items if s.status == "MATCHED")
    missed_sig = sum(1 for s in signal_items if s.status == "MISSED_IN_PAPER")
    unexp_sig = sum(1 for s in signal_items if s.status == "UNEXPECTED_IN_PAPER")

    signals_summary = {
        "total_paper": len(p_signals),
        "total_backtest": len(bt_signals),
        "matched": matched_sig,
        "missed": missed_sig,
        "unexpected": unexp_sig,
    }

    matched_exec = sum(1 for e in exec_items if e.status == "MATCHED")
    slippage_drift = sum(1 for e in exec_items if e.status == "SLIPPAGE_DRIFT")
    qty_mismatch = sum(1 for e in exec_items if e.status == "QUANTITY_MISMATCH")
    dropped_exec = sum(1 for e in exec_items if e.status == "DROPPED_FILL")

    executions_summary = {
        "total_paper": len(paper_fills),
        "total_backtest": len(backtest_fills),
        "matched": matched_exec,
        "slippage_drift": slippage_drift,
        "quantity_mismatch": qty_mismatch,
        "dropped": dropped_exec,
    }

    # Evaluate Overall Verdict
    severities = {d.severity for d in all_discrepancies}
    if DivergenceSeverity.CRITICAL_MISMATCH in severities:
        verdict = DivergenceSeverity.CRITICAL_MISMATCH
        is_deployable = False
    elif DivergenceSeverity.DIVERGENCE_DETECTED in severities:
        verdict = DivergenceSeverity.DIVERGENCE_DETECTED
        is_deployable = False
    elif DivergenceSeverity.ACCEPTABLE_DRIFT in severities or (
        len(all_discrepancies) == 0
        and (
            abs(pnl_summary.costs_delta) > 0
            or any(e.price_delta and abs(e.price_delta) > 0 for e in exec_items)
        )
    ):
        verdict = DivergenceSeverity.ACCEPTABLE_DRIFT
        is_deployable = True
    else:
        verdict = DivergenceSeverity.PERFECT_MATCH
        is_deployable = True

    return SessionDivergenceReport(
        session_id=session_id,
        strategy_name=strategy_name,
        generated_at=datetime.now(UTC),
        verdict=verdict,
        is_deployable=is_deployable,
        tolerances=cfg,
        signals_summary=signals_summary,
        executions_summary=executions_summary,
        pnl_summary=pnl_summary,
        discrepancies=all_discrepancies,
        signals=signal_items,
        executions=exec_items,
    )


def generate_account_divergence_report(
    account_id: str,
    strategy_name: str,
    backtest_fills: list[FillEvent],
    backtest_portfolio: Portfolio | None = None,
    paper_signals: list[dict[str, Any]] | None = None,
    backtest_signals: list[dict[str, Any]] | None = None,
    tolerances: DivergenceTolerances | None = None,
    repository: PaperRepository | None = None,
) -> SessionDivergenceReport:
    """Generate divergence report directly from a live/paper account."""
    repo = repository or paper_repository
    paper_fills = repo.list_fills(account_id)
    paper_portfolio = paper_account_to_portfolio(account_id, repository=repo)

    return generate_divergence_report(
        session_id=f"session-{account_id}",
        strategy_name=strategy_name,
        paper_fills=paper_fills,
        backtest_fills=backtest_fills,
        paper_portfolio=paper_portfolio,
        backtest_portfolio=backtest_portfolio,
        paper_signals=paper_signals,
        backtest_signals=backtest_signals,
        tolerances=tolerances,
    )
