"""Fix mention notification cascade delete

Revision ID: a7d3e4f2b8c9
Revises: f3a9b2c1d5e7
Create Date: 2026-03-09 19:30:00

"""

import sqlalchemy as sa
from alembic import op

revision = "a7d3e4f2b8c9"
down_revision = "f3a9b2c1d5e7"
branch_labels = None
depends_on = None


def upgrade():
    # Drop existing foreign key constraint and recreate with ON DELETE CASCADE
    with op.batch_alter_table("mention_notifications", schema=None) as batch_op:
        batch_op.drop_constraint("mention_notifications_comment_id_fkey", type_="foreignkey")
        batch_op.create_foreign_key(
            "mention_notifications_comment_id_fkey", "cell_comments", ["comment_id"], ["id"], ondelete="CASCADE"
        )


def downgrade():
    # Revert to no cascade
    with op.batch_alter_table("mention_notifications", schema=None) as batch_op:
        batch_op.drop_constraint("mention_notifications_comment_id_fkey", type_="foreignkey")
        batch_op.create_foreign_key("mention_notifications_comment_id_fkey", "cell_comments", ["comment_id"], ["id"])
