#!/usr/bin/env python3
"""
Create complete fake dataset: 10 KPIs with monthly snapshots from 2024-2026
"""

import os
import random
from datetime import date
from decimal import Decimal

# Force development config
os.environ["FLASK_ENV"] = "development"

from app import create_app  # noqa: E402
from app.extensions import db  # noqa: E402
from app.models import (  # noqa: E402
    KPI,
    Challenge,
    ChallengeInitiativeLink,
    Initiative,
    InitiativeSystemLink,
    KPISnapshot,
    KPIValueTypeConfig,
    Space,
    System,
    ValueType,
)


def create_full_dataset():
    app = create_app("development")

    with app.app_context():
        print("=" * 80)
        print("🚀 CREATING COMPLETE FAKE DATASET")
        print("=" * 80)
        print()

        # Get organization - USE ORG 33 (MIKRON_AUTOMATION)
        from app.models import Organization

        org = Organization.query.filter_by(id=33).first()
        if not org:
            print("❌ Organization 33 (MIKRON_AUTOMATION) not found")
            return

        print(f"✅ Using organization: {org.name} (ID: {org.id})")
        print()

        # Get or create Test Space
        space = Space.query.filter_by(organization_id=org.id, name="Fake Data Space").first()
        if not space:
            space = Space(
                organization_id=org.id,
                name="Fake Data Space",
                description="Test space with fake KPIs for pivot analysis",
                display_order=999,
                is_private=False,
            )
            db.session.add(space)
            db.session.flush()
            print(f"✅ Created Space: {space.name} (ID: {space.id})")
        else:
            print(f"✅ Using existing Space: {space.name} (ID: {space.id})")

        # Get or create Challenge
        challenge = Challenge.query.filter_by(space_id=space.id, name="Performance Tracking").first()
        if not challenge:
            challenge = Challenge(
                organization_id=org.id,
                space_id=space.id,
                name="Performance Tracking",
                description="Track key performance metrics",
                display_order=1,
            )
            db.session.add(challenge)
            db.session.flush()
            print(f"✅ Created Challenge: {challenge.name} (ID: {challenge.id})")
        else:
            print(f"✅ Using existing Challenge: {challenge.name} (ID: {challenge.id})")

        # Get or create Initiative
        initiative = Initiative.query.filter_by(organization_id=org.id, name="Operational Excellence").first()
        if not initiative:
            initiative = Initiative(
                organization_id=org.id, name="Operational Excellence", description="Improve operational metrics"
            )
            db.session.add(initiative)
            db.session.flush()
            print(f"✅ Created Initiative: {initiative.name} (ID: {initiative.id})")
        else:
            print(f"✅ Using existing Initiative: {initiative.name} (ID: {initiative.id})")

        # Link Challenge to Initiative
        link = ChallengeInitiativeLink.query.filter_by(challenge_id=challenge.id, initiative_id=initiative.id).first()
        if not link:
            link = ChallengeInitiativeLink(challenge_id=challenge.id, initiative_id=initiative.id, display_order=1)
            db.session.add(link)
            db.session.flush()
            print("✅ Linked Challenge to Initiative")

        # Get or create System
        system = System.query.filter_by(organization_id=org.id, name="Core Operations").first()
        if not system:
            system = System(organization_id=org.id, name="Core Operations", description="Core operational system")
            db.session.add(system)
            db.session.flush()
            print(f"✅ Created System: {system.name} (ID: {system.id})")
        else:
            print(f"✅ Using existing System: {system.name} (ID: {system.id})")

        # Link Initiative to System
        init_sys_link = InitiativeSystemLink.query.filter_by(initiative_id=initiative.id, system_id=system.id).first()
        if not init_sys_link:
            init_sys_link = InitiativeSystemLink(initiative_id=initiative.id, system_id=system.id, display_order=1)
            db.session.add(init_sys_link)
            db.session.flush()
            print("✅ Linked Initiative to System")

        # Get value types (case-sensitive names)
        cost_vt = ValueType.query.filter_by(organization_id=org.id, name="Cost").first()
        time_vt = ValueType.query.filter_by(organization_id=org.id, name="Time to deliver").first()

        if not cost_vt or not time_vt:
            print("❌ Required value types (Cost, Time to Deliver) not found")
            return

        print(f"✅ Found value types: Cost (ID: {cost_vt.id}), Time (ID: {time_vt.id})")
        print()

        # Define 10 KPIs with realistic values - demonstrating all 3 target types
        kpi_definitions = [
            # MAXIMIZE targets (at or above)
            {
                "name": "Revenue",
                "vt": cost_vt,
                "base": 500000,
                "trend": "up",
                "volatility": 0.05,
                "target": 750000,
                "target_date": date(2026, 12, 31),
                "target_direction": "maximize",
            },
            {
                "name": "Customer Satisfaction Score",
                "vt": cost_vt,
                "base": 85,
                "trend": "up",
                "volatility": 0.03,
                "target": 90,
                "target_date": date(2026, 6, 30),
                "target_direction": "maximize",
            },
            # MINIMIZE targets (at or below)
            {
                "name": "Operating Costs",
                "vt": cost_vt,
                "base": 350000,
                "trend": "down",
                "volatility": 0.03,
                "target": 300000,
                "target_date": date(2026, 12, 31),
                "target_direction": "minimize",
            },
            {
                "name": "Customer Acquisition Cost",
                "vt": cost_vt,
                "base": 45000,
                "trend": "down",
                "volatility": 0.06,
                "target": 35000,
                "target_date": date(2026, 12, 31),
                "target_direction": "minimize",
            },
            {
                "name": "Support Response Time",
                "vt": time_vt,
                "base": 24,
                "trend": "down",
                "volatility": 0.12,
                "target": 12,
                "target_date": date(2026, 9, 30),
                "target_direction": "minimize",
            },
            # EXACT targets (at with band)
            {
                "name": "Product Development Time",
                "vt": time_vt,
                "base": 120,
                "trend": "stable",
                "volatility": 0.10,
                "target": 90,
                "target_date": date(2026, 9, 30),
                "target_direction": "exact",
                "target_tolerance_pct": 15,
            },
            {
                "name": "Inventory Turnover Days",
                "vt": time_vt,
                "base": 45,
                "trend": "stable",
                "volatility": 0.08,
                "target": 45,
                "target_date": date(2026, 12, 31),
                "target_direction": "exact",
                "target_tolerance_pct": 10,
            },
            # NO TARGET examples
            {"name": "Marketing Spend", "vt": cost_vt, "base": 80000, "trend": "up", "volatility": 0.08},
            {"name": "R&D Budget", "vt": cost_vt, "base": 120000, "trend": "up", "volatility": 0.04},
            {"name": "Infrastructure Costs", "vt": cost_vt, "base": 95000, "trend": "stable", "volatility": 0.02},
        ]

        print("📊 Creating 10 KPIs with configurations...")
        print()

        configs = []
        for idx, kpi_def in enumerate(kpi_definitions):
            # Check if KPI exists
            kpi = KPI.query.filter_by(initiative_system_link_id=init_sys_link.id, name=kpi_def["name"]).first()

            if not kpi:
                kpi = KPI(
                    initiative_system_link_id=init_sys_link.id,
                    name=kpi_def["name"],
                    description=f"Tracking {kpi_def['name'].lower()} over time",
                    display_order=idx + 1,
                )
                db.session.add(kpi)
                db.session.flush()
                print(f"  ✅ Created KPI: {kpi.name} (ID: {kpi.id})")
            else:
                print(f"  ℹ️  Using existing KPI: {kpi.name} (ID: {kpi.id})")

            # Create config
            config = KPIValueTypeConfig.query.filter_by(kpi_id=kpi.id, value_type_id=kpi_def["vt"].id).first()

            if not config:
                config = KPIValueTypeConfig(kpi_id=kpi.id, value_type_id=kpi_def["vt"].id, display_order=1)
                db.session.add(config)
                db.session.flush()

            # Update target if specified in definition
            if "target" in kpi_def:
                config.target_value = Decimal(str(kpi_def["target"]))
                config.target_date = kpi_def.get("target_date")
                config.target_direction = kpi_def.get("target_direction", "maximize")
                config.target_tolerance_pct = kpi_def.get("target_tolerance_pct", 10)
                direction_label = config.target_direction
                if config.target_direction == "exact":
                    direction_label = f"exact ±{config.target_tolerance_pct}%"
                print(f"    🎯 Set target: {config.target_value} by {config.target_date} ({direction_label})")

            configs.append({"config": config, "kpi": kpi, "definition": kpi_def})

        db.session.commit()
        print()
        print(f"✅ Created/verified {len(configs)} KPI configurations")
        print()

        # Delete existing snapshots for these configs
        print("🧹 Cleaning up old snapshots...")
        config_ids = [c["config"].id for c in configs]
        deleted = KPISnapshot.query.filter(KPISnapshot.kpi_value_type_config_id.in_(config_ids)).delete(
            synchronize_session=False
        )
        db.session.commit()
        print(f"  ✅ Deleted {deleted} old snapshots")
        print()

        # Generate monthly snapshots: Jan 2024 - Dec 2026 (36 months)
        print("📅 Creating monthly snapshots: 2024-2026 (36 months)...")
        print()

        months = []
        for year in [2024, 2025, 2026]:
            for month in range(1, 13):
                # Last day of month
                if month == 12:
                    snapshot_date = date(year, month, 31)
                elif month in [4, 6, 9, 11]:
                    snapshot_date = date(year, month, 30)
                elif month == 2:
                    snapshot_date = date(year, month, 28)
                else:
                    snapshot_date = date(year, month, 31)

                quarter = (month - 1) // 3 + 1
                months.append(
                    {
                        "date": snapshot_date,
                        "year": year,
                        "month": month,
                        "quarter": quarter,
                        "label": f"{snapshot_date.strftime('%B %Y')}",
                        "month_index": (year - 2024) * 12 + month - 1,  # 0-35
                    }
                )

        snapshot_count = 0
        for month_data in months:
            month_idx = month_data["month_index"]

            for config_data in configs:
                config = config_data["config"]
                definition = config_data["definition"]

                # Calculate value with trend
                base = definition["base"]
                trend = definition["trend"]
                volatility = definition["volatility"]

                # Apply trend over 36 months
                if trend == "up":
                    # 30% growth over 3 years
                    trend_factor = 1 + (0.30 * month_idx / 35)
                elif trend == "down":
                    # 20% reduction over 3 years
                    trend_factor = 1 - (0.20 * month_idx / 35)
                else:  # stable
                    trend_factor = 1

                # Add random volatility
                random_factor = 1 + random.uniform(-volatility, volatility)

                value = Decimal(base * trend_factor * random_factor)

                # Create snapshot
                snapshot = KPISnapshot(
                    kpi_value_type_config_id=config.id,
                    snapshot_date=month_data["date"],
                    snapshot_label=month_data["label"],
                    year=month_data["year"],
                    quarter=month_data["quarter"],
                    month=month_data["month"],
                    snapshot_batch_id=f"fake-{month_data['date'].isoformat()}",
                    consensus_status="strong_consensus",
                    consensus_value=value,
                    contributor_count=1,
                    is_rollup_eligible=True,
                    is_public=True,
                    created_by_user_id=1,
                )
                db.session.add(snapshot)
                snapshot_count += 1

            if month_idx % 6 == 5:  # Progress every 6 months
                db.session.commit()
                print(f"  ✅ {month_data['label']}: {len(configs)} snapshots created")

        db.session.commit()
        print()
        print(f"✅ Created {snapshot_count} total snapshots")
        print("   = 10 KPIs × 36 months × 1 value type")
        print()
        print("=" * 80)
        print("✨ DATASET CREATION COMPLETE!")
        print("=" * 80)
        print()
        print("🔍 View your data at:")
        print("   http://localhost:5003/workspace/snapshots/pivot")
        print()
        print("💡 Try different views:")
        print("   - Monthly: See all 36 months of data")
        print("   - Quarterly: See Q1-Q4 for each year")
        print("   - Yearly: Compare 2024, 2025, 2026")
        print()
        print("📊 Features to explore:")
        print("   - Select KPIs by checking boxes")
        print("   - Switch to Chart View for visualizations")
        print("   - Filter by Space: 'Fake Data Space'")
        print()


if __name__ == "__main__":
    create_full_dataset()
