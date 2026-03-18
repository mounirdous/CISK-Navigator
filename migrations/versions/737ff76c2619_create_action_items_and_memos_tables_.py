"""create_action_items_and_memos_tables_clean

Revision ID: 737ff76c2619
Revises: 5f87aa9fccb9
Create Date: 2026-03-17 15:51:45.563550

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "737ff76c2619"
down_revision = "5f87aa9fccb9"
branch_labels = None
depends_on = None


def upgrade():
    # Create enum types
    op.execute("CREATE TYPE action_item_type AS ENUM ('memo', 'action')")
    op.execute("CREATE TYPE action_item_status AS ENUM ('draft', 'active', 'completed', 'cancelled')")
    op.execute("CREATE TYPE action_item_priority AS ENUM ('low', 'medium', 'high', 'urgent')")
    op.execute("CREATE TYPE action_item_visibility AS ENUM ('private', 'shared')")
    op.execute(
        "CREATE TYPE action_item_mention_entity_type AS ENUM ('space', 'challenge', 'initiative', 'system', 'kpi')"
    )

    # Create action_items table using raw SQL to avoid SQLAlchemy re-creating enum types
    op.execute("""
        CREATE TABLE action_items (
            id SERIAL PRIMARY KEY,
            organization_id INTEGER NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
            type action_item_type NOT NULL,
            title VARCHAR(200) NOT NULL,
            description TEXT,
            status action_item_status NOT NULL,
            priority action_item_priority NOT NULL,
            due_date DATE,
            completed_at TIMESTAMP,
            owner_user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            visibility action_item_visibility NOT NULL,
            created_by_user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
            created_at TIMESTAMP NOT NULL,
            updated_at TIMESTAMP NOT NULL
        )
    """)
    op.execute("CREATE INDEX ix_action_items_organization_id ON action_items (organization_id)")
    op.execute("CREATE INDEX ix_action_items_owner_user_id ON action_items (owner_user_id)")
    op.execute("CREATE INDEX ix_action_items_status ON action_items (status)")
    op.execute("CREATE INDEX ix_action_items_visibility ON action_items (visibility)")

    # Create action_item_mentions table using raw SQL
    op.execute("""
        CREATE TABLE action_item_mentions (
            id SERIAL PRIMARY KEY,
            action_item_id INTEGER NOT NULL REFERENCES action_items(id) ON DELETE CASCADE,
            entity_type action_item_mention_entity_type NOT NULL,
            entity_id INTEGER NOT NULL,
            mention_text VARCHAR(255) NOT NULL,
            created_at TIMESTAMP NOT NULL
        )
    """)
    op.execute("CREATE INDEX ix_action_item_mentions_action_item_id ON action_item_mentions (action_item_id)")


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
