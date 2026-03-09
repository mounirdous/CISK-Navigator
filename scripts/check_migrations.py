#!/usr/bin/env python3
"""
Migration Health Check Script

Validates migration chain integrity before deployment.
Run this before every commit that includes migrations.

Usage:
    python scripts/check_migrations.py
"""
import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def check_migration_chain():
    """Verify all migrations have valid revision chain"""
    migrations_dir = project_root / "migrations" / "versions"

    if not migrations_dir.exists():
        print("❌ Migrations directory not found!")
        return False

    migration_files = list(migrations_dir.glob("*.py"))
    migration_files = [f for f in migration_files if not f.name.startswith("__")]

    print(f"🔍 Found {len(migration_files)} migration files")
    print()

    # Parse all migrations
    migrations = {}
    errors = []

    for migration_file in migration_files:
        content = migration_file.read_text()

        # Extract revision and down_revision
        revision = None
        down_revision = None

        for line in content.split("\n"):
            if line.startswith("revision = "):
                revision = line.split("=")[1].strip().strip("'\"")
            elif line.startswith("down_revision = "):
                down_revision = line.split("=")[1].strip().strip("'\"")
                if down_revision == "None":
                    down_revision = None

        if not revision:
            errors.append(f"❌ {migration_file.name}: No revision ID found")
            continue

        migrations[revision] = {"file": migration_file.name, "down_revision": down_revision, "revision": revision}

    if errors:
        print("\n".join(errors))
        return False

    # Check for duplicates
    print("✅ All migrations have revision IDs")

    # Build chain
    heads = []
    for rev, data in migrations.items():
        if data["down_revision"] is None:
            heads.append(rev)

    if len(heads) == 0:
        print("❌ No migration head found (no migration with down_revision=None)")
        return False

    if len(heads) > 1:
        print(f"⚠️  Multiple heads found: {heads}")
        print("   This might indicate branched migration history")

    print(f"✅ Migration head(s): {heads}")

    # Check all down_revisions point to existing migrations
    missing_refs = []
    for rev, data in migrations.items():
        if data["down_revision"] and data["down_revision"] not in migrations:
            missing_refs.append(f"❌ {data['file']}: down_revision '{data['down_revision']}' not found")

    if missing_refs:
        print("\n".join(missing_refs))
        return False

    print("✅ All down_revision references are valid")

    # Check for cycles
    visited = set()

    def has_cycle(rev, path=None):
        if path is None:
            path = []
        if rev in path:
            return True
        if rev is None or rev in visited:
            return False
        visited.add(rev)
        path.append(rev)
        down = migrations[rev]["down_revision"]
        return has_cycle(down, path)

    for rev in migrations:
        if has_cycle(rev):
            print(f"❌ Cycle detected in migration chain starting at {rev}")
            return False

    print("✅ No cycles detected in migration chain")

    # Print chain
    print("\n📋 Migration Chain:")

    # Find leaf (most recent migration)
    children = {rev: [] for rev in migrations}
    for rev, data in migrations.items():
        if data["down_revision"]:
            children[data["down_revision"]].append(rev)

    # Find nodes with no children (leaves)
    leaves = [rev for rev in migrations if not children[rev]]

    if len(leaves) > 1:
        print(f"⚠️  Multiple leaf migrations (possible branches): {leaves}")

    # Trace from each leaf to root
    for leaf in leaves:
        print(f"\n  Chain from {leaf}:")
        current = leaf
        depth = 0
        while current and depth < 100:  # Prevent infinite loop
            data = migrations[current]
            print(f"    {'  ' * depth}↓ {current[:12]}... ({data['file']})")
            current = data["down_revision"]
            depth += 1

        if depth >= 100:
            print("    ⚠️  Chain too deep, possible cycle")

    return True


def check_migration_syntax():
    """Check that all migrations have proper upgrade/downgrade functions"""
    migrations_dir = project_root / "migrations" / "versions"
    migration_files = [f for f in migrations_dir.glob("*.py") if not f.name.startswith("__")]

    print("\n🔍 Checking migration syntax...")
    errors = []

    for migration_file in migration_files:
        content = migration_file.read_text()

        if "def upgrade():" not in content:
            errors.append(f"❌ {migration_file.name}: Missing upgrade() function")

        if "def downgrade():" not in content:
            errors.append(f"❌ {migration_file.name}: Missing downgrade() function")

    if errors:
        print("\n".join(errors))
        return False

    print("✅ All migrations have upgrade() and downgrade() functions")
    return True


def check_dangerous_operations():
    """Warn about potentially dangerous migration operations"""
    migrations_dir = project_root / "migrations" / "versions"
    migration_files = [f for f in migrations_dir.glob("*.py") if not f.name.startswith("__")]

    print("\n🔍 Checking for dangerous operations...")
    warnings = []

    dangerous_patterns = {
        "DROP TABLE": "⚠️  Dropping tables (data loss)",
        "DROP COLUMN": "⚠️  Dropping columns (data loss)",
        "ALTER COLUMN": "⚠️  Altering columns (may lock table)",
        "NOT NULL": "⚠️  Adding NOT NULL (check server_default)",
    }

    for migration_file in migration_files:
        content = migration_file.read_text()

        for pattern, warning in dangerous_patterns.items():
            if pattern in content.upper():
                warnings.append(f"  {migration_file.name}: {warning}")

    if warnings:
        print("⚠️  Potentially dangerous operations found:")
        print("\n".join(warnings))
        print("\n  Review these carefully before deploying!")
    else:
        print("✅ No obviously dangerous operations detected")

    return True


def main():
    print("=" * 70)
    print("🏥 MIGRATION HEALTH CHECK")
    print("=" * 70)
    print()

    success = True

    # Check migration chain
    if not check_migration_chain():
        success = False

    # Check syntax
    if not check_migration_syntax():
        success = False

    # Check dangerous operations
    check_dangerous_operations()

    print()
    print("=" * 70)
    if success:
        print("✅ ALL CHECKS PASSED - Migrations are healthy!")
    else:
        print("❌ CHECKS FAILED - Fix issues before deploying!")
    print("=" * 70)

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
