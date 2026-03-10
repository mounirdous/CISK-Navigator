"""Add target direction and tolerance to KPI configs

Revision ID: c7d9e5f8a2b1
Revises: a8c4b3e7d2f6
Create Date: 2026-03-10 16:30:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "c7d9e5f8a2b1"
down_revision = "a8c4b3e7d2f6"
branch_labels = None
depends_on = None


def upgrade():
    """Add target_direction and target_tolerance_pct columns to kpi_value_type_configs"""

    # Add target_direction column with default 'maximize'
    op.add_column(
        "kpi_value_type_configs",
        sa.Column(
            "target_direction",
            sa.String(20),
            nullable=True,
            server_default="maximize",
            comment="Target direction: maximize (higher is better), minimize (lower is better), or exact (at target)",
        ),
    )

    # Add target_tolerance_pct column with default 10
    op.add_column(
        "kpi_value_type_configs",
        sa.Column(
            "target_tolerance_pct",
            sa.Integer(),
            nullable=True,
            server_default="10",
            comment="Tolerance percentage for 'exact' target direction",
        ),
    )

    # Update existing rows to have the default value
    op.execute("UPDATE kpi_value_type_configs SET target_direction = 'maximize' WHERE target_direction IS NULL")
    op.execute("UPDATE kpi_value_type_configs SET target_tolerance_pct = 10 WHERE target_tolerance_pct IS NULL")


def downgrade():
    """Remove target_direction and target_tolerance_pct columns"""

    op.drop_column("kpi_value_type_configs", "target_tolerance_pct")
    op.drop_column("kpi_value_type_configs", "target_direction")
