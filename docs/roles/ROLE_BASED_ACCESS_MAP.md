# CISK Navigator - Role-Based Access Control Map

**Purpose:** Complete mapping of user experiences by role
**Date:** 2026-03-13
**Version:** 1.22.0

---

## 📋 Overview

This document provides a comprehensive map of:
- ✅ What each role can do
- ✅ Which features they can access
- ✅ Which entities they can manipulate
- ✅ Code files involved (routes, templates, models)
- ✅ Complete user journeys

---

## 🎭 Roles Hierarchy

```
┌─────────────────────────────────────┐
│        Super Admin                  │  ← Full system access
│  (is_super_admin = True)           │     Manages everything
└─────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────┐
│        Global Admin                 │  ← Manages organizations
│  (is_global_admin = True)          │     and users
└─────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────┐
│     Organization Admin              │  ← Manages one org
│  (membership.is_org_admin = True)  │     Full org permissions
└─────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────┐
│        Regular User                 │  ← Organization member
│  (membership with permissions)     │     Limited permissions
└─────────────────────────────────────┘
```

---

## 🔑 Permission Levels

### Level 1: Super Admin
- **Database Field:** `users.is_super_admin = True`
- **Bypasses:** ALL permission checks
- **Access:** Everything (super admin panel + global admin + org admin + user)
- **User Count:** Typically 1-2 per installation

### Level 2: Global Admin (Instance Admin)
- **Database Field:** `users.is_global_admin = True`
- **Bypasses:** Organization-level permission checks
- **Access:** Global admin panel + org admin + user features
- **User Count:** 2-5 per installation

### Level 3: Organization Admin
- **Database Field:** `user_organization_memberships.is_org_admin = True`
- **Bypasses:** Permission checks within THEIR organization only
- **Access:** Org admin panel + user features (for their org)
- **User Count:** 1-3 per organization

### Level 4: Regular User
- **Database Field:** `user_organization_memberships.can_manage_*` flags
- **Bypasses:** Nothing - granular permissions
- **Access:** Only what permissions allow
- **User Count:** Unlimited

---

## 📊 Access Matrix

| Feature | Regular User | Org Admin | Global Admin | Super Admin |
|---------|-------------|-----------|--------------|-------------|
| **View Workspace** | ✅ Yes | ✅ Yes | ✅ Yes | ✅ Yes |
| **Contribute Values** | ✅ If permitted | ✅ Yes | ✅ Yes | ✅ Yes |
| **Create KPIs** | ✅ If permitted | ✅ Yes | ✅ Yes | ✅ Yes |
| **Manage Value Types** | ✅ If permitted | ✅ Yes | ✅ Yes | ✅ Yes |
| **Org Admin Panel** | ❌ No | ✅ Yes | ✅ Yes | ✅ Yes |
| **Global Admin Panel** | ❌ No | ❌ No | ✅ Yes | ✅ Yes |
| **Super Admin Panel** | ❌ No | ❌ No | ❌ No | ✅ Yes |
| **Manage Organizations** | ❌ No | ❌ No | ✅ Yes | ✅ Yes |
| **Manage All Users** | ❌ No | ❌ No | ✅ Yes | ✅ Yes |
| **System Settings** | ❌ No | ❌ No | ❌ No | ✅ Yes |

---

## 📂 Detailed Role Documentation

Each role has its own detailed documentation file:

### [→ Regular User Journey](./ROLE_USER_REGULAR.md)
- Workspace navigation
- Contributing values
- Viewing reports
- Creating entities (if permitted)
- Files: workspace.py, templates/workspace/

### [→ Organization Admin Journey](./ROLE_ORG_ADMIN.md)
- Organization onboarding
- Structure management
- User permissions (future feature)
- Value type creation
- YAML backup/restore
- Files: organization_admin.py, templates/org-admin/

### [→ Global Admin Journey](./ROLE_GLOBAL_ADMIN.md)
- Organization management
- User management
- Cross-org permissions
- Health monitoring
- Files: global_admin.py, templates/global_admin/

### [→ Super Admin Journey](./ROLE_SUPER_ADMIN.md)
- System-wide backups
- SSO configuration
- System settings
- Announcements
- Full database access
- Files: super_admin.py, templates/super_admin/

---

## 🔐 Permission System Architecture

### Models
```python
# app/models/user.py
class User:
    is_super_admin: bool      # System-wide admin
    is_global_admin: bool     # Instance admin

    def is_org_admin(org_id) → bool
    def can_manage_spaces(org_id) → bool
    def can_manage_kpis(org_id) → bool
    # ... other permission methods

# app/models/organization.py
class UserOrganizationMembership:
    is_org_admin: bool              # NEW! Organization admin flag
    can_manage_spaces: bool
    can_manage_value_types: bool
    can_manage_governance_bodies: bool
    can_manage_challenges: bool
    can_manage_initiatives: bool
    can_manage_systems: bool
    can_manage_kpis: bool
    can_view_comments: bool
    can_add_comments: bool
    can_contribute: bool
```

