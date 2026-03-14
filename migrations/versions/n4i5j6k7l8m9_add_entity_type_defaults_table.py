"""add entity type defaults table

Revision ID: n4i5j6k7l8m9
Revises: 41a5ed2746c5
Create Date: 2026-03-14 16:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "n4i5j6k7l8m9"
down_revision = "41a5ed2746c5"
branch_labels = None
depends_on = None


def upgrade():
    # Create entity_type_defaults table
    op.create_table(
        "entity_type_defaults",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("entity_type", sa.String(length=50), nullable=False),
        sa.Column("default_color", sa.String(length=7), nullable=False),
        sa.Column("default_icon", sa.String(length=10), nullable=False),
        sa.Column("display_name", sa.String(length=100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("updated_by", sa.Integer(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(
            ["updated_by"],
            ["users.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_entity_type_defaults_entity_type"), "entity_type_defaults", ["entity_type"], unique=True)

    # Insert default values
    op.execute(
        """
        INSERT INTO entity_type_defaults (entity_type, default_color, default_icon, display_name, description)
        VALUES
            ('organization', '#3b82f6', '🏢', 'Organization', 'Top-level business unit or company'),
            ('space', '#10b981', '🎯', 'Space', 'Strategic grouping (seasons, sites, customers)'),
            ('challenge', '#f59e0b', '⚡', 'Challenge', 'High-level business challenge or theme'),
            ('initiative', '#8b5cf6', '🚀', 'Initiative', 'Strategic initiative or project'),
            ('system', '#ec4899', '⚙️', 'System', 'Functional area or capability'),
            ('kpi', '#06b6d4', '📊', 'KPI', 'Key Performance Indicator')
    """
    )


def downgrade():
    op.drop_index(op.f("ix_entity_type_defaults_entity_type"), table_name="entity_type_defaults")
    op.drop_table("entity_type_defaults")
