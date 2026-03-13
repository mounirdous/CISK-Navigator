# Regular User - Complete Journey Map

**Role:** Regular User (Organization Member)
**Database:** `user_organization_memberships` with granular permissions
**Access Level:** Limited to granted permissions within their organization

---

## 🎯 Role Overview

### Who Is This User?
- **Regular team member** working within one or more organizations
- Has **specific permissions** granted by admin (not full access)
- **Primary activities:** Enter data, view KPIs, create entities if allowed

### Core Permissions (Configurable)
```python
can_manage_spaces: bool           # Create/edit Spaces
can_manage_value_types: bool      # Create/edit Value Types
can_manage_governance_bodies: bool # Create/edit Governance Bodies
can_manage_challenges: bool       # Create/edit Challenges
can_manage_initiatives: bool      # Create/edit Initiatives
can_manage_systems: bool          # Create/edit Systems
can_manage_kpis: bool             # Create/edit KPIs
can_view_comments: bool           # View cell comments
can_add_comments: bool            # Add cell comments
can_contribute: bool              # Enter KPI values
```

---

## 📊 Access Summary

| Feature Area | Read | Create | Edit | Delete |
|--------------|------|--------|------|--------|
| **Workspace** | ✅ Always | ❌ | ❌ | ❌ |
| **Dashboards** | ✅ Always | ❌ | ❌ | ❌ |
| **Spaces** | ✅ Always | ✅ If `can_manage_spaces` | ✅ If `can_manage_spaces` | ✅ If `can_manage_spaces` |
| **Challenges** | ✅ Always | ✅ If `can_manage_challenges` | ✅ If `can_manage_challenges` | ✅ If `can_manage_challenges` |
| **Initiatives** | ✅ Always | ✅ If `can_manage_initiatives` | ✅ If `can_manage_initiatives` | ✅ If `can_manage_initiatives` |
| **Systems** | ✅ Always | ✅ If `can_manage_systems` | ✅ If `can_manage_systems` | ✅ If `can_manage_systems` |
| **KPIs** | ✅ Always | ✅ If `can_manage_kpis` | ✅ If `can_manage_kpis` | ✅ If `can_manage_kpis` |
| **Value Types** | ✅ Always | ✅ If `can_manage_value_types` | ✅ If `can_manage_value_types` | ✅ If `can_manage_value_types` |
| **Governance Bodies** | ✅ Always | ✅ If `can_manage_governance_bodies` | ✅ If `can_manage_governance_bodies` | ✅ If `can_manage_governance_bodies` |
| **Comments** | ✅ If `can_view_comments` | ✅ If `can_add_comments` | ✅ Own only | ✅ Own only |
| **Contributions** | ✅ Always | ✅ If `can_contribute` | ✅ Own only | ✅ Own only |
| **Org Admin Panel** | ❌ Never | ❌ | ❌ | ❌ |
| **Global Admin Panel** | ❌ Never | ❌ | ❌ | ❌ |

---

## 🗺️ Complete User Journeys

### Journey 1: First Login

#### Step 1.1: Authentication
**Route:** `/auth/login`
**Template:** `auth/login.html`
**File:** `app/routes/auth.py`

```
User Experience:
1. Open browser → https://cisk.company.com
2. See login page
3. Enter username/password (or use SSO)
4. Click "Sign In"
   → Authenticated
   → Redirected to organization selector (if multiple orgs)
```

**Code Flow:**
```python
# app/routes/auth.py
@bp.route("/login", methods=["GET", "POST"])
def login():
    # Validates credentials
    # Sets session
    # Redirects to select_organization or workspace
```

---

#### Step 1.2: Select Organization
**Route:** `/auth/select-organization`
**Template:** `auth/select_organization.html`
**File:** `app/routes/auth.py`

```
User Experience:
1. See list of organizations user belongs to
2. Click on organization name
   → Sets session['organization_id']
   → Sets session['organization_name']
   → Redirects to /workspace/dashboard
```

**Code Flow:**
```python
# app/routes/auth.py
@bp.route("/select-organization/<int:org_id>")
@login_required
def select_organization(org_id):
    # Validates user has access to org
    # Sets session variables
    # Redirects to dashboard
```

---

#### Step 1.3: Land on Dashboard
**Route:** `/workspace/dashboard`
**Template:** `workspace/dashboard.html`
**File:** `app/routes/workspace.py`

