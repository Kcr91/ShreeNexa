"""create backfill_job, backfill_window and bar_coverage tables

Revision ID: 9c0d1e2f3a4b
Revises: 8b9c0d1e2f3a
Create Date: 2026-09-08 22:40:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "9c0d1e2f3a4b"
down_revision: str | Sequence[str] | None = "8b9c0d1e2f3a"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

JOB_STATES = (
    "pending",
    "running",
    "done",
    "failed",
    "paused_auth",
    "unavailable",
)
WINDOW_STATES = ("pending", "running", "done", "failed", "empty")


def upgrade() -> None:
    """Create the resumable backfill queue and the warehouse coverage catalogue."""
    op.create_table(
        "backfill_job",
        sa.Column("job_id", sa.Text(), nullable=False),
        sa.Column("tier", sa.Integer(), nullable=False),
        sa.Column("dataset", sa.Text(), nullable=False),
        sa.Column("exchange_segment", sa.Text(), nullable=False),
        sa.Column("security_id", sa.Text(), nullable=False),
        sa.Column("symbol", sa.Text(), nullable=False),
        sa.Column("underlying_symbol", sa.Text(), nullable=True),
        sa.Column("instrument_type", sa.Text(), nullable=True),
        sa.Column("expiry_flag", sa.Text(), nullable=True),
        sa.Column("expiry_code", sa.Integer(), nullable=True),
        sa.Column("strike_offset", sa.Integer(), nullable=True),
        sa.Column("interval", sa.Text(), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="100"),
        sa.Column("state", sa.Text(), nullable=False, server_default="pending"),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("job_id", name="pk_backfill_job"),
        sa.CheckConstraint("end_date >= start_date", name="ck_backfill_job_date_order"),
        sa.CheckConstraint(
            "state IN ('" + "', '".join(JOB_STATES) + "')",
            name="ck_backfill_job_state",
        ),
    )
    # Claim order: lowest tier first, then priority, then stable insertion order.
    op.create_index(
        "ix_backfill_job_claim",
        "backfill_job",
        ["state", "tier", "priority", "created_at"],
    )
    # One job per addressable series; re-enqueueing a tier must not duplicate work.
    op.create_index(
        "uq_backfill_job_series",
        "backfill_job",
        [
            "dataset",
            "exchange_segment",
            "security_id",
            "interval",
            sa.text("COALESCE(expiry_flag, '')"),
            sa.text("COALESCE(expiry_code, -1)"),
            sa.text("COALESCE(strike_offset, -9999)"),
        ],
        unique=True,
    )

    op.create_table(
        "backfill_window",
        sa.Column("job_id", sa.Text(), nullable=False),
        sa.Column("window_start", sa.Date(), nullable=False),
        sa.Column("window_end", sa.Date(), nullable=False),
        sa.Column("state", sa.Text(), nullable=False, server_default="pending"),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("raw_ingest_id", sa.Text(), nullable=True),
        sa.Column("rows", sa.Integer(), nullable=True),
        sa.Column("sha256", sa.Text(), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("claimed_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("completed_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("job_id", "window_start", name="pk_backfill_window"),
        sa.ForeignKeyConstraint(
            ["job_id"],
            ["backfill_job.job_id"],
            name="fk_backfill_window_job",
            ondelete="CASCADE",
        ),
        sa.CheckConstraint("window_end >= window_start", name="ck_backfill_window_date_order"),
        sa.CheckConstraint(
            "state IN ('" + "', '".join(WINDOW_STATES) + "')",
            name="ck_backfill_window_state",
        ),
    )
    op.create_index(
        "ix_backfill_window_claim",
        "backfill_window",
        ["state", "job_id", "window_start"],
    )

    op.create_table(
        "bar_coverage",
        sa.Column("dataset", sa.Text(), nullable=False),
        sa.Column("exchange_segment", sa.Text(), nullable=False),
        sa.Column("symbol", sa.Text(), nullable=False),
        sa.Column("interval", sa.Text(), nullable=False),
        sa.Column("security_id", sa.Text(), nullable=True),
        sa.Column("underlying_symbol", sa.Text(), nullable=True),
        sa.Column("min_ts", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("max_ts", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("rows", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column(
            "last_verified_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint(
            "dataset",
            "exchange_segment",
            "symbol",
            "interval",
            name="pk_bar_coverage",
        ),
        sa.CheckConstraint(
            "max_ts IS NULL OR min_ts IS NULL OR max_ts >= min_ts",
            name="ck_bar_coverage_ts_order",
        ),
        sa.CheckConstraint("rows >= 0", name="ck_bar_coverage_rows_non_negative"),
    )
    # The export UI looks coverage up by symbol across datasets.
    op.create_index("ix_bar_coverage_symbol", "bar_coverage", ["symbol", "interval"])


def downgrade() -> None:
    """Drop the coverage catalogue and the backfill queue."""
    op.drop_index("ix_bar_coverage_symbol", table_name="bar_coverage")
    op.drop_table("bar_coverage")
    op.drop_index("ix_backfill_window_claim", table_name="backfill_window")
    op.drop_table("backfill_window")
    op.drop_index("uq_backfill_job_series", table_name="backfill_job")
    op.drop_index("ix_backfill_job_claim", table_name="backfill_job")
    op.drop_table("backfill_job")
