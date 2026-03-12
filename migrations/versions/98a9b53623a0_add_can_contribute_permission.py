"""add_can_contribute_permission

Revision ID: 98a9b53623a0
Revises: 6a27bd82c5e5
Create Date: 2026-03-12 16:22:10.557526

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "98a9b53623a0"
down_revision = "6a27bd82c5e5"
branch_labels = None
depends_on = None


def upgrade():
    # Add can_contribute permission to user_organization_memberships
    op.add_column(
        "user_organization_memberships",
        sa.Column("can_contribute", sa.Boolean(), nullable=False, server_default="true"),
    )


def downgrade():
    # Remove can_contribute permission
    op.drop_column("user_organization_memberships", "can_contribute")
