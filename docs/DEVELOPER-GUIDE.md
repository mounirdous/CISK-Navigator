# CISK Navigator - Developer Quick Reference

**Purpose:** Fast lookup for common development tasks

---

## Quick Links

- **Architecture:** See `ARCHITECTURE.md` for comprehensive documentation
- **Data Models:** See model files in `app/models/`
- **Deployment:** See `deployment.md` in memory folder

---

## "I Want To..." Cookbook

### Add a New Field to an Existing Entity

**Example:** Add `priority` field to Initiatives

```bash
# 1. Edit model
# app/models/initiative.py
priority = db.Column(db.String(20), nullable=True)

# 2. Create migration
flask db revision -m "add priority to initiatives"

# 3. Edit migration file (migrations/versions/xxx_add_priority.py)
def upgrade():
    op.add_column('initiatives', sa.Column('priority', sa.String(20), nullable=True))

def downgrade():
    op.drop_column('initiatives', 'priority')

# 4. Apply migration
flask db upgrade

# 5. Update form (app/forms/initiative_forms.py)
priority = SelectField('Priority', choices=[...])

# 6. Update templates
# app/templates/organization_admin/create_initiative.html
{{ form.priority.label }}
{{ form.priority }}

# 7. Test and commit
git add app/models/initiative.py migrations/versions/*.py app/forms/initiative_forms.py
git commit -m "Add priority field to initiatives"
```

---

### Add a New Permission

**Example:** Add `can_export_data` permission

```bash
# 1. Update membership model
# app/models/organization.py (UserOrganizationMembership class)
can_export_data = db.Column(db.Boolean, default=False)

# 2. Create migration
flask db revision -m "add can_export_data permission"

# Edit migration file:
def upgrade():
    op.add_column('user_organization_memberships',
        sa.Column('can_export_data', sa.Boolean(), nullable=False, server_default='false'))

def downgrade():
    op.drop_column('user_organization_memberships', 'can_export_data')

# 3. Apply migration
flask db upgrade

# 4. Update user forms
# app/forms/user_forms.py
can_export_data = BooleanField('Can export data')

# 5. Update templates
# app/templates/global_admin/create_user.html and edit_user.html
{{ form.can_export_data.label }}
{{ form.can_export_data }}

# 6. Create decorator (app/decorators.py) - optional
def export_permission_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.get_permission('can_export_data'):
            abort(403)
        return f(*args, **kwargs)
    return decorated_function

# 7. Use decorator on routes
@bp.route('/export')
@login_required
@export_permission_required
def export_data():
    pass
```

---

### Add a New Route/Page

**Example:** Add a "Reports" page

```bash
# 1. Add route
# app/routes/workspace.py (or create new blueprint)
@bp.route('/reports')
@login_required
def reports():
    org_id = session.get('organization_id')
    # Your logic here
    return render_template('workspace/reports.html')

# 2. Create template
# app/templates/workspace/reports.html
{% extends "base.html" %}
{% block title %}Reports - CISK Navigator{% endblock %}
{% block content %}
<div class="container-fluid py-4">
    <h2>Reports</h2>
    <!-- Your content -->
</div>
{% endblock %}

# 3. Add navigation link
# app/templates/base.html (in navbar)
<a class="nav-link" href="{{ url_for('workspace.reports') }}">
    <i class="bi bi-file-bar-graph"></i> Reports
</a>

# 4. Test
# Visit http://localhost:5003/workspace/reports
```

---

### Add a New Service

**Example:** Create a reporting service

```bash
# 1. Create service file
# app/services/report_service.py
"""Report generation service"""

class ReportService:
    @staticmethod
    def generate_summary_report(organization_id):
        """Generate summary report for organization"""
        # Your logic
        return report_data

# 2. Import in services __init__.py
# app/services/__init__.py
from .report_service import ReportService

# 3. Use in routes
from app.services import ReportService

@bp.route('/reports/summary')
def summary_report():
    report = ReportService.generate_summary_report(org_id)
    return render_template('workspace/summary_report.html', report=report)
```

---

### Add Cascade Delete Handling

**Example:** When deleting a Space, also delete related custom entity

