"""add milestone to action_item_type enum + is_global flag

Revision ID: a8b9c0d1e2f3
Revises: z7a8b9c0d1e2
Create Date: 2026-04-02
"""
import sqlalchemy as sa
from alembic import op

revision = "a8b9c0d1e2f3"
down_revision = "z7a8b9c0d1e2"
branch_labels = None
depends_on = None


def upgrade():
    # ALTER TYPE ... ADD VALUE cannot run inside a transaction
    op.execute("COMMIT")
    op.execute("ALTER TYPE action_item_type ADD VALUE IF NOT EXISTS 'milestone'")
    # Re-open transaction for DDL
    op.execute("BEGIN")
    op.add_column("action_items", sa.Column("is_global", sa.Boolean(), nullable=False, server_default="false"))
    op.add_column("action_items", sa.Column("milestone_category", sa.String(50), nullable=True))
    op.add_column("action_items", sa.Column("tags", sa.JSON(), nullable=True))
    op.add_column("organizations", sa.Column("action_tags", sa.JSON(), nullable=True))
    op.add_column("governance_bodies", sa.Column("is_global", sa.Boolean(), nullable=False, server_default="false"))


def downgrade():
    op.drop_column("organizations", "action_tags")
    op.drop_column("action_items", "tags")
    op.drop_column("action_items", "milestone_category")
    op.drop_column("action_items", "is_global")
