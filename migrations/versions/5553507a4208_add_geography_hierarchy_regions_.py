"""Add geography hierarchy (regions, countries, sites) with KPI site assignments

Revision ID: 5553507a4208
Revises: b22a92c1a37e
Create Date: 2026-03-15 08:50:48.667538

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "5553507a4208"
down_revision = "b22a92c1a37e"
branch_labels = None
depends_on = None


def upgrade():
    # Create geography_regions table
    op.create_table(
        "geography_regions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("organization_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("code", sa.String(length=20), nullable=True, comment="Short code (e.g., EMEA, AMER)"),
        sa.Column("display_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_geography_regions_organization_id", "geography_regions", ["organization_id"])

    # Create geography_countries table
    op.create_table(
        "geography_countries",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("region_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("code", sa.String(length=10), nullable=True, comment="Short code (e.g., FR, DE, ES)"),
        sa.Column("iso_code", sa.String(length=3), nullable=True, comment="ISO 3166-1 alpha-2/3 code"),
        sa.Column("display_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("geojson", sa.JSON(), nullable=True, comment="GeoJSON polygon for country borders"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["region_id"], ["geography_regions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_geography_countries_region_id", "geography_countries", ["region_id"])

    # Create geography_sites table
    op.create_table(
        "geography_sites",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("country_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("code", sa.String(length=20), nullable=True, comment="Short code for display (e.g., PAR-HQ)"),
        sa.Column("address", sa.Text(), nullable=True, comment="Physical address"),
        sa.Column("latitude", sa.Numeric(precision=10, scale=8), nullable=True, comment="Latitude for map display"),
        sa.Column("longitude", sa.Numeric(precision=11, scale=8), nullable=True, comment="Longitude for map display"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("display_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["country_id"], ["geography_countries.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_geography_sites_country_id", "geography_sites", ["country_id"])
    op.create_index("ix_geography_sites_is_active", "geography_sites", ["is_active"])

    # Create kpi_site_assignments junction table
    op.create_table(
        "kpi_site_assignments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("kpi_id", sa.Integer(), nullable=False),
        sa.Column("site_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["kpi_id"], ["kpis.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["site_id"], ["geography_sites.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("kpi_id", "site_id", name="uq_kpi_site"),
    )
    op.create_index("ix_kpi_site_assignments_kpi_id", "kpi_site_assignments", ["kpi_id"])
    op.create_index("ix_kpi_site_assignments_site_id", "kpi_site_assignments", ["site_id"])


def downgrade():
    # Drop in reverse order due to foreign keys
    op.drop_index("ix_kpi_site_assignments_site_id", table_name="kpi_site_assignments")
    op.drop_index("ix_kpi_site_assignments_kpi_id", table_name="kpi_site_assignments")
    op.drop_table("kpi_site_assignments")

    op.drop_index("ix_geography_sites_is_active", table_name="geography_sites")
    op.drop_index("ix_geography_sites_country_id", table_name="geography_sites")
    op.drop_table("geography_sites")

    op.drop_index("ix_geography_countries_region_id", table_name="geography_countries")
    op.drop_table("geography_countries")

    op.drop_index("ix_geography_regions_organization_id", table_name="geography_regions")
    op.drop_table("geography_regions")
