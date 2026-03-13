"""Add SavedChart model for persistent chart configurations

Revision ID: 6dbe28a58429
Revises: 3e602a96475c
Create Date: 2026-03-13 21:51:47.056332

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "6dbe28a58429"
down_revision = "3e602a96475c"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "saved_charts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("organization_id", sa.Integer(), nullable=False),
        sa.Column("created_by_user_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("year_start", sa.Integer(), nullable=False),
        sa.Column("year_end", sa.Integer(), nullable=False),
        sa.Column("view_type", sa.String(length=20), nullable=False),
        sa.Column("chart_type", sa.String(length=20), nullable=False),
        sa.Column("space_id", sa.Integer(), nullable=True),
        sa.Column("value_type_id", sa.Integer(), nullable=True),
        sa.Column("period_filter", sa.String(length=50), nullable=True),
        sa.Column("config_ids_colors", sa.Text(), nullable=False),
        sa.Column("is_shared", sa.Boolean(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["created_by_user_id"],
            ["users.id"],
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
        ),
        sa.ForeignKeyConstraint(
            ["space_id"],
            ["spaces.id"],
        ),
        sa.ForeignKeyConstraint(
            ["value_type_id"],
            ["value_types.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade():
    op.drop_table("saved_charts")
