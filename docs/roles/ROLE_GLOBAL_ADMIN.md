# Global Admin (Instance Admin) - Complete Journey Map

**Role:** Global Administrator / Instance Administrator
**Database:** `users.is_global_admin = True`
**Access Level:** Full access to ALL organizations + user management + system monitoring

---

## 🎯 Role Overview

### Who Is This User?
- **Instance administrator** who manages the entire CISK Navigator installation
- Has **full access** to all organizations (treated as Org Admin everywhere)
- **Primary activities:** Create organizations, manage users, monitor system health
- **Key difference:** Access to `/global-admin` panel + manages MULTIPLE organizations

### How Permissions Work
```python
# When is_global_admin = True:
- Bypasses ALL organization-level permission checks
- Treated as is_org_admin = True for EVERY organization
- Can access org-admin panel for any org
- Can create/edit/delete organizations
- Can manage all users and permissions

# Permission hierarchy:
is_global_admin(user) → True
  ├─ is_org_admin(ANY org_id) → True (treated as admin everywhere)
  ├─ can_manage_*(ANY org_id) → True (all permissions)
  └─ Access to /global-admin → True
```

---

## 📊 Access Summary

| Feature Area | Access Level |
|--------------|-------------|
| **Everything Org Admin Can Do** | ✅ Yes - For ALL organizations |
| **Everything Regular User Can Do** | ✅ Yes - All features |
| **Global Admin Panel** | ✅ **YES - This is the key difference!** |
| **Create Organizations** | ✅ Yes |
| **Edit Organizations** | ✅ Yes |
| **Delete Organizations** | ✅ Yes (with safeguards) |
| **Manage All Users** | ✅ Yes |
| **Assign Users to Orgs** | ✅ Yes |
| **Set Permissions** | ✅ Yes |
| **Health Monitoring** | ✅ Yes |
| **Cross-Org Operations** | ✅ Yes |
| **Super Admin Panel** | ❌ No (system settings only for super admin) |

---

## 🗺️ Complete User Journeys

### Journey 1: Access Global Admin Panel

#### Step 1.1: Navigate to Admin Menu
**Location:** Top navigation bar

```
User Experience:
1. User sees navigation:
   [Organization ▼] [Dashboards] [Admin ▼] [Profile]

2. Click "Admin" dropdown
3. See menu:
   🏢 MIKRON Administration  ← Can access any org
   🌐 Instance Admin         ← **VISIBLE!**
   🔧 Super Admin            ← NOT visible (not super admin)

4. Click "Instance Admin"
   → Redirects to /global-admin
```

---

#### Step 1.2: Global Admin Dashboard
**Route:** `/global-admin`
**Template:** `global_admin/index.html`
**File:** `app/routes/global_admin.py`

```
User Experience:
1. See global admin panel:

   ╔══════════════════════════════════════════╗
   ║ Global Administration                    ║
   ║ CISK Navigator Instance Management       ║
   ╚══════════════════════════════════════════╝

   📊 System Overview:
   - 5 Organizations (4 active, 1 deleted)
   - 23 Users (21 active, 2 inactive)
   - 137 KPIs across all organizations
   - 1,234 Contributions this month

   🏢 Organizations:
   ┌─────────────────────┐
   │ [View Organizations]│
   └─────────────────────┘

   👥 Users:
   ┌─────────────────────┐
   │ [Manage Users]      │
   └─────────────────────┘

   🏥 Health:
   ┌─────────────────────┐
   │ [Health Dashboard]  │
   └─────────────────────┘
```

**Entities Displayed:**
- System-wide statistics
- Links to management sections

---

### Journey 2: Manage Organizations

#### Step 2.1: View Organizations List
**Route:** `/global-admin/organizations`
**Template:** `global_admin/organizations.html`

