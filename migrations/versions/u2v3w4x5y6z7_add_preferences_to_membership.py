"""Add preferences JSON column to user_organization_memberships

Revision ID: u2v3w4x5y6z7
Revises: t1u2v3w4x5y6
Create Date: 2026-03-22

"""
import sqlalchemy as sa
from alembic import op

revision = "u2v3w4x5y6z7"
down_revision = "t1u2v3w4x5y6"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "user_organization_memberships",
        sa.Column("preferences", sa.JSON(), nullable=True, comment="Per-user per-org UI preferences"),
    )


def downgrade():
    op.drop_column("user_organization_memberships", "preferences")
