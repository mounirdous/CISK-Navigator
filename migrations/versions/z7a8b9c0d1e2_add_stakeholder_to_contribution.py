"""add stakeholder_id to contributions

Revision ID: z7a8b9c0d1e2
Revises: y6z7a8b9c0d1
Create Date: 2026-04-02
"""
import sqlalchemy as sa
from alembic import op

revision = "z7a8b9c0d1e2"
down_revision = "y6z7a8b9c0d1"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("contributions", sa.Column("stakeholder_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_contributions_stakeholder_id", "contributions", "stakeholders",
        ["stakeholder_id"], ["id"], ondelete="SET NULL"
    )


def downgrade():
    op.drop_constraint("fk_contributions_stakeholder_id", "contributions", type_="foreignkey")
    op.drop_column("contributions", "stakeholder_id")
