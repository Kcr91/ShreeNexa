"""Unit tests verifying zero-fork reuse of Epic 3 metric registry in paper trading."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from app.backtest.grading import evaluate_strategy_scorecard
from app.backtest.metrics import calculate_backtest_metrics
from app.engine.contracts import EquityPoint, FillEvent, OrderSide, Portfolio, Position
from app.main import app
from app.paper.adapter import (
    calculate_paper_metrics,
    evaluate_paper_scorecard,
    paper_account_to_portfolio,
)
from app.paper.models import PaperAccount, PaperFill, PaperOrderSide, PaperPosition
from app.paper.repository import PaperRepository, paper_repository
from fastapi.testclient import TestClient

client = TestClient(app)


def test_paper_and_backtest_trade_equity_parity() -> None:
    """Proof: The same trade/equity fixture produces identical metrics in backtest and paper."""
    fixture_path = (
        Path(__file__).parent.parent / "fixtures" / "trade_equity_parity_fixture.json"
    )
    with open(fixture_path, encoding="utf-8") as f:
        data = json.load(f)

    initial_capital = float(data["initial_capital"])
    start_date = datetime.fromisoformat(data["start_date"])
    end_date = datetime.fromisoformat(data["end_date"])

    # 1. Mode A: Build backtest Portfolio directly from fixture
    fill_events: list[FillEvent] = []
    positions_map: dict[str, Position] = {}

    for t in data["trades"]:
        side = OrderSide.BUY if t["side"] == "BUY" else OrderSide.SELL
        fe = FillEvent(
            order_id=t["order_id"],
            security_id=t["security_id"],
            exchange_segment=t["segment"],
            side=side,
            quantity=t["quantity"],
            price=t["price"],
            timestamp=datetime.fromisoformat(t["timestamp"]),
            brokerage=0.0,
            taxes=t["transaction_cost"],
            slippage=t["slippage"],
        )
        fill_events.append(fe)
        if t["security_id"] not in positions_map:
            positions_map[t["security_id"]] = Position(
                security_id=t["security_id"],
                exchange_segment=t["segment"],
            )
        positions_map[t["security_id"]].apply_fill(side, t["quantity"], t["price"])

    equity_points: list[EquityPoint] = [
        EquityPoint(
            timestamp=datetime.fromisoformat(ep["timestamp"]),
            equity=ep["equity"],
            cash=ep["cash"],
            realized_pnl=ep["realized_pnl"],
            unrealized_pnl=ep["unrealized_pnl"],
        )
        for ep in data["equity_curve"]
    ]

    bt_portfolio = Portfolio(
        initial_cash=initial_capital,
        cash=equity_points[-1].cash,
        positions=positions_map,
        fills=fill_events,
        equity_curve=equity_points,
    )

    bt_metrics = calculate_backtest_metrics(
        initial_capital=initial_capital,
        portfolio=bt_portfolio,
        start_date=start_date,
        end_date=end_date,
    )
    bt_scorecard = evaluate_strategy_scorecard(
        strategy_name="ParityStrategy",
        metrics=bt_metrics,
    )

    # 2. Mode B: Build paper trading PaperRepository state from fixture
    repo = PaperRepository()
    account = PaperAccount(
        account_id="parity-acc",
        name="Parity Forward Test",
        initial_capital=initial_capital,
        cash_balance=equity_points[-1].cash,
        realized_pnl=equity_points[-1].realized_pnl,
        unrealized_pnl=equity_points[-1].unrealized_pnl,
    )
    repo.save_account(account)

    for t in data["trades"]:
        side_p = PaperOrderSide.BUY if t["side"] == "BUY" else PaperOrderSide.SELL
        pf = PaperFill(
            fill_id=t["fill_id"],
            order_id=t["order_id"],
            account_id="parity-acc",
            symbol=t["symbol"],
            segment=t["segment"],
            security_id=t["security_id"],
            side=side_p,
            quantity=t["quantity"],
            price=t["price"],
            slippage=t["slippage"],
            transaction_cost=t["transaction_cost"],
            timestamp=datetime.fromisoformat(t["timestamp"]),
        )
        repo.save_fill(pf)

    for p in positions_map.values():
        pp = PaperPosition(
            position_id=f"pos-{p.security_id}",
            account_id="parity-acc",
            symbol=p.security_id,
            segment=p.exchange_segment,
            security_id=p.security_id,
            quantity=p.quantity,
            avg_entry_price=p.average_price,
            current_price=p.current_price,
            realized_pnl=p.realized_pnl,
            unrealized_pnl=p.unrealized_pnl,
        )
        repo.save_position(pp)

    for ep in equity_points:
        repo.record_equity_point("parity-acc", ep)

    paper_metrics = calculate_paper_metrics(
        account_id="parity-acc",
        repository=repo,
        start_date=start_date,
        end_date=end_date,
    )
    paper_scorecard = evaluate_paper_scorecard(
        account_id="parity-acc",
        strategy_name="ParityStrategy",
        repository=repo,
        start_date=start_date,
        end_date=end_date,
    )

    # 3. Exact Parity Assertions
    # Return & Risk Parity
    assert paper_metrics.initial_capital == bt_metrics.initial_capital
    assert paper_metrics.final_equity == bt_metrics.final_equity
    assert paper_metrics.total_return_pct == bt_metrics.total_return_pct
    assert paper_metrics.cagr_pct == bt_metrics.cagr_pct
    assert paper_metrics.total_pnl == bt_metrics.total_pnl
    assert paper_metrics.total_costs == bt_metrics.total_costs
    assert paper_metrics.realized_pnl == bt_metrics.realized_pnl
    assert paper_metrics.unrealized_pnl == bt_metrics.unrealized_pnl
    assert paper_metrics.max_drawdown_pct == bt_metrics.max_drawdown_pct
    assert paper_metrics.max_drawdown_value == bt_metrics.max_drawdown_value
    assert paper_metrics.sharpe_ratio == bt_metrics.sharpe_ratio
    assert paper_metrics.sortino_ratio == bt_metrics.sortino_ratio
    assert paper_metrics.calmar_ratio == bt_metrics.calmar_ratio

    # Trade Statistics Parity
    assert paper_metrics.total_trades == bt_metrics.total_trades
    assert paper_metrics.winning_trades == bt_metrics.winning_trades
    assert paper_metrics.losing_trades == bt_metrics.losing_trades
    assert paper_metrics.win_rate_pct == bt_metrics.win_rate_pct
    assert paper_metrics.profit_factor == bt_metrics.profit_factor

    # Scorecard & Deployment Gate Parity
    assert paper_scorecard.strategy_name == bt_scorecard.strategy_name
    assert paper_scorecard.overall_score == bt_scorecard.overall_score
    assert paper_scorecard.overall_grade == bt_scorecard.overall_grade
    assert paper_scorecard.verdict == bt_scorecard.verdict
    assert len(paper_scorecard.metric_scores) == len(bt_scorecard.metric_scores)
    assert len(paper_scorecard.deployment_gates) == len(bt_scorecard.deployment_gates)

    for p_gate, b_gate in zip(
        paper_scorecard.deployment_gates, bt_scorecard.deployment_gates, strict=True
    ):
        assert p_gate.gate_name == b_gate.gate_name
        assert p_gate.passed == b_gate.passed


def test_paper_metrics_zero_trades_and_boundary_conditions() -> None:
    """Proof: Account with zero fills computes metrics safely without division by zero."""
    repo = PaperRepository()
    repo.get_or_create_account("empty-acc", initial_capital=500000.0)

    metrics = calculate_paper_metrics("empty-acc", repository=repo)
    assert metrics.initial_capital == 500000.0
    assert metrics.total_trades == 0
    assert metrics.total_return_pct == 0.0
    assert metrics.win_rate_pct == 0.0
    assert metrics.profit_factor == 1.0

    scorecard = evaluate_paper_scorecard(
        "empty-acc",
        strategy_name="EmptyPaper",
        repository=repo,
    )
    assert scorecard.strategy_name == "EmptyPaper"
    assert scorecard.verdict in ("INVESTIGATE", "REJECT")


def test_paper_account_to_portfolio_structure() -> None:
    """Verify paper_account_to_portfolio accurately reconstructs canonical contracts."""
    repo = PaperRepository()
    repo.get_or_create_account("acc-struct", initial_capital=200000.0)

    fill = PaperFill(
        fill_id="f-101",
        order_id="o-101",
        account_id="acc-struct",
        symbol="SBIN",
        security_id="3045",
        side=PaperOrderSide.BUY,
        quantity=50,
        price=800.0,
        slippage=0.25,
        transaction_cost=15.0,
    )
    repo.save_fill(fill)

    pos = PaperPosition(
        position_id="p-101",
        account_id="acc-struct",
        symbol="SBIN",
        security_id="3045",
        quantity=50,
        avg_entry_price=800.0,
        current_price=820.0,
        realized_pnl=0.0,
        unrealized_pnl=1000.0,
    )
    repo.save_position(pos)

    portfolio = paper_account_to_portfolio("acc-struct", repository=repo)
    assert portfolio.initial_cash == 200000.0
    assert len(portfolio.fills) == 1
    assert portfolio.fills[0].order_id == "o-101"
    assert portfolio.fills[0].side == OrderSide.BUY
    assert portfolio.fills[0].total_cost == 15.25
    assert "3045" in portfolio.positions
    assert portfolio.positions["3045"].quantity == 50
    assert portfolio.positions["3045"].unrealized_pnl == 1000.0


def test_paper_metrics_and_scorecard_api_endpoints() -> None:
    """Verify /api/v1/paper/metrics and /api/v1/paper/scorecard endpoints."""
    paper_repository.clear()
    acc = paper_repository.get_or_create_account("api-paper-acc", initial_capital=1000000.0)
    acc.cash_balance = 980000.0
    acc.realized_pnl = 15000.0
    acc.unrealized_pnl = 5000.0
    paper_repository.save_account(acc)

    fill = PaperFill(
        fill_id="f-api-1",
        order_id="o-api-1",
        account_id="api-paper-acc",
        symbol="TCS",
        security_id="11536",
        side=PaperOrderSide.BUY,
        quantity=20,
        price=3500.0,
        slippage=0.0,
        transaction_cost=25.0,
    )
    paper_repository.save_fill(fill)

    # 1. Query Metrics Endpoint
    resp_metrics = client.get("/api/v1/paper/metrics?account_id=api-paper-acc")
    assert resp_metrics.status_code == 200
    m_data = resp_metrics.json()
    assert m_data["initial_capital"] == 1000000.0
    assert m_data["total_trades"] == 1
    assert "sharpe_ratio" in m_data
    assert "max_drawdown_pct" in m_data

    # 2. Query Scorecard Endpoint
    resp_scorecard = client.get(
        "/api/v1/paper/scorecard?account_id=api-paper-acc&strategy_name=TestForward"
    )
    assert resp_scorecard.status_code == 200
    sc_data = resp_scorecard.json()
    assert sc_data["strategy_name"] == "TestForward"
    assert "overall_grade" in sc_data
    assert "overall_score" in sc_data
    assert "verdict" in sc_data
    assert len(sc_data["deployment_gates"]) > 0
