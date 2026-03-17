"""drop_action_items_cleanup

Revision ID: 66388e544042
Revises: 5f87aa9fccb9
Create Date: 2026-03-17 15:50:20.695656

"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "66388e544042"
down_revision = "c1e3ad7e2081"
branch_labels = None
depends_on = None


def upgrade():
    """Drop all action_items related objects to clean up broken state"""
    # Drop tables first (if they exist)
    op.execute("DROP TABLE IF EXISTS action_item_mentions CASCADE")
    op.execute("DROP TABLE IF EXISTS action_items CASCADE")

    # Drop enum types
    op.execute("DROP TYPE IF EXISTS action_item_mention_entity_type CASCADE")
    op.execute("DROP TYPE IF EXISTS action_item_visibility CASCADE")
    op.execute("DROP TYPE IF EXISTS action_item_priority CASCADE")
    op.execute("DROP TYPE IF EXISTS action_item_status CASCADE")
    op.execute("DROP TYPE IF EXISTS action_item_type CASCADE")


def downgrade():
    # Cannot recreate from scratch here, will be done in next migration
    pass
