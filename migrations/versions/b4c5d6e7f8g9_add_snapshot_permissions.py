"""add can_view_snapshots and can_create_snapshots to user_organization_memberships

Revision ID: b4c5d6e7f8g9
Revises: a3b4c5d6e7f8
Create Date: 2026-03-27 18:00:00.000000

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = 'b4c5d6e7f8g9'
down_revision = 'a3b4c5d6e7f8'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('user_organization_memberships', sa.Column('can_view_snapshots', sa.Boolean(), nullable=False, server_default='true'))
    op.add_column('user_organization_memberships', sa.Column('can_create_snapshots', sa.Boolean(), nullable=False, server_default='true'))


def downgrade():
    op.drop_column('user_organization_memberships', 'can_create_snapshots')
    op.drop_column('user_organization_memberships', 'can_view_snapshots')
