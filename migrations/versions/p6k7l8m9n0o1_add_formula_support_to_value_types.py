"""add formula support to value types

Revision ID: p6k7l8m9n0o1
Revises: 0604faa9fc5b
Create Date: 2026-03-18 14:30:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "p6k7l8m9n0o1"
down_revision = "0604faa9fc5b"
branch_labels = None
depends_on = None


def upgrade():
    # Add calculation_type column (default to 'manual')
    op.add_column(
        "value_types",
        sa.Column(
            "calculation_type",
            sa.String(length=20),
            nullable=False,
            server_default="manual",
            comment="manual or formula",
        ),
    )

    # Add calculation_config column (JSON for formula configuration)
    op.add_column(
        "value_types",
        sa.Column(
            "calculation_config",
            sa.JSON(),
            nullable=True,
            comment="Formula definition: {operation: 'add', source_value_type_ids: [1, 2]}",
        ),
    )


def downgrade():
    op.drop_column("value_types", "calculation_config")
    op.drop_column("value_types", "calculation_type")
