"""FastAPI Router for Feature 4: Multi-Variant Engine, Condition Library & Live Tradebook."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Annotated, Any

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import delete, insert, select, update
from sqlalchemy.engine import Engine

from app.contracts import heartbeat as hb
from app.engine.multi_variant_loop import MultiVariantSimulator
from app.engine.variant_models import (
    LibraryConditionCreate,
    LibraryConditionRecord,
    LibraryConditionUpdate,
    LiveTradebookCreate,
    LiveTradebookRecord,
    MultiVariantRunRequest,
    MultiVariantRunResponse,
    VixHeatmapResponse,
    live_tradebook_table,
    variant_library_table,
    variant_runs_table,
    variant_trades_table,
)
from app.engine.vix_analytics import generate_vix_iv_heatmap
from app.strategy.models import strategy_configs_table

router = APIRouter(prefix="/api/v1", tags=["Multi-Variant Engine & Live Tradebook"])


def get_db_engine() -> Engine:
    """Dependency providing a connected SQLAlchemy Engine."""
    return hb.make_engine()


DbEngineDep = Annotated[Engine, Depends(get_db_engine)]

# Built-in Seed Conditions for the Reusable Library
BUILTIN_SEEDS = [
    {
        "name": "Multi-Target Partial Exit (50/50)",
        "description": (
            "Exits 50% lots at Target 1 (+30%), moves SL to Breakeven, "
            "exits remainder at Target 2 (+60%)"
        ),
        "category": "PARTIAL_EXIT",
        "condition_config": {
            "target_1": 30.0,
            "target_2": 60.0,
            "exit_lots_pct_1": 50.0,
            "exit_lots_pct_2": 50.0,
            "move_sl_to_be": True,
        },
        "is_built_in": True,
    },
    {
        "name": "Trailing Stop-Loss on Premium",
        "description": "Activates trailing stop-loss after Target 1 with a 10% premium step",
        "category": "TRAILING_SL",
        "condition_config": {"trail_step_pct": 10.0, "trail_after_target": 1},
        "is_built_in": True,
    },
    {
        "name": "Spot VWAP Level Stop-Loss",
        "description": "Exits position immediately if underlying spot price crosses below VWAP",
        "category": "SL_VARIANT",
        "condition_config": {"reference": "SPOT", "indicator": "VWAP", "operator": "crosses_below"},
        "is_built_in": True,
    },
    {
        "name": "Aggressive Tight Stop-Loss (10%)",
        "description": "Tighter 10% stop-loss for high-volatility event days",
        "category": "SL_VARIANT",
        "condition_config": {"sl_pct": 10.0},
        "is_built_in": True,
    },
]


def _seed_builtins_if_empty(engine: Engine) -> None:
    """Auto-seed built-in tracking conditions if library is fresh."""
    with engine.begin() as conn:
        count = conn.execute(select(variant_library_table.c.id).limit(1)).first()
        if not count:
            now = datetime.now(UTC)
            for seed in BUILTIN_SEEDS:
                conn.execute(
                    insert(variant_library_table).values(
                        name=seed["name"],
                        description=seed["description"],
                        category=seed["category"],
                        condition_config=seed["condition_config"],
                        is_built_in=True,
                        created_at=now,
                        updated_at=now,
                    )
                )


# --- 1. Reusable Tracking Condition Library Endpoints ---


@router.get(
    "/variant/library",
    response_model=list[LibraryConditionRecord],
    summary="List Library Conditions",
)
def list_library_conditions(
    engine: DbEngineDep,
    category: str | None = Query(None, description="Filter by condition category"),
) -> list[LibraryConditionRecord]:
    """Retrieve all saved & built-in tracking conditions from library."""
    _seed_builtins_if_empty(engine)
    query = select(variant_library_table).order_by(variant_library_table.c.id.asc())
    if category:
        query = query.where(variant_library_table.c.category == category.upper())

    with engine.connect() as conn:
        rows = conn.execute(query).mappings().all()

    return [LibraryConditionRecord.model_validate(dict(r)) for r in rows]


@router.post(
    "/variant/library",
    response_model=LibraryConditionRecord,
    status_code=201,
    summary="Create Condition",
)
def create_library_condition(
    engine: DbEngineDep,
    payload: LibraryConditionCreate,
) -> LibraryConditionRecord:
    """Save a new custom tracking condition to the library for future use."""
    now = datetime.now(UTC)
    with engine.begin() as conn:
        res = conn.execute(
            insert(variant_library_table).values(
                name=payload.name,
                description=payload.description,
                category=payload.category,
                condition_config=payload.condition_config,
                is_built_in=payload.is_built_in,
                created_at=now,
                updated_at=now,
            )
        )
        cond_id = res.inserted_primary_key[0]  # type: ignore[index]
        row = (
            conn.execute(select(variant_library_table).where(variant_library_table.c.id == cond_id))
            .mappings()
            .first()
        )

    if not row:
        raise HTTPException(status_code=500, detail="Failed to create library condition")
    return LibraryConditionRecord.model_validate(dict(row))


@router.put(
    "/variant/library/{id}", response_model=LibraryConditionRecord, summary="Update Condition"
)
def update_library_condition(
    id: int,
    engine: DbEngineDep,
    payload: LibraryConditionUpdate,
) -> LibraryConditionRecord:
    """Update an existing library tracking condition."""
    now = datetime.now(UTC)
    with engine.begin() as conn:
        existing = (
            conn.execute(select(variant_library_table).where(variant_library_table.c.id == id))
            .mappings()
            .first()
        )

        if not existing:
            raise HTTPException(status_code=404, detail=f"Condition {id} not found")

        update_values: dict[str, Any] = {"updated_at": now}
        if payload.name is not None:
            update_values["name"] = payload.name
        if payload.description is not None:
            update_values["description"] = payload.description
        if payload.category is not None:
            update_values["category"] = payload.category
        if payload.condition_config is not None:
            update_values["condition_config"] = payload.condition_config

        conn.execute(
            update(variant_library_table)
            .where(variant_library_table.c.id == id)
            .values(**update_values)
        )

        row = (
            conn.execute(select(variant_library_table).where(variant_library_table.c.id == id))
            .mappings()
            .first()
        )

    if not row:
        raise HTTPException(status_code=500, detail="Failed to update condition")
    return LibraryConditionRecord.model_validate(dict(row))


@router.delete("/variant/library/{id}", status_code=204, summary="Delete Condition")
def delete_library_condition(id: int, engine: DbEngineDep) -> None:
    """Delete a custom tracking condition from the library."""
    with engine.begin() as conn:
        res = conn.execute(delete(variant_library_table).where(variant_library_table.c.id == id))
        if res.rowcount == 0:
            raise HTTPException(status_code=404, detail=f"Condition {id} not found")


# --- 2. Multi-Variant Run Execution Endpoints ---


def _generate_synthetic_market_candles(n: int = 150) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Generate sample Spot and Option OHLCV data for backtest execution."""
    base_time = datetime(2026, 9, 1, 9, 15, tzinfo=UTC)
    spot_rows = []
    opt_rows = []
    spot_price = 24500.0
    opt_price = 150.0

    for idx in range(n):
        dt = base_time + timedelta(minutes=idx)
        # Create an intentional Open == High trigger pattern at index 20
        if idx == 20:
            s_open = spot_price
            s_high = s_open
            s_low = s_open - 30.0
            s_close = s_open - 25.0
            o_open = opt_price
            o_high = o_open + 25.0
            o_low = o_open - 5.0
            o_close = o_open + 20.0
        else:
            s_open = spot_price
            s_high = s_open + 15.0
            s_low = s_open - 10.0
            s_close = s_open + 5.0
            o_open = opt_price
            o_high = o_open + 8.0
            o_low = o_open - 6.0
            o_close = o_open + 2.0

        spot_rows.append(
            {
                "datetime_ist": dt,
                "open": s_open,
                "high": s_high,
                "low": s_low,
                "close": s_close,
                "volume": 50000 + idx * 100,
            }
        )
        opt_rows.append(
            {
                "datetime_ist": dt,
                "open": o_open,
                "high": o_high,
                "low": o_low,
                "close": o_close,
                "volume": 20000 + idx * 50,
            }
        )
        spot_price = s_close
        opt_price = o_close

    return pd.DataFrame(spot_rows), pd.DataFrame(opt_rows)


