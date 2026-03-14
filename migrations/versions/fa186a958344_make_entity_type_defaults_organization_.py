"""make entity type defaults organization specific

Revision ID: fa186a958344
Revises: 1269a7d04dcd
Create Date: 2026-03-14 17:24:34.572191

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "fa186a958344"
down_revision = "1269a7d04dcd"
branch_labels = None
depends_on = None


def upgrade():
    # Drop unique index on entity_type
    op.drop_index("ix_entity_type_defaults_entity_type", table_name="entity_type_defaults")

    # Add organization_id column (nullable initially)
    op.add_column("entity_type_defaults", sa.Column("organization_id", sa.Integer(), nullable=True))

    # Populate organization_id with first organization's ID for existing rows
    op.execute(
        """
        UPDATE entity_type_defaults
        SET organization_id = (SELECT id FROM organizations ORDER BY id LIMIT 1)
        WHERE organization_id IS NULL
    """
    )

    # Make organization_id non-nullable
    op.alter_column("entity_type_defaults", "organization_id", nullable=False)

    # Add foreign key to organizations
    op.create_foreign_key(
        "fk_entity_type_defaults_organization",
        "entity_type_defaults",
        "organizations",
        ["organization_id"],
        ["id"],
        ondelete="CASCADE",
    )

    # Add composite unique constraint (organization_id, entity_type)
    op.create_unique_constraint(
        "uq_entity_type_defaults_org_type", "entity_type_defaults", ["organization_id", "entity_type"]
    )


def downgrade():
    # Drop composite unique constraint
    op.drop_constraint("uq_entity_type_defaults_org_type", "entity_type_defaults", type_="unique")

    # Drop foreign key
    op.drop_constraint("fk_entity_type_defaults_organization", "entity_type_defaults", type_="foreignkey")

    # Drop organization_id column
    op.drop_column("entity_type_defaults", "organization_id")

    # Restore unique index on entity_type
    op.create_index("ix_entity_type_defaults_entity_type", "entity_type_defaults", ["entity_type"], unique=True)
