"""add_map_color_preferences_to_organizations

Revision ID: 33275eefdf80
Revises: 999c86785d6c
Create Date: 2026-03-15 15:11:10.476788

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '33275eefdf80'
down_revision = '999c86785d6c'
branch_labels = None
depends_on = None


def upgrade():
    # Add map color preferences to organizations
    op.add_column('organizations', sa.Column('map_country_color_with_kpis', sa.String(7), nullable=True,
                                              comment='Hex color for countries with KPIs on map'))
    op.add_column('organizations', sa.Column('map_country_color_no_kpis', sa.String(7), nullable=True,
                                              comment='Hex color for countries in system without KPIs'))

    # Set default values (Mikron blue and grey)
    op.execute("UPDATE organizations SET map_country_color_with_kpis = '#3b82f6' WHERE map_country_color_with_kpis IS NULL")
    op.execute("UPDATE organizations SET map_country_color_no_kpis = '#9ca3af' WHERE map_country_color_no_kpis IS NULL")


def downgrade():
    op.drop_column('organizations', 'map_country_color_no_kpis')
    op.drop_column('organizations', 'map_country_color_with_kpis')
