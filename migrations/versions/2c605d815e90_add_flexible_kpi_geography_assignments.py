"""add_flexible_kpi_geography_assignments

Revision ID: 2c605d815e90
Revises: 65f84da12457
Create Date: 2026-03-15 10:34:36.042098

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "2c605d815e90"
down_revision = "65f84da12457"
branch_labels = None
depends_on = None


def upgrade():
    # Create new flexible geography assignments table
    op.create_table(
        "kpi_geography_assignments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("kpi_id", sa.Integer(), nullable=False),
        sa.Column("region_id", sa.Integer(), nullable=True),
        sa.Column("country_id", sa.Integer(), nullable=True),
        sa.Column("site_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["kpi_id"], ["kpis.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["region_id"], ["geography_regions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["country_id"], ["geography_countries.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["site_id"], ["geography_sites.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create indexes for performance
    op.create_index("ix_kpi_geography_assignments_kpi_id", "kpi_geography_assignments", ["kpi_id"])
    op.create_index("ix_kpi_geography_assignments_region_id", "kpi_geography_assignments", ["region_id"])
    op.create_index("ix_kpi_geography_assignments_country_id", "kpi_geography_assignments", ["country_id"])
    op.create_index("ix_kpi_geography_assignments_site_id", "kpi_geography_assignments", ["site_id"])

    # Migrate existing site assignments to new table
    op.execute(
        """
        INSERT INTO kpi_geography_assignments (kpi_id, site_id, created_at)
        SELECT kpi_id, site_id, created_at
        FROM kpi_site_assignments
    """
    )


def downgrade():
    # Drop indexes
    op.drop_index("ix_kpi_geography_assignments_site_id", table_name="kpi_geography_assignments")
    op.drop_index("ix_kpi_geography_assignments_country_id", table_name="kpi_geography_assignments")
    op.drop_index("ix_kpi_geography_assignments_region_id", table_name="kpi_geography_assignments")
    op.drop_index("ix_kpi_geography_assignments_kpi_id", table_name="kpi_geography_assignments")

    # Drop new table
    op.drop_table("kpi_geography_assignments")
