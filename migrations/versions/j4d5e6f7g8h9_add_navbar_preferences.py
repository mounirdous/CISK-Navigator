"""Add navbar preferences to users

Revision ID: j4d5e6f7g8h9
Revises: i3c4d5e6f7g8
Create Date: 2026-03-10 15:30:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "j4d5e6f7g8h9"
down_revision = "i3c4d5e6f7g8"
branch_labels = None
depends_on = None


def upgrade():
    """Add navbar preferences columns to users table"""
    # Add navbar_position column (default 'top')
    op.add_column("users", sa.Column("navbar_position", sa.String(10), nullable=False, server_default="top"))

    # Add navbar_autohide column (default False)
    op.add_column("users", sa.Column("navbar_autohide", sa.Boolean(), nullable=False, server_default="false"))


def downgrade():
    """Remove navbar preferences columns"""
    op.drop_column("users", "navbar_autohide")
    op.drop_column("users", "navbar_position")
