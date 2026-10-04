"""Create variant_library_conditions, variant_runs, variant_trades, and live_tradebook tables.

Revision ID: sb_variant_f4
Revises: f6a7b8c9d0e1
Create Date: 2026-10-03 08:05:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

# revision identifiers, used by Alembic.
revision: str = "sb_variant_f4"
down_revision: str | Sequence[str] | None = "f6a7b8c9d0e1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create variant tracking and live tradebook tables."""
    # 1. variant_library_conditions
    op.create_table(
        "variant_library_conditions",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("category", sa.Text(), nullable=False),
        sa.Column("condition_config", JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("is_built_in", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
    )
    op.create_index("ix_variant_lib_category", "variant_library_conditions", ["category"])

    # 2. variant_runs
    op.create_table(
        "variant_runs",
        sa.Column("run_id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "strategy_id",
            sa.Integer(),
            sa.ForeignKey("strategy_configs.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column("run_name", sa.Text(), nullable=False, server_default="Multi-Variant Run"),
        sa.Column("run_type", sa.Text(), nullable=False, server_default="BACKTEST"),
        sa.Column("start_time", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("end_time", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("total_signals", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_variants_run", sa.Integer(), nullable=False, server_default="1"),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
    )
    op.create_index("ix_variant_runs_strat", "variant_runs", ["strategy_id"])

    # 3. variant_trades
    op.create_table(
        "variant_trades",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "run_id",
            sa.Integer(),
            sa.ForeignKey("variant_runs.run_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("variant_name", sa.Text(), nullable=False),
        sa.Column("symbol", sa.Text(), nullable=False),
        sa.Column("signal_type", sa.Text(), nullable=False),
        sa.Column("entry_time", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("entry_spot_price", sa.Numeric(12, 4), nullable=True),
        sa.Column("entry_option_price", sa.Numeric(12, 4), nullable=True),
        sa.Column("entry_india_vix", sa.Numeric(6, 2), nullable=True),
        sa.Column("entry_option_iv", sa.Numeric(6, 2), nullable=True),
        sa.Column("entry_delta", sa.Numeric(6, 3), nullable=True),
        sa.Column("entry_gamma", sa.Numeric(6, 4), nullable=True),
        sa.Column("entry_theta", sa.Numeric(8, 2), nullable=True),
        sa.Column("entry_vega", sa.Numeric(8, 2), nullable=True),
        sa.Column("exit_time", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("exit_spot_price", sa.Numeric(12, 4), nullable=True),
        sa.Column("exit_option_price", sa.Numeric(12, 4), nullable=True),
        sa.Column("exit_india_vix", sa.Numeric(6, 2), nullable=True),
        sa.Column("exit_option_iv", sa.Numeric(6, 2), nullable=True),
        sa.Column("vix_change", sa.Numeric(6, 2), nullable=True),
        sa.Column("iv_change", sa.Numeric(6, 2), nullable=True),
        sa.Column("exit_reason", sa.Text(), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("realized_pnl", sa.Numeric(12, 2), nullable=False, server_default="0.00"),
        sa.Column("max_favorable_excursion", sa.Numeric(12, 4), nullable=True),
        sa.Column("max_adverse_excursion", sa.Numeric(12, 4), nullable=True),
    )
    op.create_index("ix_variant_trades_run_id", "variant_trades", ["run_id"])
    op.create_index("ix_variant_trades_variant", "variant_trades", ["variant_name"])

    # 4. live_tradebook
    op.create_table(
        "live_tradebook",
        sa.Column("trade_id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("dhan_order_id", sa.Text(), unique=True, nullable=False),
        sa.Column(
            "strategy_id",
            sa.Integer(),
            sa.ForeignKey("strategy_configs.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("symbol", sa.Text(), nullable=False),
        sa.Column("signal_type", sa.Text(), nullable=False),
        sa.Column("fill_time", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("buy_price", sa.Numeric(12, 4), nullable=False),
        sa.Column("sell_price", sa.Numeric(12, 4), nullable=True),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("entry_vix", sa.Numeric(6, 2), nullable=True),
        sa.Column("exit_vix", sa.Numeric(6, 2), nullable=True),
        sa.Column("entry_iv", sa.Numeric(6, 2), nullable=True),
        sa.Column("exit_iv", sa.Numeric(6, 2), nullable=True),
        sa.Column("exit_reason", sa.Text(), nullable=True),
        sa.Column("realized_pnl", sa.Numeric(12, 2), nullable=True),
        sa.Column("brokerage_charges", sa.Numeric(10, 2), nullable=False, server_default="0.00"),
        sa.Column("stt_taxes", sa.Numeric(10, 2), nullable=False, server_default="0.00"),
        sa.Column("slippage_amount", sa.Numeric(10, 2), nullable=False, server_default="0.00"),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
    )
    op.create_index("ix_live_tradebook_strat", "live_tradebook", ["strategy_id"])


def downgrade() -> None:
    """Drop variant and tradebook tables."""
    op.drop_table("live_tradebook")
    op.drop_table("variant_trades")
    op.drop_table("variant_runs")
    op.drop_table("variant_library_conditions")
