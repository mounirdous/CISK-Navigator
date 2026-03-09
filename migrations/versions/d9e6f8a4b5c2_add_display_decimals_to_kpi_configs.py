"""Add display decimals to KPI value type configs

Revision ID: d9e6f8a4b5c2
Revises: c8f5a9b2e3d1
Create Date: 2026-03-09 10:37:00

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "d9e6f8a4b5c2"
down_revision = "c8f5a9b2e3d1"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("kpi_value_type_configs", schema=None) as batch_op:
        batch_op.add_column(sa.Column("display_decimals", sa.Integer(), nullable=True))


def downgrade():
    with op.batch_alter_table("kpi_value_type_configs", schema=None) as batch_op:
        batch_op.drop_column("display_decimals")
