"""Unit tests for engine contracts, clocks, data sources, and state recovery."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.engine.contracts import (
    EngineCheckpoint,
    FillEvent,
    HistoricalDataSource,
    OrderSide,
    Portfolio,
    SimClock,
)
from app.warehouse.schema import BarRecord


def _make_bar(sec_id: str, ts: datetime, close: float) -> BarRecord:
    return BarRecord(
        symbol=sec_id,
        exchange_segment="NSE_EQ",
        security_id=sec_id,
        timestamp=ts,
        open=close - 1.0,
        high=close + 2.0,
        low=close - 2.0,
        close=close,
        volume=1000,
        open_interest=0,
    )


def test_sim_clock_advancement_and_state_recovery() -> None:
    """Test SimClock discrete step advance, completion detection, and checkpoint restoration."""
    t0 = datetime(2026, 9, 1, 9, 15, tzinfo=UTC)
    timestamps = [t0 + timedelta(minutes=i) for i in range(5)]

    clock = SimClock(timestamps)
    assert clock.now() == timestamps[0]
    assert not clock.is_done()

    clock.step()
    clock.step()
    assert clock.now() == timestamps[2]

    # Checkpoint and restore
    state = clock.get_state()
    restored_clock = SimClock.restore_state(state)
    assert restored_clock.now() == timestamps[2]

    restored_clock.step()
    assert restored_clock.now() == timestamps[3]
    restored_clock.step()
    assert restored_clock.now() == timestamps[4]
    assert restored_clock.is_done()
    assert restored_clock.step() is None


def test_historical_datasource_playback_and_no_lookahead() -> None:
    """Test HistoricalDataSource chronological emission and zero future lookahead."""
    t0 = datetime(2026, 9, 1, 9, 15, tzinfo=UTC)
    bars = [
        _make_bar("SEC1", t0, 100.0),
        _make_bar("SEC2", t0, 200.0),
        _make_bar("SEC1", t0 + timedelta(minutes=1), 101.0),
        _make_bar("SEC2", t0 + timedelta(minutes=1), 202.0),
        _make_bar("SEC1", t0 + timedelta(minutes=2), 102.0),
    ]

    source = HistoricalDataSource(bars)

    # Advance to t0
    emitted_0 = source.advance(t0)
    assert len(emitted_0) == 2
    sec_ids = {b.security_id for b in emitted_0}
    assert sec_ids == {"SEC1", "SEC2"}

    # Historical lookup strictly <= t0
    hist = source.get_history("SEC1", until=t0, count=5)
    assert len(hist) == 1
    assert hist[0].close == 100.0

    # Advance to t0 + 1m
    emitted_1 = source.advance(t0 + timedelta(minutes=1))
    assert len(emitted_1) == 2

    # Checkpoint and restore
    ds_state = source.get_state()
    new_source = HistoricalDataSource(bars)
    new_source.restore_state(ds_state)

    # Advance to t0 + 2m
    emitted_2 = new_source.advance(t0 + timedelta(minutes=2))
    assert len(emitted_2) == 1
    assert emitted_2[0].security_id == "SEC1"
    assert emitted_2[0].close == 102.0


def test_portfolio_state_machine_long_short_and_flip() -> None:
    """Test Portfolio accounting through Long entry, partial exit, reversal to Short, and cover."""
    t0 = datetime(2026, 9, 1, 9, 15, tzinfo=UTC)
    portfolio = Portfolio.create(initial_cash=100_000.0)

    # 1. Buy 100 @ 100 (Brokerage = 20.0)
    f1 = FillEvent(
        order_id="o1",
        security_id="RELIANCE",
        exchange_segment="NSE_EQ",
        side=OrderSide.BUY,
        quantity=100,
        price=100.0,
        timestamp=t0,
        brokerage=20.0,
    )
    portfolio.apply_fill(f1)
    pos = portfolio.positions["RELIANCE"]
    assert pos.quantity == 100
    assert pos.average_price == 100.0
    assert portfolio.cash == 100_000.0 - (100 * 100.0 + 20.0)

    # 2. Sell 50 @ 110 (Partial exit, profit = 50 * 10 = 500)
    f2 = FillEvent(
        order_id="o2",
        security_id="RELIANCE",
        exchange_segment="NSE_EQ",
        side=OrderSide.SELL,
        quantity=50,
        price=110.0,
        timestamp=t0 + timedelta(minutes=1),
        brokerage=20.0,
    )
    portfolio.apply_fill(f2)
    assert pos.quantity == 50
    assert pos.average_price == 100.0
    assert pos.realized_pnl == 500.0

    # 3. Sell 100 @ 120 (Reversal to Short 50: closes 50 long @ +20/sh, opens 50 short @ 120)
    f3 = FillEvent(
        order_id="o3",
        security_id="RELIANCE",
        exchange_segment="NSE_EQ",
        side=OrderSide.SELL,
        quantity=100,
        price=120.0,
        timestamp=t0 + timedelta(minutes=2),
        brokerage=20.0,
    )
    portfolio.apply_fill(f3)
    assert pos.quantity == -50
    assert pos.average_price == 120.0
    assert pos.realized_pnl == 500.0 + (50 * 20.0)  # 1500.0

    # 4. Mark to Market @ 115 (Unrealized gain on short of 50 * (120 - 115) = 250)
    eq = portfolio.mark_to_market({"RELIANCE": 115.0}, timestamp=t0 + timedelta(minutes=3))
    assert pos.unrealized_pnl == 250.0
    # Expected Equity = 100,000 + 1500 (realized) + 250 (unrealized) - 60 (costs) = 101,690
    assert eq == 101_690.0

    # 5. Buy 50 @ 115 (Cover Short completely, realized gain = 50 * 5 = 250)
    f4 = FillEvent(
        order_id="o4",
        security_id="RELIANCE",
        exchange_segment="NSE_EQ",
        side=OrderSide.BUY,
        quantity=50,
        price=115.0,
        timestamp=t0 + timedelta(minutes=4),
        brokerage=20.0,
    )
    portfolio.apply_fill(f4)
    assert pos.quantity == 0
    assert pos.average_price == 0.0
    assert pos.realized_pnl == 1750.0

    final_eq = portfolio.mark_to_market({"RELIANCE": 115.0}, timestamp=t0 + timedelta(minutes=5))
    # Final Equity = 100,000 + 1750 (realized) - 80 (costs) = 101,670
    assert final_eq == 101_670.0


def test_checkpoint_restore_state_machine_equivalence() -> None:
    """State-machine test: resuming from checkpoint produces identical portfolio result."""
    t0 = datetime(2026, 9, 1, 9, 15, tzinfo=UTC)
    timestamps = [t0 + timedelta(minutes=i) for i in range(10)]
    bars = [_make_bar("TCS", ts, 3000.0 + i * 10.0) for i, ts in enumerate(timestamps)]

    def run_simulation(
        start_step: int,
        clock: SimClock,
        datasource: HistoricalDataSource,
        portfolio: Portfolio,
    ) -> None:
        for step in range(start_step, len(timestamps)):
            now = clock.now()
            current_bars = datasource.advance(now)
            for bar in current_bars:
                # Deterministic trading rule: Buy on step 1, Sell on step 7
                if step == 1:
                    portfolio.apply_fill(
                        FillEvent(
                            order_id=f"o_{step}",
                            security_id=bar.security_id,
                            exchange_segment=bar.exchange_segment,
                            side=OrderSide.BUY,
                            quantity=10,
                            price=bar.close,
                            timestamp=now,
                            brokerage=20.0,
                        )
                    )
                elif step == 7:
                    portfolio.apply_fill(
                        FillEvent(
                            order_id=f"o_{step}",
                            security_id=bar.security_id,
                            exchange_segment=bar.exchange_segment,
                            side=OrderSide.SELL,
                            quantity=10,
                            price=bar.close,
                            timestamp=now,
                            brokerage=20.0,
                        )
                    )
                portfolio.mark_to_market({bar.security_id: bar.close}, now)
            if not clock.is_done():
                clock.step()

    # --- Run A: Uninterrupted continuous execution (steps 0 to 9) ---
    clock_a = SimClock(timestamps)
    source_a = HistoricalDataSource(bars)
    portfolio_a = Portfolio.create(initial_cash=500_000.0)
    run_simulation(0, clock_a, source_a, portfolio_a)

    # --- Run B: Interrupted at step 4, checkpointed, restored, and resumed (steps 4 to 9) ---
    clock_b = SimClock(timestamps)
    source_b = HistoricalDataSource(bars)
    portfolio_b = Portfolio.create(initial_cash=500_000.0)

    # Execute first 4 steps
    for step in range(4):
        now = clock_b.now()
        current_bars = source_b.advance(now)
        for bar in current_bars:
            if step == 1:
                portfolio_b.apply_fill(
                    FillEvent(
                        order_id=f"o_{step}",
                        security_id=bar.security_id,
                        exchange_segment=bar.exchange_segment,
                        side=OrderSide.BUY,
                        quantity=10,
                        price=bar.close,
                        timestamp=now,
                        brokerage=20.0,
                    )
                )
            portfolio_b.mark_to_market({bar.security_id: bar.close}, now)
        if not clock_b.is_done():
            clock_b.step()

    # Save Checkpoint at step 4
    checkpoint = EngineCheckpoint(
        timestamp=clock_b.now(),
        step_index=4,
        clock_state=clock_b.get_state(),
        datasource_state=source_b.get_state(),
        portfolio_state=portfolio_b.get_state(),
    )

    # Restore into fresh components
    restored_clock = SimClock.restore_state(checkpoint.clock_state)
    restored_source = HistoricalDataSource(bars)
    restored_source.restore_state(checkpoint.datasource_state)
    restored_portfolio = Portfolio.restore_state(checkpoint.portfolio_state)

    # Resume simulation from step 4 to end
    run_simulation(4, restored_clock, restored_source, restored_portfolio)

    # Assert exact state-machine equivalence
    assert portfolio_a.cash == restored_portfolio.cash
    assert portfolio_a.total_equity() == restored_portfolio.total_equity()
    assert len(portfolio_a.fills) == len(restored_portfolio.fills)
    assert len(portfolio_a.equity_curve) == len(restored_portfolio.equity_curve)

    for p_a, p_b in zip(portfolio_a.equity_curve, restored_portfolio.equity_curve, strict=True):
        assert p_a.equity == p_b.equity
        assert p_a.cash == p_b.cash
        assert p_a.realized_pnl == p_b.realized_pnl
