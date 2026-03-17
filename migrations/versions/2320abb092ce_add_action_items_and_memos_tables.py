"""Add action items and memos tables

Revision ID: 2320abb092ce
Revises: c1e3ad7e2081
Create Date: 2026-03-17 13:40:34.436299

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "2320abb092ce"
down_revision = "c1e3ad7e2081"
branch_labels = None
depends_on = None


def upgrade():
    # Create enum types (if not exists)
    op.execute(
        "DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'action_item_type') THEN CREATE TYPE action_item_type AS ENUM ('memo', 'action'); END IF; END $$;"
    )
    op.execute(
        "DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'action_item_status') THEN CREATE TYPE action_item_status AS ENUM ('draft', 'active', 'completed', 'cancelled'); END IF; END $$;"
    )
    op.execute(
        "DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'action_item_priority') THEN CREATE TYPE action_item_priority AS ENUM ('low', 'medium', 'high', 'urgent'); END IF; END $$;"
    )
    op.execute(
        "DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'action_item_visibility') THEN CREATE TYPE action_item_visibility AS ENUM ('private', 'shared'); END IF; END $$;"
    )
    op.execute(
        "DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'action_item_mention_entity_type') THEN CREATE TYPE action_item_mention_entity_type AS ENUM ('space', 'challenge', 'initiative', 'system', 'kpi'); END IF; END $$;"
    )

    # Create action_items table
    op.create_table(
        "action_items",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("organization_id", sa.Integer(), nullable=False),
        sa.Column("type", sa.Enum("memo", "action", name="action_item_type"), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "status", sa.Enum("draft", "active", "completed", "cancelled", name="action_item_status"), nullable=False
        ),
        sa.Column("priority", sa.Enum("low", "medium", "high", "urgent", name="action_item_priority"), nullable=False),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("owner_user_id", sa.Integer(), nullable=False),
        sa.Column("visibility", sa.Enum("private", "shared", name="action_item_visibility"), nullable=False),
        sa.Column("created_by_user_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["owner_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_action_items_organization_id"), "action_items", ["organization_id"], unique=False)
    op.create_index(op.f("ix_action_items_owner_user_id"), "action_items", ["owner_user_id"], unique=False)
    op.create_index(op.f("ix_action_items_status"), "action_items", ["status"], unique=False)
    op.create_index(op.f("ix_action_items_visibility"), "action_items", ["visibility"], unique=False)

    # Create action_item_mentions table
    op.create_table(
        "action_item_mentions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("action_item_id", sa.Integer(), nullable=False),
        sa.Column(
            "entity_type",
            sa.Enum("space", "challenge", "initiative", "system", "kpi", name="action_item_mention_entity_type"),
            nullable=False,
        ),
        sa.Column("entity_id", sa.Integer(), nullable=False),
        sa.Column("mention_text", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["action_item_id"], ["action_items.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_action_item_mentions_action_item_id"), "action_item_mentions", ["action_item_id"], unique=False
    )


def downgrade():
    # Drop tables
    op.drop_index(op.f("ix_action_item_mentions_action_item_id"), table_name="action_item_mentions")
    op.drop_table("action_item_mentions")

    op.drop_index(op.f("ix_action_items_visibility"), table_name="action_items")
    op.drop_index(op.f("ix_action_items_status"), table_name="action_items")
    op.drop_index(op.f("ix_action_items_owner_user_id"), table_name="action_items")
    op.drop_index(op.f("ix_action_items_organization_id"), table_name="action_items")
    op.drop_table("action_items")

    # Drop enum types
    op.execute("DROP TYPE action_item_mention_entity_type")
    op.execute("DROP TYPE action_item_visibility")
    op.execute("DROP TYPE action_item_priority")
    op.execute("DROP TYPE action_item_status")
    op.execute("DROP TYPE action_item_type")
