"""add default logo to entity type defaults

Revision ID: 5da7a6743629
Revises: fa186a958344
Create Date: 2026-03-14 17:55:58.743280

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "5da7a6743629"
down_revision = "fa186a958344"
branch_labels = None
depends_on = None


def upgrade():
    # Add default logo columns to entity_type_defaults
    op.add_column(
        "entity_type_defaults",
        sa.Column(
            "default_logo_data",
            sa.LargeBinary,
            nullable=True,
            comment="Default logo image binary data for this entity type",
        ),
    )
    op.add_column(
        "entity_type_defaults",
        sa.Column("default_logo_mime_type", sa.String(length=50), nullable=True, comment="Default logo MIME type"),
    )


def downgrade():
    # Remove default logo columns
    op.drop_column("entity_type_defaults", "default_logo_mime_type")
    op.drop_column("entity_type_defaults", "default_logo_data")
