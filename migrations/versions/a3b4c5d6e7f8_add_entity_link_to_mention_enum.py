"""add entity_link to action_item_mention_entity_type enum

Revision ID: a3b4c5d6e7f8
Revises: 31aed0926b2e
Create Date: 2026-03-27 12:00:00.000000

"""
from alembic import op

# revision identifiers, used by Alembic.
revision = 'a3b4c5d6e7f8'
down_revision = '31aed0926b2e'
branch_labels = None
depends_on = None


def upgrade():
    op.execute("ALTER TYPE action_item_mention_entity_type ADD VALUE 'entity_link'")


def downgrade():
    # PostgreSQL does not support removing values from an enum type.
    # The 'entity_link' value will remain in the enum but will be unused
    # after a downgrade. To fully remove it, recreate the enum type manually.
    pass
