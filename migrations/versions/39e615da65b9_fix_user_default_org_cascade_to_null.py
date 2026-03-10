"""fix user default org cascade to null

Revision ID: 39e615da65b9
Revises: 23ad6ce4003d
Create Date: 2026-03-10 10:04:57.231255

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "39e615da65b9"
down_revision = "23ad6ce4003d"
branch_labels = None
depends_on = None


def upgrade():
    """
    Fix default_organization_id foreign key to SET NULL on organization deletion.

    Without this, deleting an organization that is set as any user's default
    will either block the deletion or leave orphaned references.

    This migration is safe to run multiple times - it checks before modifying.
    """
    # Get database connection
    conn = op.get_bind()

    # Check if constraint exists and what its delete behavior is
    result = conn.execute(sa.text("""
        SELECT c.confdeltype
        FROM pg_constraint c
        JOIN pg_class t ON c.conrelid = t.oid
        JOIN pg_namespace n ON t.relnamespace = n.oid
        WHERE c.conname = 'users_default_organization_id_fkey'
        AND t.relname = 'users'
        AND c.contype = 'f'
    """))

    row = result.fetchone()

    # If constraint doesn't exist, create it with SET NULL
    if row is None:
        op.create_foreign_key(
            "users_default_organization_id_fkey",
            "users",
            "organizations",
            ["default_organization_id"],
            ["id"],
            ondelete="SET NULL",
        )
    # If constraint exists but doesn't have SET NULL (confdeltype != 'n'), fix it
    elif row[0] != 'n':
        # Drop existing constraint
        op.drop_constraint("users_default_organization_id_fkey", "users", type_="foreignkey")

        # Recreate with ON DELETE SET NULL
        op.create_foreign_key(
            "users_default_organization_id_fkey",
            "users",
            "organizations",
            ["default_organization_id"],
            ["id"],
            ondelete="SET NULL",
        )
    # Else: constraint already has SET NULL, nothing to do


def downgrade():
    """
    Revert to old foreign key without CASCADE behavior.
    """
    # Drop CASCADE foreign key
    op.drop_constraint("users_default_organization_id_fkey", "users", type_="foreignkey")

    # Recreate without ON DELETE clause
    op.create_foreign_key(
        "users_default_organization_id_fkey", "users", "organizations", ["default_organization_id"], ["id"]
    )
