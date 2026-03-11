"""add initiative form fields

Revision ID: 9dd04a9578c9
Revises: k1f2g3h4i5j6
Create Date: 2026-03-11 14:30:00

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "9dd04a9578c9"
down_revision = "k1f2g3h4i5j6"
branch_labels = None
depends_on = None


def upgrade():
    # Add new fields for initiative form
    op.add_column("initiatives", sa.Column("mission", sa.Text(), nullable=True))
    op.add_column("initiatives", sa.Column("success_criteria", sa.Text(), nullable=True))
    op.add_column("initiatives", sa.Column("responsible_person", sa.String(200), nullable=True))
    op.add_column("initiatives", sa.Column("team_members", sa.Text(), nullable=True))
    op.add_column("initiatives", sa.Column("handover_organization", sa.String(200), nullable=True))
    op.add_column("initiatives", sa.Column("deliverables", sa.Text(), nullable=True))
    op.add_column("initiatives", sa.Column("group_label", sa.String(1), nullable=True))


def downgrade():
    # Remove columns
    op.drop_column("initiatives", "group_label")
    op.drop_column("initiatives", "deliverables")
    op.drop_column("initiatives", "handover_organization")
    op.drop_column("initiatives", "team_members")
    op.drop_column("initiatives", "responsible_person")
    op.drop_column("initiatives", "success_criteria")
    op.drop_column("initiatives", "mission")
