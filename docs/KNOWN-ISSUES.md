# Known Issues & Gotchas

**Last Updated:** 2026-03-18

This document tracks known issues, gotchas, and lessons learned from bugs.

---

## Implicit Relationships (CRITICAL)

**Issue:** Some models use `backref` instead of explicit `back_populates` relationships.

**Why It's Bad:**
- Creates invisible relationships
- No control over cascade behavior
- SQLAlchemy default is to SET NULL, not CASCADE DELETE
- Can cause IntegrityError with NOT NULL constraints

**Example Bug (2026-03-10):**
```python
# BAD: Implicit relationship
class RollupSnapshot(db.Model):
    value_type_id = db.Column(db.Integer, db.ForeignKey("value_types.id"), nullable=False)
    value_type = db.relationship("ValueType", backref="rollup_snapshots")  # Creates implicit relationship on ValueType
```

**Result:** When ValueType is deleted, SQLAlchemy tries to SET NULL on value_type_id, fails due to NOT NULL constraint.

**Fix:**
```python
# GOOD: Explicit relationship with cascade
# In ValueType model:
rollup_snapshots = db.relationship("RollupSnapshot", back_populates="value_type", cascade="all, delete-orphan")

# In RollupSnapshot model:
value_type_id = db.Column(db.Integer, db.ForeignKey("value_types.id", ondelete="CASCADE"), nullable=False)
value_type = db.relationship("ValueType", back_populates="rollup_snapshots")
```

**Action Items:**
- [ ] Audit all models for implicit `backref` relationships
- [ ] Convert to explicit `back_populates`
- [ ] Add cascade behavior explicitly
- [ ] Add tests for cascade delete

---

## SQLAlchemy vs Database Cascade (CRITICAL)

**Issue:** Setting `ON DELETE CASCADE` in database isn't enough - SQLAlchemy ORM needs to know too.

**Why:**
- SQLAlchemy loads objects into session before database delete
- Tries to manage relationships itself
- If not configured correctly, attempts SET NULL

**Three-Layer Fix Required:**

1. **Database Constraint:**
   ```sql
   ALTER TABLE rollup_snapshots
   ADD CONSTRAINT fk_value_type
   FOREIGN KEY (value_type_id) REFERENCES value_types(id)
   ON DELETE CASCADE;
   ```

2. **Model ForeignKey:**
   ```python
   value_type_id = db.Column(db.Integer,
       db.ForeignKey("value_types.id", ondelete="CASCADE"),
       nullable=False)
   ```

3. **SQLAlchemy Relationship:**
   ```python
   rollup_snapshots = db.relationship("RollupSnapshot",
       back_populates="value_type",
       cascade="all, delete-orphan")
   ```

**All three must be consistent!**

---

## Database Migration Chain Integrity

**Issue:** Inserting migrations into middle of chain after production deployment.

**Problem:**
- Production tracks current revision in `alembic_version` table
- Alembic won't run migrations "behind" current revision
- Inserting missed migrations doesn't work

**Example:**
```
Production: A → B → D (at revision D)
You create: C (between B and D)
Result: C never runs! (already past D)
```

**Solution:**
- Create NEW migration at END of chain
- Point to current HEAD
- Never rewrite history after production deploy

**See:** MEMORY.md PRE-COMMIT CHECKLIST

---

## Snapshot Privacy Migration (v1.15.0)

**Issue:** Added `is_public` and `owner_user_id` columns without migration.

**Impact:** Production crashed with "column does not exist" error.

**Lesson:** NEVER modify database directly, even for "quick tests".

**Prevention:** PRE-COMMIT CHECKLIST enforces migration creation.

---

## SSO Callback URL Scheme

**Issue:** Hardcoded `_scheme='https'` in callback URL broke local development.

**Problem:**
```python
# BAD: Hardcoded
callback_url = url_for('auth.sso_callback', _external=True, _scheme='https')
# Breaks localhost (needs http://)
```

