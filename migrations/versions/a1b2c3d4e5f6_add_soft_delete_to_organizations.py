"""add soft delete to organizations

Revision ID: a1b2c3d4e5f6
Revises: 9f8e7d6c5b4a
Create Date: 2026-03-10 14:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "a1b2c3d4e5f6"
down_revision = "9f8e7d6c5b4a"
branch_labels = None
depends_on = None


def upgrade():
    """
    Add soft delete columns to organizations table.

    This allows organizations to be "archived" instead of permanently deleted,
    preserving data for recovery while hiding from normal operations.
    """
    # Add soft delete columns
    op.add_column('organizations', sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('organizations', sa.Column('deleted_at', sa.DateTime(), nullable=True))
    op.add_column('organizations', sa.Column('deleted_by', sa.Integer(), nullable=True))

    # Create index on is_deleted for query performance
    op.create_index('ix_organizations_is_deleted', 'organizations', ['is_deleted'])

    # Create foreign key for deleted_by
    op.create_foreign_key(
        'fk_organizations_deleted_by',
        'organizations',
        'users',
        ['deleted_by'],
        ['id'],
        ondelete='SET NULL'
    )


def downgrade():
    """
    Remove soft delete functionality.
    """
    # Drop foreign key
    op.drop_constraint('fk_organizations_deleted_by', 'organizations', type_='foreignkey')

    # Drop index
    op.drop_index('ix_organizations_is_deleted', 'organizations')

    # Drop columns
    op.drop_column('organizations', 'deleted_by')
    op.drop_column('organizations', 'deleted_at')
    op.drop_column('organizations', 'is_deleted')
