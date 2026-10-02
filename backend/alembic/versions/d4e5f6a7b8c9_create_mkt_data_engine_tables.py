"""create mkt data engine tables

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-10-02 21:55:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d4e5f6a7b8c9"
down_revision: str | Sequence[str] | None = "c3d4e5f6a7b8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create mkt_ohlcv_equity, mkt_ohlcv_futures, mkt_ohlcv_options, mkt_download_state, and mkt_api_quota."""
    # 1. mkt_ohlcv_equity
    op.create_table(
        "mkt_ohlcv_equity",
        sa.Column("security_id", sa.Text(), nullable=False),
        sa.Column("exchange_segment", sa.Text(), nullable=False, server_default="NSE_EQ"),
        sa.Column("symbol", sa.Text(), nullable=False),
        sa.Column("datetime_ist", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("open", sa.Numeric(12, 4), nullable=False),
        sa.Column("high", sa.Numeric(12, 4), nullable=False),
        sa.Column("low", sa.Numeric(12, 4), nullable=False),
        sa.Column("close", sa.Numeric(12, 4), nullable=False),
        sa.Column("volume", sa.BigInteger(), nullable=False, server_default="0"),
        sa.PrimaryKeyConstraint("exchange_segment", "security_id", "datetime_ist", name="pk_mkt_ohlcv_equity"),
    )
    op.create_index("ix_mkt_eq_sym_dt", "mkt_ohlcv_equity", ["symbol", "datetime_ist"])

    # 2. mkt_ohlcv_futures
    op.create_table(
        "mkt_ohlcv_futures",
        sa.Column("security_id", sa.Text(), nullable=False),
        sa.Column("exchange_segment", sa.Text(), nullable=False, server_default="NSE_FNO"),
        sa.Column("symbol", sa.Text(), nullable=False),
        sa.Column("datetime_ist", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("open", sa.Numeric(12, 4), nullable=False),
        sa.Column("high", sa.Numeric(12, 4), nullable=False),
        sa.Column("low", sa.Numeric(12, 4), nullable=False),
        sa.Column("close", sa.Numeric(12, 4), nullable=False),
        sa.Column("volume", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("oi", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("underlying_spot", sa.Numeric(12, 4), nullable=True),
        sa.PrimaryKeyConstraint("exchange_segment", "security_id", "datetime_ist", name="pk_mkt_ohlcv_futures"),
    )
    op.create_index("ix_mkt_fut_sym_dt", "mkt_ohlcv_futures", ["symbol", "datetime_ist"])

    # 3. mkt_ohlcv_options
    op.create_table(
        "mkt_ohlcv_options",
        sa.Column("security_id", sa.Text(), nullable=False),
        sa.Column("exchange_segment", sa.Text(), nullable=False, server_default="NSE_FNO"),
        sa.Column("symbol", sa.Text(), nullable=False),
        sa.Column("datetime_ist", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("open", sa.Numeric(12, 4), nullable=False),
        sa.Column("high", sa.Numeric(12, 4), nullable=False),
        sa.Column("low", sa.Numeric(12, 4), nullable=False),
        sa.Column("close", sa.Numeric(12, 4), nullable=False),
        sa.Column("volume", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("oi", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("iv", sa.Numeric(8, 4), nullable=True),
        sa.Column("underlying_spot", sa.Numeric(12, 4), nullable=True),
        sa.PrimaryKeyConstraint("exchange_segment", "security_id", "datetime_ist", name="pk_mkt_ohlcv_options"),
    )
    op.create_index("ix_mkt_opt_sym_dt", "mkt_ohlcv_options", ["symbol", "datetime_ist"])

    # 4. mkt_download_state
    op.create_table(
        "mkt_download_state",
        sa.Column("security_id", sa.Text(), nullable=False),
        sa.Column("exchange_segment", sa.Text(), nullable=False),
        sa.Column("symbol", sa.Text(), nullable=False),
        sa.Column("instrument_type", sa.Text(), nullable=False),
        sa.Column("last_candle_ts", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("last_sync_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("sync_status", sa.Text(), nullable=False, server_default="PENDING"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("total_candles", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("api_requests_used", sa.Integer(), nullable=False, server_default="0"),
        sa.PrimaryKeyConstraint("exchange_segment", "security_id", name="pk_mkt_download_state"),
    )

    # 5. mkt_api_quota
    op.create_table(
        "mkt_api_quota",
        sa.Column("date", sa.Date(), primary_key=True),
        sa.Column("daily_limit", sa.Integer(), nullable=False, server_default="100000"),
        sa.Column("used_historical", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("used_live", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("reserved_live", sa.Integer(), nullable=False, server_default="5000"),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")),
    )

    # 6. mkt_segment and mkt_segment_constituent
    op.create_table(
        "mkt_segment",
        sa.Column("code", sa.Text(), primary_key=True),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("category", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
    )

    op.create_table(
        "mkt_segment_constituent",
        sa.Column("segment_code", sa.Text(), nullable=False),
        sa.Column("symbol", sa.Text(), nullable=False),
        sa.Column("weight", sa.Numeric(8, 4), nullable=True),
        sa.PrimaryKeyConstraint("segment_code", "symbol", name="pk_mkt_segment_constituent"),
    )


def downgrade() -> None:
    """Drop mkt data engine tables."""
    op.drop_table("mkt_segment_constituent")
    op.drop_table("mkt_segment")
    op.drop_table("mkt_api_quota")
    op.drop_table("mkt_download_state")
    op.drop_table("mkt_ohlcv_options")
    op.drop_table("mkt_ohlcv_futures")
    op.drop_table("mkt_ohlcv_equity")
