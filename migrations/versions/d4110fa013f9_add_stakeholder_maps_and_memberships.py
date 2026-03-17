"""add_stakeholder_maps_and_memberships

Revision ID: d4110fa013f9
Revises: b2854c101d3b
Create Date: 2026-03-17 18:22:33.006726

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "d4110fa013f9"
down_revision = "b2854c101d3b"
branch_labels = None
depends_on = None


def upgrade():
    # Check if tables already exist (idempotency)
    from sqlalchemy import inspect

    bind = op.get_bind()
    inspector = inspect(bind)
    existing_tables = inspector.get_table_names()

    # Create stakeholder_maps table if it doesn't exist
    if "stakeholder_maps" not in existing_tables:
        op.create_table(
            "stakeholder_maps",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("organization_id", sa.Integer(), nullable=False),
            sa.Column("created_by_user_id", sa.Integer(), nullable=True),
            sa.Column("name", sa.String(length=200), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("visibility", sa.String(length=20), nullable=False, server_default="shared"),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.PrimaryKeyConstraint("id"),
            sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL"),
            sa.CheckConstraint("visibility IN ('private', 'shared')", name="ck_stakeholder_maps_visibility"),
        )
        op.create_index("ix_stakeholder_maps_organization_id", "stakeholder_maps", ["organization_id"])
        op.create_index("ix_stakeholder_maps_visibility", "stakeholder_maps", ["visibility"])

    # Create stakeholder_map_memberships table if it doesn't exist
    if "stakeholder_map_memberships" not in existing_tables:
        op.create_table(
            "stakeholder_map_memberships",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("map_id", sa.Integer(), nullable=False),
            sa.Column("stakeholder_id", sa.Integer(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.PrimaryKeyConstraint("id"),
            sa.ForeignKeyConstraint(["map_id"], ["stakeholder_maps.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["stakeholder_id"], ["stakeholders.id"], ondelete="CASCADE"),
            sa.UniqueConstraint("map_id", "stakeholder_id", name="uq_map_stakeholder"),
        )
        op.create_index("ix_stakeholder_map_memberships_map_id", "stakeholder_map_memberships", ["map_id"])
        op.create_index(
            "ix_stakeholder_map_memberships_stakeholder_id", "stakeholder_map_memberships", ["stakeholder_id"]
        )


def downgrade():
    op.drop_table("stakeholder_map_memberships")
    op.drop_table("stakeholder_maps")
