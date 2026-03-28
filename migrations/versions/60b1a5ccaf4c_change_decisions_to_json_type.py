"""change decisions to JSON type

Revision ID: 60b1a5ccaf4c
Revises: 46e8f568eb5e
Create Date: 2026-03-28 23:02:29.113865

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '60b1a5ccaf4c'
down_revision = '46e8f568eb5e'
branch_labels = None
depends_on = None


def upgrade():
    # First set any existing text values to NULL (can't auto-cast text to json)
    op.execute("UPDATE initiative_progress_updates SET decisions = NULL WHERE decisions IS NOT NULL")
    with op.batch_alter_table('initiative_progress_updates', schema=None) as batch_op:
        batch_op.alter_column('decisions',
               existing_type=sa.TEXT(),
               type_=sa.JSON(),
               comment='Structured decisions: [{what, who, tag, mentions}, ...]',
               existing_nullable=True,
               postgresql_using='decisions::json')


def downgrade():
    with op.batch_alter_table('initiative_progress_updates', schema=None) as batch_op:
        batch_op.alter_column('decisions',
               existing_type=sa.JSON(),
               type_=sa.TEXT(),
               existing_nullable=True)
