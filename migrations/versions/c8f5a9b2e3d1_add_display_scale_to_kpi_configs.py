"""Add display scale to KPI value type configs

Revision ID: c8f5a9b2e3d1
Revises: a7d3e4f2b8c9
Create Date: 2026-03-09 10:30:00

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "c8f5a9b2e3d1"
down_revision = "a7d3e4f2b8c9"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("kpi_value_type_configs", schema=None) as batch_op:
        batch_op.add_column(sa.Column("display_scale", sa.String(20), nullable=True, server_default="default"))


def downgrade():
    with op.batch_alter_table("kpi_value_type_configs", schema=None) as batch_op:
        batch_op.drop_column("display_scale")