```bash
# 1. Add relationship in Space model
# app/models/space.py
custom_entities = db.relationship(
    'CustomEntity',
    backref='space',
    lazy='dynamic',
    cascade='all, delete-orphan'  # KEY: This enables cascade delete
)

# 2. Add foreign key in CustomEntity model
# app/models/custom_entity.py
space_id = db.Column(db.Integer, db.ForeignKey('spaces.id'), nullable=False)

# 3. Update DeletionImpactService
# app/services/deletion_impact_service.py
@staticmethod
def get_space_deletion_impact(space_id):
    space = Space.query.get_or_404(space_id)

    custom_entities = space.custom_entities.all()

    return {
        'space': space,
        'challenges': space.challenges.all(),
        'custom_entities': custom_entities,  # Add this
        'total_deletions': len(challenges) + len(custom_entities)
    }

# 4. Update delete confirmation template
# app/templates/organization_admin/delete_space_preview.html
<li>{{ impact.custom_entities|length }} custom entities</li>
```

---

### Debug a Permission Issue

**Checklist:**

```python
# 1. Check user's membership
psql -d cisknavigator -c "SELECT * FROM user_organization_memberships WHERE user_id = X AND organization_id = Y;"

# 2. Check permission flags
psql -d cisknavigator -c "SELECT can_manage_kpis, can_manage_systems FROM user_organization_memberships WHERE user_id = X;"

# 3. Check session context
# In Flask route or template:
{{ session.get('organization_id') }}
{{ current_user.id }}

# 4. Check decorator
# app/decorators.py - verify logic matches expectation

# 5. Check role hierarchy
# Is user super_admin? is_global_admin?
psql -d cisknavigator -c "SELECT is_super_admin, is_global_admin FROM users WHERE id = X;"
```

---

### Add Database Index for Performance

**Example:** Index frequently queried columns

```bash
# 1. Create migration
flask db revision -m "add indexes for performance"

# 2. Edit migration file
def upgrade():
    # Index on foreign keys
    op.create_index('idx_kpis_system_id', 'kpis', ['system_id'])
    op.create_index('idx_contributions_kpi_id', 'contributions', ['kpi_id'])

    # Composite index for common query
    op.create_index('idx_kpis_org_archived', 'kpis', ['organization_id', 'is_archived'])

def downgrade():
    op.drop_index('idx_kpis_system_id', 'kpis')
    op.drop_index('idx_contributions_kpi_id', 'contributions')
    op.drop_index('idx_kpis_org_archived', 'kpis')

# 3. Apply
flask db upgrade

# 4. Verify
psql -d cisknavigator -c "\d kpis"
```

---

### Debug SSO Issues

```bash
# 1. Check SSO config in database
psql -d cisknavigator -c "SELECT provider_type, is_enabled, client_id, LEFT(client_secret, 20) FROM sso_config;"

# 2. Check encryption key is set
echo $ENCRYPTION_KEY

# 3. Check Flask logs
# Look for "SSO callback error" or "JWT verification failed"

# 4. Test callback URL
# Should match exactly what's in Google Console
curl -I http://localhost:5003/auth/sso/callback

# 5. Check user was created
psql -d cisknavigator -c "SELECT id, login, email, sso_provider, sso_subject_id FROM users WHERE sso_provider IS NOT NULL;"

# 6. Check pending users
http://localhost:5003/super-admin/users/pending
```

---

### Run Database Migrations in Production

**⚠️ CRITICAL:** Test in development first!

```bash
# Local testing
flask db upgrade
# Verify with: psql -d cisknavigator -c "\d table_name"

# Production (Render)
# Migrations run automatically on deploy via startCommand
# Manual run (if needed):
# 1. Go to Render dashboard
# 2. Open Shell
# 3. Run: flask db upgrade

# Rollback (emergency)
flask db downgrade  # Goes back one migration
```

---

### Export/Import Organization Data

**⚠️ IMPORTANT: YAML Export/Import is STRUCTURE ONLY**

**What IS exported:**
- ✅ Value types (definitions)
- ✅ Spaces, Challenges, Initiatives, Systems, KPIs (structure)
- ✅ KPI configurations (colors, display settings, targets)
- ✅ Rollup rules (as of v1.16.0 - NOT YET IMPLEMENTED)

**What is NOT exported:**
- ❌ **Contributions (actual KPI cell values)** ← THIS IS THE DATA!
- ❌ **Comments**
- ❌ **Snapshots**
- ❌ **User memberships**
- ❌ **Governance body links to KPIs**

