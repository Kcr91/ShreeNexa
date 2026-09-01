"""create instrument table

Revision ID: 7a8b9c0d1e2f
Revises: 577be887b8fd
Create Date: 2026-09-01 20:45:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

# revision identifiers, used by Alembic.
revision: str = "7a8b9c0d1e2f"
down_revision: str | Sequence[str] | None = "577be887b8fd"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema: create instrument table with composite primary key and indexes."""
    op.create_table(
        "instrument",
        sa.Column("security_id", sa.Text(), nullable=False),
        sa.Column("exchange_segment", sa.Text(), nullable=False),
        sa.Column("instrument_type", sa.Text(), nullable=False),
        sa.Column("symbol", sa.Text(), nullable=False),
        sa.Column("trading_symbol", sa.Text(), nullable=False),
        sa.Column("isin", sa.Text(), nullable=True),
        sa.Column("lot_size", sa.Integer(), nullable=True),
        sa.Column("tick_size", sa.Numeric(12, 4), nullable=True),
        sa.Column("expiry_date", sa.Date(), nullable=True),
        sa.Column("strike_price", sa.Numeric(14, 4), nullable=True),
        sa.Column("option_type", sa.Text(), nullable=True),
        sa.Column("underlying_id", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("raw", JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("synced_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("exchange_segment", "security_id", name="pk_instrument"),
    )
    op.create_index("ix_instrument_symbol", "instrument", ["symbol"])
    op.create_index(
        "ix_instrument_options",
        "instrument",
        ["underlying_id", "expiry_date", "strike_price"],
    )


def downgrade() -> None:
    """Downgrade schema: drop indexes and table."""
    op.drop_index("ix_instrument_options", table_name="instrument")
    op.drop_index("ix_instrument_symbol", table_name="instrument")
    op.drop_table("instrument")
