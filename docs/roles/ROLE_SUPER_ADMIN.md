# Super Admin - Complete Journey Map

**Role:** Super Administrator (God Mode)
**Database:** `users.is_super_admin = True`
**Access Level:** UNLIMITED - Full system access, all features, all organizations

---

## 🎯 Role Overview

### Who Is This User?
- **System owner/architect** with complete control
- Has **unrestricted access** to everything
- **Primary activities:** System configuration, backups, SSO setup, announcements
- **Key difference:** Access to `/super-admin` panel + system-wide operations

### How Permissions Work
```python
# When is_super_admin = True:
- Bypasses ALL permission checks (every decorator)
- is_global_admin() → True (automatic)
- is_org_admin(ANY org) → True (automatic)
- can_*() → True (everything)
- Access to /super-admin → True
- Can do ANYTHING

# This is the TOP of the hierarchy
# No restrictions whatsoever
```

---

## 📊 Access Summary

| Feature Area | Access Level |
|--------------|-------------|
| **Everything** | ✅ **UNLIMITED** |
| **All User Features** | ✅ Yes |
| **All Org Admin Features** | ✅ Yes (all orgs) |
| **All Global Admin Features** | ✅ Yes |
| **Super Admin Panel** | ✅ **YES - Exclusive!** |
| **System-Wide Backups** | ✅ Yes |
| **Full Restore** | ✅ Yes |
| **SSO Configuration** | ✅ Yes |
| **System Settings** | ✅ Yes |
| **System Announcements** | ✅ Yes |
| **Direct Database Access** | ✅ Yes (via shell) |
| **Can Create Super Admins** | ✅ Yes (only super admins can) |

---

## 🗺️ Complete User Journeys

### Journey 1: Access Super Admin Panel

#### Step 1.1: Navigate to Admin Menu
**Location:** Top navigation bar

```
User Experience:
1. User sees navigation:
   [Organization ▼] [Dashboards] [Admin ▼] [Profile]

2. Click "Admin" dropdown
3. See menu:
   🏢 MIKRON Administration  ← Access any org
   🌐 Instance Admin         ← Full user/org management
   🔧 Super Admin            ← **VISIBLE - Exclusive!**

4. Click "Super Admin"
   → Redirects to /super-admin
```

---

#### Step 1.2: Super Admin Dashboard
**Route:** `/super-admin`
**Template:** `super_admin/index.html`
**File:** `app/routes/super_admin.py`

```
User Experience:
1. See super admin panel:

   ╔══════════════════════════════════════════╗
   ║ 🔧 Super Administration                  ║
   ║ System-Wide Configuration & Control      ║
   ╚══════════════════════════════════════════╝

   🏢 System Overview:
   - 5 Organizations
   - 23 Users (including 2 super admins)
   - 137 KPIs total
   - 1,234 Contributions
   - PostgreSQL 18 - 45.3 MB
   - Version: 1.22.0

   🔐 SSO Configuration:
   ┌─────────────────────┐
   │ [Configure SSO]     │
   └─────────────────────┘

   💾 System Backups:
   ┌─────────────────────┐ ┌─────────────────────┐
   │ [Full Backup]       │ │ [Full Restore]      │
   └─────────────────────┘ └─────────────────────┘

   📢 Announcements:
   ┌─────────────────────┐
   │ [Manage Announcements]│
   └─────────────────────┘

   ⚙️ System Settings:
   ┌─────────────────────┐
   │ [System Configuration]│
   └─────────────────────┘

   🗄️ Database Tools:
   ┌─────────────────────┐
   │ [Direct DB Access]  │
   └─────────────────────┘
```

---

### Journey 2: System-Wide Backup

**Purpose:** Backup ENTIRE CISK instance (all organizations) to a single file

#### Step 2.1: Initiate Full Backup
**Route:** `/super-admin/backup`
**Template:** `super_admin/backup.html`

