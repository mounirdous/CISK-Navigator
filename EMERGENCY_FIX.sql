-- EMERGENCY FIX FOR PRODUCTION
-- Run this directly on Render PostgreSQL if migration hasn't applied yet

-- Add missing columns to kpi_snapshots
ALTER TABLE kpi_snapshots
ADD COLUMN IF NOT EXISTS is_public BOOLEAN NOT NULL DEFAULT true;

ALTER TABLE kpi_snapshots
ADD COLUMN IF NOT EXISTS owner_user_id INTEGER;

ALTER TABLE kpi_snapshots
ADD CONSTRAINT fk_kpi_snapshots_owner
FOREIGN KEY (owner_user_id) REFERENCES users(id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS ix_kpi_snapshots_public ON kpi_snapshots(is_public);
CREATE INDEX IF NOT EXISTS ix_kpi_snapshots_owner ON kpi_snapshots(owner_user_id);

-- Add missing columns to rollup_snapshots
ALTER TABLE rollup_snapshots
ADD COLUMN IF NOT EXISTS is_public BOOLEAN NOT NULL DEFAULT true;

ALTER TABLE rollup_snapshots
ADD COLUMN IF NOT EXISTS owner_user_id INTEGER;

ALTER TABLE rollup_snapshots
ADD CONSTRAINT fk_rollup_snapshots_owner
FOREIGN KEY (owner_user_id) REFERENCES users(id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS ix_rollup_snapshots_public ON rollup_snapshots(is_public);
CREATE INDEX IF NOT EXISTS ix_rollup_snapshots_owner ON rollup_snapshots(owner_user_id);

-- Verify columns were added
\d kpi_snapshots
\d rollup_snapshots
