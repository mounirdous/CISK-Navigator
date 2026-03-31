"""add no_consensus columns to impact entities

Revision ID: n5i6j7k8l9m0
Revises: 0f4c84e5c919
Create Date: 2026-03-31 20:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "n5i6j7k8l9m0"
down_revision = "0f4c84e5c919"
branch_labels = None
depends_on = None

_tables = ["spaces", "challenges", "initiatives", "systems", "kpis"]


def upgrade():
    for table in _tables:
        op.add_column(
            table,
            sa.Column(
                "impact_no_consensus",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("false"),
                comment="True when assessors could not agree on impact level",
            ),
        )
        op.add_column(
            table,
            sa.Column(
                "impact_no_consensus_note",
                sa.Text(),
                nullable=True,
                comment="Documents the disagreement when no consensus reached",
            ),
        )
    # Organization-level color settings for special impact states
    op.add_column(
        "organizations",
        sa.Column(
            "impact_no_consensus_color",
            sa.String(7),
            nullable=True,
            server_default=sa.text("'#f59e0b'"),
            comment="Hex color for no-consensus impact badge",
        ),
    )
    op.add_column(
        "organizations",
        sa.Column(
            "impact_not_set_color",
            sa.String(7),
            nullable=True,
            server_default=sa.text("'#94a3b8'"),
            comment="Hex color for not-set impact badge",
        ),
    )


def downgrade():
    op.drop_column("organizations", "impact_not_set_color")
    op.drop_column("organizations", "impact_no_consensus_color")
    for table in reversed(_tables):
        op.drop_column(table, "impact_no_consensus_note")
        op.drop_column(table, "impact_no_consensus")