@router.post(
    "/variant/run", response_model=MultiVariantRunResponse, summary="Execute Multi-Variant Run"
)
def run_multi_variant_backtest(
    engine: DbEngineDep,
    payload: MultiVariantRunRequest,
) -> MultiVariantRunResponse:
    """Execute single-pass multi-variant backtest with entry/exit volatility snapshots."""
    # 1. Fetch Strategy Config
    with engine.connect() as conn:
        strat_row = (
            conn.execute(
                select(strategy_configs_table).where(
                    strategy_configs_table.c.id == payload.strategy_id
                )
            )
            .mappings()
            .first()
        )

    if not strat_row:
        raise HTTPException(status_code=404, detail=f"Strategy {payload.strategy_id} not found")

    strat_config = dict(strat_row["config_json"])
    strat_name = str(strat_row["name"])

    # 2. Generate / Fetch Market Candles
    spot_df, opt_df = _generate_synthetic_market_candles()

    # 3. Execute MultiVariantSimulator
    simulator = MultiVariantSimulator()
    rankings, trades = simulator.run_simulation(
        strategy_config=strat_config,
        spot_candles=spot_df,
        option_candles=opt_df,
        selected_variations=payload.selected_variations,
        initial_capital=payload.capital,
    )

    # 4. Persist run & trades
    now = datetime.now(UTC)
    with engine.begin() as conn:
        res = conn.execute(
            insert(variant_runs_table).values(
                strategy_id=payload.strategy_id,
                run_name=payload.run_name,
                run_type="BACKTEST",
                start_time=now - timedelta(days=30),
                end_time=now,
                total_signals=len(trades) // max(1, len(rankings)),
                total_variants_run=len(rankings),
                created_at=now,
            )
        )
        run_id = res.inserted_primary_key[0]  # type: ignore[index]

        for t in trades:
            conn.execute(
                insert(variant_trades_table).values(
                    run_id=run_id,
                    variant_name=t.variant_name,
                    symbol=t.symbol,
                    signal_type=t.signal_type,
                    entry_time=t.entry_time,
                    entry_spot_price=t.entry_spot_price,
                    entry_option_price=t.entry_option_price,
                    entry_india_vix=t.entry_india_vix,
                    entry_option_iv=t.entry_option_iv,
                    entry_delta=t.entry_delta,
                    entry_gamma=t.entry_gamma,
                    entry_theta=t.entry_theta,
                    entry_vega=t.entry_vega,
                    exit_time=t.exit_time,
                    exit_spot_price=t.exit_spot_price,
                    exit_option_price=t.exit_option_price,
                    exit_india_vix=t.exit_india_vix,
                    exit_option_iv=t.exit_option_iv,
                    vix_change=t.vix_change,
                    iv_change=t.iv_change,
                    exit_reason=t.exit_reason,
                    quantity=t.quantity,
                    realized_pnl=t.realized_pnl,
                    max_favorable_excursion=t.max_favorable_excursion,
                    max_adverse_excursion=t.max_adverse_excursion,
                )
            )

    return MultiVariantRunResponse(
        run_id=run_id,
        strategy_id=payload.strategy_id,
        strategy_name=strat_name,
        total_signals=len(trades) // max(1, len(rankings)),
        total_variants_run=len(rankings),
        rankings=rankings,
        trades=trades,
    )


