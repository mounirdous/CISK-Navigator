#!/bin/bash
# Create test snapshots for Q1-Q4 2026 using Flask shell

flask shell << 'EOF'
from datetime import date
from app.services.snapshot_service import SnapshotService
from flask import session

# Set organization ID (change if needed)
org_id = 1
user_id = 1

quarters = [
    (date(2026, 3, 31), "Q1 2026", 1, 1),
    (date(2026, 6, 30), "Q2 2026", 2, 6),
    (date(2026, 9, 30), "Q3 2026", 3, 9),
    (date(2026, 12, 31), "Q4 2026", 4, 12),
]

print("🎯 Creating test snapshots for quarters Q1-Q4 2026...")
print()

for snapshot_date, label, quarter, month in quarters:
    print(f"📊 Creating: {label}")
    try:
        result = SnapshotService.create_organization_snapshot(
            org_id,
            snapshot_date=snapshot_date,
            label=label,
            user_id=user_id,
            is_public=True,
            year_override=2026,
            quarter_override=quarter,
            month_override=month
        )
        print(f"   ✅ {result['kpi_snapshots']} KPI snapshots, {result['rollup_snapshots']} rollups")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    print()

print("✨ Complete! View at: http://localhost:5003/workspace/snapshots/pivot")
EOF
