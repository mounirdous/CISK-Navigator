# Known Issues & Gotchas

**Last Updated:** 2026-03-10

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

**End of Known Issues**