```
User Experience:
1. Click "Full Backup"
2. See backup configuration page:

   ╔════════════════════════════════════════╗
   ║ 📦 System-Wide Backup                  ║
   ╚════════════════════════════════════════╝

   This will create a complete backup of:
   ✓ All organizations (5)
   ✓ All users and permissions (23)
   ✓ All KPIs and data (137 KPIs, 1,234 contributions)
   ✓ All configuration (SSO, settings, etc.)
   ✓ System metadata

   Backup Options:
   [✓] Include user passwords (hashed)
   [✓] Include deleted organizations
   [✓] Include audit logs
   [ ] Include SSO secrets (⚠️  sensitive!)

   Estimated backup size: ~50 MB

   [Cancel] [Download Full Backup]

3. Click "Download Full Backup"
   → Server generates complete backup
   → Downloads: cisk_full_backup_2026-03-13.zip
   → Contains:
     - backup.json (all data)
     - metadata.json (version, date, info)
     - README.txt (restoration instructions)
```

**Code Flow:**
```python
# app/routes/super_admin.py
@bp.route("/backup", methods=["GET", "POST"])
@login_required
@super_admin_required
def full_backup():
    if request.method == 'POST':
        # Use FullBackupService
        backup_data = FullBackupService.create_full_backup(
            include_passwords=request.form.get('include_passwords') == 'on',
            include_deleted=request.form.get('include_deleted') == 'on',
            include_audit_logs=request.form.get('include_audit_logs') == 'on',
            include_sso_secrets=request.form.get('include_sso_secrets') == 'on'
        )

        # Create ZIP file
        zip_file = create_backup_zip(backup_data)

        return send_file(
            zip_file,
            as_attachment=True,
            download_name=f'cisk_full_backup_{datetime.now().strftime("%Y-%m-%d")}.zip'
        )

    return render_template('super_admin/backup.html')
```

**Service Used:** `app/services/full_backup_service.py`

**Backup Contents:**
```json
{
  "metadata": {
    "version": "1.22.0",
    "backup_date": "2026-03-13T08:30:00Z",
    "postgres_version": "18",
    "organizations_count": 5,
    "users_count": 23
  },
  "organizations": [...],  // All org data
  "users": [...],          // All users
  "system_settings": {...}, // System config
  "sso_config": {...},     // SSO settings
  "audit_logs": [...]      // Full audit trail
}
```

---

#### Step 2.2: Full System Restore
**Route:** `/super-admin/restore`
**Template:** `super_admin/restore.html`

```
User Experience:
1. Click "Full Restore"
2. See MASSIVE WARNING PAGE:

   ╔════════════════════════════════════════╗
   ║ ⚠️⚠️⚠️  DANGER ZONE  ⚠️⚠️⚠️              ║
   ╚════════════════════════════════════════╝

   FULL SYSTEM RESTORE

   ⚠️  THIS WILL:
   - DELETE EVERYTHING in the database
   - REPLACE with backup data
   - CANNOT BE UNDONE
   - System will be OFFLINE during restore

   Current System:
   - 5 Organizations
   - 23 Users
   - 137 KPIs
   - ALL WILL BE DELETED

   Upload Backup File:
   [Choose File: cisk_full_backup_2026-03-13.zip]

   Type "DELETE EVERYTHING AND RESTORE" to confirm:
   [_______________________________________]

   [Cancel] [RESTORE FULL SYSTEM]

3. Select backup ZIP file
4. Type exact confirmation phrase
5. Click "RESTORE FULL SYSTEM"
   → Shows progress bar
   → Deletes everything
   → Imports backup
   → Restarts application
   → Takes 1-5 minutes depending on size
```

**Code Flow:**
```python
# app/routes/super_admin.py
@bp.route("/restore", methods=["GET", "POST"])
@login_required
@super_admin_required
def full_restore():
    if request.method == 'POST':
        # Strict confirmation check
        if request.form.get('confirmation') != "DELETE EVERYTHING AND RESTORE":
            flash("Confirmation phrase incorrect", "danger")
            return redirect(url_for('super_admin.restore'))

        file = request.files['backup_file']

        # Extract ZIP
        backup_data = extract_backup_zip(file)

        # Use FullRestoreService
        success = FullRestoreService.restore_full_system(
            backup_data,
            current_user_id=current_user.id
        )

        if success:
            flash("System restored successfully! Please log in again.", "success")
            return redirect(url_for('auth.logout'))
        else:
            flash("Restore failed! Check logs", "danger")

    return render_template('super_admin/restore.html')
```

**Service Used:** `app/services/full_restore_service.py`

**Database Impact:**
- TRUNCATE all tables
- INSERT all data from backup
- Rebuild indexes
- Reset sequences
- Audit log records restore operation

