"""add per-window quality metrics to backfill_window

Nothing fetched is discarded any more. Exchange calendars are not something this
system can adjudicate - holidays differ per exchange, special sessions exist, holiday
dates move, and sessions are sometimes shortened or run outside the usual window. So
every window is stored and anything unusual about it is recorded here for the Historic
Data Report to highlight. Cleaning is a separate, later task.

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-09-09 12:10:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

# revision identifiers, used by Alembic.
revision: str = "b2c3d4e5f6a7"
down_revision: str | Sequence[str] | None = "a1b2c3d4e5f6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Record what was fetched and what looked unusual about it."""
    op.add_column("backfill_window", sa.Column("quality", JSONB(), nullable=True))
    op.add_column(
        "backfill_window",
        sa.Column("suspect", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.add_column("backfill_window", sa.Column("distinct_days", sa.Integer(), nullable=True))
    op.add_column(
        "backfill_window", sa.Column("min_ts", sa.TIMESTAMP(timezone=True), nullable=True)
    )
    op.add_column(
        "backfill_window", sa.Column("max_ts", sa.TIMESTAMP(timezone=True), nullable=True)
    )
    # The report's primary lens: which stored windows need a human look.
    op.create_index(
        "ix_backfill_window_suspect",
        "backfill_window",
        ["suspect", "job_id"],
        postgresql_where=sa.text("suspect"),
    )


def downgrade() -> None:
    """Drop the quality columns and their index."""
    op.drop_index("ix_backfill_window_suspect", table_name="backfill_window")
    op.drop_column("backfill_window", "max_ts")
    op.drop_column("backfill_window", "min_ts")
    op.drop_column("backfill_window", "distinct_days")
    op.drop_column("backfill_window", "suspect")
    op.drop_column("backfill_window", "quality")
