"""Add is_private to spaces

Revision ID: a8c4b3e7d2f6
Revises: f5c8a9b3d2e4
Create Date: 2026-03-09 14:00:00

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a8c4b3e7d2f6'
down_revision = 'f5c8a9b3d2e4'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('spaces', schema=None) as batch_op:
        batch_op.add_column(sa.Column('is_private', sa.Boolean(), nullable=False, server_default='0'))


def downgrade():
    with op.batch_alter_table('spaces', schema=None) as batch_op:
        batch_op.drop_column('is_private')
