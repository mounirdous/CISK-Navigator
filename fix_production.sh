#!/bin/bash
# EMERGENCY FIX SCRIPT
# Usage: ./fix_production.sh "your-render-external-database-url"

if [ -z "$1" ]; then
    echo "Usage: ./fix_production.sh 'postgresql://user:pass@host/db'"
    echo ""
    echo "Get the URL from Render:"
    echo "1. Go to cisk-navigator-db"
    echo "2. Click Connect dropdown"
    echo "3. Click External tab"
    echo "4. Copy the URL"
    exit 1
fi

DATABASE_URL="$1"

echo "🚨 Applying emergency fix to production database..."
echo ""

psql "$DATABASE_URL" <<'EOF'
-- Add missing columns to kpi_snapshots
ALTER TABLE kpi_snapshots ADD COLUMN IF NOT EXISTS is_public BOOLEAN NOT NULL DEFAULT true;
ALTER TABLE kpi_snapshots ADD COLUMN IF NOT EXISTS owner_user_id INTEGER;
ALTER TABLE kpi_snapshots ADD CONSTRAINT fk_kpi_snapshots_owner FOREIGN KEY (owner_user_id) REFERENCES users(id) ON DELETE SET NULL;
CREATE INDEX IF NOT EXISTS ix_kpi_snapshots_public ON kpi_snapshots(is_public);
CREATE INDEX IF NOT EXISTS ix_kpi_snapshots_owner ON kpi_snapshots(owner_user_id);

-- Add missing columns to rollup_snapshots
ALTER TABLE rollup_snapshots ADD COLUMN IF NOT EXISTS is_public BOOLEAN NOT NULL DEFAULT true;
ALTER TABLE rollup_snapshots ADD COLUMN IF NOT EXISTS owner_user_id INTEGER;
ALTER TABLE rollup_snapshots ADD CONSTRAINT fk_rollup_snapshots_owner FOREIGN KEY (owner_user_id) REFERENCES users(id) ON DELETE SET NULL;
CREATE INDEX IF NOT EXISTS ix_rollup_snapshots_public ON rollup_snapshots(is_public);
CREATE INDEX IF NOT EXISTS ix_rollup_snapshots_owner ON rollup_snapshots(owner_user_id);

-- Verify
SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'kpi_snapshots' AND column_name IN ('is_public', 'owner_user_id');
EOF

echo ""
echo "✅ Production database fixed!"
echo "🔄 Wait for Render deployment to complete and your app will be back online."
