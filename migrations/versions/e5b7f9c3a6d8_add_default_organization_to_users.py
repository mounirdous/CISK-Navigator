"""Add default organization to users

Revision ID: e5b7f9c3a6d8
Revises: d9e6f8a4b5c2
Create Date: 2026-03-09 14:00:00

"""
from alembic import op
import sqlalchemy as sa

revision = 'e5b7f9c3a6d8'
down_revision = 'd9e6f8a4b5c2'
branch_labels = None
depends_on = None

def upgrade():
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.add_column(sa.Column('default_organization_id', sa.Integer(), nullable=True))
        batch_op.create_foreign_key('fk_users_default_organization', 'organizations', ['default_organization_id'], ['id'])

def downgrade():
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.drop_constraint('fk_users_default_organization', type_='foreignkey')
        batch_op.drop_column('default_organization_id')
