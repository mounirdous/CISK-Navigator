"""add comment_user_mentions table

Revision ID: x5y6z7a8b9c0
Revises: w4x5y6z7a8b9
Create Date: 2026-03-25 00:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

revision = "x5y6z7a8b9c0"
down_revision = "w4x5y6z7a8b9"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "comment_user_mentions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("comment_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("mention_login", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["comment_id"], ["cell_comments.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_comment_user_mention_id", "comment_user_mentions", ["comment_id"])
    op.create_index("idx_comment_user_mention", "comment_user_mentions", ["comment_id", "user_id"])


def downgrade():
    op.drop_index("idx_comment_user_mention", table_name="comment_user_mentions")
    op.drop_index("idx_comment_user_mention_id", table_name="comment_user_mentions")
    op.drop_table("comment_user_mentions")