```
User Experience:
1. Click "View Organizations"
2. See table of all organizations:

   Name         | Status  | Users | KPIs | Created    | Actions
   ------------ | ------- | ----- | ---- | ---------- | -------
   MIKRON       | Active  | 8     | 13   | 2025-01-15 | Edit | Delete
   FBT          | Active  | 5     | 8    | 2025-02-01 | Edit | Delete
   KPI Test     | Active  | 3     | 4    | 2025-03-10 | Edit | Delete
   OLD_ORG      | Deleted | -     | -    | 2024-12-01 | Restore

3. Click "[+ Create Organization]" button
   → Opens organization creation form
```

**Routes:**
- GET `/global-admin/organizations` - List all
- GET `/global-admin/organizations/create` - Create form
- POST `/global-admin/organizations/create` - Submit
- GET `/global-admin/organizations/<id>/edit` - Edit form
- POST `/global-admin/organizations/<id>/edit` - Submit edit
- GET `/global-admin/organizations/<id>/delete-preview` - Preview deletion
- POST `/global-admin/organizations/<id>/delete` - Soft delete

---

#### Step 2.2: Create Organization
**Route:** `/global-admin/organizations/create`
**Template:** `global_admin/create_organization.html`

```
User Experience:
1. Click "Create Organization"
2. See form:

   ┌────────────────────────────────────────┐
   │ Create New Organization                │
   ├────────────────────────────────────────┤
   │                                        │
   │ Name: [________________________]       │
   │       e.g., "ACME Corporation"         │
   │                                        │
   │ Description (optional):                │
   │ [________________________________]     │
   │ [________________________________]     │
   │                                        │
   │ Status: [✓] Active                     │
   │                                        │
   │ ┌────────────────────────────────────┐ │
   │ │ 👥 Assign Users                    │ │
   │ │                                    │ │
   │ │ Select users and their permissions │ │
   │ │                                    │ │
   │ │ [✓] John Doe                       │ │
   │ │     Permissions: [Checkboxes...]   │ │
   │ │                                    │ │
   │ │ [✓] Jane Smith                     │ │
   │ │     [✓] Organization Admin         │ │
   │ │                                    │ │
   │ └────────────────────────────────────┘ │
   │                                        │
   │ [Cancel] [Create Organization]         │
   └────────────────────────────────────────┘

3. Fill in details
4. Select users to assign
5. For each user, set:
   - [✓] Organization Admin (is_org_admin = True)
   - OR individual permissions (checkboxes)

6. Click "Create Organization"
   → Creates organization
   → Creates user memberships
   → Redirects to organization list
```

**Code Flow:**
```python
# app/routes/global_admin.py
@bp.route("/organizations/create", methods=["GET", "POST"])
@login_required
@global_admin_required
def create_organization():
    if form.validate_on_submit():
        # Create organization
        org = Organization(
            name=form.name.data,
            description=form.description.data,
            is_active=form.is_active.data
        )
        db.session.add(org)
        db.session.flush()

        # Assign users with permissions
        for user_id in form.users.data:
            membership = UserOrganizationMembership(
                user_id=user_id,
                organization_id=org.id,
                is_org_admin=request.form.get(f'perm_is_org_admin_{user_id}') == 'on',
                can_manage_spaces=request.form.get(f'perm_spaces_{user_id}') == 'on',
                # ... other permissions
            )
            db.session.add(membership)

        db.session.commit()
        return redirect(url_for('global_admin.organizations'))
```

**Database Changes:**
- INSERT into `organizations` table
- INSERT into `user_organization_memberships` (for each assigned user)
- Audit log entry

---

### Journey 3: Manage Users

#### Step 3.1: View Users List
**Route:** `/global-admin/users`
**Template:** `global_admin/users.html`

```
User Experience:
1. Click "Manage Users"
2. See table of all users:

   Login      | Display Name  | Email            | Status  | Roles        | Actions
   ---------- | ------------- | ---------------- | ------- | ------------ | -------
   john.doe   | John Doe      | john@company.com | Active  | Global Admin | Edit | Delete
   jane.smith | Jane Smith    | jane@company.com | Active  | Org Admin    | Edit | Delete
   bob.jones  | Bob Jones     | bob@company.com  | Active  | User         | Edit | Delete
   old.user   | Old User      | old@company.com  | Inactive| User         | Edit | Delete

3. Click "[+ Create User]" button
   → Opens user creation form
```

