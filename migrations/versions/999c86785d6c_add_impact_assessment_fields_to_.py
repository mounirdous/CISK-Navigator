"""Add impact assessment fields to Initiative

Revision ID: 999c86785d6c
Revises: 2c605d815e90
Create Date: 2026-03-15 14:28:16.872494

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '999c86785d6c'
down_revision = '2c605d815e90'
branch_labels = None
depends_on = None


def upgrade():
    # Add impact assessment fields to initiatives table
    op.add_column(
        'initiatives',
        sa.Column(
            'impact_on_challenge',
            sa.String(length=20),
            nullable=True,
            comment='Impact level on challenge: not_assessed, low, medium, high, no_consensus'
        )
    )
    op.add_column(
        'initiatives',
        sa.Column(
            'impact_rationale',
            sa.Text(),
            nullable=True,
            comment='Rationale and opinions about the impact assessment'
        )
    )

    # Set default value for existing rows
    op.execute("UPDATE initiatives SET impact_on_challenge = 'not_assessed' WHERE impact_on_challenge IS NULL")


def downgrade():
    # Remove impact assessment fields
    op.drop_column('initiatives', 'impact_rationale')
    op.drop_column('initiatives', 'impact_on_challenge')
