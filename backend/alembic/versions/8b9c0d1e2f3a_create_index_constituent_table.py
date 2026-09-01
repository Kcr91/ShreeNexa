"""create index_constituent table

Revision ID: 8b9c0d1e2f3a
Revises: 7a8b9c0d1e2f
Create Date: 2026-09-01 21:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "8b9c0d1e2f3a"
down_revision: str | Sequence[str] | None = "7a8b9c0d1e2f"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema: create index_constituent table with interval constraints and index."""
    op.create_table(
        "index_constituent",
        sa.Column("index_name", sa.Text(), nullable=False),
        sa.Column("symbol", sa.Text(), nullable=False),
        sa.Column("weight", sa.Numeric(8, 4), nullable=True),
        sa.Column("sector", sa.Text(), nullable=True),
        sa.Column("valid_from", sa.Date(), nullable=False),
        sa.Column("valid_to", sa.Date(), nullable=True),
        sa.Column("source_date", sa.Date(), nullable=False),
        sa.Column("source", sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint("index_name", "symbol", "valid_from", name="pk_index_constituent"),
        sa.CheckConstraint(
            "valid_to IS NULL OR valid_to >= valid_from",
            name="ck_index_constituent_valid_interval",
        ),
    )
    op.create_index(
        "ix_index_constituent_interval",
        "index_constituent",
        ["index_name", "valid_from", "valid_to"],
    )


def downgrade() -> None:
    """Downgrade schema: drop index and table."""
    op.drop_index("ix_index_constituent_interval", table_name="index_constituent")
    op.drop_table("index_constituent")
