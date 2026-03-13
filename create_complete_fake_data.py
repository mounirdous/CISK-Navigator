#!/usr/bin/env python3
"""
Create complete fake data: KPIs, contributions, and snapshots for a full year.
"""

import random
import sys
from datetime import date
from decimal import Decimal

# Add app to path
sys.path.insert(0, "/Users/mounir.dous/projects/CISK-Navigator")

from app import create_app
from app.extensions import db
from app.models import (
    KPI,
    Challenge,
    ChallengeInitiativeLink,
    Contribution,
    Initiative,
    InitiativeSystemLink,
    KPIValueTypeConfig,
    Organization,
    Space,
    System,
    ValueType,
)
from app.services.snapshot_service import SnapshotService


def create_fake_data():
    # Force development config to use PostgreSQL
    import os

    os.environ["FLASK_ENV"] = "development"
    app = create_app("development")

    with app.app_context():
        # Get organization
        org = Organization.query.first()
        if not org:
            print("❌ No organization found. Please create an organization first.")
            return

        org_id = org.id
        user_id = 1

        print(f"🏢 Using organization: {org.name} (ID: {org_id})")
        print()

        # Check for existing KPIs
        existing_configs = (
            db.session.query(KPIValueTypeConfig)
            .join(KPI, KPIValueTypeConfig.kpi_id == KPI.id)
            .join(InitiativeSystemLink, KPI.initiative_system_link_id == InitiativeSystemLink.id)
            .join(Initiative, InitiativeSystemLink.initiative_id == Initiative.id)
            .filter(Initiative.organization_id == org_id)
            .count()
        )

        if existing_configs > 0:
            print(f"✅ Found {existing_configs} existing KPI configurations")
            configs = (
                db.session.query(KPIValueTypeConfig)
                .join(KPI, KPIValueTypeConfig.kpi_id == KPI.id)
                .join(InitiativeSystemLink, KPI.initiative_system_link_id == InitiativeSystemLink.id)
                .join(Initiative, InitiativeSystemLink.initiative_id == Initiative.id)
                .filter(Initiative.organization_id == org_id)
                .all()
            )
        else:
            print("📝 Creating fake KPIs structure...")
            configs = create_fake_kpis(org_id)
            print(f"✅ Created {len(configs)} KPI configurations")

        print()
        print("📊 Creating quarterly snapshots with trending data...")
        print()

        # Define quarters with trending multipliers
        quarters = [
            (date(2026, 3, 31), "Q1 2026", 1, 1.0),
            (date(2026, 6, 30), "Q2 2026", 2, 1.15),
            (date(2026, 9, 30), "Q3 2026", 3, 1.30),
            (date(2026, 12, 31), "Q4 2026", 4, 1.50),
        ]

        for snapshot_date, label, quarter, multiplier in quarters:
            print(f"📈 {label} (multiplier: {multiplier:.0%})")

            # Create contributions for each config
            for config in configs:
                value_type = config.value_type

                # Generate fake value
                if value_type.is_numeric():
                    base_value = random.randint(500, 2000)
                    value = Decimal(base_value * multiplier)
                else:
                    value = random.choice([1, 2, 3])

                # Delete old contributions for this config
                Contribution.query.filter_by(kpi_value_type_config_id=config.id).delete()

                # Create new contribution
                contribution = Contribution(
                    kpi_value_type_config_id=config.id,
                    contributor_name="TestUser",
                    numeric_value=value if value_type.is_numeric() else None,
                    qualitative_level=value if not value_type.is_numeric() else None,
                )
                db.session.add(contribution)

            db.session.commit()

            # Create snapshots
            result = SnapshotService.create_organization_snapshot(
                org_id,
                snapshot_date=snapshot_date,
                label=label,
                user_id=user_id,
                is_public=True,
                year_override=2026,
                quarter_override=quarter,
                month_override=snapshot_date.month,
            )

            print(f"   ✅ {result['kpi_snapshots']} KPI snapshots, {result['rollup_snapshots']} rollups")

        print()
        print("✨ Complete! View your data at:")
        print("   http://localhost:5003/workspace/snapshots/pivot")
        print()


def create_fake_kpis(org_id):
    """Create fake KPI structure if none exists"""

    # Get or create space
    space = Space.query.filter_by(organization_id=org_id).first()
    if not space:
        space = Space(organization_id=org_id, name="Test Space", display_order=1)
        db.session.add(space)
        db.session.flush()

    # Get or create challenge
    challenge = Challenge.query.filter_by(space_id=space.id).first()
    if not challenge:
        challenge = Challenge(space_id=space.id, name="Test Challenge", display_order=1)
        db.session.add(challenge)
        db.session.flush()

    # Get or create initiative
    initiative = Initiative.query.filter_by(organization_id=org_id).first()
    if not initiative:
        initiative = Initiative(organization_id=org_id, name="Test Initiative", display_order=1)
        db.session.add(initiative)
        db.session.flush()

        # Link challenge to initiative
        link = ChallengeInitiativeLink(challenge_id=challenge.id, initiative_id=initiative.id, display_order=1)
        db.session.add(link)
        db.session.flush()

    # Get or create system
    system = System.query.filter_by(organization_id=org_id).first()
    if not system:
        system = System(organization_id=org_id, name="Test System", display_order=1)
        db.session.add(system)
        db.session.flush()

    # Create initiative-system link
    init_sys_link = InitiativeSystemLink.query.filter_by(initiative_id=initiative.id, system_id=system.id).first()

    if not init_sys_link:
        init_sys_link = InitiativeSystemLink(initiative_id=initiative.id, system_id=system.id, display_order=1)
        db.session.add(init_sys_link)
        db.session.flush()

    # Get value types
    value_types = ValueType.query.filter_by(organization_id=org_id, is_active=True).limit(3).all()

    if not value_types:
        print("❌ No value types found. Please create value types first.")
        return []

    # Create KPIs
    kpi_names = ["Revenue", "Cost", "Customer Satisfaction", "Efficiency", "Quality"]
    configs = []

    for i, kpi_name in enumerate(kpi_names):
        # Check if KPI exists
        existing_kpi = KPI.query.filter_by(initiative_system_link_id=init_sys_link.id, name=kpi_name).first()

        if existing_kpi:
            kpi = existing_kpi
        else:
            kpi = KPI(initiative_system_link_id=init_sys_link.id, name=kpi_name, display_order=i + 1)
            db.session.add(kpi)
            db.session.flush()

        # Create KPI-ValueType configs
        for vt in value_types[:2]:  # Use first 2 value types
            existing_config = KPIValueTypeConfig.query.filter_by(kpi_id=kpi.id, value_type_id=vt.id).first()

            if not existing_config:
                config = KPIValueTypeConfig(kpi_id=kpi.id, value_type_id=vt.id, display_order=1)
                db.session.add(config)
                configs.append(config)
            else:
                configs.append(existing_config)

    db.session.commit()
    return configs


if __name__ == "__main__":
    create_fake_data()
