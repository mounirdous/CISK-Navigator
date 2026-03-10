# CISK Navigator Documentation

Welcome to the CISK Navigator documentation! This folder contains comprehensive documentation for developers, administrators, and maintainers.

---

## Documentation Index

### 📘 **Core Documentation**

1. **[ARCHITECTURE.md](./ARCHITECTURE.md)** ⭐ **START HERE**
   - Complete system architecture overview
   - Data model relationships and diagrams
   - Impact analysis for all major components
   - File reference guide
   - Common operations and workflows

2. **[DEVELOPER-GUIDE.md](./DEVELOPER-GUIDE.md)** ⚡ **Quick Reference**
   - "I want to..." cookbook for common tasks
   - Step-by-step examples
   - Troubleshooting guide
   - SQL query examples
   - Code style conventions

3. **[DATA-DICTIONARY.md](./DATA-DICTIONARY.md)** 📊 **Database Reference**
   - Complete database schema
   - All tables and columns documented
   - Relationship diagrams
   - JSONB schemas
   - Index reference

4. **[KNOWN-ISSUES.md](./KNOWN-ISSUES.md)** ⚠️ **Known Issues & Gotchas**
   - Bug patterns and lessons learned
   - Cascade delete gotchas
   - Implicit relationship dangers
   - Best practices to prevent issues

---

## Additional Documentation (Memory Folder)

Located in: `~/.claude/projects/-Users-mounir-dous-projects-CISK-Navigator/memory/`

4. **deployment.md** - Production deployment guide
5. **sso-complete-implementation.md** - SSO setup and configuration
6. **sso-fixes.md** - SSO troubleshooting history
7. **comment-permissions.md** - Comment system documentation
8. **MEMORY.md** - Project facts and quick reference

---

## Quick Navigation

### **For New Developers:**
1. Read `ARCHITECTURE.md` sections 1-3 (Overview, Layers, Data Model)
2. Skim `DEVELOPER-GUIDE.md` "I Want To..." section
3. Reference `DATA-DICTIONARY.md` as needed

### **For Impact Analysis:**
1. Go to `ARCHITECTURE.md` → "Impact Analysis Guide"
2. Find the entity you're modifying
3. Check cascade delete behavior
4. Review related services and templates

### **For Adding Features:**
1. Use `DEVELOPER-GUIDE.md` → "I Want To..." cookbook
2. Follow step-by-step examples
3. Reference `ARCHITECTURE.md` for file locations
4. Check `DATA-DICTIONARY.md` for database changes

### **For Debugging:**
1. Use `DEVELOPER-GUIDE.md` → "Troubleshooting" section
2. Check SQL query examples
3. Review permission system in `ARCHITECTURE.md`

### **For Database Changes:**
1. Check `DATA-DICTIONARY.md` for current schema
2. Follow migration workflow in `DEVELOPER-GUIDE.md`
3. Review cascade behavior in `ARCHITECTURE.md`

---

## Documentation Standards

### When to Update Documentation:

- ✅ **ALWAYS** when adding new models or tables
- ✅ **ALWAYS** when adding new routes/blueprints
- ✅ **ALWAYS** when changing data relationships
- ✅ **ALWAYS** when adding new permissions
- ✅ When adding significant business logic services
- ✅ When changing authentication/authorization
- Optional when fixing bugs (unless it reveals undocumented behavior)

### Where to Document:

| Change Type | Document Location |
|-------------|------------------|
| New entity/model | `ARCHITECTURE.md` (Key Components), `DATA-DICTIONARY.md` |
| New route/endpoint | `ARCHITECTURE.md` (File Reference) |
| New service | `ARCHITECTURE.md` (Services), `DEVELOPER-GUIDE.md` (if common use case) |
| Database migration | `DATA-DICTIONARY.md`, migration file comments |
| Permission change | `ARCHITECTURE.md` (Permission Matrix), `DATA-DICTIONARY.md` |
| SSO changes | `sso-complete-implementation.md` |
| Deployment changes | `deployment.md` (memory folder) |

### How to Update:

```bash
# 1. Make your code changes
# 2. Update relevant documentation files
# 3. Commit both code and docs together

git add app/ docs/ migrations/
git commit -m "Add feature X

- Added new model Y
- Updated ARCHITECTURE.md with impact analysis
- Updated DATA-DICTIONARY.md with new table
"
```

---

## Key Concepts

### Multi-Tenancy
Organizations are isolated data containers. All entities belong to one organization. Users can access multiple organizations via memberships.

### Permission Model
- **Super Admin** - System-wide access (SSO, settings)
- **Global Admin** - Multi-org management
- **Organization Member** - Granular permissions per org

