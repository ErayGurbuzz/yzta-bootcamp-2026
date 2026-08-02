from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "c7be1ad81ff6"
down_revision = "c2d493a6e711"
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column(
        "quiz_answers",
        "user_answer",
        existing_type=sa.String(length=100),
        type_=sa.Text(),
        existing_nullable=False,
    )


def downgrade():
    op.alter_column(
        "quiz_answers",
        "user_answer",
        existing_type=sa.Text(),
        type_=sa.String(length=100),
        existing_nullable=False,
    )