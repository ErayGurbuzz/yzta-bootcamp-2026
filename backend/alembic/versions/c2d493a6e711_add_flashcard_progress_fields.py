"""add flashcard progress fields

Revision ID: c2d493a6e711
Revises: f8c056f07c77
Create Date: 2026-07-11 22:10:00
"""

from typing import Sequence, Union

from alembic import op


revision: str = "c2d493a6e711"
down_revision: Union[str, None] = "f8c056f07c77"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # The project creates its initial schema on startup, so this migration must
    # also be safe for a brand-new database where the table does not exist yet.
    op.execute("ALTER TABLE IF EXISTS flashcards ADD COLUMN IF NOT EXISTS is_learned BOOLEAN NOT NULL DEFAULT FALSE")
    op.execute("ALTER TABLE IF EXISTS flashcards ADD COLUMN IF NOT EXISTS review_count INTEGER NOT NULL DEFAULT 0")
    op.execute("ALTER TABLE IF EXISTS flashcards ADD COLUMN IF NOT EXISTS last_reviewed_at TIMESTAMP WITHOUT TIME ZONE")


def downgrade() -> None:
    op.execute("ALTER TABLE IF EXISTS flashcards DROP COLUMN IF EXISTS last_reviewed_at")
    op.execute("ALTER TABLE IF EXISTS flashcards DROP COLUMN IF EXISTS review_count")
    op.execute("ALTER TABLE IF EXISTS flashcards DROP COLUMN IF EXISTS is_learned")
