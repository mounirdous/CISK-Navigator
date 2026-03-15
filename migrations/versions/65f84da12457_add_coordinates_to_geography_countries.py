"""add_coordinates_to_geography_countries

Revision ID: 65f84da12457
Revises: 5553507a4208
Create Date: 2026-03-15 09:38:08.335381

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "65f84da12457"
down_revision = "5553507a4208"
branch_labels = None
depends_on = None


def upgrade():
    # Add latitude and longitude columns to geography_countries
    op.add_column("geography_countries", sa.Column("latitude", sa.Numeric(precision=10, scale=8), nullable=True))
    op.add_column("geography_countries", sa.Column("longitude", sa.Numeric(precision=11, scale=8), nullable=True))


def downgrade():
    # Remove latitude and longitude columns from geography_countries
    op.drop_column("geography_countries", "longitude")
    op.drop_column("geography_countries", "latitude")
