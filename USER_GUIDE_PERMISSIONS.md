# CISK Navigator - User Permissions Guide

**Version 2.11.0 - March 2026**

This guide explains the per-organization user permission system introduced in v1.12.0 and expanded in v2.11.0.

---

## 🔐 Overview

CISK Navigator now supports **granular permissions** allowing administrators to control what users can create, edit, and delete on a **per-organization basis**. This means:

- ✅ Same user can have different permissions in different organizations
- ✅ Fine-grained control over 6 different entity types
- ✅ Global administrators automatically bypass all restrictions
- ✅ UI automatically hides buttons user cannot access
- ✅ Direct URL access is blocked with friendly error messages

---

## 📋 Permission Types

Each user-organization membership has **11 independent permissions**:

### Structural Entity Permissions (v1.12.0)

| Permission | Controls Access To |
|------------|-------------------|
| **Spaces** | Create, edit, delete spaces |
| **Value Types** | Create, edit, delete value types (Cost, CO2, Risk, etc.) |
| **Challenges** | Create, edit, delete challenges |
| **Initiatives** | Create, edit, delete initiatives |
| **Systems** | Create, edit, delete systems |
| **KPIs** | Create, edit, delete KPIs |

### Feature Access Permissions (v2.11.0)

| Permission | Controls Access To |
|------------|-------------------|
| **Contribute Values** | Enter/edit values in workspace cells |
| **View Action Items** | View action register menu and list |
| **Create Action Items** | Create/edit action items (requires View permission) |
| **View Stakeholders** | View stakeholders menu and list under People & Action |
| **Manage Stakeholders** | Create/edit/delete stakeholders (requires View permission) |
| **View Map** | View map dashboard menu and page |

### Default Behavior

**Structural Entity Permissions**:
- **New users**: All structural permissions enabled by default
- **Existing users** (after v1.12.0 upgrade): All structural permissions enabled by default

**Feature Access Permissions** (v2.11.0):
- **Contribute Values**: Enabled by default (new and existing users)
- **View/Create Action Items**: Enabled by default (backward compatibility)
- **View Map**: Enabled by default (backward compatibility)
- **View/Manage Stakeholders**: Disabled by default (new feature in v2.11.0)

**Admin Overrides**:
- **Global administrators**: Always have full access, regardless of permission settings
- **Organization administrators**: Always have full access within their organization

---

## 👥 User Roles

### Global Administrator
- Can access **Global Administration** menu
- Can create/edit users and organizations
- **Bypasses all permission checks** - always has full access
- To test permissions, you must uncheck "Global Administrator" checkbox

### Regular User
- Can only access organizations they're assigned to
- Permissions are checked per organization
- Cannot access Global Administration menu
- Can edit their own profile (display name, email)

---

## 🔧 Managing User Permissions

### Creating a New User

1. Navigate to **Global Administration → Users**
2. Click **Create User**
3. Fill in basic information (login, email, display name, password)
4. Check **organization checkboxes** for organizations user should access
5. For each checked organization, **permission checkboxes appear below**:

   **Structural Permissions**:
   - ☑️ Spaces
   - ☑️ Value Types
   - ☑️ Challenges
   - ☑️ Initiatives
   - ☑️ Systems
   - ☑️ KPIs

   **Feature Permissions**:
   - ☑️ Contribute Values (enter/edit data in workspace)
   - ☑️ View Action Items
   - ☑️ Create Action Items (requires View Action Items)
   - ☐ View Stakeholders
   - ☐ Manage Stakeholders (requires View Stakeholders)
   - ☑️ View Map

6. **Uncheck permissions** you want to restrict
7. Click **Create User**

**Note**: All permissions are checked by default. Uncheck only what you want to restrict.

### Editing Existing User Permissions

1. Navigate to **Global Administration → Users**
2. Click **Edit** on the user
3. Expand organizations by clicking checkboxes (if not already checked)
4. **Permission checkboxes show current settings**
5. Check/uncheck permissions as needed
6. Click **Save Changes**

**Important**: If user is a "Global Administrator", they will have full access regardless of permission checkboxes.

---

## 🎯 Use Cases

### Example 1: Read-Only User
**Scenario**: User should view data but not modify structure

**Solution**: Create user with **no permissions checked**
- User can still view workspace and enter values
- Cannot create/edit/delete any structural entities

### Example 2: KPI-Only User
**Scenario**: User manages KPIs but not organizational structure

**Solution**: Create user with only **KPIs** permission checked
- User can create/edit/delete KPIs
- Cannot modify spaces, challenges, initiatives, or systems
- Cannot create new value types

### Example 3: Different Permissions Per Organization
**Scenario**: User is admin in Org A, read-only in Org B

**Solution**:
- Assign user to both organizations
- In Org A: Check all permissions
- In Org B: Uncheck all permissions

### Example 4: Value Type Manager
**Scenario**: User manages value types across all organizations

**Solution**: Create user with only **Value Types** permission
- Can create/edit/delete value types
- Cannot modify organizational structure

### Example 5: Data Entry User (NEW in v2.11.0)
**Scenario**: User should only enter values in workspace, no structural changes

**Solution**: Create user with only **Contribute Values** checked
- Can enter/edit values in workspace cells
- Cannot create or edit any entities (spaces, challenges, KPIs, etc.)
- Cannot view action items, stakeholders, or map

