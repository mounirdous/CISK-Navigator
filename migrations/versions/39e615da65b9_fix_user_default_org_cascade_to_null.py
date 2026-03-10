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
    # Drop existing foreign key constraint
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