```
User Experience:
1. See organization overview
2. See statistics cards:
   - # Spaces
   - # Challenges
   - # Initiatives
   - # Systems
   - # KPIs
   - # Value Types
   - # Governance Bodies
3. See quick actions:
   - Open Workspace
   - Create Snapshot
   - Export Excel
4. Navigation bar at top:
   [Organization] [Dashboards] [Profile]
   Note: NO Admin menu (not an admin)
```

**Entities Displayed:**
- `Space`
- `Challenge`
- `Initiative`
- `System`
- `KPI`
- `ValueType`
- `GovernanceBody`

---

### Journey 2: View Workspace

#### Step 2.1: Open Workspace Grid
**Route:** `/workspace`
**Template:** `workspace/index.html`
**File:** `app/routes/workspace.py`

```
User Experience:
1. Click "Open Workspace" from dashboard
2. See hierarchical grid:

   ┌─ 🏢 Space: Digital Transformation
   │  ├─ 🎯 Challenge: Improve Customer Experience
   │  │  ├─ 💡 Initiative: New CRM System
   │  │  │  ├─ ⚙️ System: Salesforce Implementation
   │  │  │  │  ├─ 📊 KPI: User Adoption Rate
   │  │  │  │  │   └─ Value: 75% (Q4 2025)
   │  │  │  │  └─ 📊 KPI: Training Completion
   │  │  │  │      └─ Value: 90% (Q4 2025)

3. See filters:
   - Governance Bodies (pill toggles)
   - Show Archived KPIs (checkbox)
   - Level Visibility (show/hide levels)

4. Actions available:
   - Click cell → View KPI detail
   - Click KPI name → View KPI settings
   - Expand/collapse hierarchy
```

**Entities Displayed:**
- `Space` (always visible)
- `Challenge` (if level not hidden)
- `Initiative` (if level not hidden)
- `System` (if level not hidden)
- `KPI` (if level not hidden)
- `Contribution` (values in cells)
- `KPISnapshot` (rollup values)

**Code Flow:**
```python
# app/routes/workspace.py
@bp.route("/")
@login_required
@organization_required
def index():
    # Loads entire hierarchy
    # Applies filters
    # Renders grid with all data
```

---

#### Step 2.2: Click KPI Cell (View Detail)
**Route:** `/workspace/kpi/<kpi_id>/value-type/<vt_id>`
**Template:** `workspace/kpi_cell_detail.html`
**File:** `app/routes/workspace.py`

```
User Experience:
1. Click on KPI cell value (e.g., "75%")
2. See KPI detail page:

   ╔════════════════════════════════════╗
   ║  User Adoption Rate                ║
   ║  🧑‍🤝‍🧑 MANUAL ENTRY                  ║
   ║  STRONG CONSENSUS                  ║
   ║                                    ║
   ║        75.00 %                     ║  ← BIG!
   ║                                    ║
   ║  Based on 3 contributions          ║
   ╚════════════════════════════════════╝

3. Scroll down to see:
   - Historical trend chart
   - Contribution table
   - Consensus information cards

4. IF can_contribute = True:
   - See "Add/Update Contribution" form
   - Enter name, value, comment
   - Submit → Updates consensus

5. IF can_contribute = False:
   - Form not visible
   - Can only view data
```

**Entities Used:**
- `KPI`
- `KPIValueTypeConfig`
- `ValueType`
- `Contribution` (list of all contributions)
- `KPISnapshot` (historical values)

**Permissions Checked:**
```python
# In template
{% if current_user.can_contribute(org_id) %}
    <!-- Show contribution form -->
{% endif %}
```

---

### Journey 3: Contribute KPI Value

**Route:** `/workspace/kpi/<kpi_id>/value-type/<vt_id>/contribute`
**Method:** POST
**File:** `app/routes/workspace.py`

```
User Journey:
1. User fills contribution form:
   - Name: "Q4 2025 Report"
   - Value: 75.0
   - Comment: "Based on December survey"
   - Date: (auto: today)

2. Click "Submit Contribution"
   → POST request
   → Server validates
   → Creates Contribution record
   → Recalculates consensus
   → Redirects back to KPI detail

3. See updated value immediately
```