### Example 6: Action Items Viewer (NEW in v2.11.0)
**Scenario**: User needs to see action items but not create them

**Solution**: Create user with only **View Action Items** checked
- Can see action register menu and view all action items
- Cannot create, edit, or delete action items
- Ideal for stakeholders who need visibility but not editing rights

### Example 7: Stakeholder Manager (NEW in v2.11.0)
**Scenario**: User manages stakeholders and map but nothing else

**Solution**: Create user with these permissions:
- ☑️ **View Stakeholders**
- ☑️ **Manage Stakeholders**
- ☑️ **View Map**
- All structural permissions unchecked
- Can add/edit stakeholders and view them on the map
- Cannot modify organizational structure

---

## 🚫 What Happens When Permission is Denied?

### In the UI

**Structural Permissions**:
- **Buttons are hidden** automatically
  - "Create Space", "Create Challenge", "Create KPI" buttons disappear
  - "Edit", "Delete" buttons disappear from lists
- User only sees entities, cannot modify them

**Feature Permissions (NEW in v2.11.0)**:
- **No Contribute Values**: Workspace cells are read-only, "Edit Mode" button hidden
- **No View Action Items**: "Action Register" menu item hidden
- **No Create Action Items**: "+ New Action Item" button hidden, existing items read-only
- **No View Stakeholders**: "Stakeholders" menu item hidden under People & Action
- **No Manage Stakeholders**: "+ New Stakeholder" button hidden, edit/delete buttons hidden
- **No View Map**: "Map" navigation icon hidden, direct URL access blocked

### Direct URL Access
- User is **redirected to Administration page**
- **Flash message** appears: "You do not have permission to perform this action"
- URL examples that would be blocked:
  - `/org-admin/value-types/create`
  - `/org-admin/challenges/123/edit`
  - `/org-admin/kpis/456/delete`

---

## 🔍 Checking Your Permissions

### As a User

1. Login and select your organization
2. Navigate to **Administration**
3. Look for available buttons:
   - If you see "Create Space" → You have Spaces permission
   - If you see "Create Value Type" → You have Value Types permission
   - If you see "+ Challenge" buttons → You have Challenges permission
   - And so on...

### As an Administrator

1. Go to **Global Administration → Users**
2. Click **Edit** on any user
3. Check/expand their organization assignments
4. View permission checkboxes for each organization

---

## ⚠️ Important Notes

### Global Administrators
- **Always have full access** regardless of permission settings
- To test restricted permissions, you must:
  1. Edit the user
  2. **Uncheck "Global Administrator"**
  3. Modify individual permissions
  4. Save changes

### Workspace Access
- Structural permissions only control **create/edit/delete operations** on entities
- Users can **always view** workspace data (if they have org access)
- Users need **Contribute Values** permission to enter/edit values on KPI cells (NEW in v2.11.0)
- Users can **always add comments** (commenting permission coming in future release)

### Permission Dependencies (NEW in v2.11.0)
- **Most permissions are independent**
- Having "Challenges" permission doesn't give "Initiatives" permission
- You can have any combination of permissions

**However, some permissions have dependencies**:
- **Create Action Items** requires **View Action Items**
  - If you uncheck "View Action Items", "Create Action Items" is automatically unchecked
- **Manage Stakeholders** requires **View Stakeholders**
  - If you uncheck "View Stakeholders", "Manage Stakeholders" is automatically unchecked

These dependencies are enforced in the UI with JavaScript and validated on the backend.

### Backward Compatibility

**v1.12.0 Upgrade**:
- After upgrading to v1.12.0, **all existing users have all structural permissions**
- You must explicitly uncheck permissions to restrict access
- This ensures no disruption to existing workflows

**v2.11.0 Upgrade** (NEW):
- **Contribute Values**: Enabled for all existing users (backward compatibility)
- **View/Create Action Items**: Enabled for all existing users (backward compatibility)
- **View Map**: Enabled for all existing users (backward compatibility)
- **View/Manage Stakeholders**: Disabled for all existing users (new feature, opt-in)
- This ensures existing workflows continue without changes

---

## 🐛 Troubleshooting

### "I can't see the Create button"
- **Check**: Do you have the appropriate permission?
- **Ask admin** to edit your user and check permission checkboxes

### "User has no permissions but can still edit everything"
- **Check**: Is user a Global Administrator?
- **Solution**: Uncheck "Global Administrator" to enforce permissions

### "After editing user, permissions didn't change"
- **Check**: Did you save the form?
- **Check**: Did you check/uncheck the correct organization's permissions?
- **Try**: Logout and login again

### "User can view but not edit - is this correct?"
- **Yes**: This is expected behavior when permissions are restricted
- Users can always view data in organizations they belong to
- They just cannot create/edit/delete structural entities

---

## 📚 Related Documentation

- [CHANGELOG.md](CHANGELOG.md) - Full version history
- [USER_GUIDE_V1.11.md](USER_GUIDE_V1.11.md) - Smart Value Entry & Target Tracking guide
- [README.md](README.md) - Project overview and features

---

## 🆘 Need Help?

If you encounter issues with the permission system:

1. **Check user's "Global Administrator" status** first
2. **Verify organization membership** is correct
3. **Check individual permission checkboxes** for each organization
4. **Test with a different user account** to isolate the issue
5. **Contact your system administrator**

---

*Last updated: March 18, 2026 - v2.11.0*
