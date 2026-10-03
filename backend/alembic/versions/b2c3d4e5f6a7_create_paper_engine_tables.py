"""Create paper_sessions, paper_positions, and paper_tradebook tables.

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-10-03 08:10:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b2c3d4e5f6a7"
down_revision: str | Sequence[str] | None = "a1b2c3d4e5f6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create paper trading engine tables."""
    # 1. paper_sessions
    op.create_table(
        "paper_sessions",
        sa.Column("session_id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "strategy_id",
            sa.Integer(),
            sa.ForeignKey("strategy_configs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("session_name", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False, server_default="RUNNING"),
        sa.Column("initial_capital", sa.Numeric(12, 2), nullable=False, server_default="500000.00"),
        sa.Column("current_capital", sa.Numeric(12, 2), nullable=False, server_default="500000.00"),
        sa.Column(
            "start_time",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column("end_time", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("readiness_score", sa.Numeric(5, 2), nullable=False, server_default="0.00"),
    )
    op.create_index("ix_paper_sessions_strat", "paper_sessions", ["strategy_id"])
    op.create_index("ix_paper_sessions_status", "paper_sessions", ["status"])

    # 2. paper_positions
    op.create_table(
        "paper_positions",
        sa.Column("position_id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "session_id",
            sa.Integer(),
            sa.ForeignKey("paper_sessions.session_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("symbol", sa.Text(), nullable=False),
        sa.Column("signal_type", sa.Text(), nullable=False),
        sa.Column("entry_time", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("entry_price", sa.Numeric(12, 4), nullable=False),
        sa.Column("current_price", sa.Numeric(12, 4), nullable=True),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("unrealized_pnl", sa.Numeric(12, 2), nullable=False, server_default="0.00"),
        sa.Column("active_sl", sa.Numeric(12, 4), nullable=True),
        sa.Column("active_target", sa.Numeric(12, 4), nullable=True),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
    )
    op.create_index("ix_paper_pos_session", "paper_positions", ["session_id"])

    # 3. paper_tradebook
    op.create_table(
        "paper_tradebook",
        sa.Column("trade_id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "session_id",
            sa.Integer(),
            sa.ForeignKey("paper_sessions.session_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("symbol", sa.Text(), nullable=False),
        sa.Column("signal_type", sa.Text(), nullable=False),
        sa.Column("entry_time", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("exit_time", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("entry_price", sa.Numeric(12, 4), nullable=False),
        sa.Column("exit_price", sa.Numeric(12, 4), nullable=True),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("realized_pnl", sa.Numeric(12, 2), nullable=False, server_default="0.00"),
        sa.Column("exit_reason", sa.Text(), nullable=True),
        sa.Column("entry_vix", sa.Numeric(6, 2), nullable=True),
        sa.Column("exit_vix", sa.Numeric(6, 2), nullable=True),
        sa.Column("entry_iv", sa.Numeric(6, 2), nullable=True),
        sa.Column("exit_iv", sa.Numeric(6, 2), nullable=True),
        sa.Column("simulated_slippage", sa.Numeric(10, 2), nullable=False, server_default="0.00"),
        sa.Column("simulated_brokerage", sa.Numeric(10, 2), nullable=False, server_default="0.00"),
    )
    op.create_index("ix_paper_tb_session", "paper_tradebook", ["session_id"])


def downgrade() -> None:
    """Drop paper trading tables."""
    op.drop_table("paper_tradebook")
    op.drop_table("paper_positions")
    op.drop_table("paper_sessions")