---

#### Step 3.2: Create User
**Route:** `/global-admin/users/create`
**Template:** `global_admin/create_user.html`

```
User Experience:
1. Click "Create User"
2. See form with sections:

   ┌────────────────────────────────────────┐
   │ 👤 Basic Information                   │
   ├────────────────────────────────────────┤
   │ Login: [______________]                │
   │ Email: [______________]                │
   │ Display Name: [______________]         │
   │ Password: [______________]             │
   │                                        │
   │ [✓] Active                             │
   │ [ ] Must Change Password               │
   └────────────────────────────────────────┘

   ┌────────────────────────────────────────┐
   │ 🔑 Global Roles                        │
   ├────────────────────────────────────────┤
   │ [ ] Global Administrator               │
   │ [ ] Super Administrator (super only)   │
   └────────────────────────────────────────┘

   ┌────────────────────────────────────────┐
   │ 🏢 Organizations & Permissions         │
   ├────────────────────────────────────────┤
   │ ✓ MIKRON                               │
   │   ┌──────────────────────────────────┐ │
   │   │ [✓] Organization Administrator   │ │
   │   │     (Full access to org)         │ │
   │   │                                  │ │
   │   │ OR Select Individual Permissions:│ │
   │   │ [✓] Spaces                       │ │
   │   │ [✓] Challenges                   │ │
   │   │ [✓] KPIs                         │ │
   │   │ ... (all checkboxes)             │ │
   │   └──────────────────────────────────┘ │
   │                                        │
   │ ✓ FBT                                  │
   │   [✓] Organization Administrator       │
   └────────────────────────────────────────┘

3. Fill in user details
4. For each organization:
   - Check org checkbox to assign
   - Check [✓] Org Administrator (simple)
   - OR check individual permissions (granular)

5. Click "Create User"
   → Creates user
   → Creates memberships
   → Sends welcome email (if configured)
```

**Code Flow:**
```python
# app/routes/global_admin.py
@bp.route("/users/create", methods=["GET", "POST"])
@login_required
@global_admin_required
def create_user():
    if form.validate_on_submit():
        user = User(
            login=form.login.data,
            email=form.email.data,
            display_name=form.display_name.data,
            is_active=form.is_active.data,
            is_global_admin=form.is_global_admin.data,
            is_super_admin=form.is_super_admin.data if current_user.is_super_admin else False,
            must_change_password=True
        )
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.flush()

        # Assign organizations with permissions
        for org_id in form.organizations.data:
            membership = UserOrganizationMembership(
                user_id=user.id,
                organization_id=org_id,
                is_org_admin=request.form.get(f'perm_is_org_admin_{org_id}') == 'on',
                # ... individual permissions
            )
            db.session.add(membership)

        db.session.commit()
        return redirect(url_for('global_admin.users'))
```

**Database Changes:**
- INSERT into `users` table
- INSERT into `user_organization_memberships` (for each org)
- Audit log entry

---

#### Step 3.3: Edit User
**Route:** `/global-admin/users/<user_id>/edit`
**Template:** `global_admin/edit_user.html`

```
User Experience:
1. Click "Edit" on user
2. See pre-filled form (same structure as create)
3. Can modify:
   - Email, display name
   - Active status
   - Global admin status
   - Organization assignments
   - **[NEW!] Org Admin checkbox** ← Visible now!
   - Individual permissions per org

4. Click "Save Changes"
   → Updates user
   → Updates memberships
   → Audit log records changes
```

**Key Feature:** The new `is_org_admin` checkbox is now visible and functional!

---

### Journey 4: Health Monitoring

#### Step 4.1: View Health Dashboard
**Route:** `/global-admin/health`
**Template:** `global_admin/health_dashboard.html`

