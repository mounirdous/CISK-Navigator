"""Add snapshot privacy columns (is_public, owner_user_id)

Revision ID: f5c8a9b3d2e4
Revises: f2d6dc7cbc3a
Create Date: 2026-03-09 13:35:00

CRITICAL: This migration was missing from v1.15.0 commit, causing production failure.
These columns were manually added locally but never migrated.
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "f5c8a9b3d2e4"
down_revision = "f2d6dc7cbc3a"
branch_labels = None
depends_on = None


def upgrade():
    # Add privacy columns to kpi_snapshots
    with op.batch_alter_table("kpi_snapshots", schema=None) as batch_op:
        batch_op.add_column(sa.Column("is_public", sa.Boolean(), nullable=False, server_default="true"))
        batch_op.add_column(sa.Column("owner_user_id", sa.Integer(), nullable=True))
        batch_op.create_foreign_key("fk_kpi_snapshots_owner", "users", ["owner_user_id"], ["id"], ondelete="SET NULL")
        batch_op.create_index("ix_kpi_snapshots_public", ["is_public"])
        batch_op.create_index("ix_kpi_snapshots_owner", ["owner_user_id"])

    # Add privacy columns to rollup_snapshots
    with op.batch_alter_table("rollup_snapshots", schema=None) as batch_op:
        batch_op.add_column(sa.Column("is_public", sa.Boolean(), nullable=False, server_default="true"))
        batch_op.add_column(sa.Column("owner_user_id", sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            "fk_rollup_snapshots_owner", "users", ["owner_user_id"], ["id"], ondelete="SET NULL"
        )
        batch_op.create_index("ix_rollup_snapshots_public", ["is_public"])
        batch_op.create_index("ix_rollup_snapshots_owner", ["owner_user_id"])


def downgrade():
    with op.batch_alter_table("rollup_snapshots", schema=None) as batch_op:
        batch_op.drop_index("ix_rollup_snapshots_owner")
        batch_op.drop_index("ix_rollup_snapshots_public")
        batch_op.drop_constraint("fk_rollup_snapshots_owner", type_="foreignkey")
        batch_op.drop_column("owner_user_id")
        batch_op.drop_column("is_public")

    with op.batch_alter_table("kpi_snapshots", schema=None) as batch_op:
        batch_op.drop_index("ix_kpi_snapshots_owner")
        batch_op.drop_index("ix_kpi_snapshots_public")
        batch_op.drop_constraint("fk_kpi_snapshots_owner", type_="foreignkey")
        batch_op.drop_column("owner_user_id")
        batch_op.drop_column("is_public")
