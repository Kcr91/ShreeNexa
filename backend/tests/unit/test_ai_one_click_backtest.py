"""Unit tests for F5.4: One-click backtest from approved generated draft with parity proof."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from app.ai.generator import generate_strategy_ir_from_prompt
from app.api.ai import compute_ir_hash
from app.backtest.models import AIGenerationMetadata, BacktestConfig
from app.backtest.runner import StockStrategyBacktestRunner
from app.backtest.store import backtest_store
from app.main import app
from app.strategy.ir import StrategyIR
from fastapi.testclient import TestClient

client = TestClient(app)


@pytest.fixture
def sample_strategy_ir() -> StrategyIR:
    prompt = (
        "Buy when 9 EMA crosses above 21 EMA on NIFTY 50 15m. Stop loss 1.5%, take profit 3.5%."
    )
    res = generate_strategy_ir_from_prompt(prompt)
    return res.strategy_ir


def test_proof_generated_run_equals_manual_run_parity(sample_strategy_ir: StrategyIR) -> None:
    """Proof invariant: Generated run equals a manual run with the same IR snapshot and config."""
    prompt = "Buy when 9 EMA crosses above 21 EMA on NIFTY 50 15m."
    now = datetime.now(tz=UTC)
    start_date = now - timedelta(days=60)
    end_date = now

    # 1. Manual run configuration (no AI metadata)
    manual_config = BacktestConfig(
        strategy=sample_strategy_ir,
        start_date=start_date,
        end_date=end_date,
        initial_cash=1_000_000.0,
        ai_metadata=None,
    )

    # 2. Generated run configuration (with AI metadata)
    ir_dict = sample_strategy_ir.to_dict()
    ir_hash = compute_ir_hash(ir_dict)
    ai_meta = AIGenerationMetadata(
        prompt=prompt,
        provider_name="default-ai",
        model_version="1.0.0",
        ir_version=sample_strategy_ir.ir_version,
        ir_hash=ir_hash,
        generated_at=now,
        approved_at=now,
        draft_status="APPROVED_DRAFT",
    )
    generated_config = BacktestConfig(
        strategy=sample_strategy_ir,
        start_date=start_date,
        end_date=end_date,
        initial_cash=1_000_000.0,
        ai_metadata=ai_meta,
    )

    runner = StockStrategyBacktestRunner()
    manual_result = runner.run(manual_config)
    generated_result = runner.run(generated_config)

    # Invariant assertions:
    # A. Performance metrics equality
    assert generated_result.metrics.total_return_pct == manual_result.metrics.total_return_pct
    assert generated_result.metrics.win_rate_pct == manual_result.metrics.win_rate_pct
    assert generated_result.metrics.max_drawdown_pct == manual_result.metrics.max_drawdown_pct
    assert generated_result.metrics.total_trades == manual_result.metrics.total_trades
    assert generated_result.metrics.sharpe_ratio == manual_result.metrics.sharpe_ratio
    assert generated_result.metrics.cagr_pct == manual_result.metrics.cagr_pct

    # B. Trades & Equity Curve parity
    assert len(generated_result.trades) == len(manual_result.trades)
    assert len(generated_result.equity_curve) == len(manual_result.equity_curve)

    # C. Metadata audit preservation
    assert manual_result.ai_metadata is None
    assert generated_result.ai_metadata is not None
    assert generated_result.ai_metadata.prompt == prompt
    assert generated_result.ai_metadata.provider_name == "default-ai"
    assert generated_result.ai_metadata.ir_hash == ir_hash
    assert generated_result.ai_metadata.draft_status == "APPROVED_DRAFT"


def test_proof_generated_run_equals_manual_run_with_bars_parity(
    sample_strategy_ir: StrategyIR,
) -> None:
    """Proof invariant: Parity holds with actual trade execution and active simulated bars."""
    from app.strategy.ir import StaticUniverse
    from app.warehouse.schema import BarRecord

    if not isinstance(sample_strategy_ir.universe, StaticUniverse):
        return

    sec_id = sample_strategy_ir.universe.instruments[0].security_id
    now = datetime(2026, 1, 1, 9, 15, tzinfo=UTC)
    bars: list[BarRecord] = []

    price = 100.0
    for i in range(100):
        # Create alternating price cycle to trigger EMA crossovers
        delta = 1.5 if (i // 10) % 2 == 0 else -1.5
        price += delta
        ts = now + timedelta(minutes=15 * i)
        bars.append(
            BarRecord(
                timestamp=ts,
                open=price - 0.5,
                high=price + 1.0,
                low=price - 1.0,
                close=price,
                volume=10_000,
                exchange_segment="NSE_EQ",
                security_id=sec_id,
                symbol="NIFTY",
            )
        )

    start_date = bars[0].timestamp
    end_date = bars[-1].timestamp
    bars_dataset = {sec_id: bars}

    manual_config = BacktestConfig(
        strategy=sample_strategy_ir,
        start_date=start_date,
        end_date=end_date,
        initial_cash=1_000_000.0,
        ai_metadata=None,
    )

    prompt = "Crossover test prompt"
    ir_hash = compute_ir_hash(sample_strategy_ir.to_dict())
    ai_meta = AIGenerationMetadata(
        prompt=prompt,
        provider_name="claude-3-7-sonnet",
        model_version="1.0.0",
        ir_version=sample_strategy_ir.ir_version,
        ir_hash=ir_hash,
        generated_at=now,
        approved_at=now,
        draft_status="APPROVED_DRAFT",
    )
    generated_config = BacktestConfig(
        strategy=sample_strategy_ir,
        start_date=start_date,
        end_date=end_date,
        initial_cash=1_000_000.0,
        ai_metadata=ai_meta,
    )

    runner = StockStrategyBacktestRunner()
    manual_result = runner.run(manual_config, bars_dataset=bars_dataset)
    generated_result = runner.run(generated_config, bars_dataset=bars_dataset)

    # Assert exact parity
    assert generated_result.metrics.total_return_pct == manual_result.metrics.total_return_pct
    assert generated_result.metrics.win_rate_pct == manual_result.metrics.win_rate_pct
    assert generated_result.metrics.max_drawdown_pct == manual_result.metrics.max_drawdown_pct
    assert generated_result.metrics.total_trades == manual_result.metrics.total_trades
    assert len(generated_result.trades) == len(manual_result.trades)
    assert len(generated_result.equity_curve) == len(manual_result.equity_curve)

    # Metadata audit trail
    assert manual_result.ai_metadata is None
    assert generated_result.ai_metadata is not None
    assert generated_result.ai_metadata.prompt == prompt
    assert generated_result.ai_metadata.provider_name == "claude-3-7-sonnet"
    assert generated_result.ai_metadata.ir_hash == ir_hash


def test_api_one_click_backtest_endpoint_success(sample_strategy_ir: StrategyIR) -> None:
    """Verify POST /api/v1/ai/backtest-draft executes and persists with AI metadata."""
    prompt = "Momentum breakout on NIFTY 50"
    payload = {
        "strategy_ir": sample_strategy_ir.to_dict(),
        "prompt": prompt,
        "provider_name": "gemini-2.5-flash",
        "model_version": "2.5.0",
        "initial_cash": 500_000.0,
    }

    response = client.post("/api/v1/ai/backtest-draft", json=payload)
    assert response.status_code == 201

    data = response.json()
    assert "backtest_id" in data
    assert "result" in data
    assert "ai_metadata" in data

    ai_meta = data["ai_metadata"]
    assert ai_meta["prompt"] == prompt
    assert ai_meta["provider_name"] == "gemini-2.5-flash"
    assert ai_meta["model_version"] == "2.5.0"
    assert ai_meta["draft_status"] == "APPROVED_DRAFT"
    assert len(ai_meta["ir_hash"]) == 64  # SHA-256 length

    # Verify persistence in durable backtest store
    saved = backtest_store.get_result(data["backtest_id"])
    assert saved is not None
    assert saved.backtest_id == data["backtest_id"]
    assert saved.ai_metadata is not None
    assert saved.ai_metadata.ir_hash == ai_meta["ir_hash"]


def test_api_one_click_backtest_invalid_schema() -> None:
    """Verify POST /api/v1/ai/backtest-draft rejects malformed StrategyIR with HTTP 422."""
    payload = {
        "strategy_ir": {"ir_version": 999, "invalid": True},
        "prompt": "Invalid prompt",
    }
    response = client.post("/api/v1/ai/backtest-draft", json=payload)
    assert response.status_code == 422
    assert "Invalid StrategyIR schema" in response.json()["detail"]
