"""add_snapshot_batch_id

Revision ID: f2d6dc7cbc3a
Revises: e5b7f9c3a6d8
Create Date: 2026-03-09 13:29:27.137836

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f2d6dc7cbc3a'
down_revision = 'e5b7f9c3a6d8'
branch_labels = None
depends_on = None


def upgrade():
    # Add snapshot_batch_id to kpi_snapshots
    op.add_column('kpi_snapshots', sa.Column('snapshot_batch_id', sa.String(36), nullable=True))

    # Add snapshot_batch_id to rollup_snapshots
    op.add_column('rollup_snapshots', sa.Column('snapshot_batch_id', sa.String(36), nullable=True))

    # Populate existing snapshots with batch IDs based on date + truncated timestamp + label
    # This groups snapshots created within the same second with the same label into one batch
    op.execute("""
        WITH snapshot_batches AS (
            SELECT
                DATE_TRUNC('second', created_at) as batch_time,
                snapshot_date,
                snapshot_label,
                MD5(snapshot_date::text || DATE_TRUNC('second', created_at)::text || COALESCE(snapshot_label, ''))::uuid as batch_id
            FROM kpi_snapshots
            GROUP BY snapshot_date, DATE_TRUNC('second', created_at), snapshot_label
        )
        UPDATE kpi_snapshots
        SET snapshot_batch_id = batch_id::text
        FROM snapshot_batches
        WHERE DATE_TRUNC('second', kpi_snapshots.created_at) = snapshot_batches.batch_time
          AND kpi_snapshots.snapshot_date = snapshot_batches.snapshot_date
          AND COALESCE(kpi_snapshots.snapshot_label, '') = COALESCE(snapshot_batches.snapshot_label, '')
    """)

    op.execute("""
        WITH snapshot_batches AS (
            SELECT
                DATE_TRUNC('second', created_at) as batch_time,
                snapshot_date,
                snapshot_label,
                MD5(snapshot_date::text || DATE_TRUNC('second', created_at)::text || COALESCE(snapshot_label, ''))::uuid as batch_id
            FROM rollup_snapshots
            GROUP BY snapshot_date, DATE_TRUNC('second', created_at), snapshot_label
        )
        UPDATE rollup_snapshots
        SET snapshot_batch_id = batch_id::text
        FROM snapshot_batches
        WHERE DATE_TRUNC('second', rollup_snapshots.created_at) = snapshot_batches.batch_time
          AND rollup_snapshots.snapshot_date = snapshot_batches.snapshot_date
          AND COALESCE(rollup_snapshots.snapshot_label, '') = COALESCE(snapshot_batches.snapshot_label, '')
    """)

    # Make snapshot_batch_id NOT NULL after populating
    op.alter_column('kpi_snapshots', 'snapshot_batch_id', nullable=False)
    op.alter_column('rollup_snapshots', 'snapshot_batch_id', nullable=False)

    # Add index for faster lookups
    op.create_index('ix_kpi_snapshots_batch_id', 'kpi_snapshots', ['snapshot_batch_id'])
    op.create_index('ix_rollup_snapshots_batch_id', 'rollup_snapshots', ['snapshot_batch_id'])


def downgrade():
    op.drop_index('ix_kpi_snapshots_batch_id', 'kpi_snapshots')
    op.drop_index('ix_rollup_snapshots_batch_id', 'rollup_snapshots')
    op.drop_column('kpi_snapshots', 'snapshot_batch_id')
    op.drop_column('rollup_snapshots', 'snapshot_batch_id')