### Decorators
```python
# Workspace routes (all users)
@login_required
@organization_required

# Organization admin routes
@login_required
@organization_required
@any_org_admin_permission_required  # At least 1 permission OR is_org_admin

@login_required
@organization_required
@permission_required('can_manage_kpis')  # Specific permission OR is_org_admin

# Global admin routes
@login_required
@global_admin_required

# Super admin routes
@login_required
@super_admin_required
```

---

## 🎯 Navigation Structure by Role

### Regular User Navigation
```
CISK v1.22.0
├─ 📂 Organization (switch org)
├─ 📊 Dashboards
│   └─ View only
├─ 🚫 Admin (not visible)
└─ 👤 Profile
```

### Org Admin Navigation
```
CISK v1.22.0
├─ 📂 Organization (switch org)
├─ 📊 Dashboards
├─ ⚙️ Admin ← VISIBLE!
│   ├─ 🏢 MIKRON Administration
│   ├─ 🚫 Instance Admin (not visible)
│   └─ 🚫 Super Admin (not visible)
└─ 👤 Profile
```

### Global Admin Navigation
```
CISK v1.22.0
├─ 📂 Organization (switch org)
├─ 📊 Dashboards
├─ ⚙️ Admin
│   ├─ 🏢 MIKRON Administration
│   ├─ 🌐 Instance Admin ← VISIBLE!
│   └─ 🚫 Super Admin (not visible)
└─ 👤 Profile
```

### Super Admin Navigation
```
CISK v1.22.0
├─ 📂 Organization (switch org)
├─ 📊 Dashboards
├─ ⚙️ Admin
│   ├─ 🏢 MIKRON Administration
│   ├─ 🌐 Instance Admin
│   └─ 🔧 Super Admin ← ALL VISIBLE!
└─ 👤 Profile
```

---

## 📁 Files Reference

### Core Permission Files
```
app/
├─ models/
│   ├─ user.py                    # User model + permission methods
│   └─ organization.py            # UserOrganizationMembership + is_org_admin
│
├─ decorators.py                  # @super_admin_required, @global_admin_required
│
└─ routes/
    ├─ workspace.py               # @organization_required
    ├─ organization_admin.py      # @any_org_admin_permission_required
    ├─ global_admin.py            # @global_admin_required
    └─ super_admin.py             # @super_admin_required
```

### Template Files
```
app/templates/
├─ workspace/                     # All users
├─ org-admin/                     # Org admins
├─ global_admin/                  # Global admins
└─ super_admin/                   # Super admins
```

---

## 🔄 Permission Check Flow

```
User logs in
    │
    ├─ Is super_admin? → YES → Access EVERYTHING
    │                  → NO ↓
    │
    ├─ Is global_admin? → YES → Access global_admin + org_admin + workspace
    │                   → NO ↓
    │
    ├─ Has organization context?
    │   │
    │   ├─ Is org_admin for this org? → YES → Access org_admin + workspace
    │   │                              → NO ↓
    │   │
    │   └─ Check specific permissions
    │       │
    │       └─ can_manage_X? → YES → Access X
    │                        → NO → Deny
    │
    └─ No org context → Redirect to login/select org
```

---

## ✅ Testing Permission Access

### Test Regular User
```bash
# In browser DevTools or flask shell
current_user.is_super_admin  # False
current_user.is_global_admin  # False
current_user.is_org_admin(org_id)  # False
current_user.can_manage_kpis(org_id)  # True/False (depends on permission)
```

### Test Org Admin
```bash
current_user.is_super_admin  # False
current_user.is_global_admin  # False
current_user.is_org_admin(org_id)  # True ✓
current_user.can_manage_kpis(org_id)  # True (always, because org admin)
```

### Test Global Admin
```bash
current_user.is_super_admin  # False
current_user.is_global_admin  # True ✓
current_user.is_org_admin(org_id)  # True (treated as org admin everywhere)
```

### Test Super Admin
```bash
current_user.is_super_admin  # True ✓
# Everything returns True
```

---

## 🎓 Quick Reference: When to Use What

### When User Needs To...

**View workspace data only:**
- Role: Regular User
- Permissions: `can_view_comments`, `can_contribute` (optional)

**Manage KPIs and structure:**
- Role: Regular User OR Org Admin
- Permissions: `can_manage_kpis`, `can_manage_spaces`, etc.

**Full control over one organization:**
- Role: **Org Admin** (`is_org_admin = True`)
- No individual permissions needed - has ALL

**Manage multiple organizations:**
- Role: **Global Admin** (`is_global_admin = True`)

**System-wide configuration:**
- Role: **Super Admin** (`is_super_admin = True`)

---

## 📈 Next Steps

1. Read role-specific documentation:
   - [Regular User](./ROLE_USER_REGULAR.md)
   - [Organization Admin](./ROLE_ORG_ADMIN.md)
   - [Global Admin](./ROLE_GLOBAL_ADMIN.md)
   - [Super Admin](./ROLE_SUPER_ADMIN.md)

2. Understand user journeys in [USER_JOURNEY_MAP.md](../ux-journey/USER_JOURNEY_MAP.md)

3. Review permissions guide in [USER_GUIDE_PERMISSIONS.md](../../USER_GUIDE_PERMISSIONS.md)

---

*Keep this map updated when adding new roles or permissions!*