```
User Experience:
1. Click "Health Dashboard"
2. See system health metrics:

   ╔════════════════════════════════════════╗
   ║ 🏥 System Health Dashboard             ║
   ╚════════════════════════════════════════╝

   📊 Database Status:
   - Connection: ✅ Healthy
   - Database: PostgreSQL 18
   - Connection URL: postgresql://localhost/cisknavigator
   - Tables: 25
   - Total Records: 12,456

   💾 Storage:
   - Database Size: 45.3 MB
   - Largest Table: contributions (8,234 rows)

   📈 Activity (Last 24 Hours):
   - Logins: 47
   - Contributions: 123
   - KPIs Created: 3
   - Comments: 28

   ⚠️ Warnings:
   - None

   📝 Recent Audit Log:
   - 2026-03-13 08:15 - john.doe created KPI "User Adoption"
   - 2026-03-13 08:10 - jane.smith exported YAML (MIKRON)
   - 2026-03-13 08:05 - bob.jones contributed value
```

**Code Flow:**
```python
# app/routes/global_admin.py
@bp.route("/health")
@login_required
@global_admin_required
def health_dashboard():
    # Gather health metrics
    health_data = {
        'db_connection': test_db_connection(),
        'db_size': get_database_size(),
        'table_counts': get_table_counts(),
        'recent_activity': get_recent_activity(),
        'audit_log': AuditLog.query.order_by(AuditLog.timestamp.desc()).limit(20).all()
    }

    return render_template('global_admin/health_dashboard.html', health=health_data)
```

---

### Journey 5: Delete Organization (Soft Delete)

**Route:** `/global-admin/organizations/<id>/delete-preview`
**Template:** `global_admin/delete_organization_preview.html`

```
User Experience:
1. Click "Delete" on organization
2. See deletion preview page:

   ╔════════════════════════════════════════╗
   ║ ⚠️  Delete Organization: OLD_ORG       ║
   ╚════════════════════════════════════════╝

   This organization will be SOFT DELETED:
   - Organization record preserved
   - All data archived (not destroyed)
   - Can be restored later

   What will be deleted:
   - 2 Spaces
   - 5 Challenges
   - 12 Initiatives
   - 8 Systems
   - 13 KPIs
   - 1,234 Contributions
   - 234 Snapshots

   Users will lose access but not be deleted:
   - 8 users currently have access

   Type organization name to confirm:
   [_________________]

   [Cancel] [Delete Organization]

3. Type org name: "OLD_ORG"
4. Click "Delete Organization"
   → Soft deletes org (sets is_deleted = True)
   → Redirects to organization list
   → Org shows as "Deleted" status
```

**Code Flow:**
```python
# app/routes/global_admin.py
@bp.route("/organizations/<int:org_id>/delete", methods=["POST"])
@login_required
@global_admin_required
def delete_organization(org_id):
    org = Organization.query.get_or_404(org_id)

    # Confirmation check
    if request.form.get('org_name') != org.name:
        flash("Organization name doesn't match", "danger")
        return redirect(...)

    # Soft delete
    org.soft_delete(current_user.id)
    db.session.commit()

    flash(f"Organization {org.name} deleted", "warning")
    return redirect(url_for('global_admin.organizations'))
```

**Database Changes:**
- UPDATE `organizations` SET:
  - `is_deleted = True`
  - `deleted_at = NOW()`
  - `deleted_by = current_user.id`
  - `is_active = False`
- No data actually deleted (soft delete)
- Can be restored later

---

## 📁 Files Reference

### Routes (Global Admin Access)
```
app/routes/global_admin.py
├─ /global-admin                           # Dashboard
├─ /global-admin/organizations             # List all orgs
├─ /global-admin/organizations/create      # Create org
├─ /global-admin/organizations/<id>/edit   # Edit org
├─ /global-admin/organizations/<id>/delete-preview  # Preview deletion
├─ /global-admin/organizations/<id>/delete # Soft delete
├─ /global-admin/organizations/<id>/restore # Restore deleted org
├─ /global-admin/users                     # List all users
├─ /global-admin/users/create              # Create user
├─ /global-admin/users/<id>/edit           # Edit user (with is_org_admin!)
├─ /global-admin/users/<id>/delete         # Delete user
└─ /global-admin/health                    # Health dashboard
```

