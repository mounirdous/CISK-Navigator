#!/usr/bin/env python3
"""
Organization Restore Script

Restores organization data from YAML backup files.
Use this for disaster recovery or cloning organization structures.

Usage:
    python scripts/restore_org.py --file backup.yaml --org-id 1 --dry-run
    python scripts/restore_org.py --file backup.yaml.gz --org-id 1
    python scripts/restore_org.py --file backup.yaml --org-id 1 --mode replace
"""
import os
import sys
import argparse
import gzip
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Must import app after path setup
from app import create_app
from app.models import Organization
from app.services.yaml_import_service import YAMLImportService


def restore_organization(file_path, org_id, dry_run=False, mode='merge'):
    """
    Restore organization from YAML backup

    Args:
        file_path: Path to backup YAML file
        org_id: Target organization ID
        dry_run: If True, validate but don't save to database
        mode: 'merge' (add to existing) or 'replace' (clear and restore)
    """
    app = create_app()
    with app.app_context():
        # Validate organization exists
        org = Organization.query.get(org_id)
        if not org:
            print(f"❌ Organization with ID {org_id} not found")
            return 1

        # Check file exists
        backup_file = Path(file_path)
        if not backup_file.exists():
            print(f"❌ Backup file not found: {file_path}")
            return 1

        print("=" * 70)
        if dry_run:
            print("🔍 DRY RUN MODE - VALIDATING BACKUP")
        else:
            print("🔄 RESTORING ORGANIZATION FROM BACKUP")
        print("=" * 70)
        print()

        print(f"📂 Backup file: {file_path}")
        print(f"📊 Target organization: {org.name} (ID: {org.id})")
        print(f"🔧 Mode: {mode.upper()}")
        if dry_run:
            print(f"⚠️  DRY RUN: No changes will be saved to database")
        print()

        # Read backup file (handle gzip compression)
        print("📖 Reading backup file...")
        if file_path.endswith('.gz'):
            print("   (Decompressing gzip...)")
            with gzip.open(file_path, 'rt', encoding='utf-8') as f:
                yaml_content = f.read()
        else:
            with open(file_path, 'r', encoding='utf-8') as f:
                yaml_content = f.read()

        # Extract metadata from comments (if present)
        lines = yaml_content.split('\n')
        metadata = {}
        for line in lines:
            if line.startswith('# Organization:'):
                metadata['org_name'] = line.split(':', 1)[1].strip()
            elif line.startswith('# Backup Date:'):
                metadata['backup_date'] = line.split(':', 1)[1].strip()
            elif line.startswith('# Organization ID:'):
                metadata['backup_org_id'] = line.split(':', 1)[1].strip()

        if metadata:
            print("📋 Backup metadata:")
            if 'org_name' in metadata:
                print(f"   Original organization: {metadata['org_name']}")
            if 'backup_org_id' in metadata:
                print(f"   Original org ID: {metadata['backup_org_id']}")
            if 'backup_date' in metadata:
                print(f"   Backup date: {metadata['backup_date']}")
            print()

        # Import from YAML
        print("🔄 Importing data...")
        print()

        try:
            result = YAMLImportService.import_from_string(
                yaml_content,
                org_id,
                dry_run=dry_run
            )

            # Display statistics
            print("=" * 70)
            print("📊 IMPORT STATISTICS")
            print("=" * 70)
            print(f"   Value Types: {result['value_types']}")
            print(f"   Spaces: {result['spaces']}")
            print(f"   Challenges: {result['challenges']}")
            print(f"   Initiatives: {result['initiatives']}")
            print(f"   Systems: {result['systems']}")
            print(f"   KPIs: {result['kpis']}")
            print()

            # Display errors
            if result['errors']:
                print("⚠️  ERRORS ENCOUNTERED:")
                for error in result['errors']:
                    print(f"   • {error}")
                print()

            # Success message
            print("=" * 70)
            if dry_run:
                print("✅ VALIDATION COMPLETED")
                print("=" * 70)
                print()
                print("Backup file is valid and ready to restore.")
                print("To apply changes to database, run without --dry-run:")
                print(f"   python scripts/restore_org.py --file {file_path} --org-id {org_id}")
            else:
                print("✅ RESTORE COMPLETED SUCCESSFULLY")
                print("=" * 70)
                print()
                print(f"Organization '{org.name}' has been restored from backup.")
                if result['errors']:
                    print(f"⚠️  Note: {len(result['errors'])} items had errors (see above)")
            print()

            return 0 if not result['errors'] else 2

        except Exception as e:
            print()
            print("=" * 70)
            print("❌ RESTORE FAILED")
            print("=" * 70)
            print(f"Error: {str(e)}")
            print()
            import traceback
            traceback.print_exc()
            return 1


def main():
    parser = argparse.ArgumentParser(
        description='Restore CISK Navigator organization from YAML backup',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  Validate backup (dry-run):
    python scripts/restore_org.py --file backup.yaml --org-id 1 --dry-run

  Restore to organization:
    python scripts/restore_org.py --file backup.yaml --org-id 1

  Restore compressed backup:
    python scripts/restore_org.py --file backup.yaml.gz --org-id 1

  Replace mode (clear existing data first):
    python scripts/restore_org.py --file backup.yaml --org-id 1 --mode replace

Notes:
  - Default mode is 'merge' which adds to existing organization data
  - Use --dry-run to validate backup file without making changes
  - Compressed (.gz) files are automatically detected and decompressed
        """
    )

    parser.add_argument('--file', required=True,
                        help='Path to backup YAML file')
    parser.add_argument('--org-id', type=int, required=True,
                        help='Target organization ID')
    parser.add_argument('--dry-run', action='store_true',
                        help='Validate backup without saving to database')
    parser.add_argument('--mode', choices=['merge', 'replace'], default='merge',
                        help='Restore mode: merge (add to existing) or replace (clear first)')

    args = parser.parse_args()

    # Run restore
    return restore_organization(args.file, args.org_id, args.dry_run, args.mode)


if __name__ == '__main__':
    sys.exit(main())
