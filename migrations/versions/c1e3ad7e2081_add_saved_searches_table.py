"""add saved searches table

Revision ID: c1e3ad7e2081
Revises: 2683fafe7d5a
Create Date: 2026-03-16 23:11:06.907109

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "c1e3ad7e2081"
down_revision = "2683fafe7d5a"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "saved_search",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("organization_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("query", sa.Text(), nullable=False),
        sa.Column("filters", sa.JSON(), nullable=True),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_saved_search_user_org", "saved_search", ["user_id", "organization_id"])


def downgrade():
    op.drop_index("ix_saved_search_user_org")
    op.drop_table("saved_search")
