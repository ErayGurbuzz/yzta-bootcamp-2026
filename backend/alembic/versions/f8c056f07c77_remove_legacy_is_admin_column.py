"""remove legacy is_admin column

Revision ID: f8c056f07c77
Revises:
Create Date: 2026-07-11 17:56:43.353413
"""

from typing import Sequence, Union

from alembic import op


revision: str = "f8c056f07c77"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE users DROP COLUMN IF EXISTS is_admin"
    )


def downgrade() -> None:
    op.execute(
        """
        ALTER TABLE users
        ADD COLUMN IF NOT EXISTS is_admin
        BOOLEAN NOT NULL DEFAULT FALSE
        """
    )