---

### Journey 3: SSO Configuration

**Purpose:** Configure Single Sign-On (OIDC, SAML, Google, Azure AD, etc.)

#### Step 3.1: View SSO Configuration
**Route:** `/super-admin/sso`
**Template:** `super_admin/sso_config.html`

```
User Experience:
1. Click "Configure SSO"
2. See SSO configuration page:

   ╔════════════════════════════════════════╗
   ║ 🔐 Single Sign-On Configuration       ║
   ╚════════════════════════════════════════╝

   Current Status: ❌ Disabled

   [ Enable SSO ]

   SSO Provider: [OIDC ▼]
   - OIDC (OpenID Connect)
   - SAML 2.0
   - Google Workspace
   - Azure AD
   - Okta

   Configuration:
   - Client ID: [_________________]
   - Client Secret: [_________________] (hidden)
   - Authorization URL: [_________________]
   - Token URL: [_________________]
   - User Info URL: [_________________]

   User Mapping:
   - Email field: [email]
   - Name field: [name]
   - Username field: [preferred_username]

   [Test SSO Connection] [Save Configuration]

3. Configure SSO provider
4. Click "Test SSO Connection" to verify
5. Click "Save Configuration"
   → Stores encrypted credentials
   → Enables SSO login
```

**Code Flow:**
```python
# app/routes/super_admin.py
@bp.route("/sso", methods=["GET", "POST"])
@login_required
@super_admin_required
def sso_configuration():
    if form.validate_on_submit():
        config = SSOConfig.query.first() or SSOConfig()
        config.provider = form.provider.data
        config.client_id = form.client_id.data
        config.client_secret = encrypt(form.client_secret.data)  # Encrypted!
        config.authorization_url = form.authorization_url.data
        config.token_url = form.token_url.data
        config.user_info_url = form.user_info_url.data
        config.is_enabled = form.is_enabled.data

        db.session.add(config)
        db.session.commit()

        flash("SSO configuration saved", "success")

    return render_template('super_admin/sso_config.html', form=form)
```

**Service Used:** `app/services/sso_service.py`

**Database Table:** `sso_config`

---

### Journey 4: System Announcements

**Purpose:** Post system-wide announcements visible to all users

#### Step 4.1: Manage Announcements
**Route:** `/super-admin/announcements`
**Template:** `super_admin/announcements.html`

```
User Experience:
1. Click "Manage Announcements"
2. See list of announcements:

   Active Announcements:
   ┌─────────────────────────────────────┐
   │ 🔔 System Maintenance                │
   │ March 15, 2026 - March 16, 2026     │
   │ Visible to: All Users               │
   │ [Edit] [Delete]                     │
   └─────────────────────────────────────┘

   ┌─────────────────────────────────────┐
   │ 🎉 New Feature Released              │
   │ March 10, 2026 - March 17, 2026     │
   │ Visible to: Organization Admins     │
   │ [Edit] [Delete]                     │
   └─────────────────────────────────────┘

3. Click "Create Announcement"
4. Fill form:
   - Title: "System Maintenance"
   - Message: "CISK Navigator will be offline..."
   - Type: [Info ▼] (Info, Warning, Success, Danger)
   - Start Date: [2026-03-15]
   - End Date: [2026-03-16]
   - Target Audience:
     ( ) All Users
     ( ) Specific Organizations: [select...]
     ( ) Specific Users: [select...]

5. Click "Create Announcement"
   → Announcement goes live
   → Users see banner at top of page
   → Can acknowledge to dismiss
```

**Code Flow:**
```python
# app/routes/super_admin.py
@bp.route("/announcements/create", methods=["GET", "POST"])
@login_required
@super_admin_required
def create_announcement():
    if form.validate_on_submit():
        announcement = SystemAnnouncement(
            title=form.title.data,
            message=form.message.data,
            type=form.type.data,
            start_date=form.start_date.data,
            end_date=form.end_date.data,
            target_audience=form.target_audience.data,
            created_by=current_user.id
        )
        db.session.add(announcement)

        # Create target links
        if form.target_audience.data == 'organizations':
            for org_id in form.target_organizations.data:
                link = AnnouncementTargetOrganization(
                    announcement=announcement,
                    organization_id=org_id
                )
                db.session.add(link)

        db.session.commit()
        return redirect(url_for('super_admin.announcements'))
```

