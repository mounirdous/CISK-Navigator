#!/usr/bin/env python3
"""
Organization Backup Script

Exports organization data to YAML backup files with metadata.
Run this regularly to create backups for disaster recovery.

Usage:
    python scripts/backup_org.py --org-id 1
    python scripts/backup_org.py --org-id 1 --output-dir backups/
    python scripts/backup_org.py --org-id 1 --compress
    python scripts/backup_org.py --list-orgs
"""
import os
import sys
import argparse
import gzip
from pathlib import Path
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Must import app after path setup
from app import create_app
from app.models import Organization, Space, Challenge, Initiative, System, KPI, ValueType, InitiativeSystemLink
from app.services.yaml_export_service import YAMLExportService
from app.extensions import db


def list_organizations():
    """List all organizations"""
    app = create_app()
    with app.app_context():
        orgs = Organization.query.order_by(Organization.name).all()

        if not orgs:
            print("No organizations found")
            return

        print("\n" + "=" * 70)
        print("AVAILABLE ORGANIZATIONS")
        print("=" * 70)

        for org in orgs:
            status = "ACTIVE" if org.is_active else "INACTIVE"
            print(f"\nID: {org.id}")
            print(f"Name: {org.name}")
            print(f"Status: {status}")
            if org.description:
                print(f"Description: {org.description}")

            # Get entity counts
            space_count = Space.query.filter_by(organization_id=org.id).count()
            challenge_count = Challenge.query.filter_by(organization_id=org.id).count()
            initiative_count = Initiative.query.filter_by(organization_id=org.id).count()
            system_count = System.query.filter_by(organization_id=org.id).count()

            # Count KPIs through the hierarchy (System -> InitiativeSystemLink -> KPI)
            kpi_count = db.session.query(KPI).join(
                InitiativeSystemLink, KPI.initiative_system_link_id == InitiativeSystemLink.id
            ).join(
                System, InitiativeSystemLink.system_id == System.id
            ).filter(System.organization_id == org.id).count()

            vt_count = ValueType.query.filter_by(organization_id=org.id).count()

            print(f"Entities: {space_count} spaces, {challenge_count} challenges, "
                  f"{initiative_count} initiatives, {system_count} systems, "
                  f"{kpi_count} KPIs, {vt_count} value types")

        print("\n" + "=" * 70)


def backup_organization(org_id, output_dir, compress=False):
    """
    Backup organization to YAML file

    Args:
        org_id: Organization ID to backup
        output_dir: Directory to save backup file
        compress: Whether to gzip compress the backup
    """
    app = create_app()
    with app.app_context():
        # Get organization
        org = Organization.query.get(org_id)
        if not org:
            print(f"❌ Organization with ID {org_id} not found")
            return 1

        print("=" * 70)
        print(f"🔄 BACKING UP ORGANIZATION: {org.name}")
        print("=" * 70)
        print()

        # Get entity counts for reporting
        space_count = Space.query.filter_by(organization_id=org_id).count()
        challenge_count = Challenge.query.filter_by(organization_id=org_id).count()
        initiative_count = Initiative.query.filter_by(organization_id=org_id).count()
        system_count = System.query.filter_by(organization_id=org_id).count()

        # Count KPIs through the hierarchy
        kpi_count = db.session.query(KPI).join(
            InitiativeSystemLink, KPI.initiative_system_link_id == InitiativeSystemLink.id
        ).join(
            System, InitiativeSystemLink.system_id == System.id
        ).filter(System.organization_id == org_id).count()

        vt_count = ValueType.query.filter_by(organization_id=org_id).count()

        print(f"📊 Organization Details:")
        print(f"   ID: {org.id}")
        print(f"   Name: {org.name}")
        print(f"   Status: {'ACTIVE' if org.is_active else 'INACTIVE'}")
        print()

        print(f"📦 Entities to backup:")
        print(f"   • {space_count} Spaces")
        print(f"   • {challenge_count} Challenges")
        print(f"   • {initiative_count} Initiatives")
        print(f"   • {system_count} Systems")
        print(f"   • {kpi_count} KPIs")
        print(f"   • {vt_count} Value Types")
        print()

        # Export to YAML
        print("🔄 Exporting to YAML...")
        yaml_content = YAMLExportService.export_to_yaml(org_id)

        # Add metadata header
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        metadata = f"""# CISK Navigator Organization Backup
# Organization: {org.name}
# Organization ID: {org.id}
# Backup Date: {timestamp}
# Backup Version: 1.0
#
# This file contains the complete structure of the organization:
# - Value Types ({vt_count})
# - Spaces ({space_count})
# - Challenges ({challenge_count})
# - Initiatives ({initiative_count})
# - Systems ({system_count})
# - KPIs ({kpi_count})
#
# To restore: python scripts/restore_org.py --file <this-file> --org-id <target-org-id>
#

"""
        full_content = metadata + yaml_content

        # Create output directory
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        # Generate filename
        safe_org_name = org.name.lower().replace(' ', '-').replace('/', '-')
        timestamp_str = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"backup_{safe_org_name}_{timestamp_str}.yaml"

        if compress:
            filename += ".gz"

        file_path = output_path / filename

        # Save file
        print(f"💾 Saving backup to: {file_path}")

        if compress:
            with gzip.open(file_path, 'wt', encoding='utf-8') as f:
                f.write(full_content)
        else:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(full_content)

        # Get file size
        file_size = file_path.stat().st_size
        size_mb = file_size / (1024 * 1024)

        print()
        print("=" * 70)
        print("✅ BACKUP COMPLETED SUCCESSFULLY")
        print("=" * 70)
        print(f"   File: {file_path}")
        print(f"   Size: {size_mb:.2f} MB")
        print(f"   Compressed: {'Yes' if compress else 'No'}")
        print()
        print("To restore this backup:")
        print(f"   python scripts/restore_org.py --file {file_path} --org-id {org_id}")
        print()

        return 0


def main():
    parser = argparse.ArgumentParser(
        description='Backup CISK Navigator organization to YAML file',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  List all organizations:
    python scripts/backup_org.py --list-orgs

  Backup organization:
    python scripts/backup_org.py --org-id 1

  Backup to specific directory:
    python scripts/backup_org.py --org-id 1 --output-dir /backups/cisk/

  Backup with compression:
    python scripts/backup_org.py --org-id 1 --compress
        """
    )

    parser.add_argument('--list-orgs', action='store_true',
                        help='List all available organizations')
    parser.add_argument('--org-id', type=int,
                        help='Organization ID to backup')
    parser.add_argument('--output-dir', default='backups',
                        help='Directory to save backup file (default: backups/)')
    parser.add_argument('--compress', action='store_true',
                        help='Compress backup with gzip')

    args = parser.parse_args()

    # List organizations
    if args.list_orgs:
        list_organizations()
        return 0

    # Validate required arguments
    if not args.org_id:
        parser.print_help()
        print("\n❌ Error: --org-id is required (or use --list-orgs to see available organizations)")
        return 1

    # Run backup
    return backup_organization(args.org_id, args.output_dir, args.compress)


if __name__ == '__main__':
    sys.exit(main())
