"""add comment entity mentions table

Revision ID: 5f87aa9fccb9
Revises: c1e3ad7e2081
Create Date: 2026-03-17 14:13:44.998600

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "5f87aa9fccb9"
down_revision = "66388e544042"
branch_labels = None
depends_on = None


def upgrade():
    # Check if table already exists - if so, skip this migration
    from sqlalchemy import inspect

    bind = op.get_bind()
    inspector = inspect(bind)
    existing_tables = inspector.get_table_names()

    if "comment_entity_mentions" in existing_tables:
        # Migration already applied, skip
        return

    # Create enum type only if it doesn't exist
    result = bind.execute(sa.text("SELECT 1 FROM pg_type WHERE typname = 'comment_entity_mention_type'"))
    if result.fetchone() is None:
        op.execute(
            "CREATE TYPE comment_entity_mention_type AS ENUM ('space', 'challenge', 'initiative', 'system', 'kpi')"
        )

    # Create comment_entity_mentions table
    op.create_table(
        "comment_entity_mentions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("comment_id", sa.Integer(), nullable=False),
        sa.Column(
            "entity_type",
            sa.Enum("space", "challenge", "initiative", "system", "kpi", name="comment_entity_mention_type"),
            nullable=False,
        ),
        sa.Column("entity_id", sa.Integer(), nullable=False),
        sa.Column("mention_text", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(
            ["comment_id"],
            ["cell_comments.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create indexes
    op.create_index("idx_comment_entity_mention", "comment_entity_mentions", ["comment_id", "entity_type", "entity_id"])
    op.create_index(op.f("ix_comment_entity_mentions_comment_id"), "comment_entity_mentions", ["comment_id"])


def downgrade():
    # Drop table and indexes
    op.drop_index(op.f("ix_comment_entity_mentions_comment_id"), table_name="comment_entity_mentions")
    op.drop_index("idx_comment_entity_mention", table_name="comment_entity_mentions")
    op.drop_table("comment_entity_mentions")

    # Drop enum type
    op.execute("DROP TYPE comment_entity_mention_type")
