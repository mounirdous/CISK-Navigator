# CISK Navigator - Functional Specifications

**Version 1.8**
**Date: March 6, 2026**

## Table of Contents

1. [Overview](#overview)
2. [User Roles](#user-roles)
3. [Core Features](#core-features)
4. [Hierarchical Data Model](#hierarchical-data-model)
5. [Authentication & Access Control](#authentication--access-control)
6. [Workspace & Tree/Grid Navigation](#workspace--treegrid-navigation)
7. [Data Entry & Consensus Model](#data-entry--consensus-model)
8. [Value Types](#value-types)
9. [Roll-up Aggregation](#roll-up-aggregation)
10. [Administration Features](#administration-features)

## Overview

CISK Navigator is a web-based collaborative data collection and aggregation system for tracking KPIs across a hierarchical organization structure. It enables teams to:

- Define organizational hierarchies (Spaces → Challenges → Initiatives → Systems → KPIs)
- Collect data from multiple contributors for each KPI
- Calculate consensus automatically based on contributions
- Roll up aggregated values through the hierarchy
- Support multiple value types (numeric, risk, impact)
- Manage everything through a user-friendly web interface

**Key Design Principles:**
- **Consensus-driven**: Multiple contributors provide input, system calculates consensus
- **Hierarchical aggregation**: Values roll up from KPIs → Systems → Initiatives → Challenges → Spaces
- **Flexible reusability**: Initiatives can address multiple challenges, systems can support multiple initiatives
- **Context-specific KPIs**: KPIs belong to initiative-system pairs, not master systems
- **Organization isolation**: Each organization has completely separate data

## User Roles

### Global Administrator
- Manages users across all organizations
- Creates and manages organizations
- Assigns users to organizations
- Cannot access organization business data

### Organization User
- Views and navigates organization structure
- Enters data for KPIs (as a contributor)
- Views consensus status and rolled-up values
- Has access to assigned organizations only

### Organization Administrator
- All organization user capabilities, plus:
- Creates and manages organization structure (Spaces, Challenges, Initiatives, Systems, KPIs)
- Configures value types
- Manages display order and metadata

**Note**: In the current implementation, all organization users have admin capabilities. Granular permissions are planned for future versions.

## Core Features

### Two-Step Login
1. **Step 1**: Username and password authentication
2. **Step 2**: Organization selection (filtered to user's accessible organizations)
   - Admin users see "Log in as Administrator" checkbox for global admin access
   - Regular users only see organizations they have access to

### Interactive Tree/Grid Workspace
- Expandable/collapsible hierarchical view
- Expand All / Collapse All buttons
- Color-coded levels:
  - **Spaces** (blue): Top-level groupings
  - **Challenges** (light gray): Business challenges
  - **Initiatives** (gray): Strategic initiatives
  - **Systems** (light blue): Technical systems
  - **KPIs** (yellow): Measurable indicators
- Value columns show consensus values with status badges
- Click any KPI cell to enter/view data

### Consensus-Based Data Entry
- Multiple contributors can provide values for each KPI
- System automatically calculates consensus status:
  - **No Data** (gray): No contributions yet
  - **Strong Consensus** (green): Single contribution OR all contributors agree - eligible for roll-up
  - **Weak Consensus** (yellow): Majority agrees but not unanimous
  - **No Consensus** (red): Conflicting values, no agreement
- Edit existing contributions by clicking "Edit" button
- Values display in workspace with status badges

### Value Types
- **Numeric**: Cost, CO2 emissions, licenses, people, etc.
  - Integer or decimal format
  - Configurable decimal places
  - Unit labels (€, tCO2e, licenses, etc.)
- **Qualitative**:
  - **Risk**: Levels 1-3 (!, !!, !!!)
  - **Impact**: Levels 1-3 (★, ★★, ★★★)
  - **Negative Impact**: Levels 1-3 (▼, ▼▼, ▼▼▼)
- Dynamic form fields: numeric-specific fields only show for numeric types
- Organization-specific: each organization defines its own value types

### Hierarchical Administration
- Create entities in context with nested buttons:
  - **Space** → + Challenge button
  - **Challenge** → + Initiative button
  - **Initiative** → + System button
  - **System** → + KPI button
- Full tree view in administration with all levels visible
- Edit any entity at any level
- Color-coded and indented for clarity

## Hierarchical Data Model

### Organizational Hierarchy

```
Organization
    └── Space (e.g., Season 1, Site A, Customer X)
        └── Challenge (business problem to solve)
            └─┬─ ChallengeInitiativeLink
              └── Initiative (strategic program)
                  └─┬─ InitiativeSystemLink
                    └── System (technical system)
                        └── KPI (at context level)
                            └─┬─ KPIValueTypeConfig
                              ├── ValueType (Cost, Risk, Impact, etc.)
                              └── Contribution (from individual contributors)
```

### Key Relationships

**Many-to-Many Reusability:**
- One Initiative can address multiple Challenges (via `ChallengeInitiativeLink`)
- One System can support multiple Initiatives (via `InitiativeSystemLink`)
- One KPI can track multiple Value Types (via `KPIValueTypeConfig`)

**Context-Specific KPIs:**
- KPIs belong to `InitiativeSystemLink`, not to the master System
- The same system in different initiatives can have completely different KPIs
- Example: "SAP" system under "Digital Transformation" initiative might track "License Cost" and "User Adoption", while "SAP" under "Finance Optimization" tracks "Processing Time" and "Error Rate"

## Authentication & Access Control

### Bootstrap Admin
On first startup, system creates:
- Login: `cisk`
- Password: `Zurich20`
- Role: Global Administrator
- Must change password on first login

### User Management
- Global admins manage all users
- Users can be assigned to multiple organizations
- User accounts are global, organization access is controlled via `UserOrganizationMembership`
- Password requirements: minimum 8 characters
- Passwords are hashed using Werkzeug security

### Session Management
- Flask-Login for user sessions
- Organization context stored in session:
  - `session['organization_id']`: Current organization or None for global admin
  - `session['organization_name']`: Display name
- Organization context enforced via `@organization_required` decorator

### Protection Rules
- Last active global admin cannot be deleted
- Users can only access organizations they're assigned to
- Regular users cannot access Global Administration
- CSRF protection on all forms (Flask-WTF)

## Workspace & Tree/Grid Navigation

### Tree Structure Display
- **Expand/Collapse**: Click arrow icons (▶/▼) to expand/collapse levels
- **Expand All**: Expand entire tree with one click
- **Collapse All**: Collapse entire tree with one click
- **Smart Collapse**: Collapsing a level automatically collapses all children

### Visual Hierarchy
- Progressive indentation: 2rem, 4rem, 6rem, 8rem
- Arrow symbols: → ⮕ ⇨ ⟹ for different levels
- Color coding by level for easy scanning
- Sticky header with value type columns

### Value Display
- **No Data**: "Click to enter" badge (gray)
- **Has Consensus**: Shows value + unit + status badge
- **No Consensus**: Shows "X conflicting values" + red badge
- Click any cell to view details and enter/edit data

### KPI Cell Detail View
Shows:
- Breadcrumb navigation (Org → Space → Challenge → Initiative → System → KPI)
- Value type information
- Consensus status card with:
  - Status badge
  - Consensus value (if exists)
  - Contribution count
  - Roll-up eligibility
- Contributions table with:
  - Contributor name
  - Value (with unit)
  - Comment
  - Timestamp
  - Edit button
- Add/Update contribution form

## Data Entry & Consensus Model

### Contribution Process
1. User navigates to KPI cell
2. Enters contributor name (free text, no account required)
3. Provides value:
   - Numeric types: decimal value
   - Qualitative types: level 1, 2, or 3
4. Optional comment
5. Submits

### Contribution Rules
- One contribution per contributor name per KPI cell
- Subsequent submissions with same name update existing contribution
- No user account binding - allows flexible contributor identification
- Contributors can be teams, roles, or individuals

### Consensus Calculation

**Algorithm:**
```
IF no contributions:
    status = NO_DATA
    is_rollup_eligible = false

ELSE IF only 1 contribution:
    status = STRONG_CONSENSUS
    value = contribution value
    is_rollup_eligible = TRUE  ← Single contribution is valid!

ELSE IF all contributions agree (same value):
    status = STRONG_CONSENSUS
    value = agreed value
    is_rollup_eligible = TRUE  ← Only strong consensus rolls up!

ELSE IF majority exists (>50%):
    status = WEAK_CONSENSUS
    value = majority value
    is_rollup_eligible = false

ELSE:
    status = NO_CONSENSUS
    value = null
    is_rollup_eligible = false
```

**Key Rule**: Strong Consensus (single contribution OR unanimous agreement) participates in upward roll-ups.

### Editing Contributions
- Click "Edit" button next to any contribution
- Form pre-populates with existing values
- Change values and submit to update
- Uses same contributor name to identify which contribution to update

## Value Types

### Creation
- Organization-specific
- Name, kind, display order
- Active/inactive flag

### Numeric Value Types
Fields displayed:
- Numeric format: Integer or Decimal
- Decimal places: 0-4
- Unit label: €, tCO2e, licenses, people, etc.
- Default aggregation formula: Sum, Min, Max, Avg

### Qualitative Value Types
Fields hidden:
- No numeric format
- No decimal places
- No unit label (symbols used instead)

Display symbols:
- Risk: !, !!, !!!
- Impact: ★, ★★, ★★★
- Negative Impact: ▼, ▼▼, ▼▼▼

### Dynamic Form Behavior
- Kind dropdown triggers show/hide of numeric fields
- JavaScript controls visibility based on selection
- Clean UX - only relevant fields shown

## Roll-up Aggregation

### Aggregation Flow
```
KPI (leaf level, contributions)
    ↓ [Value Type default formula]
System (first aggregation)
    ↓ [Configurable via InitiativeSystemLink RollupRule]
Initiative
    ↓ [Configurable via ChallengeInitiativeLink RollupRule]
Challenge
    ↓ [Configurable via Challenge RollupRule]
Space (root level)
```

### Aggregation Formulas
- **Sum**: Add all eligible values (most common for costs, emissions)
- **Min**: Minimum value (e.g., best-case scenario)
- **Max**: Maximum value (e.g., worst-case risk)
- **Avg**: Average value (e.g., mean impact)

### Partial Data Handling
If some child rows lack strong consensus:
- Ignore those rows in aggregation
- Compute parent value if at least one valid child exists
- Mark parent cell as "computed from partial data"
- Display indicator showing data completeness

### Roll-up Rules (Future Enhancement)
Location: `app/models/rollup_rule.py`
Current status: Data model exists, UI configuration pending
Enables per-context formula overrides

## Administration Features

### Global Administration
Accessible to: Global administrators only

**User Management:**
- Create new users
- Edit user details (login, email, display name)
- Assign users to organizations
- Activate/deactivate users
- Delete users (except last active global admin)

**Organization Management:**
- Create organizations
- Edit organization details
- Activate/deactivate organizations
- View organization statistics

### Organization Administration
Accessible to: Organization users (all users in current implementation)

**Space Management:**
- Create, edit, delete spaces
- Set space label (Season, Site, Customer, etc.)
- Set display order
- View full hierarchy

**Challenge Management:**
- Create challenges under spaces
- Edit challenge details
- Set display order
- View linked initiatives

**Initiative Management:**
- Create initiatives (linked to challenge)
- Edit initiative details
- Initiatives automatically available for reuse
- View linked systems

**System Management:**
- Create systems (linked to initiative)
- Edit system details
- Systems automatically available for reuse
- View KPIs in context

**KPI Management:**
- Create KPIs under initiative-system links
- Edit KPI details
- Select multiple value types for KPI
- Set display order

**Value Type Management:**
- Create value types
- Edit name, display order, active status
- Cannot edit kind, format, or formula after creation
- Delete check shows usage before deletion
- Cannot delete if used in KPIs, contributions, or rollup rules

### Hierarchical Creation Workflow
Administration view shows full tree with creation buttons at each level:
```
Space [Edit] [+ Challenge] [Delete]
    → Challenge [Edit] [+ Initiative]
        ⮕ Initiative [Edit] [+ System]
            ⇨ System [Edit] [+ KPI]
                ⟹ KPI [Edit]
```

Benefits:
- Context-aware creation
- Automatic linking
- Visual hierarchy understanding
- Quick navigation

## Version History

### v1.8 (Current)
- Two-step login with organization filtering
- Users only see organizations they have access to
- Admin checkbox only for global administrators
- Interactive tree/grid workspace with expand/collapse
- Expand All / Collapse All buttons
- Consensus values displayed in workspace
- Edit contributions functionality
- Conflicting values indicator
- Dynamic value type forms (hide numeric fields for qualitative types)
- Full hierarchical administration view

### v1.7
- Fixed numeric field visibility for value types
- Renamed "Positive Impact" to "Impact"
- JavaScript-based dynamic form fields

### v1.6
- Fixed organization dropdown validation
- Changed validator from DataRequired() to InputRequired() to allow organization ID 0

### v1.0 - v1.5
- Initial implementation
- Core data models
- Authentication system
- Basic CRUD operations
- Consensus calculation
- Initial workspace view

## Future Enhancements

### Planned Features
1. **Roll-up Rule Configuration UI**
   - Per-context formula overrides
   - Enable/disable roll-up at each level
   - Visual roll-up preview

2. **Granular Permissions**
   - Organization role: Admin vs. Viewer vs. Contributor
   - Space-level permissions
   - Challenge-level permissions

3. **Data Export**
   - Excel export with hierarchy
   - PDF reports
   - CSV for analysis

4. **Audit Trail**
   - Track all changes
   - Contribution history
   - Consensus changes over time

5. **Bulk Operations**
   - Copy KPI structure across contexts
   - Bulk value import
   - Template application

6. **Advanced Visualizations**
   - Charts and graphs
   - Trend analysis
   - Comparison views

7. **Notifications**
   - Alert on consensus reached
   - Alert on conflicting contributions
   - Weekly summary emails

8. **API Access**
   - REST API for integrations
   - Webhook support
   - Bulk data operations

## Technical Requirements

### Browser Support
- Modern browsers (Chrome, Firefox, Safari, Edge)
- JavaScript enabled
- Cookies enabled (for session management)

### Server Requirements
- Python 3.11+
- Flask 3.0
- SQLite 3 (or PostgreSQL for production)
- 100MB disk space minimum
- 512MB RAM minimum

### Deployment
- Runs on port 5003 by default
- Single-process server (development)
- Gunicorn for production deployment
- No external database server required (SQLite)

## Security Considerations

### Authentication
- Password hashing with Werkzeug (PBKDF2)
- Session-based authentication (Flask-Login)
- Forced password change for bootstrap admin
- No password hints or exposure

### Authorization
- Organization isolation enforced at database query level
- Session-based organization context
- Decorator-based route protection
- CSRF protection on all forms

### Data Protection
- SQL injection prevention via SQLAlchemy ORM
- XSS prevention via Jinja2 auto-escaping
- No sensitive data in logs
- Foreign key enforcement for referential integrity

### Best Practices
- Minimum 8-character passwords
- Session timeout on browser close
- No user enumeration during login
- Secure session cookies

---

**Document Version**: 1.8
**Last Updated**: March 6, 2026
**Author**: CISK Navigator Team
