"""add stakeholder to action_item_mention_entity_type enum

Revision ID: y6z7a8b9c0d1
Revises: n5i6j7k8l9m0
Create Date: 2026-04-01
"""
from alembic import op

revision = "y6z7a8b9c0d1"
down_revision = "n5i6j7k8l9m0"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("ALTER TYPE action_item_mention_entity_type ADD VALUE IF NOT EXISTS 'stakeholder'")


def downgrade():
    pass