**Code Flow:**
```python
# app/routes/workspace.py
@bp.route("/kpi/<int:kpi_id>/value-type/<int:value_type_id>/contribute", methods=["POST"])
@login_required
@organization_required
def contribute_value(kpi_id, value_type_id):
    # Permission check
    if not current_user.can_contribute(session['organization_id']):
        flash("No permission", "danger")
        return redirect(...)

    # Create contribution
    contrib = Contribution(...)
    db.session.add(contrib)

    # Trigger consensus recalculation
    ConsensusService.calculate(...)

    db.session.commit()
    return redirect(url_for('workspace.kpi_cell_detail', ...))
```

**Database Changes:**
- INSERT into `contributions` table
- UPDATE `kpi_snapshots` with new consensus value
- INSERT into `audit_logs` (who contributed what)

---

### Journey 4: Create KPI (If Permitted)

**Prerequisite:** `can_manage_kpis = True`

#### Step 4.1: Navigate to Initiative-System Link
**Route:** `/workspace`

```
User Journey:
1. Open workspace
2. Find Initiative-System link
3. See "+" button next to link
4. Click "+" button
   → Redirects to KPI creation form
```

---

#### Step 4.2: Fill KPI Form
**Route:** `/kpis/create/<link_id>`
**Template:** `workspace/create_kpi.html`
**File:** `app/routes/workspace.py`

```
User Journey:
1. See KPI creation form:
   - Name: "User Adoption Rate"
   - Description: "Percentage of trained users actively using system"
   - Value Types: [✓] Percentage [ ] Cost [ ] Effort
   - Governance Bodies: [✓] Steering Committee
   - Colors: (optional)

2. Click "Create KPI"
   → Validates form
   → Creates KPI
   → Creates KPIValueTypeConfig for each selected VT
   → Redirects to KPI detail

3. See new KPI in workspace grid
```

**Code Flow:**
```python
# app/routes/workspace.py
@bp.route("/kpis/create/<int:link_id>", methods=["GET", "POST"])
@login_required
@organization_required
def create_kpi(link_id):
    # Permission check
    if not current_user.can_manage_kpis(session['organization_id']):
        abort(403)

    if form.validate_on_submit():
        kpi = KPI(...)
        db.session.add(kpi)

        # Create configs for each value type
        for vt_id in form.value_types.data:
            config = KPIValueTypeConfig(kpi=kpi, value_type_id=vt_id)
            db.session.add(config)

        db.session.commit()
        return redirect(...)
```

**Entities Created:**
- `KPI` (1 record)
- `KPIValueTypeConfig` (1+ records, one per value type)
- `kpi_governance_body_links` (many-to-many)

---

### Journey 5: View Comments (If Permitted)

**Route:** `/workspace/kpi/<kpi_id>/value-type/<vt_id>/comments`
**File:** `app/routes/workspace.py`

```
User Journey (if can_view_comments = True):
1. Click on KPI cell
2. Scroll to "Comments" section
3. See list of comments:
   - @john.doe mentioned: "Please verify this value"
   - @jane.smith replied: "Verified, looks good"

4. IF can_add_comments = True:
   - See "Add Comment" form
   - Write comment with @mentions
   - Submit → Creates comment + notifications
```

**Entities Used:**
- `CellComment`
- `MentionNotification` (if @mention used)

**Permissions:**
```python
{% if current_user.can_view_comments(org_id) %}
    <!-- Show comments -->
    {% if current_user.can_add_comments(org_id) %}
        <!-- Show add comment form -->
    {% endif %}
{% endif %}
```

---

## 📁 Files Reference

### Routes (User Can Access)
```
app/routes/
├─ auth.py
│   ├─ /login                    # Login page
│   ├─ /logout                   # Logout
│   └─ /select-organization      # Org selector
│
├─ workspace.py
│   ├─ /                         # Workspace grid
│   ├─ /dashboard                # Dashboard
│   ├─ /kpi/<id>/value-type/<vt> # KPI detail
│   ├─ /kpi/<id>/contribute      # Submit contribution (if can_contribute)
│   ├─ /kpis/create              # Create KPI (if can_manage_kpis)
│   ├─ /kpis/<id>/edit           # Edit KPI (if can_manage_kpis)
│   └─ ... (other workspace routes)
│
└─ analytics.py (future)
    └─ /analytics/dashboard      # Analytics views
```

### Templates (User Sees)
```
app/templates/
├─ auth/
│   ├─ login.html
│   └─ select_organization.html
│
├─ workspace/
│   ├─ index.html                # Main grid
│   ├─ dashboard.html            # Overview
│   ├─ kpi_cell_detail.html      # KPI detail page
│   ├─ create_kpi.html           # KPI form
│   └─ ...
│
└─ base.html                      # Base template (navbar)
```

