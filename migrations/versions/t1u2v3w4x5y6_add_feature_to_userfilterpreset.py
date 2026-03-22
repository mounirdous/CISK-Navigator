"""Add feature column to user_filter_presets to distinguish workspace vs action_items presets

Revision ID: t1u2v3w4x5y6
Revises: s1t2u3v4w5x6
Create Date: 2026-03-22

"""

import sqlalchemy as sa
from alembic import op

revision = "t1u2v3w4x5y6"
down_revision = "s1t2u3v4w5x6"
branch_labels = None
depends_on = None


def upgrade():
    # Add feature column (default 'workspace' so all existing presets are preserved)
    with op.batch_alter_table("user_filter_presets") as batch_op:
        batch_op.add_column(sa.Column("feature", sa.String(50), nullable=False, server_default="workspace"))
        batch_op.drop_constraint("uq_user_org_preset_name", type_="unique")
        batch_op.create_unique_constraint(
            "uq_user_org_feature_preset_name",
            ["user_id", "organization_id", "feature", "name"],
        )


def downgrade():
    with op.batch_alter_table("user_filter_presets") as batch_op:
        batch_op.drop_constraint("uq_user_org_feature_preset_name", type_="unique")
        batch_op.create_unique_constraint(
            "uq_user_org_preset_name",
            ["user_id", "organization_id", "name"],
        )
        batch_op.drop_column("feature")
