"""create live engine tables

Revision ID: sb_live_f6
Revises: sb_paper_f5
Create Date: 2026-10-03 08:30:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "sb_live_f6"
down_revision: str | None = "sb_paper_f5"
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

    # NOTE: the `live_tradebook` table is created by the earlier
    # `sb_variant_f4` (create variant and tradebook tables) migration, whose
    # schema is the one the ORM (`app.engine.variant_models.live_tradebook_table`)
    # and both the live- and variant-engine APIs use. It is intentionally NOT
    # re-created here to avoid a DuplicateTable failure on `upgrade head`.

    # 2. Live Safety Audit Events Table
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
    # `live_tradebook` is owned by the `sb_variant_f4` migration; dropped there.
    op.drop_table("live_risk_settings")
