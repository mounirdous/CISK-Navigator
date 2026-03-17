"""add_stakeholder_mapping_tables

Revision ID: 55cabdbb3a13
Revises: 737ff76c2619
Create Date: 2026-03-17 16:57:42.863988

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "55cabdbb3a13"
down_revision = "737ff76c2619"
branch_labels = None
depends_on = None


def upgrade():
    # Skip enum creation and use String with CHECK constraints instead
    # This avoids the enum duplication nightmare completely

    # Check if tables already exist (idempotency)
    from sqlalchemy import inspect

    bind = op.get_bind()
    inspector = inspect(bind)
    existing_tables = inspector.get_table_names()

    if "stakeholders" in existing_tables:
        # Migration already applied
        return

    # Create stakeholders table using String columns instead of Enum
    op.create_table(
        "stakeholders",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("organization_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("role", sa.String(length=200), nullable=True),
        sa.Column("department", sa.String(length=200), nullable=True),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("influence_level", sa.Integer(), nullable=False, server_default="50"),
        sa.Column("interest_level", sa.Integer(), nullable=False, server_default="50"),
        sa.Column("support_level", sa.String(length=20), nullable=False, server_default="neutral"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("position_x", sa.Float(), nullable=True),
        sa.Column("position_y", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint(
            "support_level IN ('champion', 'supporter', 'neutral', 'skeptic', 'blocker')",
            name="ck_stakeholders_support_level",
        ),
    )
    op.create_index(op.f("ix_stakeholders_organization_id"), "stakeholders", ["organization_id"], unique=False)
    op.create_index(op.f("ix_stakeholders_support_level"), "stakeholders", ["support_level"], unique=False)
    op.create_index(op.f("ix_stakeholders_department"), "stakeholders", ["department"], unique=False)

    # Create stakeholder_relationships table using String instead of Enum
    op.create_table(
        "stakeholder_relationships",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("from_stakeholder_id", sa.Integer(), nullable=False),
        sa.Column("to_stakeholder_id", sa.Integer(), nullable=False),
        sa.Column("relationship_type", sa.String(length=20), nullable=False),
        sa.Column("strength", sa.Integer(), nullable=False, server_default="50"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["from_stakeholder_id"], ["stakeholders.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["to_stakeholder_id"], ["stakeholders.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint(
            "relationship_type IN ('reports_to', 'influences', 'collaborates', 'sponsors', 'blocks')",
            name="ck_stakeholder_relationships_type",
        ),
    )
    op.create_index(
        op.f("ix_stakeholder_relationships_from_stakeholder_id"),
        "stakeholder_relationships",
        ["from_stakeholder_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_stakeholder_relationships_to_stakeholder_id"),
        "stakeholder_relationships",
        ["to_stakeholder_id"],
        unique=False,
    )

    # Create stakeholder_entity_links table
    op.create_table(
        "stakeholder_entity_links",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("stakeholder_id", sa.Integer(), nullable=False),
        sa.Column("entity_type", sa.String(length=50), nullable=False),
        sa.Column("entity_id", sa.Integer(), nullable=False),
        sa.Column("interest_level", sa.Integer(), nullable=False, server_default="50"),
        sa.Column("impact_level", sa.Integer(), nullable=False, server_default="50"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["stakeholder_id"], ["stakeholders.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_stakeholder_entity_links_stakeholder_id"), "stakeholder_entity_links", ["stakeholder_id"], unique=False
    )
    op.create_index(
        op.f("ix_stakeholder_entity_links_entity_type"), "stakeholder_entity_links", ["entity_type"], unique=False
    )
    op.create_index(
        "ix_stakeholder_entity_links_entity", "stakeholder_entity_links", ["entity_type", "entity_id"], unique=False
    )


def downgrade():
    # Drop tables (no enum types to drop since we used String with CHECK constraints)
    op.drop_index("ix_stakeholder_entity_links_entity", table_name="stakeholder_entity_links")
    op.drop_index(op.f("ix_stakeholder_entity_links_entity_type"), table_name="stakeholder_entity_links")
    op.drop_index(op.f("ix_stakeholder_entity_links_stakeholder_id"), table_name="stakeholder_entity_links")
    op.drop_table("stakeholder_entity_links")

    op.drop_index(op.f("ix_stakeholder_relationships_to_stakeholder_id"), table_name="stakeholder_relationships")
    op.drop_index(op.f("ix_stakeholder_relationships_from_stakeholder_id"), table_name="stakeholder_relationships")
    op.drop_table("stakeholder_relationships")

    op.drop_index(op.f("ix_stakeholders_department"), table_name="stakeholders")
    op.drop_index(op.f("ix_stakeholders_support_level"), table_name="stakeholders")
    op.drop_index(op.f("ix_stakeholders_organization_id"), table_name="stakeholders")
    op.drop_table("stakeholders")
