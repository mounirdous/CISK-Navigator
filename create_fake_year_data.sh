#!/bin/bash
# Create fake contributions and snapshots for a full year of data

flask shell << 'EOF'
from datetime import date
from decimal import Decimal
import random
from app.extensions import db
from app.models import KPIValueTypeConfig, KPI, Initiative, InitiativeSystemLink, Contribution, ValueType
from app.services.snapshot_service import SnapshotService

# Configuration
org_id = 1
user_id = 1

print("🎯 Creating fake year of data for pivot analysis...")
print()

# Get all KPI configs for the organization
configs = (
    db.session.query(KPIValueTypeConfig)
    .join(KPI, KPIValueTypeConfig.kpi_id == KPI.id)
    .join(InitiativeSystemLink, KPI.initiative_system_link_id == InitiativeSystemLink.id)
    .join(Initiative, InitiativeSystemLink.initiative_id == Initiative.id)
    .filter(Initiative.organization_id == org_id)
    .all()
)

print(f"📊 Found {len(configs)} KPI-ValueType configurations")
print()

# Define quarters with dates and trending values
quarters = [
    (date(2026, 3, 31), "Q1 2026", 1, 1.0),    # Base value
    (date(2026, 6, 30), "Q2 2026", 2, 1.15),   # +15%
    (date(2026, 9, 30), "Q3 2026", 3, 1.30),   # +30%
    (date(2026, 12, 31), "Q4 2026", 4, 1.50),  # +50%
]

for snapshot_date, label, quarter, multiplier in quarters:
    print(f"📈 Creating data for {label}")

    # Create fake contributions for each config
    contribution_count = 0
    for config in configs:
        value_type = config.value_type

        # Generate fake value based on type
        if value_type.is_numeric():
            # Numeric values with trending growth
            base_value = random.randint(100, 1000) * 100  # Base between 10k-100k
            value = Decimal(base_value * multiplier)
        else:
            # Qualitative values (1, 2, or 3)
            value = random.choice([1, 2, 3])

        # Delete existing contributions for this config to replace with new values
        Contribution.query.filter_by(
            kpi_value_type_config_id=config.id,
            user_id=user_id
        ).delete()

        # Create contribution
        contribution = Contribution(
            kpi_value_type_config_id=config.id,
            user_id=user_id,
            value=value if value_type.is_numeric() else None,
            qualitative_level=value if not value_type.is_numeric() else None,
        )
        db.session.add(contribution)
        contribution_count += 1

    db.session.commit()
    print(f"   ✅ Created {contribution_count} contributions")

    # Now create snapshots
    try:
        result = SnapshotService.create_organization_snapshot(
            org_id,
            snapshot_date=snapshot_date,
            label=label,
            user_id=user_id,
            is_public=True,
            year_override=2026,
            quarter_override=quarter,
            month_override=snapshot_date.month
        )
        print(f"   ✅ Created {result['kpi_snapshots']} KPI snapshots")
        print(f"   ✅ Created {result['rollup_snapshots']} rollup snapshots")
    except Exception as e:
        print(f"   ❌ Snapshot error: {e}")

    print()

print("✨ Fake year data complete!")
print()
print("🔍 View results at:")
print("   http://localhost:5003/workspace/snapshots/pivot")
print()
print("📊 You should now see:")
print("   - Q1-Q4 2026 data in quarterly view")
print("   - Trending values showing growth over the year")
print("   - Multiple KPIs to compare in chart view")

EOF