# --- 3. Volatility Regime Heatmap Analytics ---


@router.get(
    "/variant/analytics/vix-heatmap",
    response_model=VixHeatmapResponse,
    summary="Get VIX/IV Heatmap",
)
def get_vix_heatmap(engine: DbEngineDep) -> VixHeatmapResponse:
    """Generate PnL & Win Rate performance heatmaps grouped by VIX and IV range."""
    with engine.connect() as conn:
        rows = conn.execute(select(variant_trades_table)).mappings().all()

    trades_list = [dict(r) for r in rows]
    return generate_vix_iv_heatmap(trades_list)


# --- 4. Live Real-Money & Shadow Tradebook ---


@router.get(
    "/tradebook/live", response_model=list[LiveTradebookRecord], summary="List Live Tradebook"
)
def list_live_tradebook(
    engine: DbEngineDep,
    strategy_id: int | None = Query(None, description="Filter by strategy"),
) -> list[LiveTradebookRecord]:
    """Retrieve real-money & shadow executed trades from the live tradebook."""
    query = select(live_tradebook_table).order_by(live_tradebook_table.c.trade_id.desc())
    if strategy_id is not None:
        query = query.where(live_tradebook_table.c.strategy_id == strategy_id)

    with engine.connect() as conn:
        rows = conn.execute(query).mappings().all()

    return [LiveTradebookRecord.model_validate(dict(r)) for r in rows]


@router.post(
    "/tradebook/live", response_model=LiveTradebookRecord, status_code=201, summary="Log Live Trade"
)
def log_live_trade(
    engine: DbEngineDep,
    payload: LiveTradebookCreate,
) -> LiveTradebookRecord:
    """Log an executed order from Dhan API into the live tradebook."""
    now = datetime.now(UTC)
    with engine.begin() as conn:
        res = conn.execute(
            insert(live_tradebook_table).values(
                dhan_order_id=payload.dhan_order_id,
                strategy_id=payload.strategy_id,
                symbol=payload.symbol,
                signal_type=payload.signal_type,
                fill_time=payload.fill_time,
                buy_price=payload.buy_price,
                sell_price=payload.sell_price,
                quantity=payload.quantity,
                entry_vix=payload.entry_vix,
                exit_vix=payload.exit_vix,
                entry_iv=payload.entry_iv,
                exit_iv=payload.exit_iv,
                exit_reason=payload.exit_reason,
                realized_pnl=payload.realized_pnl,
                brokerage_charges=payload.brokerage_charges,
                stt_taxes=payload.stt_taxes,
                slippage_amount=payload.slippage_amount,
                created_at=now,
            )
        )
        trade_id = res.inserted_primary_key[0]  # type: ignore[index]
        row = (
            conn.execute(
                select(live_tradebook_table).where(live_tradebook_table.c.trade_id == trade_id)
            )
            .mappings()
            .first()
        )

    if not row:
        raise HTTPException(status_code=500, detail="Failed to log live trade")
    return LiveTradebookRecord.model_validate(dict(row))
