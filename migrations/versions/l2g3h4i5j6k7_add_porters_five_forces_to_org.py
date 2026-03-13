"""add porters five forces to org

Revision ID: l2g3h4i5j6k7
Revises: k1f2g3h4i5j6
Create Date: 2026-03-13 10:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "l2g3h4i5j6k7"
down_revision = "be485d1bc44f"
branch_labels = None
depends_on = None


def upgrade():
    # Add Porter's Five Forces fields to organizations
    op.add_column(
        "organizations",
        sa.Column("porters_new_entrants", sa.Text(), nullable=True, comment="Porter's: Threat of new entrants"),
    )
    op.add_column(
        "organizations",
        sa.Column("porters_suppliers", sa.Text(), nullable=True, comment="Porter's: Bargaining power of suppliers"),
    )
    op.add_column(
        "organizations",
        sa.Column("porters_buyers", sa.Text(), nullable=True, comment="Porter's: Bargaining power of buyers"),
    )
    op.add_column(
        "organizations",
        sa.Column("porters_substitutes", sa.Text(), nullable=True, comment="Porter's: Threat of substitutes"),
    )
    op.add_column(
        "organizations", sa.Column("porters_rivalry", sa.Text(), nullable=True, comment="Porter's: Competitive rivalry")
    )


def downgrade():
    # Remove Porter's Five Forces fields from organizations
    op.drop_column("organizations", "porters_rivalry")
    op.drop_column("organizations", "porters_substitutes")
    op.drop_column("organizations", "porters_buyers")
    op.drop_column("organizations", "porters_suppliers")
    op.drop_column("organizations", "porters_new_entrants")
