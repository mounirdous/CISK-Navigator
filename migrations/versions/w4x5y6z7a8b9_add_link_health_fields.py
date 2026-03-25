"""Add link_status, detected_type, last_checked_at to entity_links

Revision ID: w4x5y6z7a8b9
Revises: v3w4x5y6z7a8
Create Date: 2026-03-25

"""
import sqlalchemy as sa
from alembic import op

revision = "w4x5y6z7a8b9"
down_revision = "v3w4x5y6z7a8"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("entity_links", sa.Column("link_status", sa.String(length=20), nullable=False, server_default="unknown"))
    op.add_column("entity_links", sa.Column("detected_type", sa.String(length=100), nullable=True))
    op.add_column("entity_links", sa.Column("last_checked_at", sa.DateTime(), nullable=True))
    op.create_index("ix_entity_links_link_status", "entity_links", ["link_status"])


def downgrade():
    op.drop_index("ix_entity_links_link_status", table_name="entity_links")
    op.drop_column("entity_links", "last_checked_at")
    op.drop_column("entity_links", "detected_type")
    op.drop_column("entity_links", "link_status")