### Models (User Interacts With)
```
app/models/
├─ user.py                       # Current user
├─ organization.py               # Current org + memberships
├─ space.py                      # Spaces
├─ challenge.py                  # Challenges
├─ initiative.py                 # Initiatives
├─ system.py                     # Systems
├─ kpi.py                        # KPIs
├─ value_type.py                 # Value types
├─ governance_body.py            # Governance bodies
├─ contribution.py               # User contributions
├─ kpi_snapshot.py               # KPI values
└─ cell_comment.py               # Comments
```

---

## 🚫 What Regular Users CANNOT Do

### No Access To:
- **Organization Admin Panel** (`/org-admin`)
  - Onboarding wizard
  - YAML backup/restore
  - Organization structure management
  - User management (future)

- **Global Admin Panel** (`/global-admin`)
  - Create organizations
  - Manage all users
  - Assign permissions
  - Health monitoring

- **Super Admin Panel** (`/super-admin`)
  - System backups
  - SSO configuration
  - Announcements
  - System settings

### Cannot Create (Without Permissions):
- Spaces (needs `can_manage_spaces`)
- Challenges (needs `can_manage_challenges`)
- Initiatives (needs `can_manage_initiatives`)
- Systems (needs `can_manage_systems`)
- KPIs (needs `can_manage_kpis`)
- Value Types (needs `can_manage_value_types`)
- Governance Bodies (needs `can_manage_governance_bodies`)

### Cannot Contribute (Without Permission):
- KPI values (needs `can_contribute`)
- Comments (needs `can_add_comments`)

---

## ✅ Common Permission Combinations

### Read-Only User
```python
can_manage_*: False (all)
can_view_comments: True
can_add_comments: False
can_contribute: False
```
**Use Case:** Executive viewing dashboards, no data entry

---

### Data Entry User
```python
can_manage_*: False (all)
can_view_comments: True
can_add_comments: True
can_contribute: True  ← KEY!
```
**Use Case:** Team member entering KPI values regularly

---

### Power User
```python
can_manage_spaces: True
can_manage_challenges: True
can_manage_initiatives: True
can_manage_systems: True
can_manage_kpis: True
can_manage_value_types: False
can_manage_governance_bodies: False
can_view_comments: True
can_add_comments: True
can_contribute: True
```
**Use Case:** Team lead managing structure + entering data

---

### Full User (Almost Admin)
```python
can_manage_*: True (all)
can_view_comments: True
can_add_comments: True
can_contribute: True
```
**Use Case:** De facto admin without is_org_admin flag
**Note:** Consider making them Org Admin instead!

---

## 🎓 Quick Decision Tree

**User wants to...**

1. **View workspace data?**
   - No permission needed ✅

2. **Enter KPI values?**
   - Needs `can_contribute = True`

3. **Create KPIs?**
   - Needs `can_manage_kpis = True`

4. **Manage organization structure?**
   - Needs multiple `can_manage_*` flags
   - OR consider making Org Admin

5. **Full control?**
   - Make them **Org Admin** (`is_org_admin = True`)
   - Don't use individual permissions

---

## 📊 Testing as Regular User

### Test Login
```bash
# Browser
http://localhost:5003/auth/login

# Login with test user credentials
Username: test.user
Password: (from admin)
```

### Verify Permissions
```python
# Flask shell
flask shell
>>> from app.models import User
>>> user = User.query.filter_by(login='test.user').first()
>>> org_id = 1
>>> user.can_contribute(org_id)  # True/False
>>> user.can_manage_kpis(org_id)  # True/False
>>> user.is_org_admin(org_id)  # Should be False
```

### Test Permission Denial
```bash
# Try accessing org-admin panel
http://localhost:5003/org-admin

# Should redirect with error:
# "You do not have permission to access organization administration"
```

---

## 🔄 Next Steps

1. Understand higher roles:
   - [Organization Admin](./ROLE_ORG_ADMIN.md)
   - [Global Admin](./ROLE_GLOBAL_ADMIN.md)
   - [Super Admin](./ROLE_SUPER_ADMIN.md)

2. Review user journeys: [USER_JOURNEY_MAP.md](../ux-journey/USER_JOURNEY_MAP.md)

3. Check permission guide: [USER_GUIDE_PERMISSIONS.md](../../USER_GUIDE_PERMISSIONS.md)

---

*Regular users are the heart of CISK Navigator - make their experience simple!*