**Database Tables:**
- `system_announcements`
- `announcement_target_organizations` (many-to-many)
- `announcement_target_users` (many-to-many)
- `user_announcement_acknowledgments` (who dismissed)

---

### Journey 5: System Settings

**Route:** `/super-admin/settings`
**Template:** `super_admin/system_settings.html`

```
User Experience:
1. Click "System Configuration"
2. See system settings:

   ╔════════════════════════════════════════╗
   ║ ⚙️ System Settings                     ║
   ╚════════════════════════════════════════╝

   Application Settings:
   - Application Name: [CISK Navigator]
   - Version: [1.22.0] (read-only)
   - Instance URL: [https://cisk.company.com]

   Database Settings:
   - Database: PostgreSQL 18
   - Connection: ✅ Healthy
   - Size: 45.3 MB

   Email Settings:
   - SMTP Server: [smtp.company.com]
   - SMTP Port: [587]
   - SMTP User: [noreply@company.com]
   - [✓] Enable TLS

   Security Settings:
   - Session Timeout: [30] minutes
   - Password Min Length: [8] characters
   - [✓] Require password change on first login
   - [✓] Enable audit logging

   Feature Flags:
   - [✓] Enable SSO
   - [✓] Enable comments
   - [✓] Enable mentions
   - [ ] Enable API (future)

   [Save Settings]

3. Modify settings
4. Click "Save Settings"
   → Updates system_settings table
   → Some changes require restart
```

---

### Journey 6: Direct Database Access

**Route:** `/super-admin/database`
**Template:** `super_admin/database.html`

```
User Experience:
1. Click "Direct DB Access"
2. See database query interface:

   ╔════════════════════════════════════════╗
   ║ 🗄️ Direct Database Access              ║
   ║ ⚠️  DANGER: Raw SQL execution          ║
   ╚════════════════════════════════════════╝

   Execute SQL Query:
   ┌────────────────────────────────────────┐
   │ SELECT * FROM users                    │
   │ WHERE is_active = true                 │
   │ LIMIT 10;                              │
   │                                        │
   └────────────────────────────────────────┘

   [Execute Query]

   Results (10 rows):
   ┌──────────────────────────────────────┐
   │ id | login     | email              │
   │ 1  | john.doe  | john@company.com   │
   │ 2  | jane.smith| jane@company.com   │
   │ ...                                  │
   └──────────────────────────────────────┘

   ⚠️  READ-ONLY MODE by default
   [ ] Enable write operations (very dangerous!)

WARNING: Use Flask shell for complex operations
```

**Code Flow:**
```python
# app/routes/super_admin.py
@bp.route("/database", methods=["GET", "POST"])
@login_required
@super_admin_required
def database_access():
    if request.method == 'POST':
        query = request.form.get('query')

        # Safety check: only allow SELECT by default
        if not request.form.get('enable_write'):
            if not query.strip().upper().startswith('SELECT'):
                flash("Only SELECT queries allowed without write mode", "danger")
                return redirect(url_for('super_admin.database_access'))

        try:
            result = db.session.execute(text(query))
            rows = result.fetchall()
            return render_template('super_admin/database.html', rows=rows, query=query)
        except Exception as e:
            flash(f"Query error: {str(e)}", "danger")

    return render_template('super_admin/database.html')
```

**WARNING:** This feature is VERY dangerous - use with extreme caution!

---

## 📁 Files Reference

### Routes (Super Admin Exclusive)
```
app/routes/super_admin.py
├─ /super-admin                            # Dashboard
├─ /super-admin/backup                     # Full system backup
├─ /super-admin/restore                    # Full system restore
├─ /super-admin/sso                        # SSO configuration
├─ /super-admin/sso/test                   # Test SSO connection
├─ /super-admin/announcements              # List announcements
├─ /super-admin/announcements/create       # Create announcement
├─ /super-admin/announcements/<id>/edit    # Edit announcement
├─ /super-admin/announcements/<id>/delete  # Delete announcement
├─ /super-admin/settings                   # System settings
└─ /super-admin/database                   # Direct DB access
```

