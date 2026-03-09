# CISK Navigator Scripts

Utility scripts for database management, backups, and system maintenance.

## Backup & Restore Scripts

### backup_org.py

Create timestamped backups of organization data for disaster recovery.

**Features:**
- Exports complete organization structure to YAML
- Includes spaces, challenges, initiatives, systems, KPIs, and value types
- Optional gzip compression
- Timestamped filenames
- Metadata tracking (org name, backup date, entity counts)

**Usage:**

```bash
# List all organizations
python scripts/backup_org.py --list-orgs

# Backup specific organization
python scripts/backup_org.py --org-id 1

# Backup to custom directory
python scripts/backup_org.py --org-id 1 --output-dir /path/to/backups/

# Backup with compression
python scripts/backup_org.py --org-id 1 --compress
```

**Examples:**

```bash
# Backup MIK organization to default location
python scripts/backup_org.py --org-id 1

# Output: backups/backup_mik_20260309_143022.yaml

# Compressed backup for large organizations
python scripts/backup_org.py --org-id 1 --output-dir /var/backups/cisk --compress

# Output: /var/backups/cisk/backup_mik_20260309_143022.yaml.gz
```

### restore_org.py

Restore organization data from YAML backup files.

**Features:**
- Validates backup integrity
- Dry-run mode for safety
- Automatic decompression of .gz files
- Metadata extraction from backup
- Detailed import statistics
- Merge or replace modes (future enhancement)

**Usage:**

```bash
# Validate backup without applying changes (dry-run)
python scripts/restore_org.py --file backup.yaml --org-id 1 --dry-run

# Restore to organization
python scripts/restore_org.py --file backup.yaml --org-id 1

# Restore compressed backup
python scripts/restore_org.py --file backup.yaml.gz --org-id 1

# Future: Replace mode (clear existing data first)
python scripts/restore_org.py --file backup.yaml --org-id 1 --mode replace
```

**Examples:**

```bash
# ALWAYS test with dry-run first
python scripts/restore_org.py --file backups/backup_mik_20260309_143022.yaml --org-id 1 --dry-run

# If validation passes, apply the restore
python scripts/restore_org.py --file backups/backup_mik_20260309_143022.yaml --org-id 1

# Clone structure to different organization
python scripts/restore_org.py --file backups/backup_mik_20260309_143022.yaml --org-id 2
```

**Restore Output:**

```
📊 IMPORT STATISTICS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   Value Types: 5
   Spaces: 3
   Challenges: 4
   Initiatives: 5
   Systems: 5
   KPIs: 9
```

## Migration Health Check

### check_migrations.py

Validates migration chain integrity before deployment.

**Features:**
- Verifies all migrations have valid revision IDs
- Checks down_revision references are valid
- Detects cycles in migration chain
- Warns about dangerous operations (DROP TABLE, ALTER COLUMN)
- Visualizes migration chain

**Usage:**

```bash
python scripts/check_migrations.py
```

**Example Output:**

```
🔍 Found 15 migration files

✅ All migrations have revision IDs
✅ Migration head(s): ['a8c4b3e7d2f6']
✅ All down_revision references are valid
✅ No cycles detected in migration chain

📋 Migration Chain:

  Chain from a8c4b3e7d2f6:
    ↓ a8c4b3e7d2f6... (add_is_private_to_spaces.py)
      ↓ f5c8a9b3d2e4... (add_snapshot_privacy_columns.py)
        ↓ c8f5a9b2e3d1... (add_display_scale_to_kpi_configs.py)
```

## Best Practices

### Backup Schedule

**Recommended Schedule:**
- **Production:** Daily automated backups (keep last 30 days)
- **Development:** Weekly backups before major changes
- **Before Migrations:** Always backup before deploying schema changes
- **Before Deletions:** Backup before deleting organizations or large datasets

**Automated Backup (Cron):**

```bash
# Daily backup at 2 AM
0 2 * * * cd /path/to/CISK-Navigator && DATABASE_URL="postgresql://..." python scripts/backup_org.py --org-id 1 --output-dir /backups/cisk --compress

# Cleanup old backups (keep last 30 days)
0 3 * * * find /backups/cisk -name "backup_*.yaml.gz" -mtime +30 -delete
```

### Disaster Recovery Workflow

1. **Verify backup integrity:**
   ```bash
   python scripts/restore_org.py --file backup.yaml.gz --org-id 1 --dry-run
   ```

2. **Check migration status** (if database corrupted):
   ```bash
   python scripts/check_migrations.py
   ```

3. **Restore data:**
   ```bash
   python scripts/restore_org.py --file backup.yaml.gz --org-id 1
   ```

4. **Verify restoration** via web UI or health dashboard

### Cloning Organizations

Use backups to clone organizational structures:

```bash
# 1. Backup source organization
python scripts/backup_org.py --org-id 1 --output-dir /tmp

# 2. Create new empty organization via web UI

# 3. Restore backup to new organization
python scripts/restore_org.py --file /tmp/backup_mik_20260309_143022.yaml --org-id 5
```

## Environment Variables

Scripts automatically use the Flask app's database configuration. To override:

```bash
# Use PostgreSQL
DATABASE_URL="postgresql://localhost/cisknavigator" python scripts/backup_org.py --org-id 1

# Use custom PostgreSQL connection
DATABASE_URL="postgresql://user:pass@host:5432/dbname" python scripts/backup_org.py --org-id 1
```

## Troubleshooting

### "Organization with ID X not found"
- Run `--list-orgs` to see available organizations
- Verify you're using the correct database (check DATABASE_URL)

### "Backup file not found"
- Check file path is correct
- Use absolute paths for clarity
- Verify file permissions

### "Import errors encountered"
- Common causes: duplicate names, missing foreign keys
- Check error messages in output
- Use --dry-run to validate before applying

### "No such column" errors
- Migrations may not be applied
- Run `python scripts/check_migrations.py`
- Apply missing migrations before running scripts

## Security Notes

- **Backup files contain sensitive data** - store securely
- **Restrict access** to backup directories (chmod 700)
- **Encrypt backups** for production environments
- **Never commit backups** to version control (.gitignore backups/)
- **Rotate backup credentials** regularly
- **Test restore process** regularly (quarterly recommended)

## File Locations

- **Scripts:** `scripts/`
- **Default backup dir:** `backups/` (auto-created)
- **Migrations:** `migrations/versions/`
- **Logs:** Check Flask app logs for script execution

## Support

For issues or questions:
1. Check script help: `python scripts/<script>.py --help`
2. Review logs and error messages
3. Consult MEMORY.md for project-specific guidance
4. Check GitHub issues: https://github.com/anthropics/claude-code/issues
