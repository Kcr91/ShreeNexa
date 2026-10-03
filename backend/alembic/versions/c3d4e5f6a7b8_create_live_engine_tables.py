"""create live engine tables

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-10-03 08:30:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "c3d4e5f6a7b8"
down_revision: str | None = "b2c3d4e5f6a7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. Live Risk Settings Table
    op.create_table(
        "live_risk_settings",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("max_daily_loss_pct", sa.Numeric(5, 2), nullable=False, server_default="3.00"),
        sa.Column(
            "max_trade_exposure_pct", sa.Numeric(5, 2), nullable=False, server_default="10.00"
        ),
        sa.Column("max_concurrent_trades", sa.Integer(), nullable=False, server_default="5"),
        sa.Column("circuit_buffer_pct", sa.Numeric(5, 2), nullable=False, server_default="0.50"),
        sa.Column(
            "kill_switch_active", sa.Boolean(), nullable=False, server_default=sa.text("false")
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )

    # 2. Live Real-Money Tradebook Table
    op.create_table(
        "live_tradebook",
        sa.Column("trade_id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("dhan_order_id", sa.String(length=100), unique=True, nullable=False),
        sa.Column(
            "strategy_id",
            sa.Integer(),
            sa.ForeignKey("strategy_configs.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column("symbol", sa.String(length=50), nullable=False),
        sa.Column("signal_type", sa.String(length=20), nullable=False),
        sa.Column("fill_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("buy_price", sa.Numeric(12, 4), nullable=False),
        sa.Column("sell_price", sa.Numeric(12, 4), nullable=True),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("entry_vix", sa.Numeric(6, 2), nullable=True),
        sa.Column("exit_vix", sa.Numeric(6, 2), nullable=True),
        sa.Column("entry_iv", sa.Numeric(6, 2), nullable=True),
        sa.Column("exit_iv", sa.Numeric(6, 2), nullable=True),
        sa.Column("exit_reason", sa.String(length=100), nullable=True),
        sa.Column("realized_pnl", sa.Numeric(12, 2), nullable=True),
        sa.Column("brokerage_charges", sa.Numeric(10, 2), nullable=True),
        sa.Column("stt_taxes", sa.Numeric(10, 2), nullable=True),
        sa.Column("slippage_amount", sa.Numeric(10, 2), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )

    # 3. Live Safety Audit Events Table
    op.create_table(
        "live_safety_events",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("event_type", sa.String(length=50), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column(
            "metadata_json",
            sa.JSON().with_variant(JSONB, "postgresql"),
            nullable=False,
            server_default=sa.text("'{}'"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )


def downgrade() -> None:
    op.drop_table("live_safety_events")
    op.drop_table("live_tradebook")
    op.drop_table("live_risk_settings")