**Solution:**
```python
# GOOD: Environment-aware
callback_url = url_for('auth.sso_callback', _external=True, _scheme=request.scheme)
# Uses http in dev, https in prod
```

---

## Dual SSO Flags Confusion

**Issue:** Two places to enable SSO caused confusion.

**Problem:**
- `SystemSetting.sso_enabled` (old)
- `SSOConfig.is_enabled` (new)
- Both could be different values

**Solution:**
- Removed `SystemSetting.sso_enabled` completely
- Single source of truth: `SSOConfig.is_enabled`

---

## Comment Permission Dependency

**Issue:** `can_add_comments` should require `can_view_comments`.

**Problem:** User could add comments but not see them (illogical).

**Solution:**
- JavaScript in UI disables "Add Comments" if "View Comments" unchecked
- Backend should also validate this dependency (TODO)

---

## Space Privacy Column Filtering

**Issue:** Private spaces showed in workspace but value type columns didn't respect filter.

**Problem:** Column visibility logic didn't account for space privacy.

**Solution:**
- Added context-aware column filtering
- Joins through Space → Challenge → Initiative → System → KPI
- Respects all filters: space type, governance bodies, archived status

---

## Comment Icon Visibility

**Issue:** Users with view-only permission saw empty comment icons (confusing).

**Problem:**
- Users who could add comments: icon always visible
- Users who could only view: icon should only show if comments exist

**Solution:**
- `.comment-icon-container-view-only` CSS class
- JavaScript hides icon if count = 0
- Prevents misleading empty state

---

## User Default Organization Orphan Reference

**Issue:** User's `default_organization_id` can block organization deletion.

**Problem:**
- User has `default_organization_id = 5`
- Try to delete organization 5
- Database blocks deletion (or leaves orphaned reference)
- On next login, user crashes with FK constraint error

**Solution:**
```sql
ALTER TABLE users
DROP CONSTRAINT users_default_organization_id_fkey;

ALTER TABLE users
ADD CONSTRAINT users_default_organization_id_fkey
FOREIGN KEY (default_organization_id) REFERENCES organizations(id)
ON DELETE SET NULL;
```

**Model Fix:**
```python
default_organization_id = db.Column(
    db.Integer,
    db.ForeignKey("organizations.id", ondelete="SET NULL"),
    nullable=True
)
```

**Login Behavior:**
- Login code already handles NULL default_organization_id
- Falls back to first available organization
- No crash, seamless experience

---

## Best Practices to Prevent Issues

### 1. Always Create Migrations
- NEVER modify database directly
- ALWAYS create migration file first
- Commit code + migration together

### 2. Explicit Relationships
- Use `back_populates`, not `backref`
- Always specify cascade behavior
- Document relationship purpose

### 3. Three-Layer Consistency
- Database constraints
- Model ForeignKey definitions
- SQLAlchemy relationships
- All three must match!

### 4. Validate Documentation
- Documentation shows intent
- Code is reality
- Validate docs against actual behavior
- Add tests to catch mismatches

### 5. Test Cascade Deletes
- Write tests for cascade behavior
- Test organization deletion
- Test value type deletion
- Verify no orphaned records

---

## Testing Checklist

**Before deploying cascade delete changes:**

- [ ] Test in development first
- [ ] Delete test organization
- [ ] Verify no IntegrityErrors
- [ ] Check for orphaned records
- [ ] Verify database constraints correct
- [ ] Verify model definitions match
- [ ] Verify relationship cascade behavior

---

## Common Error Patterns

### IntegrityError: NOT NULL violation
**Cause:** Cascade not configured, database trying to SET NULL
**Fix:** Add cascade to database, model, and relationship

### IntegrityError: FOREIGN KEY constraint
**Cause:** Trying to delete parent with orphaned children
**Fix:** Add cascade delete or handle children explicitly

### DetachedInstanceError
**Cause:** Accessing relationship after commit/expunge
**Fix:** Use joinedload or refresh object

