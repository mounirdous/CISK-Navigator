"""Add action items, stakeholders, and map permissions

Revision ID: adf138430006
Revises: 7a2248e4f425
Create Date: 2026-03-18 09:13:54.892894

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "adf138430006"
down_revision = "7a2248e4f425"
branch_labels = None
depends_on = None


def upgrade():
    # Add new permission columns to user_organization_memberships
    op.add_column(
        "user_organization_memberships",
        sa.Column("can_view_action_items", sa.Boolean(), nullable=False, server_default="1"),
    )
    op.add_column(
        "user_organization_memberships",
        sa.Column("can_create_action_items", sa.Boolean(), nullable=False, server_default="1"),
    )
    op.add_column(
        "user_organization_memberships",
        sa.Column("can_view_stakeholders", sa.Boolean(), nullable=False, server_default="0"),
    )
    op.add_column(
        "user_organization_memberships",
        sa.Column("can_manage_stakeholders", sa.Boolean(), nullable=False, server_default="0"),
    )
    op.add_column(
        "user_organization_memberships", sa.Column("can_view_map", sa.Boolean(), nullable=False, server_default="1")
    )


def downgrade():
    # Remove permission columns
    op.drop_column("user_organization_memberships", "can_view_map")
    op.drop_column("user_organization_memberships", "can_manage_stakeholders")
    op.drop_column("user_organization_memberships", "can_view_stakeholders")
    op.drop_column("user_organization_memberships", "can_create_action_items")
    op.drop_column("user_organization_memberships", "can_view_action_items")
