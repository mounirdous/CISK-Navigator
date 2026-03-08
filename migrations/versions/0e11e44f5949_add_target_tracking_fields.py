"""Add target tracking fields to KPIValueTypeConfig

Revision ID: 0e11e44f5949
Revises: 498afb934c2e
Create Date: 2026-03-08 07:45:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0e11e44f5949'
down_revision = '498afb934c2e'
branch_labels = None
depends_on = None


def upgrade():
    # Add target tracking fields to kpi_value_type_configs
    with op.batch_alter_table('kpi_value_type_configs', schema=None) as batch_op:
        batch_op.add_column(sa.Column('target_value', sa.Numeric(precision=20, scale=6), nullable=True, comment='Target value to achieve (numeric only)'))
        batch_op.add_column(sa.Column('target_date', sa.Date(), nullable=True, comment='Date by which target should be achieved'))


def downgrade():
    # Remove target tracking fields from kpi_value_type_configs
    with op.batch_alter_table('kpi_value_type_configs', schema=None) as batch_op:
        batch_op.drop_column('target_date')
        batch_op.drop_column('target_value')
