"""store logos as binary data in database

Revision ID: 1269a7d04dcd
Revises: o5j6k7l8m9n0
Create Date: 2026-03-14 17:10:01.226172

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "1269a7d04dcd"
down_revision = "o5j6k7l8m9n0"
branch_labels = None
depends_on = None


def upgrade():
    # Organization: Replace logo_path with logo_data and logo_mime_type
    op.drop_column("organizations", "logo_path")
    op.add_column(
        "organizations", sa.Column("logo_data", sa.LargeBinary, nullable=True, comment="Logo image binary data")
    )
    op.add_column(
        "organizations",
        sa.Column("logo_mime_type", sa.String(length=50), nullable=True, comment="Logo MIME type (e.g., image/png)"),
    )

    # Add logo columns to all entity types
    op.add_column("spaces", sa.Column("logo_data", sa.LargeBinary, nullable=True, comment="Logo image binary data"))
    op.add_column("spaces", sa.Column("logo_mime_type", sa.String(length=50), nullable=True, comment="Logo MIME type"))

    op.add_column("challenges", sa.Column("logo_data", sa.LargeBinary, nullable=True, comment="Logo image binary data"))
    op.add_column(
        "challenges", sa.Column("logo_mime_type", sa.String(length=50), nullable=True, comment="Logo MIME type")
    )

    op.add_column(
        "initiatives", sa.Column("logo_data", sa.LargeBinary, nullable=True, comment="Logo image binary data")
    )
    op.add_column(
        "initiatives", sa.Column("logo_mime_type", sa.String(length=50), nullable=True, comment="Logo MIME type")
    )

    op.add_column("systems", sa.Column("logo_data", sa.LargeBinary, nullable=True, comment="Logo image binary data"))
    op.add_column("systems", sa.Column("logo_mime_type", sa.String(length=50), nullable=True, comment="Logo MIME type"))

    op.add_column("kpis", sa.Column("logo_data", sa.LargeBinary, nullable=True, comment="Logo image binary data"))
    op.add_column("kpis", sa.Column("logo_mime_type", sa.String(length=50), nullable=True, comment="Logo MIME type"))


def downgrade():
    # Remove logo columns from all entity types
    op.drop_column("kpis", "logo_mime_type")
    op.drop_column("kpis", "logo_data")

    op.drop_column("systems", "logo_mime_type")
    op.drop_column("systems", "logo_data")

    op.drop_column("initiatives", "logo_mime_type")
    op.drop_column("initiatives", "logo_data")

    op.drop_column("challenges", "logo_mime_type")
    op.drop_column("challenges", "logo_data")

    op.drop_column("spaces", "logo_mime_type")
    op.drop_column("spaces", "logo_data")

    # Organization: Restore logo_path
    op.drop_column("organizations", "logo_mime_type")
    op.drop_column("organizations", "logo_data")
    op.add_column(
        "organizations",
        sa.Column("logo_path", sa.String(length=500), nullable=True, comment="Path to organization logo file"),
    )
