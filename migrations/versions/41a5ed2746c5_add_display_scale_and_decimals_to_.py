"""Add display scale and decimals to rollup rules

Revision ID: 41a5ed2746c5
Revises: 6dbe28a58429
Create Date: 2026-03-14 09:54:56.383252

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "41a5ed2746c5"
down_revision = "6dbe28a58429"
branch_labels = None
depends_on = None


def upgrade():
    # Add display_scale column to rollup_rules
    op.add_column(
        "rollup_rules",
        sa.Column(
            "display_scale",
            sa.String(length=20),
            nullable=True,
            comment="Display scale for rollup: inherit, default, thousands, millions",
        ),
    )

    # Add display_decimals column to rollup_rules
    op.add_column(
        "rollup_rules",
        sa.Column(
            "display_decimals",
            sa.Integer(),
            nullable=True,
            comment="Number of decimals for rollup display (overrides value_type decimals)",
        ),
    )


def downgrade():
    # Remove columns
    op.drop_column("rollup_rules", "display_decimals")
    op.drop_column("rollup_rules", "display_scale")
