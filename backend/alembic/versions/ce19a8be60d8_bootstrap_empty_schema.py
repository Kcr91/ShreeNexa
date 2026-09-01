"""bootstrap empty schema

Revision ID: ce19a8be60d8
Revises:
Create Date: 2026-09-01 10:11:49.706959

"""
from collections.abc import Sequence

# revision identifiers, used by Alembic.
revision: str = 'ce19a8be60d8'
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
