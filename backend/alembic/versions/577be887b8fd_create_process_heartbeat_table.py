"""create process_heartbeat table

Revision ID: 577be887b8fd
Revises: ce19a8be60d8
Create Date: 2026-09-01 10:33:07.884550

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "577be887b8fd"
down_revision: str | Sequence[str] | None = "ce19a8be60d8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "process_heartbeat",
        sa.Column("process_name", sa.Text(), primary_key=True),
        sa.Column("pid", sa.Integer(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("started_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("last_heartbeat_at", sa.TIMESTAMP(timezone=True), nullable=False),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("process_heartbeat")
