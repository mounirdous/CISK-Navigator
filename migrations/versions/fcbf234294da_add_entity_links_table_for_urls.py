"""add_entity_links_table_for_urls

Revision ID: fcbf234294da
Revises: 33275eefdf80
Create Date: 2026-03-15 15:47:52.367457

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'fcbf234294da'
down_revision = '33275eefdf80'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'entity_links',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('entity_type', sa.String(20), nullable=False, comment='Type: space, challenge, initiative, system, kpi'),
        sa.Column('entity_id', sa.Integer(), nullable=False, comment='ID of the entity'),
        sa.Column('url', sa.Text(), nullable=False, comment='The URL/link'),
        sa.Column('title', sa.String(200), nullable=True, comment='Optional description'),
        sa.Column('is_public', sa.Boolean(), nullable=False, default=False, comment='Public (shared) or private link'),
        sa.Column('display_order', sa.Integer(), nullable=False, default=0, comment='Sort order'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=True, onupdate=sa.text('now()')),
        sa.Column('created_by', sa.Integer(), sa.ForeignKey('users.id'), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )

    # Indexes for performance
    op.create_index('ix_entity_links_entity_type_id', 'entity_links', ['entity_type', 'entity_id'])
    op.create_index('ix_entity_links_created_by', 'entity_links', ['created_by'])


def downgrade():
    op.drop_index('ix_entity_links_created_by', 'entity_links')
    op.drop_index('ix_entity_links_entity_type_id', 'entity_links')
    op.drop_table('entity_links')