**Export:**
```bash
# Via UI (structure only!)
http://localhost:5003/org-admin/export/yaml

# Via service
from app.services import YAMLExportService
yaml_data = YAMLExportService.export_organization(org_id)
```

**Import:**
```bash
# Via UI (structure only!)
http://localhost:5003/org-admin/import/yaml

# Via service
from app.services import YAMLImportService
result = YAMLImportService.import_yaml(yaml_content, org_id)
```

**For FULL backup with data, use database dump:**
```bash
# Full backup (includes everything)
pg_dump -U postgres -d cisknavigator > backup_$(date +%Y%m%d).sql

# Restore
psql -U postgres -d cisknavigator_new < backup_20260311.sql
```

---

### Clone an Organization

**⚠️ IMPORTANT: Organization Clone is STRUCTURE ONLY (same as YAML export)**

**What IS cloned:**
- ✅ Value types
- ✅ Spaces, Challenges, Initiatives, Systems, KPIs
- ✅ All links and configurations
- ✅ Rollup rules

**What is NOT cloned:**
- ❌ User memberships
- ❌ **Contributions (actual KPI values)**
- ❌ Comments
- ❌ Snapshots
- ❌ Governance body links to KPIs

```bash
# Via UI
http://localhost:5003/global-admin/organizations/clone/<org_id>

# Via service
from app.services import OrganizationCloneService
new_org = OrganizationCloneService.clone_organization(
    source_org_id=1,
    new_name="New Org Name",
    new_org_description="Clone of original"
)
```

---

### Create Snapshot

```bash
# Via UI
http://localhost:5003/workspace/snapshots/create

# Via service
from app.services import SnapshotService
SnapshotService.create_snapshot(
    organization_id=org_id,
    snapshot_name="Q4 2026",
    kpi_ids=[1, 2, 3]  # or None for all
)
```

---

### Compare Snapshots

```bash
# Via UI
http://localhost:5003/workspace/snapshots/compare?a=<batch_id_1>&b=<batch_id_2>

# Via service
from app.services import SnapshotService
comparison = SnapshotService.compare_snapshots(batch_id_a, batch_id_b)
```

---

## Common SQL Queries

### Find All KPIs Without Contributions
```sql
SELECT k.id, k.name, s.name as system_name
FROM kpis k
JOIN systems s ON k.system_id = s.id
LEFT JOIN contributions c ON k.id = c.kpi_id
WHERE k.organization_id = <ORG_ID>
  AND k.is_archived = false
  AND c.id IS NULL;
```

### Find Unused Value Types
```sql
SELECT vt.id, vt.name
FROM value_types vt
LEFT JOIN contributions c ON vt.id = c.value_type_id
WHERE vt.organization_id = <ORG_ID>
  AND c.id IS NULL;
```

### Find Users with No Organization Access
```sql
SELECT u.id, u.login, u.email
FROM users u
LEFT JOIN user_organization_memberships m ON u.id = m.user_id
WHERE u.is_active = true
  AND u.is_global_admin = false
  AND m.id IS NULL;
```

### Find Most Commented KPIs
```sql
SELECT k.id, k.name, COUNT(c.id) as comment_count
FROM kpis k
JOIN cell_comments c ON k.id = c.kpi_id
WHERE k.organization_id = <ORG_ID>
GROUP BY k.id, k.name
ORDER BY comment_count DESC
LIMIT 10;
```

### Find KPIs by Governance Body
```sql
SELECT k.id, k.name, gb.name as governance_body
FROM kpis k
JOIN kpi_governance_body_links l ON k.id = l.kpi_id
JOIN governance_bodies gb ON l.governance_body_id = gb.id
WHERE k.organization_id = <ORG_ID>
ORDER BY gb.name, k.name;
```

---

## Troubleshooting

### Issue: "No module named 'app'"

**Fix:**
```bash
# Make sure you're in project root
cd /Users/mounir.dous/projects/CISK-Navigator

# Activate venv
source venv/bin/activate

# Set PYTHONPATH (if needed)
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
```

---

### Issue: "CSRF token missing"

**Fix:**
```html
<!-- Ensure form has CSRF token -->
<form method="POST">
    {{ form.hidden_tag() }}  <!-- This includes CSRF token -->
    ...
</form>
```

