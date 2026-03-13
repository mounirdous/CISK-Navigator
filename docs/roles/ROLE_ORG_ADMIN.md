# Organization Admin - Complete Journey Map

**Role:** Organization Administrator
**Database:** `user_organization_memberships.is_org_admin = True`
**Access Level:** Full access to ONE organization + all regular user features

---

## 🎯 Role Overview

### Who Is This User?
- **Organization administrator** with full control over their organization
- Has **ALL permissions** within their organization automatically
- **Primary activities:** Setup organization, manage structure, configure settings
- **Key difference from regular user:** Access to `/org-admin` panel

### How Permissions Work
```python
# When is_org_admin = True, ALL permission checks return True:
can_manage_spaces(org_id) → True  # Always
can_manage_value_types(org_id) → True  # Always
can_manage_kpis(org_id) → True  # Always
# ... all permissions are True

# Individual permission flags are ignored when is_org_admin = True
```

---

## 📊 Access Summary

| Feature Area | Access Level |
|--------------|-------------|
| **Everything Regular User Can Do** | ✅ Yes - All features |
| **Organization Admin Panel** | ✅ **YES - This is the key difference!** |
| **Onboarding Wizard** | ✅ Yes |
| **YAML Backup/Restore** | ✅ Yes |
| **Structure Management** | ✅ Full control |
| **Value Types** | ✅ Create/Edit/Delete |
| **Governance Bodies** | ✅ Create/Edit/Delete/Reorder |
| **Organization Settings** | ✅ Yes (future: rename, description) |
| **Global Admin Panel** | ❌ No (can't manage other orgs) |
| **Super Admin Panel** | ❌ No (can't access system settings) |

---

## 🗺️ Complete User Journeys

### Journey 0: First Time Setup (Organization Onboarding)

**Trigger:** User logs into empty organization (0 spaces, 0 gov bodies, 0 value types)

#### Step 0.1: See Onboarding Prompt
**Route:** `/workspace/dashboard`
**Template:** `workspace/dashboard.html`

```
User Experience:
1. User logs in, selects organization
2. Dashboard shows welcome card:
   ┌────────────────────────────────────┐
   │ 🚀 Welcome to CISK Navigator!     │
   │                                    │
   │ Let's set up your organization     │
   │ in just a few steps.               │
   │                                    │
   │ [Start Onboarding] ←               │
   └────────────────────────────────────┘

3. Click "Start Onboarding"
   → Redirects to /org-admin/onboarding?step=1
```

---

#### Step 0.2: Onboarding Step 1 - Welcome
**Route:** `/org-admin/onboarding?step=1`
**Template:** `org-admin/onboarding_step1.html`
**File:** `app/routes/organization_admin.py`

```
User Experience:
1. See welcome screen with progress bar (0/4)
2. Explanation of what will be set up:
   - Space (organize work by domain)
   - Governance Body (oversight committee)
   - Value Types (measurement dimensions)

3. Click "Get Started"
   → POST to /org-admin/onboarding
   → Redirects to step=2
```

**Code Flow:**
```python
# app/routes/organization_admin.py
@bp.route("/onboarding", methods=["GET", "POST"])
@login_required
@organization_required
@any_org_admin_permission_required  # is_org_admin = True passes this
def onboarding():
    step = request.args.get('step', '1')

    if step == '1':
        # Show welcome
        if request.method == 'POST':
            return redirect(url_for('organization_admin.onboarding', step='2'))

    # ... handle other steps
```

---

#### Step 0.3: Onboarding Step 2 - Create First Space
**Route:** `/org-admin/onboarding?step=2`
**Template:** `org-admin/onboarding_step2.html`

```
User Experience:
1. See space creation form (embedded)
2. Enter:
   - Name: "Digital Transformation"
   - Type: [Strategic ▼]
   - Description: (optional)

3. Click "Continue"
   → Creates space
   → Redirects to step=3

4. Progress bar shows 25% complete
```

**Database Changes:**
- INSERT into `spaces` table
- Audit log entry

---

#### Step 0.4: Onboarding Step 3 - Create Governance Body
**Route:** `/org-admin/onboarding?step=3`
**Template:** `org-admin/onboarding_step3.html`

```
User Experience:
1. See governance body creation form (embedded)
2. Enter:
   - Name: "Steering Committee"
   - Abbreviation: "SC"
   - Description: (optional)
   - Color: [🟦 Blue]

3. Click "Continue"
   → Creates governance body
   → Redirects to step=4

4. Progress bar shows 50% complete
```

**Database Changes:**
- INSERT into `governance_bodies` table
- Sets `is_default = False`
- Audit log entry

---

#### Step 0.5: Onboarding Step 4 - Create Default Value Types
**Route:** `/org-admin/onboarding?step=4`
**Template:** `org-admin/onboarding_step4.html`

```
User Experience:
1. See explanation:
   "We'll create 3 essential value types:
    - Cost (€)
    - Revenue (€)
    - User Satisfaction (sentiment)"

2. Click "Create Value Types"
   → Creates all 3 automatically
   → Redirects to step=5

3. Progress bar shows 75% complete
```

**Database Changes:**
- INSERT 3 rows into `value_types`:
  1. Cost (numeric, unit=€)
  2. Revenue (numeric, unit=€)
  3. User Satisfaction (qualitative, sentiment)

---

#### Step 0.6: Onboarding Step 5 - Complete
**Route:** `/org-admin/onboarding?step=5`
**Template:** `org-admin/onboarding_step5.html`

```
User Experience:
1. See success message: "You're All Set! 🎉"
2. See next steps card:
   ✓ Space created
   ✓ Governance Body created
   ✓ Value Types created

   Next steps:
   1. Create Challenges
   2. Create Initiatives
   3. Add Systems
   4. Create KPIs
   5. View Workspace

3. Click "Go to Organization Dashboard"
   → Redirects to /org-admin

4. Progress bar shows 100% complete
```

**Note:** Onboarding is skipped if org already has spaces + gov bodies + value types

---

### Journey 1: Access Organization Admin Panel

#### Step 1.1: Navigate to Admin Menu
**Location:** Top navigation bar

```
User Experience:
1. User sees navigation:
   [Organization ▼] [Dashboards] [Admin ▼] [Profile]
                                    ↑
                                 VISIBLE!

2. Click "Admin" dropdown
3. See menu:
   🏢 MIKRON Administration  ← Click this
   🌐 Instance Admin         ← NOT visible (not global admin)
   🔧 Super Admin            ← NOT visible (not super admin)

4. Click "MIKRON Administration"
   → Redirects to /org-admin
```

**Permission Check:**
```python
# In template base.html
{% if current_user.is_org_admin(session['organization_id'])
   or current_user.is_global_admin
   or current_user.is_super_admin %}
    <li>🏢 MIKRON Administration</li>
{% endif %}
```

---

#### Step 1.2: Organization Admin Dashboard
**Route:** `/org-admin`
**Template:** `org-admin/index.html`
**File:** `app/routes/organization_admin.py`

```
User Experience:
1. See organization admin panel:

   ╔════════════════════════════════════════╗
   ║ Organization: MIKRON                   ║
   ║ Admin Settings                         ║
   ╚════════════════════════════════════════╝

   📊 Statistics:
   - 2 Spaces
   - 5 Challenges
   - 12 Initiatives
   - 8 Systems
   - 13 KPIs
   - 6 Value Types
   - 1 Governance Body

   🛠️ Management Tools:
   ┌─────────────────────┐ ┌─────────────────────┐
   │ Manage Spaces       │ │ Manage Challenges   │
   └─────────────────────┘ └─────────────────────┘

   ┌─────────────────────┐ ┌─────────────────────┐
   │ Manage Initiatives  │ │ Manage Systems      │
   └─────────────────────┘ └─────────────────────┘

   ┌─────────────────────┐ ┌─────────────────────┐
   │ Manage Value Types  │ │ Governance Bodies   │
   └─────────────────────┘ └─────────────────────┘

   📦 YAML Backup & Restore:
   ┌─────────────────────┐ ┌─────────────────────┐
   │ ⬇️ Export YAML      │ │ ⬆️ Import YAML      │
   └─────────────────────┘ └─────────────────────┘

   ⚠️ Danger Zone:
   [ Clear All Organization Data ]
```

**Entities Displayed:**
- Organization statistics (counts)
- Links to management pages

---

### Journey 2: Manage Organization Structure

#### Step 2.1: Manage Spaces
**Route:** `/org-admin/spaces`
**Template:** `org-admin/spaces.html`

```
User Experience:
1. Click "Manage Spaces"
2. See list of all spaces:

   Space Name              | Type       | # Challenges | Actions
   ----------------------- | ---------- | ------------ | -------
   Digital Transformation  | Strategic  | 3           | Edit | Delete
   Operations Excellence   | Operational| 2           | Edit | Delete

3. Click "Create Space" button
   → Opens creation form

4. Click "Edit" on existing space
   → Opens edit form

5. Click "Delete" on space
   → Shows deletion preview (what will be deleted)
   → Requires confirmation
```

**Routes:**
- GET `/org-admin/spaces` - List
- GET `/org-admin/spaces/create` - Create form
- POST `/org-admin/spaces/create` - Submit creation
- GET `/org-admin/spaces/<id>/edit` - Edit form
- POST `/org-admin/spaces/<id>/edit` - Submit edit
- POST `/org-admin/spaces/<id>/delete` - Delete

---

#### Step 2.2: Manage Value Types
**Route:** `/org-admin/value-types`
**Template:** `org-admin/value_types.html`

```
User Experience:
1. Click "Manage Value Types"
2. See list of value types:

   Name         | Kind        | Unit  | Active | Actions
   ------------ | ----------- | ----- | ------ | -------
   Cost         | Numeric     | €     | ✓      | Edit | Delete
   Revenue      | Numeric     | €     | ✓      | Edit | Delete
   Risk Level   | Qualitative | -     | ✓      | Edit | Delete

3. Click "Create Value Type"
   → Opens form with:
      - Name
      - Kind (Numeric/Qualitative)
      - IF Numeric: Unit, Decimal places
      - Active checkbox

4. Can edit or deactivate (not delete if in use)
```

**Business Rule:**
- Can't delete value type if used by any KPI
- Can deactivate instead (is_active = False)
- Deactivated types don't appear in KPI creation

---

#### Step 2.3: Manage Governance Bodies
**Route:** `/org-admin/governance-bodies`
**Template:** `org-admin/governance_bodies.html`

```
User Experience:
1. Click "Governance Bodies"
2. See draggable list:

   ⋮⋮ Steering Committee (SC) 🟦        [Edit] [Delete]
   ⋮⋮ Technical Committee (TECH) 🟩    [Edit] [Delete]
   ⋮⋮ Finance Board (FIN) 🟨           [Edit] [Delete]
   ⋮⋮ General (GEN) ⚪                  [Edit] [Rename Only]
                                        ↑ Can't delete default

3. Drag to reorder (saves automatically)

4. Click "Create Governance Body"
   → Opens form:
      - Name: "Operations Team"
      - Abbreviation: "OPS"
      - Color: [🟧 Orange]
      - Description: (optional)

5. Click "Edit" to modify
6. Click "Delete" to remove (if not default)
```

**Business Rules:**
- Every org has ONE default governance body (can't delete)
- Default can be renamed but not deleted
- Order is saved and used in workspace filters
- KPIs must belong to at least one governance body

---

### Journey 3: YAML Backup & Restore

#### Step 3.1: Export YAML
**Route:** `/org-admin/yaml/export`
**File:** `app/routes/organization_admin.py`

```
User Experience:
1. Click "Export YAML" button
2. Browser downloads file:
   mikron_backup_2026-03-13.yaml

3. File contains complete organization structure:
   organization:
     name: MIKRON
     description: ...

   spaces:
     - name: Digital Transformation
       type: strategic
       challenges:
         - name: Improve Customer Experience
           initiatives:
             - name: New CRM System
               systems:
                 - name: Salesforce Implementation
                   kpis:
                     - name: User Adoption Rate
                       value_types:
                         - name: Percentage
                           target: 80

   value_types:
     - name: Cost
       kind: numeric
       unit: €

   governance_bodies:
     - name: Steering Committee
       abbreviation: SC
```

**Code Flow:**
```python
# app/routes/organization_admin.py
@bp.route("/yaml/export")
@login_required
@organization_required
@any_org_admin_permission_required
def export_yaml():
    org_id = session.get('organization_id')

    # Use YAMLExportService
    yaml_content = YAMLExportService.export_organization(org_id)

    # Return as downloadable file
    return Response(
        yaml_content,
        mimetype='application/x-yaml',
        headers={'Content-Disposition': f'attachment;filename=backup.yaml'}
    )
```

**Service Used:** `app/services/yaml_export_service.py`

---

#### Step 3.2: Import YAML
**Route:** `/org-admin/yaml/import`
**Template:** `org-admin/yaml_import.html`

```
User Experience:
1. Click "Import YAML" button
2. See upload form with BIG WARNING:
   ⚠️ WARNING: This will DELETE ALL current data!

   This action:
   ✓ Deletes all spaces, challenges, initiatives, systems, KPIs
   ✓ Deletes all value types and governance bodies
   ✓ Keeps users and permissions
   ✓ Cannot be undone

   [Choose YAML File] [Upload & Import]

3. Click "Choose YAML File"
   → Select mikron_backup.yaml

4. Click "Upload & Import"
   → Shows confirmation dialog
   → User types org name to confirm
   → Processes import (takes 10-30 seconds)
   → Shows success message

5. Redirected to /org-admin
   → Organization fully restored from backup
```

**Code Flow:**
```python
# app/routes/organization_admin.py
@bp.route("/yaml/import", methods=["GET", "POST"])
@login_required
@organization_required
@any_org_admin_permission_required
def import_yaml():
    if request.method == 'POST':
        file = request.files['yaml_file']

        # Use YAMLImportService
        success = YAMLImportService.import_organization(
            org_id,
            file.read().decode('utf-8')
        )

        if success:
            flash("Import successful!", "success")
        else:
            flash("Import failed", "danger")

    return render_template('org-admin/yaml_import.html')
```

**Service Used:** `app/services/yaml_import_service.py`

**Database Impact:**
- DELETE all entities in organization
- INSERT all entities from YAML
- Preserves user memberships and permissions
- Audit log records the import

---

### Journey 4: Danger Zone - Clear Organization Data

**Route:** `/org-admin/clear-data`
**Template:** `org-admin/index.html` (confirmation modal)

```
User Experience:
1. Scroll to "Danger Zone" section
2. See warning:
   ⚠️ WARNING: Destructive Action

   The following action will permanently delete ALL data
   in this organization. This cannot be undone!

   [ Clear All Organization Data ]

3. Click button
   → Opens confirmation modal:

     ╔════════════════════════════════════════╗
     ║ ⚠️  Are you absolutely sure?          ║
     ║                                        ║
     ║ This will permanently delete:          ║
     ║ • All Spaces, Challenges, Initiatives  ║
     ║ • All Systems and KPIs                 ║
     ║ • All Value Types & Governance Bodies  ║
     ║ • All Contributions and historical data║
     ║ • All Snapshots and rollup data        ║
     ║                                        ║
     ║ Type organization name to confirm:     ║
     ║ [________________]                     ║
     ║                                        ║
     ║ [Cancel] [Yes, Delete Everything]      ║
     ╚════════════════════════════════════════╝

4. Type org name: "MIKRON"
5. Click "Yes, Delete Everything"
   → Deletes all data (keeps org shell + users)
   → Redirects to dashboard
   → Shows onboarding prompt (empty org)
```

**Code Flow:**
```python
# app/routes/organization_admin.py
@bp.route("/clear-data", methods=["POST"])
@login_required
@organization_required
@any_org_admin_permission_required
def clear_organization_data():
    org_id = session.get('organization_id')
    org = Organization.query.get(org_id)

    # Confirmation check
    if request.form.get('org_name') != org.name:
        flash("Organization name doesn't match", "danger")
        return redirect(url_for('organization_admin.index'))

    # Delete all data
    Space.query.filter_by(organization_id=org_id).delete()
    ValueType.query.filter_by(organization_id=org_id).delete()
    GovernanceBody.query.filter_by(organization_id=org_id).delete()
    # ... delete everything

    db.session.commit()
    flash("All organization data cleared", "warning")
    return redirect(url_for('workspace.dashboard'))
```

**Database Impact:**
- CASCADE deletes all related entities
- Keeps organization record
- Keeps user memberships
- Audit log records the clear operation

---

## 📁 Files Reference

### Routes (Org Admin Access)
```
app/routes/organization_admin.py
├─ /org-admin                          # Dashboard
├─ /org-admin/onboarding               # Onboarding wizard
├─ /org-admin/spaces                   # Manage spaces
├─ /org-admin/spaces/create            # Create space
├─ /org-admin/spaces/<id>/edit         # Edit space
├─ /org-admin/challenges               # Manage challenges
├─ /org-admin/initiatives              # Manage initiatives
├─ /org-admin/systems                  # Manage systems
├─ /org-admin/value-types              # Manage value types
├─ /org-admin/governance-bodies        # Manage governance bodies
├─ /org-admin/yaml/export              # Export YAML
├─ /org-admin/yaml/import              # Import YAML
└─ /org-admin/clear-data               # Clear all data
```

### Templates (Org Admin Specific)
```
app/templates/org-admin/
├─ index.html                          # Admin dashboard
├─ onboarding_step1.html               # Welcome
├─ onboarding_step2.html               # Create space
├─ onboarding_step3.html               # Create gov body
├─ onboarding_step4.html               # Create value types
├─ onboarding_step5.html               # Complete
├─ spaces.html                         # Manage spaces
├─ value_types.html                    # Manage value types
├─ governance_bodies.html              # Manage gov bodies
├─ yaml_export.html                    # Export page
└─ yaml_import.html                    # Import page
```

### Services (Org Admin Uses)
```
app/services/
├─ yaml_export_service.py              # YAML export logic
├─ yaml_import_service.py              # YAML import logic
├─ deletion_impact_service.py          # Shows what will be deleted
└─ audit_service.py                    # Logs all admin actions
```

### Decorators (Permission Checks)
```python
# app/routes/organization_admin.py

@organization_required
# Ensures user has org context

@any_org_admin_permission_required
# Allows if:
#   - is_org_admin = True (automatic)
#   - OR has at least one can_manage_* permission

@permission_required('can_manage_kpis')
# Allows if:
#   - is_org_admin = True (automatic)
#   - OR can_manage_kpis = True
```

---

## ✅ Key Differences from Regular User

| Feature | Regular User | Org Admin |
|---------|-------------|-----------|
| **View Workspace** | ✅ Yes | ✅ Yes |
| **Contribute Values** | ✅ If permitted | ✅ Always |
| **Create KPIs** | ✅ If permitted | ✅ Always |
| **Access /org-admin** | ❌ **No** | ✅ **Yes** |
| **Onboarding Wizard** | ❌ No | ✅ Yes |
| **YAML Backup/Restore** | ❌ No | ✅ Yes |
| **Clear All Data** | ❌ No | ✅ Yes |
| **Reorder Gov Bodies** | ❌ No | ✅ Yes |
| **Manage All Entities** | ⚠️ If each permission set | ✅ Always (auto) |
| **Bypass Permission Checks** | ❌ No | ✅ **Yes (within org)** |

---

## 🚫 What Org Admins CANNOT Do

### No Access To:
- **Global Admin Panel** (`/global-admin`)
  - Create new organizations
  - Manage users across organizations
  - Assign users to organizations
  - View health dashboard

- **Super Admin Panel** (`/super-admin`)
  - System-wide backups
  - SSO configuration
  - System settings
  - Announcements

### Cannot Manage:
- **Other Organizations**
  - Can only manage the org where `is_org_admin = True`
  - If member of multiple orgs, must switch org context

- **User Permissions (Yet)**
  - Future feature: Org admins will be able to manage user permissions
  - Currently: Only Global Admins can assign permissions

---

## 🎓 When to Make Someone Org Admin

### Make Org Admin If:
- ✅ User needs **full control** over organization
- ✅ User manages organization structure regularly
- ✅ User performs backups/restores
- ✅ User is the **organization owner/lead**
- ✅ Simpler than setting 10+ individual permissions

### Keep as Regular User If:
- User only enters data (`can_contribute` is enough)
- User only creates KPIs (`can_manage_kpis` is enough)
- User doesn't need backup/restore access
- You want **granular control** over what they can do

### Decision Tree:
```
Does user need full org control?
├─ YES → Make Org Admin (is_org_admin = True)
└─ NO → Use granular permissions
    ├─ Only data entry → can_contribute = True
    ├─ Manage specific areas → can_manage_X = True
    └─ Multiple permissions → Consider Org Admin instead
```

---

## 📊 Testing as Org Admin

### Test Login
```bash
# Browser
http://localhost:5003/auth/login

# Login with org admin credentials
Username: admin.mikron
Password: (from global admin)
```

### Verify Org Admin Status
```python
# Flask shell
flask shell
>>> from app.models import User
>>> user = User.query.filter_by(login='admin.mikron').first()
>>> org_id = 1
>>> user.is_org_admin(org_id)  # Should be True
>>> user.can_manage_kpis(org_id)  # Should be True (auto)
>>> user.can_manage_spaces(org_id)  # Should be True (auto)
```

### Test Admin Panel Access
```bash
# Try accessing org-admin panel
http://localhost:5003/org-admin

# Should see admin dashboard (not error)
```

### Test Permission Bypass
```bash
# Try creating KPI without can_manage_kpis permission
# Should work because is_org_admin = True
```

---

## 🔄 Next Steps

1. Understand higher roles:
   - [Global Admin](./ROLE_GLOBAL_ADMIN.md) - Manages multiple orgs
   - [Super Admin](./ROLE_SUPER_ADMIN.md) - System-wide access

2. Review previous role:
   - [Regular User](./ROLE_USER_REGULAR.md) - Base permissions

3. Check overall map: [ROLE_BASED_ACCESS_MAP.md](./ROLE_BASED_ACCESS_MAP.md)

---

*Org Admins are the guardians of their organization - empower them!*
