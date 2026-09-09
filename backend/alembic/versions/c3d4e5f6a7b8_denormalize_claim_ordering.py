"""denormalize tier and priority onto backfill_window for an indexable claim

The claim query ordered by columns spanning both tables (job.tier, job.priority,
job.created_at, window.window_start), so Postgres had to sort the whole join on every
claim. Measured against a 137,000-window queue that took 2.24 s per claim, against a
Dhan API call of 0.39 s - the queue was nearly six times slower than the thing it
existed to feed.

Tier and priority are fixed when a job is enqueued, so copying them onto the window row
lets the claim be a single-table index scan with LIMIT 1.

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-09-09 13:05:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c3d4e5f6a7b8"
down_revision: str | Sequence[str] | None = "b2c3d4e5f6a7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

CLAIM_INDEX = "ix_backfill_window_claim_order"


def upgrade() -> None:
    """Copy the ordering keys onto the window and index the claim path."""
    op.add_column(
        "backfill_window",
        sa.Column("tier", sa.Integer(), nullable=False, server_default="99"),
    )
    op.add_column(
        "backfill_window",
        sa.Column("priority", sa.Integer(), nullable=False, server_default="100"),
    )
    op.execute(
        """
        UPDATE backfill_window w
        SET tier = j.tier, priority = j.priority
        FROM backfill_job j
        WHERE j.job_id = w.job_id
        """
    )
    # Partial index: only pending rows are ever claimed, so the index stays small
    # even as millions of settled windows accumulate.
    op.create_index(
        CLAIM_INDEX,
        "backfill_window",
        ["tier", "priority", "job_id", "window_start"],
        postgresql_where=sa.text("state = 'pending'"),
    )


def downgrade() -> None:
    """Drop the claim index and the denormalized columns."""
    op.drop_index(CLAIM_INDEX, table_name="backfill_window")
    op.drop_column("backfill_window", "priority")
    op.drop_column("backfill_window", "tier")
