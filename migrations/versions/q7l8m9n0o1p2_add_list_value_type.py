"""Add list value type support

Revision ID: q7l8m9n0o1p2
Revises: p6k7l8m9n0o1
Create Date: 2026-03-20

"""

import sqlalchemy as sa
from alembic import op

revision = "q7l8m9n0o1p2"
down_revision = "86d06c10d056"
branch_labels = None
depends_on = None


def upgrade():
    # value_types: list_options JSON column
    op.add_column("value_types", sa.Column("list_options", sa.JSON(), nullable=True))

    # contributions: list_value string column
    op.add_column("contributions", sa.Column("list_value", sa.String(255), nullable=True))

    # kpi_snapshots: list_value string column
    op.add_column("kpi_snapshots", sa.Column("list_value", sa.String(255), nullable=True))

    # rollup_snapshots: list_value string column
    op.add_column("rollup_snapshots", sa.Column("list_value", sa.String(255), nullable=True))

    # kpi_value_type_configs: target_list_value string column
    op.add_column("kpi_value_type_configs", sa.Column("target_list_value", sa.String(255), nullable=True))


def downgrade():
    op.drop_column("kpi_value_type_configs", "target_list_value")
    op.drop_column("rollup_snapshots", "list_value")
    op.drop_column("kpi_snapshots", "list_value")
    op.drop_column("contributions", "list_value")
    op.drop_column("value_types", "list_options")
