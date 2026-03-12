"""support_multiple_orgs_in_announcements

Revision ID: 0d21cf9d82e7
Revises: 0724f618001f
Create Date: 2026-03-12 17:01:42.868808

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "0d21cf9d82e7"
down_revision = "0724f618001f"
branch_labels = None
depends_on = None


def upgrade():
    # Create announcement_target_organizations table
    op.create_table(
        "announcement_target_organizations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("announcement_id", sa.Integer(), nullable=False),
        sa.Column("organization_id", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["announcement_id"], ["system_announcements.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
    )
    op.create_index(
        op.f("ix_announcement_target_organizations_organization_id"),
        "announcement_target_organizations",
        ["organization_id"],
        unique=False,
    )

    # Migrate existing single organization targets to the new table
    connection = op.get_bind()
    result = connection.execute(
        sa.text(
            "SELECT id, target_organization_id FROM system_announcements WHERE target_type = 'organization' AND target_organization_id IS NOT NULL"
        )
    )
    for row in result:
        connection.execute(
            sa.text(
                "INSERT INTO announcement_target_organizations (announcement_id, organization_id) VALUES (:ann_id, :org_id)"
            ),
            {"ann_id": row[0], "org_id": row[1]},
        )

    # Update target_type from 'organization' to 'organizations'
    connection.execute(
        sa.text("UPDATE system_announcements SET target_type = 'organizations' WHERE target_type = 'organization'")
    )

    # Drop the old target_organization_id column
    op.drop_constraint("system_announcements_target_organization_id_fkey", "system_announcements", type_="foreignkey")
    op.drop_column("system_announcements", "target_organization_id")


def downgrade():
    # Add back the target_organization_id column
    op.add_column("system_announcements", sa.Column("target_organization_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "system_announcements_target_organization_id_fkey",
        "system_announcements",
        "organizations",
        ["target_organization_id"],
        ["id"],
    )

    # Migrate data back (take first organization from junction table)
    connection = op.get_bind()
    result = connection.execute(
        sa.text("SELECT DISTINCT announcement_id, organization_id FROM announcement_target_organizations")
    )
    for row in result:
        connection.execute(
            sa.text("UPDATE system_announcements SET target_organization_id = :org_id WHERE id = :ann_id"),
            {"org_id": row[1], "ann_id": row[0]},
        )

    # Update target_type back
    connection.execute(
        sa.text("UPDATE system_announcements SET target_type = 'organization' WHERE target_type = 'organizations'")
    )

    # Drop the junction table
    op.drop_index(
        op.f("ix_announcement_target_organizations_organization_id"), table_name="announcement_target_organizations"
    )
    op.drop_table("announcement_target_organizations")
