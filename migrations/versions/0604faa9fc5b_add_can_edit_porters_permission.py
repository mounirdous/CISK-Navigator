"""add_can_edit_porters_permission

Revision ID: 0604faa9fc5b
Revises: adf138430006
Create Date: 2026-03-18 09:54:53.537392

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "0604faa9fc5b"
down_revision = "adf138430006"
branch_labels = None
depends_on = None


def upgrade():
    # Add can_edit_porters permission column
    op.add_column(
        "user_organization_memberships",
        sa.Column("can_edit_porters", sa.Boolean(), nullable=False, server_default="1"),
    )


def downgrade():
    # Remove can_edit_porters column
    op.drop_column("user_organization_memberships", "can_edit_porters")