### Data Hierarchy
```
Organization
  → Space
      → Challenge
           → Initiative
                → System
                     → KPI
                          → Contribution (actual values)
```

### Cascade Deletes
Deleting entities cascades to children. Most dangerous: deleting value types deletes ALL contributions of that type!

### Soft Deletes
Some entities use soft delete flags:
- `organizations.is_active`
- `kpis.is_archived`
- `users.is_active`

---

## Architecture Decisions

### Why SQLAlchemy ORM vs Raw SQL?
- **Pro:** Type safety, relationships, migrations
- **Con:** Learning curve, query optimization
- **Decision:** Use ORM for CRUD, raw SQL for complex analytics

### Why Flask Blueprints?
- **Pro:** Modular, separated concerns, reusable
- **Con:** More files, indirection
- **Decision:** Separate by functional area (auth, workspace, admin)

### Why JSONB for Settings?
- **Pro:** Flexible schema, no migrations for new settings
- **Con:** Harder to query, no schema validation
- **Decision:** Use for variable/extensible data only

### Why Instance-Wide SSO?
- **Pro:** Simpler, matches real-world usage
- **Con:** Can't support multi-company scenarios
- **Decision:** Organizations are departments, not companies

---

## Common Patterns

### Model Pattern:
```python
class MyEntity(db.Model):
    __tablename__ = "my_entities"

    # Primary key
    id = db.Column(db.Integer, primary_key=True)

    # Foreign keys
    organization_id = db.Column(db.Integer, db.ForeignKey('organizations.id'), nullable=False)

    # Data fields
    name = db.Column(db.String(255), nullable=False)

    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)

    # Relationships
    organization = db.relationship('Organization', backref='my_entities')
```

### Route Pattern:
```python
@bp.route('/my-entities')
@login_required
@permission_required('can_manage_my_entities')
def list_entities():
    org_id = session.get('organization_id')
    entities = MyEntity.query.filter_by(organization_id=org_id).all()
    return render_template('organization_admin/my_entities.html', entities=entities)
```

### Service Pattern:
```python
class MyService:
    @staticmethod
    def do_complex_operation(entity_id):
        """Business logic goes here"""
        entity = MyEntity.query.get_or_404(entity_id)
        # Complex logic...
        db.session.commit()
        return result
```

---

## Version History

- **v1.15.2** (2026-03-10) - SSO complete implementation, documentation overhaul
- **v1.15.1** - Private spaces, smart column filtering
- **v1.15.0** - Snapshot privacy and batching
- **v1.14.x** - UI modernization, bug fixes

---

## Getting Help

1. **Check Documentation:** Start with ARCHITECTURE.md
2. **Search Code:** Use grep/Glob to find examples
3. **Check Memory:** Review memory folder for historical context
4. **Ask Questions:** Clear, specific questions get best results

---

## Contributing to Documentation

### Before Submitting Code:

- [ ] Added/updated relevant documentation
- [ ] Documented new models in ARCHITECTURE.md
- [ ] Updated DATA-DICTIONARY.md for schema changes
- [ ] Added examples to DEVELOPER-GUIDE.md if applicable
- [ ] Verified links work
- [ ] Ran spell check

### Documentation Review Checklist:

- [ ] Is it accurate? (matches current code)
- [ ] Is it complete? (covers all key aspects)
- [ ] Is it clear? (understandable to target audience)
- [ ] Is it findable? (indexed, linked, searchable)
- [ ] Is it maintainable? (will stay current)

---

## Quick Commands Reference

```bash
# Start Flask
./venv/bin/flask run --port 5003

# Database shell
psql -d cisknavigator

# Create migration
flask db revision -m "description"

# Apply migration
flask db upgrade

# Flask shell (Python REPL with app context)
flask shell

# Check routes
flask routes

# View logs
tail -f logs/flask.log
```

---

## File Locations Quick Reference

```
app/
├── models/           # Database models (SQLAlchemy)
├── routes/           # URL endpoints (Flask blueprints)
├── services/         # Business logic
├── forms/            # Input validation (WTForms)
├── templates/        # HTML templates (Jinja2)
├── static/           # CSS, JS, images
└── utils/            # Utilities (encryption, etc.)

docs/                 # This folder
migrations/           # Database migrations (Alembic)
tests/                # Unit tests
```

---

## Contact & Feedback

For issues, questions, or suggestions about documentation:
- Update docs directly via PR
- Add comments to code explaining tricky parts
- Create issue with "documentation" label

---

**Last Updated:** 2026-03-10
**Maintained By:** Development Team
**Version:** 1.0

---

**Happy Coding! 🚀**
