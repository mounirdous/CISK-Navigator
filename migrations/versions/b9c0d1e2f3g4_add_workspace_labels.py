"""add user-scoped workspace labels for organizing workspaces

Revision ID: b9c0d1e2f3g4
Revises: a8b9c0d1e2f3
Create Date: 2026-04-05
"""
import sqlalchemy as sa
from alembic import op

revision = "b9c0d1e2f3g4"
down_revision = "a8b9c0d1e2f3"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "workspace_labels",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=50), nullable=False),
        sa.Column("color", sa.String(length=7), nullable=False, server_default="#6366f1"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "name", name="uq_user_label_name"),
    )
    op.create_index(op.f("ix_workspace_labels_user_id"), "workspace_labels", ["user_id"])

    op.create_table(
        "organization_labels",
        sa.Column("organization_id", sa.Integer(), nullable=False),
        sa.Column("label_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["label_id"], ["workspace_labels.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("organization_id", "label_id"),
    )


def downgrade():
    op.drop_table("organization_labels")
    op.drop_index(op.f("ix_workspace_labels_user_id"), table_name="workspace_labels")
    op.drop_table("workspace_labels")
