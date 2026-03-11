"""Add linked KPI source columns

Revision ID: k1f2g3h4i5j6
Revises: 07901b5ce63b
Create Date: 2026-03-11 13:25:00

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "k1f2g3h4i5j6"
down_revision = "07901b5ce63b"
branch_labels = None
depends_on = None


def upgrade():
    # Add three new columns for linked KPI support
    op.add_column(
        "kpi_value_type_configs",
        sa.Column("linked_source_org_id", sa.Integer(), nullable=True),
    )
    op.add_column(
        "kpi_value_type_configs",
        sa.Column("linked_source_kpi_id", sa.Integer(), nullable=True),
    )
    op.add_column(
        "kpi_value_type_configs",
        sa.Column("linked_source_value_type_id", sa.Integer(), nullable=True),
    )

    # Add foreign key constraints
    op.create_foreign_key(
        "fk_kpi_value_type_configs_linked_source_org",
        "kpi_value_type_configs",
        "organizations",
        ["linked_source_org_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_kpi_value_type_configs_linked_source_kpi",
        "kpi_value_type_configs",
        "kpis",
        ["linked_source_kpi_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_kpi_value_type_configs_linked_source_vt",
        "kpi_value_type_configs",
        "value_types",
        ["linked_source_value_type_id"],
        ["id"],
        ondelete="RESTRICT",
    )


def downgrade():
    # Drop foreign key constraints
    op.drop_constraint("fk_kpi_value_type_configs_linked_source_vt", "kpi_value_type_configs", type_="foreignkey")
    op.drop_constraint("fk_kpi_value_type_configs_linked_source_kpi", "kpi_value_type_configs", type_="foreignkey")
    op.drop_constraint("fk_kpi_value_type_configs_linked_source_org", "kpi_value_type_configs", type_="foreignkey")

    # Drop columns
    op.drop_column("kpi_value_type_configs", "linked_source_value_type_id")
    op.drop_column("kpi_value_type_configs", "linked_source_kpi_id")
    op.drop_column("kpi_value_type_configs", "linked_source_org_id")
