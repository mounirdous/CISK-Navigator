"""Add period tags to snapshots (year, quarter, month)

Revision ID: 3e602a96475c
Revises: m3h4i5j6k7l8
Create Date: 2026-03-13 19:23:08.385872

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "3e602a96475c"
down_revision = "m3h4i5j6k7l8"
branch_labels = None
depends_on = None


def upgrade():
    # Add period tag columns to kpi_snapshots
    op.add_column("kpi_snapshots", sa.Column("year", sa.Integer(), nullable=True))
    op.add_column("kpi_snapshots", sa.Column("quarter", sa.Integer(), nullable=True))
    op.add_column("kpi_snapshots", sa.Column("month", sa.Integer(), nullable=True))

    # Add period tag columns to rollup_snapshots
    op.add_column("rollup_snapshots", sa.Column("year", sa.Integer(), nullable=True))
    op.add_column("rollup_snapshots", sa.Column("quarter", sa.Integer(), nullable=True))
    op.add_column("rollup_snapshots", sa.Column("month", sa.Integer(), nullable=True))

    # Create indexes for efficient period filtering
    op.create_index("idx_kpi_snapshot_period", "kpi_snapshots", ["year", "quarter", "month"])
    op.create_index("idx_rollup_snapshot_period", "rollup_snapshots", ["year", "quarter", "month"])

    # Backfill period tags from snapshot_date for existing snapshots
    op.execute(
        """
        UPDATE kpi_snapshots
        SET year = EXTRACT(YEAR FROM snapshot_date)::INTEGER,
            quarter = EXTRACT(QUARTER FROM snapshot_date)::INTEGER,
            month = EXTRACT(MONTH FROM snapshot_date)::INTEGER
        WHERE snapshot_date IS NOT NULL
    """
    )

    op.execute(
        """
        UPDATE rollup_snapshots
        SET year = EXTRACT(YEAR FROM snapshot_date)::INTEGER,
            quarter = EXTRACT(QUARTER FROM snapshot_date)::INTEGER,
            month = EXTRACT(MONTH FROM snapshot_date)::INTEGER
        WHERE snapshot_date IS NOT NULL
    """
    )


def downgrade():
    # Drop indexes
    op.drop_index("idx_rollup_snapshot_period", table_name="rollup_snapshots")
    op.drop_index("idx_kpi_snapshot_period", table_name="kpi_snapshots")

    # Drop columns
    op.drop_column("rollup_snapshots", "month")
    op.drop_column("rollup_snapshots", "quarter")
    op.drop_column("rollup_snapshots", "year")
    op.drop_column("kpi_snapshots", "month")
    op.drop_column("kpi_snapshots", "quarter")
    op.drop_column("kpi_snapshots", "year")
