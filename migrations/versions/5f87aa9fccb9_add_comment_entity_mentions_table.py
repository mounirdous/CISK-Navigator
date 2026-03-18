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

    # Drop stale enum if it exists (e.g. from a partial prior run), then recreate it
    op.execute("DROP TYPE IF EXISTS comment_entity_mention_type")
    op.execute(
        "CREATE TYPE comment_entity_mention_type AS ENUM ('space', 'challenge', 'initiative', 'system', 'kpi')"
    )

    # Create table using raw SQL to avoid SQLAlchemy re-creating the enum type
    op.execute("""
        CREATE TABLE comment_entity_mentions (
            id SERIAL PRIMARY KEY,
            comment_id INTEGER NOT NULL REFERENCES cell_comments(id) ON DELETE CASCADE,
            entity_type comment_entity_mention_type NOT NULL,
            entity_id INTEGER NOT NULL,
            mention_text VARCHAR(255) NOT NULL,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    """)
    op.execute("CREATE INDEX idx_comment_entity_mention ON comment_entity_mentions (comment_id, entity_type, entity_id)")
    op.execute("CREATE INDEX ix_comment_entity_mentions_comment_id ON comment_entity_mentions (comment_id)")


def downgrade():
    # Drop table and indexes
    op.drop_index(op.f("ix_comment_entity_mentions_comment_id"), table_name="comment_entity_mentions")
    op.drop_index("idx_comment_entity_mention", table_name="comment_entity_mentions")
    op.drop_table("comment_entity_mentions")

    # Drop enum type
    op.execute("DROP TYPE comment_entity_mention_type")
