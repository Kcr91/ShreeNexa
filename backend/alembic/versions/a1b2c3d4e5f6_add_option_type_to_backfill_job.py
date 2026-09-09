"""add option_type to backfill_job

charts/rollingoption requires drvOptionType and returns only the requested leg, so a
CE+PE chain is two API calls per strike rather than one. The job identity therefore has
to distinguish the legs, and the per-series unique index has to include it.

Revision ID: a1b2c3d4e5f6
Revises: 9c0d1e2f3a4b
Create Date: 2026-09-09 11:20:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: str | Sequence[str] | None = "9c0d1e2f3a4b"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SERIES_INDEX = "uq_backfill_job_series"


def upgrade() -> None:
    """Add option_type and widen the per-series uniqueness to include it."""
    op.add_column("backfill_job", sa.Column("option_type", sa.Text(), nullable=True))
    op.drop_index(SERIES_INDEX, table_name="backfill_job")
    op.create_index(
        SERIES_INDEX,
        "backfill_job",
        [
            "dataset",
            "exchange_segment",
            "security_id",
            "interval",
            sa.text("COALESCE(expiry_flag, '')"),
            sa.text("COALESCE(expiry_code, -1)"),
            sa.text("COALESCE(strike_offset, -9999)"),
            sa.text("COALESCE(option_type, '')"),
        ],
        unique=True,
    )


def downgrade() -> None:
    """Restore the narrower index and drop the column."""
    op.drop_index(SERIES_INDEX, table_name="backfill_job")
    op.create_index(
        SERIES_INDEX,
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
    op.drop_column("backfill_job", "option_type")
