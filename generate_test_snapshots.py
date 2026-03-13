#!/usr/bin/env python3
"""
Generate test snapshot data for pivot analysis demonstration.

Creates snapshots for Q1-Q4 2026 with trending values.
"""

from datetime import date

from flask import session

from app import create_app
from app.services.snapshot_service import SnapshotService


def generate_test_snapshots():
    """Generate test snapshots across multiple quarters"""
    app = create_app()

    with app.app_context():
        # You'll need to set your organization ID here
        org_id = 1  # Change this to your actual organization ID

        # Define quarters with dates and labels
        quarters = [
            (date(2026, 3, 31), "Q1 2026", 1, 2026, 1),  # Q1: Jan-Mar
            (date(2026, 6, 30), "Q2 2026", 2, 2026, 2),  # Q2: Apr-Jun
            (date(2026, 9, 30), "Q3 2026", 3, 2026, 3),  # Q3: Jul-Sep
            (date(2026, 12, 31), "Q4 2026", 4, 2026, 4),  # Q4: Oct-Dec
        ]

        print("🎯 Generating test snapshots for pivot analysis...")
        print(f"Organization ID: {org_id}")
        print()

        for snapshot_date, label, quarter, year, _ in quarters:
            print(f"📊 Creating snapshot: {label} ({snapshot_date})")

            try:
                result = SnapshotService.create_organization_snapshot(
                    org_id,
                    snapshot_date=snapshot_date,
                    label=label,
                    user_id=1,  # Change to your user ID if needed
                    is_public=True,
                    year_override=year,
                    quarter_override=quarter,
                    month_override=snapshot_date.month,
                )

                print(f"   ✅ Created {result['kpi_count']} KPI snapshots")
                print(f"   ✅ Created {result['rollup_count']} rollup snapshots")
                print(f"   📦 Batch ID: {result['batch_id']}")

            except Exception as e:
                print(f"   ❌ Error: {e}")

            print()

        print("✨ Test data generation complete!")
        print()
        print("🔍 View results at:")
        print("   http://localhost:5003/workspace/snapshots/pivot")
        print()
        print("💡 Tip: Try different view types:")
        print("   - Quarterly: See Q1-Q4 trends")
        print("   - Monthly: See month-by-month detail")
        print("   - Yearly: Compare across years")


if __name__ == "__main__":
    generate_test_snapshots()
