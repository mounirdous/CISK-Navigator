"""add last_organization_id to users

Revision ID: ea56856d9837
Revises: 19d31425d0e7
Create Date: 2026-03-20 19:09:53.763458

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'ea56856d9837'
down_revision = '19d31425d0e7'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.add_column(sa.Column('last_organization_id', sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            'fk_users_last_organization', 'organizations', ['last_organization_id'], ['id'],
            ondelete='SET NULL'
        )


def downgrade():
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.drop_constraint('fk_users_last_organization', type_='foreignkey')
        batch_op.drop_column('last_organization_id')
