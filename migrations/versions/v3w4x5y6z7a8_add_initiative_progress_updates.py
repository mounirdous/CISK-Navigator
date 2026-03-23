"""Add initiative_progress_updates table

Revision ID: v3w4x5y6z7a8
Revises: u2v3w4x5y6z7
Create Date: 2026-03-23

"""
import sqlalchemy as sa
from alembic import op

revision = "v3w4x5y6z7a8"
down_revision = "u2v3w4x5y6z7"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "initiative_progress_updates",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("initiative_id", sa.Integer(), nullable=False),
        sa.Column("rag_status", sa.String(length=10), nullable=False),
        sa.Column("accomplishments", sa.Text(), nullable=True),
        sa.Column("next_steps", sa.Text(), nullable=True),
        sa.Column("blockers", sa.Text(), nullable=True),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["initiative_id"], ["initiatives.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_initiative_progress_updates_initiative_id", "initiative_progress_updates", ["initiative_id"])
    op.create_index("ix_initiative_progress_updates_created_at", "initiative_progress_updates", ["created_at"])


def downgrade():
    op.drop_index("ix_initiative_progress_updates_created_at", table_name="initiative_progress_updates")
    op.drop_index("ix_initiative_progress_updates_initiative_id", table_name="initiative_progress_updates")
    op.drop_table("initiative_progress_updates")
