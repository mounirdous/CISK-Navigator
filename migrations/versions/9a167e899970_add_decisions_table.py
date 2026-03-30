"""add decisions table

Revision ID: 9a167e899970
Revises: 91554d2e4ea0
Create Date: 2026-03-30 13:03:57.043672

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '9a167e899970'
down_revision = '91554d2e4ea0'
branch_labels = None
depends_on = None


def upgrade():
    # Create decisions table (clean — no initiative_id FK)
    op.create_table('decisions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('organization_id', sa.Integer(), nullable=False),
        sa.Column('created_by_id', sa.Integer(), nullable=False),
        sa.Column('what', sa.Text(), nullable=False, comment='Decision description'),
        sa.Column('who', sa.String(length=200), nullable=True, comment='Decision maker / owner'),
        sa.Column('tags', sa.JSON(), nullable=True, comment="Tag categories: ['scope', 'budget', ...]"),
        sa.Column('entity_mentions', sa.JSON(), nullable=True, comment='[{entity_type, entity_id, entity_name}]'),
        sa.Column('governance_body_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['created_by_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['governance_body_id'], ['governance_bodies.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade():
    op.drop_table('decisions')
