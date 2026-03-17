"""add_site_to_stakeholders

Revision ID: 7a2248e4f425
Revises: d4110fa013f9
Create Date: 2026-03-17 21:58:38.477781

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "7a2248e4f425"
down_revision = "d4110fa013f9"
branch_labels = None
depends_on = None


def upgrade():
    # Check if column already exists
    from sqlalchemy import inspect

    bind = op.get_bind()
    inspector = inspect(bind)

    columns = [col["name"] for col in inspector.get_columns("stakeholders")]

    if "site_id" not in columns:
        # Add site_id column to stakeholders table
        op.add_column("stakeholders", sa.Column("site_id", sa.Integer(), nullable=True))

        # Add foreign key constraint
        op.create_foreign_key(
            "fk_stakeholders_site_id", "stakeholders", "geography_sites", ["site_id"], ["id"], ondelete="SET NULL"
        )
        print("✓ Added site_id column to stakeholders table")
    else:
        print("→ Column site_id already exists in stakeholders table, skipping")


def downgrade():
    # Check if column exists before trying to drop it
    from sqlalchemy import inspect

    bind = op.get_bind()
    inspector = inspect(bind)

    columns = [col["name"] for col in inspector.get_columns("stakeholders")]

    if "site_id" in columns:
        # Drop foreign key first
        op.drop_constraint("fk_stakeholders_site_id", "stakeholders", type_="foreignkey")
        # Drop column
        op.drop_column("stakeholders", "site_id")
        print("✓ Removed site_id column from stakeholders table")
    else:
        print("→ Column site_id doesn't exist in stakeholders table, skipping")
