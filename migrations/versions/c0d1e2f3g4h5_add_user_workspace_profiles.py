"""add user workspace profiles for persistent named configurations

Revision ID: c0d1e2f3g4h5
Revises: b9c0d1e2f3g4
Create Date: 2026-04-05
"""
import sqlalchemy as sa
from alembic import op

revision = "c0d1e2f3g4h5"
down_revision = "b9c0d1e2f3g4"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "user_workspace_profiles",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=50), nullable=False),
        sa.Column("icon", sa.String(length=10), nullable=False, server_default="briefcase"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("config", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "name", name="uq_user_profile_name"),
    )
    op.create_index(op.f("ix_user_workspace_profiles_user_id"), "user_workspace_profiles", ["user_id"])


def downgrade():
    op.drop_index(op.f("ix_user_workspace_profiles_user_id"), table_name="user_workspace_profiles")
    op.drop_table("user_workspace_profiles")
