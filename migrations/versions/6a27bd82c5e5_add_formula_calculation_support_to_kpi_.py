"""Add formula calculation support to KPI configs

Revision ID: 6a27bd82c5e5
Revises: 16138fd82405
Create Date: 2026-03-12 07:41:25.979191

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "6a27bd82c5e5"
down_revision = "16138fd82405"
branch_labels = None
depends_on = None


def upgrade():
    # Add calculation_type column (manual, linked, formula)
    op.add_column(
        "kpi_value_type_configs",
        sa.Column(
            "calculation_type",
            sa.String(20),
            nullable=True,
            server_default="manual",
            comment="How value is determined: manual (contributions), linked (from another KPI), formula (calculated)",
        ),
    )

    # Add calculation_config column (JSON for formula configuration)
    op.add_column(
        "kpi_value_type_configs",
        sa.Column(
            "calculation_config",
            sa.JSON,
            nullable=True,
            comment='Configuration for formula calculations: {operation: "sum", kpi_config_ids: [1, 2, 3]}',
        ),
    )

    # Set existing linked KPIs to 'linked' type
    op.execute(
        """
        UPDATE kpi_value_type_configs
        SET calculation_type = 'linked'
        WHERE linked_source_kpi_id IS NOT NULL
    """
    )

    # Set remaining to 'manual'
    op.execute(
        """
        UPDATE kpi_value_type_configs
        SET calculation_type = 'manual'
        WHERE calculation_type IS NULL
    """
    )

    # Make calculation_type NOT NULL after setting defaults
    op.alter_column("kpi_value_type_configs", "calculation_type", nullable=False)


def downgrade():
    op.drop_column("kpi_value_type_configs", "calculation_config")
    op.drop_column("kpi_value_type_configs", "calculation_type")
