"""add logo_path to organization

Revision ID: o5j6k7l8m9n0
Revises: n4i5j6k7l8m9
Create Date: 2026-03-14 17:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "o5j6k7l8m9n0"
down_revision = "n4i5j6k7l8m9"
branch_labels = None
depends_on = None


def upgrade():
    # Add logo_path column to organizations table
    op.add_column(
        "organizations",
        sa.Column("logo_path", sa.String(length=500), nullable=True, comment="Path to organization logo file"),
    )


def downgrade():
    # Remove logo_path column
    op.drop_column("organizations", "logo_path")
