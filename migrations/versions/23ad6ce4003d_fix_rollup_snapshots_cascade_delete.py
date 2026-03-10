"""fix rollup snapshots cascade delete

Revision ID: 23ad6ce4003d
Revises: i3c4d5e6f7g8
Create Date: 2026-03-10 09:55:03.064702

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "23ad6ce4003d"
down_revision = "i3c4d5e6f7g8"
branch_labels = None
depends_on = None


def upgrade():
    """
    Fix CASCADE DELETE behavior for rollup_snapshots.value_type_id.

    When a value_type is deleted (e.g., via organization deletion),
    rollup_snapshots should be deleted too, not left with NULL value_type_id.
    """
    # Drop existing foreign key constraint (without ON DELETE clause)
    op.drop_constraint("rollup_snapshots_value_type_id_fkey", "rollup_snapshots", type_="foreignkey")

    # Recreate with CASCADE DELETE
    op.create_foreign_key(
        "rollup_snapshots_value_type_id_fkey",
        "rollup_snapshots",
        "value_types",
        ["value_type_id"],
        ["id"],
        ondelete="CASCADE",
    )


def downgrade():
    """
    Revert to old foreign key without CASCADE DELETE.
    """
    # Drop CASCADE DELETE foreign key
    op.drop_constraint("rollup_snapshots_value_type_id_fkey", "rollup_snapshots", type_="foreignkey")

    # Recreate without ON DELETE clause (default behavior)
    op.create_foreign_key(
        "rollup_snapshots_value_type_id_fkey", "rollup_snapshots", "value_types", ["value_type_id"], ["id"]
    )