---

## Future Improvements Needed

1. **Audit all relationships:**
   - Find all `backref` usages
   - Convert to explicit `back_populates`
   - Add cascade specifications

2. **Add cascade tests:**
   - Test organization deletion
   - Test value type deletion
   - Test space deletion
   - Verify no orphaned records

3. **Documentation validation:**
   - Automated checks
   - Compare docs to actual code
   - Flag mismatches

4. **Improve error messages:**
   - Catch IntegrityErrors earlier
   - Provide helpful messages
   - Suggest fixes

---

## Full Backup Restore Silently Fails (Empty Org After Restore)

**Issue:** Restoring a JSON backup with governance bodies produced no error but left the target organization empty.

**Root Cause:** The backup restore flow stores intermediate state in the Flask session cookie so the governance-body mapping page can access it. For any non-trivial backup the JSON content pushes the session cookie over the browser's 4 KB limit (~4093 bytes). Browsers silently discard oversized cookies, so when the governance-mapping page loaded the session was empty, it hit the "No pending backup restore found" guard and redirected back — without any visible error (the flash message was in the now-dropped session too).

**Symptoms:**
- `POST /backup-restore/restore` → 302 to governance-mapping
- `GET /backup-restore/governance-mapping` → immediate 302 back to backup-restore (no form shown)
- Org remains empty, no error displayed
- Server log shows: `UserWarning: The 'session' cookie is too large`

**Fix (2026-03-18):** Instead of storing the backup JSON string in the session, the route now writes it to a temporary file (`cisk_restore_*.json` in the system temp dir) and stores only the file path in the session. The temp file is deleted after a successful restore.

```python
# BAD: stores entire JSON in session cookie
session["pending_full_backup"] = backup_content  # can be megabytes

# GOOD: write to temp file, store path only
tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, ...)
tmp.write(backup_content)
session["pending_full_backup_path"] = tmp.name
```

**Files changed:** `app/routes/global_admin.py` — `restore_backup()` and `full_backup_governance_mapping()`

---

## Windows cp1252 UnicodeEncodeError in Migration Files

**Issue:** Migration files with emoji in `print()` statements crash on Windows with `UnicodeEncodeError: 'charmap' codec can't encode character`.

**Cause:** Windows terminal uses the cp1252 codec by default. Emoji and special Unicode characters (✓, →, etc.) are not in cp1252.

**Fix:** Remove all emoji from `print()` calls in migration files. Plain ASCII only.

**Affected migrations fixed:** `7a2248e4f425_add_site_to_stakeholders.py`

---

## SQLAlchemy Named Enum Re-Creation in Alembic Migrations

**Issue:** Migrations that manually create a PostgreSQL enum type via `op.execute("CREATE TYPE ...")` and then use `op.create_table(... sa.Enum(..., name="type_name", create_type=False) ...)` fail with `DuplicateObject: type already exists`.

**Root Cause:** Despite `create_type=False`, SQLAlchemy's internal `_on_table_create` event listener still fires and attempts to issue a `CREATE TYPE` DDL, conflicting with the one already created by `op.execute`.

**Fix:** Replace `op.create_table(...)` with raw SQL for any table that uses a named enum type:

```python
# BAD: SQLAlchemy re-creates the enum even with create_type=False
op.execute("CREATE TYPE my_enum AS ENUM ('a', 'b')")
op.create_table("my_table",
    sa.Column("col", sa.Enum("a", "b", name="my_enum", create_type=False), ...),
    ...
)

# GOOD: raw SQL bypasses the event listener
op.execute("CREATE TYPE my_enum AS ENUM ('a', 'b')")
op.execute("""
    CREATE TABLE my_table (
        id SERIAL PRIMARY KEY,
        col my_enum NOT NULL
    )
""")
```

**Affected migrations fixed:** `5f87aa9fccb9`, `737ff76c2619`

---

**End of Known Issues**
