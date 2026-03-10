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
    """
    # Get database connection to check if constraint exists
    conn = op.get_bind()

    # Check if constraint exists (PostgreSQL specific query)
    result = conn.execute(sa.text("""
        SELECT constraint_name
        FROM information_schema.table_constraints
        WHERE table_name = 'users'
        AND constraint_name = 'users_default_organization_id_fkey'
        AND constraint_type = 'FOREIGN KEY'
    """))

    constraint_exists = result.fetchone() is not None

    if constraint_exists:
        # Drop existing foreign key constraint
        op.drop_constraint("users_default_organization_id_fkey", "users", type_="foreignkey")

    # Check if constraint already has correct definition
    result = conn.execute(sa.text("""
        SELECT confdeltype
        FROM pg_constraint
        WHERE conname = 'users_default_organization_id_fkey'
    """))

    existing_delete_type = result.fetchone()

    # Only recreate if constraint doesn't exist or doesn't have SET NULL behavior
    # confdeltype: 'a' = no action, 'r' = restrict, 'c' = cascade, 'n' = set null
    if not existing_delete_type or existing_delete_type[0] != 'n':
        # Recreate with ON DELETE SET NULL
        op.create_foreign_key(
            "users_default_organization_id_fkey",
            "users",
            "organizations",
            ["default_organization_id"],
            ["id"],
            ondelete="SET NULL",
        )


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
