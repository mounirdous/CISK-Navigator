"""add created_by to spaces for privacy

Revision ID: m3h4i5j6k7l8
Revises: l2g3h4i5j6k7
Create Date: 2026-03-13 15:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "m3h4i5j6k7l8"
down_revision = "l2g3h4i5j6k7"
branch_labels = None
depends_on = None


def upgrade():
    # Add created_by column to spaces
    op.add_column(
        "spaces",
        sa.Column(
            "created_by",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
            comment="User who created this space (owner for private spaces)",
        ),
    )


def downgrade():
    # Remove created_by column from spaces
    op.drop_column("spaces", "created_by")
