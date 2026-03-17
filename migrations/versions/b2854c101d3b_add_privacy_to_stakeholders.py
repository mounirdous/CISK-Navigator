"""add_privacy_to_stakeholders

Revision ID: b2854c101d3b
Revises: 55cabdbb3a13
Create Date: 2026-03-17 17:12:02.048721

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "b2854c101d3b"
down_revision = "55cabdbb3a13"
branch_labels = None
depends_on = None


def upgrade():
    # Add privacy columns to stakeholders table with idempotency
    from sqlalchemy import inspect

    bind = op.get_bind()
    inspector = inspect(bind)

    # Check if table exists
    existing_tables = inspector.get_table_names()
    if "stakeholders" not in existing_tables:
        # Table doesn't exist, skip
        return

    # Check if columns already exist
    columns = [col["name"] for col in inspector.get_columns("stakeholders")]

    if "created_by_user_id" not in columns:
        op.add_column("stakeholders", sa.Column("created_by_user_id", sa.Integer(), nullable=True))
        op.create_foreign_key(
            "fk_stakeholders_created_by", "stakeholders", "users", ["created_by_user_id"], ["id"], ondelete="SET NULL"
        )

    if "visibility" not in columns:
        op.add_column(
            "stakeholders", sa.Column("visibility", sa.String(length=20), nullable=False, server_default="shared")
        )
        op.create_index(op.f("ix_stakeholders_visibility"), "stakeholders", ["visibility"], unique=False)
        # Add CHECK constraint for visibility
        op.execute(
            "ALTER TABLE stakeholders ADD CONSTRAINT ck_stakeholders_visibility CHECK (visibility IN ('private', 'shared'))"
        )


def downgrade():
    # Remove privacy columns
    from sqlalchemy import inspect

    bind = op.get_bind()
    inspector = inspect(bind)

    # Check if table exists
    existing_tables = inspector.get_table_names()
    if "stakeholders" not in existing_tables:
        return

    # Check which columns exist before dropping
    columns = [col["name"] for col in inspector.get_columns("stakeholders")]

    if "visibility" in columns:
        op.execute("ALTER TABLE stakeholders DROP CONSTRAINT IF EXISTS ck_stakeholders_visibility")
        op.drop_index(op.f("ix_stakeholders_visibility"), table_name="stakeholders")
        op.drop_column("stakeholders", "visibility")

    if "created_by_user_id" in columns:
        op.drop_constraint("fk_stakeholders_created_by", "stakeholders", type_="foreignkey")
        op.drop_column("stakeholders", "created_by_user_id")