### Templates (Global Admin Specific)
```
app/templates/global_admin/
├─ index.html                              # Dashboard
├─ organizations.html                      # Org list
├─ create_organization.html                # Create org form
├─ edit_organization.html                  # Edit org form
├─ delete_organization_preview.html        # Deletion preview
├─ users.html                              # User list
├─ create_user.html                        # Create user form
├─ edit_user.html                          # Edit user form (NEW: is_org_admin checkbox!)
└─ health_dashboard.html                   # Health metrics
```

### Services (Global Admin Uses)
```
app/services/
├─ audit_service.py                        # Logs all admin actions
└─ deletion_impact_service.py              # Shows deletion impact
```

### Decorators (Permission Checks)
```python
# app/decorators.py

@global_admin_required
# Allows only if:
#   - is_global_admin = True
#   - OR is_super_admin = True
```

---

## ✅ Key Differences from Org Admin

| Feature | Org Admin | Global Admin |
|---------|-----------|--------------|
| **Access Own Org** | ✅ One org | ✅ ALL orgs |
| **Access /org-admin** | ✅ One org only | ✅ **Any org** |
| **Create Organizations** | ❌ No | ✅ **Yes** |
| **Edit Any Organization** | ❌ No | ✅ **Yes** |
| **Delete Organizations** | ❌ No | ✅ **Yes** |
| **Manage Users** | ❌ No | ✅ **Yes** |
| **Assign Users to Orgs** | ❌ No | ✅ **Yes** |
| **Set Permissions** | ❌ No | ✅ **Yes** |
| **Health Monitoring** | ❌ No | ✅ **Yes** |
| **System Settings** | ❌ No | ❌ No (super only) |

---

## 🚫 What Global Admins CANNOT Do

### No Access To:
- **Super Admin Panel** (`/super-admin`)
  - System-wide backups (all orgs at once)
  - SSO configuration
  - System settings
  - Announcements
  - Direct database access

### Cannot Set:
- **is_super_admin flag**
  - Only super admins can create other super admins
  - Global admins can set is_global_admin flag

---

## 🎓 When to Make Someone Global Admin

### Make Global Admin If:
- ✅ User manages **multiple organizations**
- ✅ User handles **user onboarding** across orgs
- ✅ User needs **system-wide oversight**
- ✅ User is **IT administrator** for CISK instance
- ✅ Trusted with **cross-org operations**

### Keep as Org Admin If:
- User only manages ONE organization
- User doesn't need user management
- User doesn't need cross-org visibility

### Decision Tree:
```
Does user manage multiple orgs?
├─ YES → Make Global Admin
└─ NO → Keep as Org Admin
    └─ Does user manage one org fully?
        ├─ YES → Org Admin
        └─ NO → Regular User with permissions
```

---

## 📊 Testing as Global Admin

### Test Login
```bash
# Browser
http://localhost:5003/auth/login

# Login with global admin credentials
Username: admin.global
Password: (from super admin)
```

### Verify Global Admin Status
```python
# Flask shell
flask shell
>>> from app.models import User
>>> user = User.query.filter_by(login='admin.global').first()
>>> user.is_global_admin  # Should be True
>>> user.is_org_admin(1)  # Should be True (treated as org admin everywhere)
>>> user.is_org_admin(2)  # Should be True (all orgs)
```

### Test Admin Panels
```bash
# Global admin panel (should work)
http://localhost:5003/global-admin

# Org admin panel for any org (should work)
http://localhost:5003/org-admin

# Super admin panel (should redirect/error)
http://localhost:5003/super-admin
```

---

## 🔄 Next Steps

1. Understand higher role:
   - [Super Admin](./ROLE_SUPER_ADMIN.md) - System-wide access

2. Review lower roles:
   - [Organization Admin](./ROLE_ORG_ADMIN.md) - One org management
   - [Regular User](./ROLE_USER_REGULAR.md) - Base permissions

3. Check overall map: [ROLE_BASED_ACCESS_MAP.md](./ROLE_BASED_ACCESS_MAP.md)

---

*Global Admins are the instance managers - give them the keys!*
