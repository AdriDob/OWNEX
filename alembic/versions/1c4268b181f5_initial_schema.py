"""initial_schema

Revision ID: 1c4268b181f5
Revises:
Create Date: 2026-07-03 11:38:18.314396

"""

from typing import Sequence, Union


# revision identifiers, used by Alembic.
revision: str = "1c4268b181f5"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Schema is managed by init_db() via Base.metadata.create_all.

    This migration is a no-op because `init_db()` in database/db.py handles
    table creation and auto-migration directly from model definitions
    (create_all + _migrate_columns). Keep it as a placeholder so alembic
    stamp/check works without conflicting with model-driven schema.
    """


def downgrade() -> None:
    """No-op to match upgrade."""