### Templates (Super Admin Specific)
```
app/templates/super_admin/
├─ index.html                              # Dashboard
├─ backup.html                             # Backup page
├─ restore.html                            # Restore page (danger!)
├─ sso_config.html                         # SSO configuration
├─ announcements.html                      # Announcement list
├─ create_announcement.html                # Create announcement
├─ edit_announcement.html                  # Edit announcement
├─ system_settings.html                    # System config
└─ database.html                           # DB query interface
```

### Services (Super Admin Uses)
```
app/services/
├─ full_backup_service.py                  # Complete system backup
├─ full_restore_service.py                 # Complete system restore
├─ sso_service.py                          # SSO integration
└─ audit_service.py                        # Logs everything
```

### Decorators (Permission Checks)
```python
# app/decorators.py

@super_admin_required
# Allows ONLY if:
#   - is_super_admin = True
# No other user can access super admin routes
```

---

## ✅ Key Differences from Global Admin

| Feature | Global Admin | Super Admin |
|---------|--------------|-------------|
| **Everything Global Admin Can Do** | ✅ Yes | ✅ **Yes** |
| **Full System Backup** | ❌ No | ✅ **Yes** |
| **Full System Restore** | ❌ No | ✅ **Yes** |
| **SSO Configuration** | ❌ No | ✅ **Yes** |
| **System Settings** | ❌ No | ✅ **Yes** |
| **System Announcements** | ❌ No | ✅ **Yes** |
| **Direct DB Access** | ❌ No | ✅ **Yes** |
| **Create Super Admins** | ❌ No | ✅ **Yes** |
| **Can Bypass Everything** | ✅ Almost | ✅ **EVERYTHING** |

---

## 🚫 What Super Admins Cannot Do

### Literally Nothing
- Super admins have **no restrictions**
- Can access and modify **anything**
- Even database-level operations

### Only Limitation
- **Should not abuse power**
- **Should follow best practices**
- **Should use audit log** (everything is tracked)

---

## ⚠️ Super Admin Responsibilities

### DO:
- ✅ Create regular backups
- ✅ Test SSO before enabling
- ✅ Document system changes
- ✅ Use staging environment for tests
- ✅ Keep credentials secure
- ✅ Monitor audit logs

### DON'T:
- ❌ Delete data without backups
- ❌ Test destructive operations in production
- ❌ Share super admin credentials
- ❌ Bypass security features
- ❌ Make undocumented changes

---

## 🎓 When to Make Someone Super Admin

### Make Super Admin If:
- ✅ User is **system owner/architect**
- ✅ User handles **infrastructure/DevOps**
- ✅ User performs **system backups**
- ✅ User configures **SSO/integrations**
- ✅ **Absolutely trusted** with full access

### Keep as Global Admin If:
- User only manages organizations and users
- User doesn't need system-wide operations
- User doesn't configure SSO or backups

### Decision Tree:
```
Does user need system-level operations?
├─ YES (backup/restore/SSO/settings) → Super Admin
└─ NO → Keep as Global Admin
    └─ Does user manage multiple orgs?
        ├─ YES → Global Admin
        └─ NO → Org Admin or User
```

---

## 📊 Testing as Super Admin

### Test Login
```bash
# Browser
http://localhost:5003/auth/login

# Login with super admin credentials
Username: admin.super
Password: (keep very secure!)
```

### Verify Super Admin Status
```python
# Flask shell
flask shell
>>> from app.models import User
>>> user = User.query.filter_by(login='admin.super').first()
>>> user.is_super_admin  # Should be True
>>> user.is_global_admin  # Should be True (auto)
>>> user.is_org_admin(ANY_ORG)  # Should be True (all orgs)
```

### Test All Panels
```bash
# Should have access to ALL three:
http://localhost:5003/super-admin    # Super admin ✓
http://localhost:5003/global-admin   # Global admin ✓
http://localhost:5003/org-admin      # Org admin ✓
```

---

## 🔄 Next Steps

1. Review all roles:
   - [Regular User](./ROLE_USER_REGULAR.md) - Base permissions
   - [Organization Admin](./ROLE_ORG_ADMIN.md) - One org management
   - [Global Admin](./ROLE_GLOBAL_ADMIN.md) - Multi-org management

2. Check overall map: [ROLE_BASED_ACCESS_MAP.md](./ROLE_BASED_ACCESS_MAP.md)

3. Review security best practices

---

*With great power comes great responsibility - use super admin wisely!*