---

### Issue: "Permission denied" but user has permission

**Debug:**
```python
# In route, add debug print
print(f"User: {current_user.login}")
print(f"Org: {session.get('organization_id')}")
membership = current_user.get_membership(session.get('organization_id'))
print(f"Membership: {membership}")
print(f"Can manage KPIs: {membership.can_manage_kpis if membership else 'NO MEMBERSHIP'}")
```

---

### Issue: Migration conflict

**Fix:**
```bash
# Check current revision
flask db current

# Check pending migrations
flask db history

# If conflicts, might need to:
# 1. Rollback: flask db downgrade
# 2. Delete conflicting migration file
# 3. Re-create: flask db revision -m "..."
# 4. Apply: flask db upgrade
```

---

### Issue: Database out of sync with models

**Fix:**
```bash
# Option 1: Create new migration (recommended)
flask db revision --autogenerate -m "sync schema"
# Review generated migration
flask db upgrade

# Option 2: Manual SQL (last resort)
psql -d cisknavigator -c "ALTER TABLE table_name ADD COLUMN column_name TYPE;"
# Then create migration to match
```

---

## Performance Tips

### 1. Eager Load Relationships
```python
# BAD: N+1 queries
kpis = KPI.query.filter_by(organization_id=org_id).all()
for kpi in kpis:
    print(kpi.system.name)  # Each iteration hits database

# GOOD: Single query with join
kpis = KPI.query.options(db.joinedload(KPI.system)).filter_by(organization_id=org_id).all()
for kpi in kpis:
    print(kpi.system.name)  # Already loaded
```

### 2. Use EXISTS for Checks
```python
# BAD: Load entire collection
if len(kpi.contributions.all()) > 0:
    pass

# GOOD: Database-level check
if db.session.query(Contribution).filter_by(kpi_id=kpi.id).first():
    pass
```

### 3. Batch Operations
```python
# BAD: One insert at a time
for item in items:
    obj = Model(**item)
    db.session.add(obj)
    db.session.commit()  # 100 commits

# GOOD: Bulk insert
for item in items:
    db.session.add(Model(**item))
db.session.commit()  # 1 commit
```

---

## Security Checklist

### Before Deploying a Feature:

- [ ] SQL injection: All queries use parameterization (SQLAlchemy handles this)
- [ ] XSS: All user input escaped in templates (Jinja2 auto-escapes)
- [ ] CSRF: All forms have `{{ form.hidden_tag() }}`
- [ ] Authorization: Routes have `@login_required` and permission decorators
- [ ] Secrets: No hardcoded passwords, API keys use environment variables
- [ ] File uploads: Validate file types, scan for malware
- [ ] Rate limiting: Consider for public endpoints
- [ ] Input validation: Use WTForms validators

---

## Code Style

### Conventions:

```python
# Imports: stdlib, third-party, local
import os
from datetime import datetime

from flask import render_template
from sqlalchemy import and_

from app.extensions import db
from app.models import User

# Class names: PascalCase
class MyService:
    pass

# Functions/variables: snake_case
def get_user_data(user_id):
    user_name = "John"

# Constants: UPPER_SNAKE_CASE
MAX_UPLOAD_SIZE = 1024 * 1024

# Docstrings: Triple quotes
def my_function():
    """
    Brief description.

    Longer explanation if needed.
    """
    pass
```

---

## Git Workflow

```bash
# 1. Create feature branch
git checkout -b feature/my-new-feature

# 2. Make changes
# Edit files...

# 3. Test locally
flask run --port 5003
# Test thoroughly

# 4. Commit
git add .
git commit -m "Add my new feature

- Detail 1
- Detail 2
"

# 5. Push
git push origin feature/my-new-feature

# 6. Create PR (if using GitHub)
# Or merge to main:
git checkout main
git merge feature/my-new-feature
git push origin main

# Render will auto-deploy on push to main
```

---

## Useful Commands

```bash
# Flask shell (interactive Python with app context)
flask shell

# Database shell
psql -d cisknavigator

# Check routes
flask routes

# Run tests (if you have tests)
pytest

# Check Python syntax
flake8 app/

# Format code
black app/

# Check dependencies
pip list --outdated

# Update requirements.txt
pip freeze > requirements.txt
```

---

**End of Developer Guide**
