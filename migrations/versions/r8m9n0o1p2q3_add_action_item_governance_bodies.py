"""Add governance bodies to action items (many-to-many)

Revision ID: r8m9n0o1p2q3
Revises: q7l8m9n0o1p2
Create Date: 2026-03-21

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "r8m9n0o1p2q3"
down_revision = "q7l8m9n0o1p2"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "action_item_governance_body",
        sa.Column("action_item_id", sa.Integer(), nullable=False),
        sa.Column("governance_body_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["action_item_id"], ["action_items.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["governance_body_id"], ["governance_bodies.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("action_item_id", "governance_body_id"),
    )


def downgrade():
    op.drop_table("action_item_governance_body")
