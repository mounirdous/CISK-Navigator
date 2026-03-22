"""Add start_date to action_items

Revision ID: s1t2u3v4w5x6
Revises: r8m9n0o1p2q3
Create Date: 2026-03-22

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "s1t2u3v4w5x6"
down_revision = "r8m9n0o1p2q3"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("action_items", sa.Column("start_date", sa.Date(), nullable=True))


def downgrade():
    op.drop_column("action_items", "start_date")
