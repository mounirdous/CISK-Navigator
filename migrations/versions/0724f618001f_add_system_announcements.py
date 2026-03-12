"""add_system_announcements

Revision ID: 0724f618001f
Revises: 98a9b53623a0
Create Date: 2026-03-12 16:43:56.831032

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "0724f618001f"
down_revision = "98a9b53623a0"
branch_labels = None
depends_on = None


def upgrade():
    # Create system_announcements table
    op.create_table(
        "system_announcements",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("banner_type", sa.String(length=20), nullable=False),  # info, warning, success, alert
        sa.Column("is_dismissible", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("target_type", sa.String(length=20), nullable=False),  # all, organization, users
        sa.Column("target_organization_id", sa.Integer(), nullable=True),
        sa.Column("start_date", sa.DateTime(), nullable=True),
        sa.Column("end_date", sa.DateTime(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_by", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["created_by"],
            ["users.id"],
        ),
        sa.ForeignKeyConstraint(
            ["target_organization_id"],
            ["organizations.id"],
        ),
    )
    op.create_index(op.f("ix_system_announcements_is_active"), "system_announcements", ["is_active"], unique=False)
    op.create_index(op.f("ix_system_announcements_start_date"), "system_announcements", ["start_date"], unique=False)
    op.create_index(op.f("ix_system_announcements_end_date"), "system_announcements", ["end_date"], unique=False)

    # Create user_announcement_acknowledgments table
    op.create_table(
        "user_announcement_acknowledgments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("announcement_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("acknowledged_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["announcement_id"], ["system_announcements.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("announcement_id", "user_id", name="uq_announcement_user"),
    )
    op.create_index(
        op.f("ix_user_announcement_acknowledgments_user_id"),
        "user_announcement_acknowledgments",
        ["user_id"],
        unique=False,
    )

    # Create announcement_target_users table (for specific user targeting)
    op.create_table(
        "announcement_target_users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("announcement_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["announcement_id"], ["system_announcements.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index(
        op.f("ix_announcement_target_users_user_id"), "announcement_target_users", ["user_id"], unique=False
    )


def downgrade():
    op.drop_index(op.f("ix_announcement_target_users_user_id"), table_name="announcement_target_users")
    op.drop_table("announcement_target_users")

    op.drop_index(op.f("ix_user_announcement_acknowledgments_user_id"), table_name="user_announcement_acknowledgments")
    op.drop_table("user_announcement_acknowledgments")

    op.drop_index(op.f("ix_system_announcements_end_date"), table_name="system_announcements")
    op.drop_index(op.f("ix_system_announcements_start_date"), table_name="system_announcements")
    op.drop_index(op.f("ix_system_announcements_is_active"), table_name="system_announcements")
    op.drop_table("system_announcements")
