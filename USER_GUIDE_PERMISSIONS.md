# CISK Navigator - User Permissions Guide

**Version 1.12.0 - March 2026**

This guide explains the per-organization user permission system introduced in v1.12.0.

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

Each user-organization membership has **6 independent permissions**:

| Permission | Controls Access To |
|------------|-------------------|
| **Spaces** | Create, edit, delete spaces |
| **Value Types** | Create, edit, delete value types (Cost, CO2, Risk, etc.) |
| **Challenges** | Create, edit, delete challenges |
| **Initiatives** | Create, edit, delete initiatives |
| **Systems** | Create, edit, delete systems |
| **KPIs** | Create, edit, delete KPIs |

### Default Behavior
- **New users**: All permissions enabled by default
- **Existing users** (after v1.12.0 upgrade): All permissions enabled by default
- **Global administrators**: Always have full access, regardless of permission settings

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
   - ☑️ Spaces
   - ☑️ Value Types
   - ☑️ Challenges
   - ☑️ Initiatives
   - ☑️ Systems
   - ☑️ KPIs
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

---

## 🚫 What Happens When Permission is Denied?

### In the UI
- **Buttons are hidden** automatically
  - "Create Space", "Create Challenge", "Create KPI" buttons disappear
  - "Edit", "Delete" buttons disappear from lists
- User only sees entities, cannot modify them

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
- Permissions only control **create/edit/delete operations**
- Users can **always view** workspace data (if they have org access)
- Users can **always enter values** on KPI cells
- Users can **always add comments**

### Permission Independence
- Permissions are independent
- Having "Challenges" permission doesn't give "Initiatives" permission
- You can have any combination of permissions

### Backward Compatibility
- After upgrading to v1.12.0, **all existing users have all permissions**
- You must explicitly uncheck permissions to restrict access
- This ensures no disruption to existing workflows

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

*Last updated: March 8, 2026 - v1.12.0*
