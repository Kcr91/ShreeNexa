"""create dynamic screener engine tables

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-10-03 07:55:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

# revision identifiers, used by Alembic.
revision: str = "e5f6a7b8c9d0"
down_revision: str | Sequence[str] | None = "d4e5f6a7b8c9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create screener_configs and screener_results tables."""
    op.create_table(
        "screener_configs",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("universe_filter", sa.Text(), nullable=False, server_default="FNO_208"),
        sa.Column("condition_tree", JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "is_strategy_mode", sa.Boolean(), nullable=False, server_default=sa.text("false")
        ),
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
    op.create_index("ix_screener_configs_universe", "screener_configs", ["universe_filter"])

    op.create_table(
        "screener_results",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "config_id",
            sa.Integer(),
            sa.ForeignKey("screener_configs.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "run_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")
        ),
        sa.Column("matched_symbols", JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("total_scanned", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_matched", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("run_duration_ms", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("result_snapshot", JSONB(astext_type=sa.Text()), nullable=False),
    )
    op.create_index("ix_screener_results_config_run", "screener_results", ["config_id", "run_at"])


def downgrade() -> None:
    """Drop screener engine tables."""
    op.drop_table("screener_results")
    op.drop_table("screener_configs")
