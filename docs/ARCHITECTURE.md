# CISK Navigator - Architecture & Impact Analysis Documentation

**Version:** v1.17.0
**Last Updated:** 2026-03-11
**Purpose:** Comprehensive documentation for impact analysis, maintenance, and development

---

## Table of Contents

1. [Project Overview](#project-overview)
2. [Architecture Layers](#architecture-layers)
3. [Data Model Reference](#data-model-reference)
4. [Key Components](#key-components)
5. [Impact Analysis Guide](#impact-analysis-guide)
6. [File Reference](#file-reference)
7. [Common Operations](#common-operations)
8. [Database Migrations](#database-migrations)

---

## Project Overview

### What is CISK Navigator?

CISK Navigator is a strategic planning and KPI management platform that helps organizations:
- Organize strategic initiatives into Spaces
- Track challenges, initiatives, systems, and KPIs
- Measure value creation across multiple dimensions
- Create snapshots for historical comparison
- Collaborate through comments and governance bodies

### Technology Stack

- **Backend:** Flask (Python 3.11+)
- **Database:** PostgreSQL
- **ORM:** SQLAlchemy
- **Forms:** WTForms / Flask-WTF
- **Authentication:** Flask-Login + OAuth 2.0/OIDC
- **Frontend:** Bootstrap 5, Vanilla JS
- **Encryption:** Fernet (cryptography library)

### Project Structure

```
CISK-Navigator/
├── app/
│   ├── __init__.py              # Flask app factory
│   ├── config.py                # Configuration (dev, prod)
│   ├── extensions.py            # Flask extensions (db, login_manager)
│   ├── decorators.py            # Custom decorators (@super_admin_required, etc.)
│   ├── models/                  # SQLAlchemy models (database schema)
│   ├── routes/                  # Flask blueprints (URL endpoints)
│   ├── services/                # Business logic layer
│   ├── forms/                   # WTForms for validation
│   ├── templates/               # Jinja2 HTML templates
│   ├── static/                  # CSS, JS, images
│   └── utils/                   # Utility modules (encryption, etc.)
├── migrations/                  # Alembic database migrations
├── docs/                        # Documentation (this file)
├── tests/                       # Unit and integration tests
├── venv/                        # Virtual environment
├── requirements.txt             # Python dependencies
└── run.py                       # Application entry point
```

---

## Architecture Layers

### 1. **Presentation Layer** (Templates + Routes)

**Purpose:** Handle HTTP requests, render HTML, manage user sessions

**Files:**
- `app/templates/` - Jinja2 templates
- `app/routes/*.py` - Flask blueprints

**Key Routes:**
- `auth.py` - Login, logout, SSO, profile
- `workspace.py` - Main workspace, KPI grid, snapshots
- `global_admin.py` - Multi-organization management
- `organization_admin.py` - Organization-specific settings
- `super_admin.py` - System-wide settings

### 2. **Business Logic Layer** (Services)

**Purpose:** Encapsulate complex operations, avoid code duplication

**Files:**
- `app/services/sso_service.py` - SSO authentication flow
- `app/services/snapshot_service.py` - Snapshot creation/comparison
- `app/services/aggregation_service.py` - Rollup calculations
- `app/services/deletion_impact_service.py` - Cascade delete analysis
- `app/services/comment_service.py` - Comment management
- `app/services/excel_export_service.py` - Excel export
- `app/services/yaml_import_service.py` - YAML structure import (no data)
- `app/services/yaml_export_service.py` - YAML structure export (no data)
- `app/services/full_backup_service.py` - JSON full backup (structure + all data)
- `app/services/full_restore_service.py` - JSON full restore with governance body mapping
- `app/services/organization_clone_service.py` - Organization cloning

### 3. **Data Access Layer** (Models)

**Purpose:** Define database schema, relationships, and basic CRUD

**Files:** `app/models/*.py`

### 4. **Validation Layer** (Forms)

**Purpose:** Validate user input before processing

**Files:** `app/forms/*.py`

---

## Data Model Reference

### Core Hierarchy

```
Organization (multi-tenant)
  └─> Space (strategic area)
       └─> Challenge (problem statement)
            └─> Initiative (solution)
                 └─> System (implementation)
                      └─> KPI (metric)
                           └─> Contribution (value measurement)
```

### Model Relationships Diagram

```
┌──────────────┐
│ Organization │ (Multi-tenant container)
└──────┬───────┘
       │ 1:N
       ├─> Space (is_private flag)
       ├─> Challenge
       ├─> Initiative
       ├─> System
       ├─> KPI
       ├─> ValueType
       ├─> GovernanceBody
       └─> UserOrganizationMembership
           │
           └─> User (M:N via membership)

┌─────────┐
│  Space  │
└────┬────┘
     │ 1:N
     └─> Challenge
          └─> ChallengeInitiativeLink (M:N)
               └─> Initiative
                    └─> InitiativeSystemLink (M:N)
                         └─> System
                              └─> KPI (1:N)
                                   ├─> KPIValueTypeConfig (M:N)
                                   │    └─> ValueType
                                   ├─> KPIGovernanceBodyLink (M:N)
                                   │    └─> GovernanceBody
                                   ├─> Contribution (actual values)
                                   ├─> CellComment (discussions)
                                   └─> KPISnapshot (historical)

┌────────────┐
│ RollupRule │ (Aggregation formula)
└─────┬──────┘
      │
      └─> RollupSnapshot (calculated results)
```

### Authentication & Authorization

```
┌──────────────┐
│ SystemSetting│ (Global settings)
└──────────────┘

┌───────────┐
│ SSOConfig │ (Instance-wide SSO)
└───────────┘

┌──────┐
│ User │ (authentication identity)
└──┬───┘
   │ M:N
   └─> UserOrganizationMembership
        └─> Organization
             └─> Permissions (JSONB in membership)
```

---

## Key Components

### 1. **Organizations**

**Purpose:** Multi-tenancy - isolate data between different companies/departments

**Model:** `app/models/organization.py`
**Routes:** `app/routes/global_admin.py`
**Templates:** `app/templates/global_admin/organizations.html`

**Database Table:** `organizations`

**Key Fields:**
- `id` (PK)
- `name` - Organization name
- `is_active` - Soft delete flag
- `created_at`, `updated_at`

**Relationships:**
- 1:N with Spaces, Challenges, Initiatives, Systems, KPIs
- M:N with Users (via `user_organization_memberships`)

**Impact Analysis:**
- **Deleting an organization:** Cascades to ALL related data (spaces, challenges, KPIs, etc.)
- **Deactivating:** Hides from user access but preserves data
- **Cloning:** Copies entire structure (see `organization_clone_service.py`)

**Related Services:**
- `OrganizationCloneService` - Deep copy with data

---

### 2. **Spaces**

**Purpose:** Top-level strategic grouping (e.g., "Product Development", "Customer Success")

**Model:** `app/models/space.py`
**Routes:** `app/routes/organization_admin.py` (lines 50-200)
**Templates:** `app/templates/organization_admin/spaces.html`

**Database Table:** `spaces`

**Key Fields:**
- `id` (PK)
- `organization_id` (FK) - Parent organization
- `name` - Space name
- `description` - Optional description
- `is_private` - Privacy flag (v1.15.1+)
- `created_at`, `updated_at`

**Relationships:**
- N:1 with Organization
- 1:N with Challenges

**Impact Analysis:**
- **Deleting a space:** Cascades to challenges → initiatives → systems → KPIs
- **Making private:** Hides from users without explicit access
- **Column filtering:** Affects which value types show in workspace (v1.15.1+)

**Related Services:**
- `DeletionImpactService` - Preview cascading deletes

---

### 3. **Challenges**

**Purpose:** Problem statements or strategic objectives

**Model:** `app/models/challenge.py`
**Routes:** `app/routes/organization_admin.py` (lines 200-350)
**Templates:** `app/templates/organization_admin/challenges.html`

**Database Table:** `challenges`

**Key Fields:**
- `id` (PK)
- `organization_id` (FK)
- `space_id` (FK) - Parent space
- `name` - Challenge name
- `description`
- `display_order` - Sort order in UI

**Relationships:**
- N:1 with Space
- M:N with Initiatives (via `challenge_initiative_links`)

**Impact Analysis:**
- **Deleting a challenge:** Removes links to initiatives (but initiatives remain)
- **Changing space:** Affects workspace filtering
- **Reordering:** Only affects UI display

**Related Services:**
- `DeletionImpactService` - Shows linked initiatives

---

### 4. **Initiatives**

**Purpose:** Solutions or action plans addressing challenges

**Model:** `app/models/initiative.py`
**Routes:** `app/routes/organization_admin.py` (lines 350-500)
**Templates:** `app/templates/organization_admin/initiatives.html`

**Database Table:** `initiatives`

**Key Fields:**
- `id` (PK)
- `organization_id` (FK)
- `name` - Initiative name
- `description`
- `display_order`

**Relationships:**
- M:N with Challenges (via `challenge_initiative_links`)
- M:N with Systems (via `initiative_system_links`)

**Impact Analysis:**
- **Deleting an initiative:** Removes links to challenges and systems
- **Unlinking from challenge:** Doesn't delete initiative (just relationship)
- **Linking to systems:** Multiple initiatives can share systems

**Related Services:**
- `DeletionImpactService` - Shows challenge/system links

---

### 5. **Systems**

**Purpose:** Implementation components or technical systems

**Model:** `app/models/system.py`
**Routes:** `app/routes/organization_admin.py` (lines 500-650)
**Templates:** `app/templates/organization_admin/systems.html`

**Database Table:** `systems`

**Key Fields:**
- `id` (PK)
- `organization_id` (FK)
- `name` - System name
- `description`
- `display_order`

**Relationships:**
- M:N with Initiatives (via `initiative_system_links`)
- 1:N with KPIs

**Impact Analysis:**
- **Deleting a system:** Cascades to all child KPIs
- **Unlinking from initiative:** Doesn't delete system
- **Reordering:** Affects workspace layout

**Related Services:**
- `DeletionImpactService` - Shows KPIs and contributions

---

### 6. **KPIs (Key Performance Indicators)**

**Purpose:** Measurable metrics tracking progress

**Model:** `app/models/kpi.py`
**Routes:** `app/routes/organization_admin.py` (lines 700-900), `app/routes/workspace.py`
**Templates:** `app/templates/workspace/index.html`, `app/templates/organization_admin/create_kpi.html`

**Database Table:** `kpis`

**Key Fields:**
- `id` (PK)
- `organization_id` (FK)
- `system_id` (FK) - Parent system
- `name` - KPI name
- `description`
- `display_order`
- `is_archived` - Soft delete flag

**Relationships:**
- N:1 with System
- M:N with ValueTypes (via `kpi_value_type_configs`)
- M:N with GovernanceBodies (via `kpi_governance_body_links`)
- 1:N with Contributions (actual values)
- 1:N with CellComments
- 1:N with KPISnapshots (historical)

**Impact Analysis:**
- **Deleting a KPI:** Deletes all contributions, comments, snapshots
- **Archiving:** Hides from workspace (soft delete)
- **Changing value types:** Affects which columns show contributions
- **Governance body links:** Affects filtering in workspace

**Related Services:**
- `DeletionImpactService` - Shows contributions, comments
- `SnapshotService` - Historical tracking
- `AggregationService` - Rollup calculations
- `CommentService` - Discussion threads

---

### 7. **Value Types**

**Purpose:** Define dimensions of value measurement (e.g., "Revenue", "Time Saved")

**Model:** `app/models/value_type.py`
**Routes:** `app/routes/organization_admin.py` (lines 1000-1200)
**Templates:** `app/templates/organization_admin/value_types.html`

**Database Table:** `value_types`

**Key Fields:**
- `id` (PK)
- `organization_id` (FK)
- `name` - Value type name (e.g., "Revenue")
- `unit` - Measurement unit (e.g., "$")
- `description`
- `display_order` - Column order in grid

**Relationships:**
- M:N with KPIs (via `kpi_value_type_configs`)
- 1:N with Contributions (via `value_type_id`)

**Impact Analysis:**
- **Deleting a value type:** Deletes ALL contributions of that type (CRITICAL!)
- **Changing display order:** Affects grid column layout
- **Renaming:** Only affects display (data preserved)

**Related Services:**
- `ValueTypeUsageService` - Check where used before delete
- `AggregationService` - Rollup by value type

---

### 8. **Contributions**

**Purpose:** Actual value measurements (the "cells" in the KPI grid)

**Model:** `app/models/contribution.py`
**Routes:** `app/routes/workspace.py`
- `kpi_cell_detail(kpi_id, vt_id)` - View/add contributions (line ~270)
- `delete_contribution(kpi_id, vt_id)` - Delete contribution (line ~459)
**Templates:**
- `workspace/kpi_cell_detail.html` - Contribution form/list
- Inline grid cells in `workspace/index.html`

**Database Table:** `contributions`

**Key Fields:**
- `id` (PK)
- `kpi_id` (FK)
- `value_type_id` (FK)
- `value` - Numeric value
- `note` - Optional explanation
- `created_at`, `updated_at`
- `updated_by` (FK to User)

**Relationships:**
- N:1 with KPI
- N:1 with ValueType

**Impact Analysis:**
- **Deleting a contribution:** Only affects that cell
- **Updating value:** Tracked in snapshots if snapshot exists
- **Deleting parent KPI:** Cascades delete all contributions
- **Deleting parent ValueType:** Cascades delete all contributions

**Related Services:**
- `SnapshotService` - Captures contribution state
- `AggregationService` - Sums for rollups

---

### 9. **Snapshots**

**Purpose:** Point-in-time captures of KPI state for historical comparison

**Models:**
- `app/models/kpi_snapshot.py` - `KPISnapshot` (individual KPI)
- `app/models/kpi_snapshot.py` - `RollupSnapshot` (aggregated)

**Routes:** `app/routes/workspace.py` (lines 500-800)
**Templates:** `app/templates/workspace/snapshots.html`, `app/templates/workspace/compare_snapshots.html`

**Database Tables:** `kpi_snapshots`, `rollup_snapshots`

**KPISnapshot Fields:**
- `id` (PK)
- `organization_id` (FK)
- `kpi_id` (FK)
- `batch_id` - Groups snapshots taken together
- `snapshot_name` - User-defined label
- `snapshot_date` - When captured
- `data` (JSONB) - Frozen contribution values
- `is_public` - Privacy flag (v1.15.0+)
- `owner_user_id` (FK) - Creator (v1.15.0+)

**Relationships:**
- N:1 with KPI
- N:1 with Organization
- Grouped by `batch_id`

**Impact Analysis:**
- **Creating snapshot:** No impact on live data
- **Deleting snapshot:** Permanent loss of historical data
- **Deleting KPI:** Orphans snapshots (consider cascade)
- **Comparing snapshots:** Diffs contribution values

**Related Services:**
- `SnapshotService` - Creation, deletion, comparison

---

### 10. **Rollup Rules & Aggregation**

**Purpose:** Define how values aggregate upward through the hierarchy

**Model:** `app/models/rollup_rule.py`
**Service:** `app/services/aggregation_service.py`
**Routes:** `app/routes/organization_admin.py` - `configure_rollup()` (line 1328)
**Templates:** `app/templates/organization_admin/configure_rollup.html`

**Database Table:** `rollup_rules`

**Key Fields:**
- `id` (PK)
- `source_type` - Where rollup originates:
  - `initiative_system` - System → Initiative rollup
  - `challenge_initiative` - Initiative → Challenge rollup
  - `challenge` - Challenge → Space rollup
- `source_id` - ID of InitiativeSystemLink, ChallengeInitiativeLink, or Challenge
- `value_type_id` (FK) - Which value type rolls up
- `rollup_enabled` (Boolean) - Whether rollup is active
- `formula_override` - Aggregation formula:
  - `default` - Use value type's default formula
  - `sum` - Sum all child values
  - `min` - Minimum of child values
  - `max` - Maximum of child values
  - `avg` - Average of child values

**How It Works:**

```
KPI contributions (actual values)
        ↓ (rollup via InitiativeSystemLink rule)
System aggregated value
        ↓ (rollup via ChallengeInitiativeLink rule)
Initiative aggregated value
        ↓ (rollup via Challenge rule)
Challenge aggregated value
        ↓
Space aggregated value
```

**Relationships:**
- N:1 with ValueType
- Rules are entity-specific (not organization-wide defaults)

**Current Implementation Status:**
- ✅ **Model**: Fully implemented
- ✅ **Service**: `AggregationService` uses rollup rules for calculations
- ✅ **Database**: Table exists, relationships configured
- ⚠️ **UI**: Route and template exist but backend is a stub
  - Access: Organization Admin → Value Types → [Value Type] → "Rollup" button
  - Shows form but doesn't save (lines 1337-1358 are placeholders)
  - UI shows "Full per-context rollup configuration coming soon!"

**Access Path:**
1. Go to Organization Admin
2. Click "Value Types"
3. Click "Rollup" button next to any value type
4. Configure rollup rules (UI exists but save functionality incomplete)

**Design Note:**
Rollup rules are **per-entity**, not organization-wide. Each InitiativeSystemLink, ChallengeInitiativeLink, and Challenge can have different rollup settings for the same value type.

**Impact Analysis:**
- **Creating/modifying rules:** Affects aggregated displays in workspace
- **Deleting rules:** Rollup uses value type defaults
- **Disabling rollup:** Aggregated values won't appear
- **Formula changes:** Affects how child values combine

**Related Services:**
- `AggregationService.calculate_system_rollup()` - System → Initiative
- `AggregationService.calculate_initiative_rollup()` - Initiative → Challenge
- `AggregationService.calculate_challenge_rollup()` - Challenge → Space

---

### 11. **Governance Bodies**

**Purpose:** Committees, boards, or teams responsible for KPIs

**Model:** `app/models/governance_body.py`
**Routes:** `app/routes/organization_admin.py` (lines 1200-1350)
**Templates:** `app/templates/organization_admin/governance_bodies.html`

**Database Table:** `governance_bodies`

**Key Fields:**
- `id` (PK)
- `organization_id` (FK)
- `name` - Body name (e.g., "Executive Board")
- `description`

**Relationships:**
- M:N with KPIs (via `kpi_governance_body_links`)

**Impact Analysis:**
- **Deleting a governance body:** Removes links to KPIs (KPIs remain)
- **Filtering by governance body:** Affects workspace display

---

### 12. **Cell Comments**

**Purpose:** Discussion threads on KPI cells (contributions)

**Model:** `app/models/cell_comment.py`
**Routes:** `app/routes/workspace.py` (AJAX endpoints)
**Templates:** Modals in `workspace/index.html`

**Database Table:** `cell_comments`

**Key Fields:**
- `id` (PK)
- `kpi_id` (FK)
- `value_type_id` (FK)
- `user_id` (FK) - Comment author
- `comment` (Text) - Comment body
- `created_at`
- `parent_id` (FK) - For threaded replies

**Relationships:**
- N:1 with KPI
- N:1 with ValueType
- N:1 with User
- Self-referencing (threaded comments)

**Impact Analysis:**
- **Deleting comment:** Removes from thread
- **Deleting KPI:** Cascades delete all comments
- **User permissions:** `can_view_comments`, `can_add_comments`

**Related Services:**
- `CommentService` - CRUD operations
- `MentionNotification` - User mentions

---

### 12. **Users & Permissions**

**Purpose:** Authentication, authorization, multi-org access

**Models:**
- `app/models/user.py` - `User`
- `app/models/organization.py` - `UserOrganizationMembership`

**Routes:** `app/routes/auth.py`, `app/routes/global_admin.py`
**Templates:** `app/templates/auth/login.html`, `app/templates/global_admin/users.html`

**Database Tables:** `users`, `user_organization_memberships`

**User Fields:**
- `id` (PK)
- `login` - Username
- `email`
- `display_name`
- `password_hash` - Bcrypt (nullable for SSO users)
- `is_active` - Account status
- `is_super_admin` - System-wide access
- `is_global_admin` - Multi-org management
- `sso_provider` - SSO identity provider
- `sso_subject_id` - IdP user ID
- `dark_mode` - UI preference

**UserOrganizationMembership Fields:**
- `user_id` (FK)
- `organization_id` (FK)
- **Permissions (Boolean flags):**
  - `can_manage_spaces`
  - `can_manage_challenges`
  - `can_manage_initiatives`
  - `can_manage_systems`
  - `can_manage_kpis`
  - `can_manage_value_types`
  - `can_manage_governance_bodies`
  - `can_view_comments`
  - `can_add_comments`

**Permission Hierarchy:**
```
Super Admin (is_super_admin=True)
  └─> Full system access (SSO config, system settings)
      └─> Global Admin (is_global_admin=True)
          └─> Manage all organizations and users
              └─> Organization Admin (via membership permissions)
                  └─> Manage organization-specific settings
                      └─> Regular User (read-only or limited permissions)
```

**Impact Analysis:**
- **Deactivating user:** Loses access to all organizations
- **Removing org membership:** Loses access to that org only
- **Changing permissions:** Affects UI visibility and API access
- **SSO users:** Cannot use password login (password_hash is NULL)

---

### 13. **SSO Configuration**

**Purpose:** Instance-wide Single Sign-On authentication

**Model:** `app/models/sso_config.py`
**Routes:** `app/routes/super_admin.py`, `app/routes/auth.py`
**Templates:** `app/templates/super_admin/sso_config.html`, `app/templates/auth/login.html`

**Database Table:** `sso_config`

**Key Fields:**
- `id` (PK) - Singleton (only 1 row)
- `provider_type` - 'google', 'azure', 'okta', 'oidc'
- `is_enabled` - Master toggle
- `client_id` - OAuth client ID
- `client_secret` (Encrypted) - OAuth client secret
- `discovery_url` - OIDC discovery endpoint
- `auto_provision_users` - JIT provisioning flag
- `default_permissions` (JSONB) - New user permissions

**Relationships:**
- Singleton (1 row per instance)
- No FK relationships

**Impact Analysis:**
- **Enabling SSO:** Shows SSO button on login page
- **Disabling SSO:** Hides SSO button (users must use password)
- **Changing client secret:** Breaks SSO until updated
- **Auto-provisioning:** Creates user accounts on first SSO login

**Related Services:**
- `SSOService` - OAuth flow, JWT verification
- `EncryptionService` - Encrypt client secret

**Security:**
- Client secret encrypted at rest (Fernet)
- JWT signatures verified using JWKS
- CSRF protection via state parameter

---

## Impact Analysis Guide

### Deleting Entities - Cascade Analysis

#### **Organization Deletion:**
```
DELETE Organization
  ├─> CASCADE: Spaces
  │    └─> CASCADE: Challenges
  │         └─> CASCADE: ChallengeInitiativeLinks
  ├─> CASCADE: Initiatives
  │    └─> CASCADE: InitiativeSystemLinks
  ├─> CASCADE: Systems
  │    └─> CASCADE: KPIs
  │         ├─> CASCADE: Contributions
  │         ├─> CASCADE: CellComments
  │         ├─> CASCADE: KPISnapshots
  │         ├─> CASCADE: KPIValueTypeConfigs
  │         └─> CASCADE: KPIGovernanceBodyLinks
  ├─> CASCADE: ValueTypes
  ├─> CASCADE: GovernanceBodies
  ├─> CASCADE: RollupRules
  │    └─> CASCADE: RollupSnapshots
  └─> CASCADE: UserOrganizationMemberships
```

**Code:** `app/services/deletion_impact_service.py` - `get_organization_deletion_impact()`

#### **Space Deletion:**
```
DELETE Space
  └─> CASCADE: Challenges (within space)
       └─> CASCADE: ChallengeInitiativeLinks
       (Initiatives remain, just unlinked)
```

**Code:** `DeletionImpactService.get_space_deletion_impact()`

#### **KPI Deletion:**
```
DELETE KPI
  ├─> CASCADE: Contributions
  ├─> CASCADE: CellComments
  ├─> CASCADE: KPISnapshots
  ├─> CASCADE: KPIValueTypeConfigs (M:N links)
  └─> CASCADE: KPIGovernanceBodyLinks (M:N links)
```

**Code:** `DeletionImpactService.get_kpi_deletion_impact()`

#### **ValueType Deletion:**
```
DELETE ValueType
  ├─> CASCADE: Contributions (ALL using this value type!)
  ├─> CASCADE: KPIValueTypeConfigs (M:N links)
  ├─> CASCADE: RollupSnapshots (contains value_type_id FK)
  └─> UPDATE: Snapshots (value type columns removed from historical data)
```

**⚠️ CRITICAL:** This is the most destructive operation! Always check usage first.

**Code:** `ValueTypeUsageService.get_value_type_usage()`

---

### Permission Impact Matrix

| Permission | Grants Access To |
|------------|------------------|
| `can_manage_spaces` | Create/edit/delete spaces |
| `can_manage_challenges` | Create/edit/delete challenges |
| `can_manage_initiatives` | Create/edit/delete initiatives |
| `can_manage_systems` | Create/edit/delete systems |
| `can_manage_kpis` | Create/edit/delete KPIs, contributions |
| `can_manage_value_types` | Create/edit/delete value types |
| `can_manage_governance_bodies` | Create/edit/delete governance bodies |
| `can_view_comments` | See comment icons and threads |
| `can_add_comments` | Post comments, reply, mention users |

**Dependency:** `can_add_comments` requires `can_view_comments` (enforced in UI)

**Code:** `app/decorators.py` - Permission decorators

---

### Database Schema Changes

**CRITICAL:** Always create migration file before modifying models!

**Workflow:**
1. Modify model in `app/models/*.py`
2. Create migration: `flask db revision -m "description"`
3. Edit migration file in `migrations/versions/`
4. Apply locally: `flask db upgrade`
5. Test thoroughly
6. Commit BOTH model and migration file

**Migration Chain Integrity:**
- Production tracks current revision in `alembic_version` table
- NEVER insert migrations into middle of chain after production deployment
- If you forget a migration, create NEW migration at end (don't rewrite history)

**Code:** `migrations/versions/*.py`

---

## File Reference

### Models (`app/models/*.py`)

| File | Model(s) | Purpose |
|------|----------|---------|
| `user.py` | `User` | Authentication, user accounts |
| `organization.py` | `Organization`, `UserOrganizationMembership` | Multi-tenancy, user-org relationships |
| `sso_config.py` | `SSOConfig` | Instance-wide SSO settings |
| `system_setting.py` | `SystemSetting` | Global system settings |
| `space.py` | `Space` | Strategic groupings |
| `challenge.py` | `Challenge` | Problem statements |
| `initiative.py` | `Initiative`, `ChallengeInitiativeLink` | Solutions, challenge links |
| `system.py` | `System`, `InitiativeSystemLink` | Implementation components |
| `kpi.py` | `KPI` | Metrics |
| `value_type.py` | `ValueType`, `KPIValueTypeConfig` | Value dimensions |
| `contribution.py` | `Contribution` | Actual measurements |
| `governance_body.py` | `GovernanceBody`, `KPIGovernanceBodyLink` | Responsible committees |
| `rollup_rule.py` | `RollupRule` | Aggregation formulas |
| `kpi_snapshot.py` | `KPISnapshot`, `RollupSnapshot` | Historical snapshots |
| `cell_comment.py` | `CellComment`, `MentionNotification` | Discussions, mentions |

### Routes (`app/routes/*.py`)

| File | Blueprint | Purpose |
|------|-----------|---------|
| `auth.py` | `auth` | Login, logout, SSO, profile |
| `workspace.py` | `workspace` | KPI grid, snapshots, comments |
| `global_admin.py` | `global_admin` | Multi-org management |
| `organization_admin.py` | `org_admin` | Org-specific settings |
| `super_admin.py` | `super_admin` | System-wide settings |

### Services (`app/services/*.py`)

| File | Purpose |
|------|---------|
| `sso_service.py` | OAuth flow, JWT verification |
| `snapshot_service.py` | Snapshot CRUD, comparison |
| `aggregation_service.py` | Rollup calculations |
| `deletion_impact_service.py` | Cascade analysis |
| `comment_service.py` | Comment CRUD, mentions |
| `excel_export_service.py` | Export to Excel |
| `yaml_import_service.py` | Import structure from YAML (no data) |
| `yaml_export_service.py` | Export structure to YAML (no data) |
| `full_backup_service.py` | Full backup to JSON (structure + all data) |
| `full_restore_service.py` | Full restore from JSON with GB mapping |
| `organization_clone_service.py` | Deep copy org structure |
| `value_type_usage_service.py` | Check value type usage |
| `consensus_service.py` | Agreement tracking |

### Forms (`app/forms/*.py`)

| File | Purpose |
|------|---------|
| `auth_forms.py` | Login, password change |
| `user_forms.py` | User create/edit |
| `organization_forms.py` | Organization create/edit |
| `sso_forms.py` | SSO configuration |
| `space_forms.py` | Space create/edit |
| `challenge_forms.py` | Challenge create/edit |
| `initiative_forms.py` | Initiative create/edit |
| `system_forms.py` | System create/edit |
| `kpi_forms.py` | KPI create/edit |
| `value_type_forms.py` | Value type create/edit |
| `governance_body_forms.py` | Governance body create/edit |
| `contribution_forms.py` | Contribution edit |
| `rollup_forms.py` | Rollup rule create/edit |
| `yaml_forms.py` | YAML import |
| `organization_clone_forms.py` | Organization clone |

### Templates (`app/templates/`)

**Structure:**
```
templates/
├── base.html                    # Master layout
├── auth/                        # Login, profile
├── workspace/                   # KPI grid, snapshots
├── global_admin/                # Multi-org management
├── organization_admin/          # Org settings
├── super_admin/                 # System settings
└── errors/                      # 404, 500, 403
```

---

## Common Operations

### Adding a New Entity Type

1. **Create Model:** `app/models/my_entity.py`
   - Define SQLAlchemy model
   - Add relationships
   - Import in `models/__init__.py`

2. **Create Migration:**
   ```bash
   flask db revision -m "add my_entity table"
   # Edit migration file
   flask db upgrade
   ```

3. **Create Form:** `app/forms/my_entity_forms.py`
   - Define WTForms class
   - Add validators

4. **Create Routes:** `app/routes/organization_admin.py` (or appropriate blueprint)
   - CRUD endpoints
   - Apply decorators

5. **Create Templates:** `app/templates/organization_admin/`
   - List view
   - Create form
   - Edit form

6. **Update Navigation:** `app/templates/base.html`
   - Add menu item

7. **Test:**
   - Create entity
   - Edit entity
   - Delete entity (check cascade)
   - Check permissions

### Adding a New Permission

1. **Update Model:** `app/models/organization.py`
   ```python
   can_my_permission = db.Column(db.Boolean, default=False)
   ```

2. **Create Migration:**
   ```bash
   flask db revision -m "add can_my_permission"
   flask db upgrade
   ```

3. **Update Forms:** `app/forms/user_forms.py`
   - Add checkbox field

4. **Update Templates:** User create/edit forms
   - Add permission checkbox

5. **Apply Decorator:** `app/decorators.py`
   - Create or use existing decorator

6. **Protect Routes:**
   ```python
   @bp.route('/my-protected-route')
   @requires_permission('can_my_permission')
   def my_route():
       pass
   ```

### Adding SSO Provider

1. **Update Model:** `app/models/sso_config.py`
   - Add provider type to choices

2. **Update Form:** `app/forms/sso_forms.py`
   - Add to provider_type SelectField

3. **Update Service:** `app/services/sso_service.py`
   - Add provider-specific logic if needed

4. **Update Template:** `app/templates/super_admin/sso_config.html`
   - Add provider documentation

5. **Test OAuth Flow:**
   - Configure in IdP
   - Test login
   - Verify JIT provisioning

### Backup and Restore

CISK Navigator provides two distinct backup/restore systems with different purposes:

#### 1. **YAML Export/Import** - Structure Only (Templates)

**Purpose:** Share organization structure as templates without data

**Format:** YAML

**Includes:**
- Value types (definitions only)
- Organization structure (spaces, challenges, initiatives, systems, KPIs)
- KPI configurations (colors, targets, display settings)

**Does NOT include:**
- ❌ Contributions (KPI values)
- ❌ Governance bodies
- ❌ Comments
- ❌ User data

**Use Cases:**
- Create organization templates
- Share structure between organizations
- Quick structure duplication without data

**How to Use:**
- **Export:** Organization Admin → YAML Import → Export Structure
- **Import:** Organization Admin → YAML Import → Upload .yaml file
- **Note:** Import CLEARS existing data before importing structure

**Files:**
- `app/services/yaml_export_service.py` - Structure export
- `app/services/yaml_import_service.py` - Structure import
- `app/routes/organization_admin.py` - YAML import/export routes
- `app/templates/organization_admin/yaml_import.html` - UI

#### 2. **Full Backup/Restore** - Complete Data (Disaster Recovery)

**Purpose:** Complete organization backup for disaster recovery

**Format:** JSON

**Includes:**
- ✅ Complete organization structure
- ✅ **ALL KPI contributions (actual values!)**
- ✅ Governance bodies (with mapping during restore)
- ✅ KPI configurations & targets
- ✅ Value type configurations

**Does NOT include:**
- ❌ User memberships
- ❌ Comments
- ❌ Snapshots
- ❌ Audit logs

**Use Cases:**
- Disaster recovery
- Production → staging data sync
- Organization migration
- Pre-migration safety backups

**How to Use:**

**Create Backup:**
1. Go to Global Admin → Backup & Restore (Super Admin only)
2. Select organization
3. Click "Download Backup" (JSON format)
4. Optional: Use "Compressed" for large organizations

**Restore Backup:**
1. Go to Global Admin → Backup & Restore
2. Select target organization (⚠️ ALL DATA WILL BE DELETED)
3. Upload JSON backup file
4. **Governance Body Mapping:** Choose action for each governance body:
   - Create new governance body
   - Map to existing governance body (if names differ)
   - Auto-selected if exact name match exists
5. Confirm restore (⚠️ irreversible)

**Files:**
- `app/services/full_backup_service.py` - JSON export with all data
- `app/services/full_restore_service.py` - JSON restore with GB mapping
- `app/routes/global_admin.py` - Backup/restore routes
- `app/templates/global_admin/backup_restore.html` - Main UI
- `app/templates/global_admin/full_backup_governance_mapping.html` - GB mapping UI

**Governance Body Mapping:**
During restore, governance bodies require user mapping because:
- Target org may already have governance bodies with different names
- Prevents automatic creation of duplicates
- Allows flexibility in mapping backup GBs to existing ones

Example mapping scenarios:
```
Backup has: "Board of Directors"
Target has: "BOD"
→ User maps "Board of Directors" to existing "BOD"

Backup has: "Executive Committee"
Target has: (none)
→ User chooses "Create new"
```

**Automated Backups (CLI):**
```bash
# Backup single organization
python scripts/backup_org.py --org-id 1 --compress

# Backup all organizations
python scripts/backup_all_orgs.py --compress

# Schedule with cron
0 2 * * * /path/to/venv/bin/python /path/to/scripts/backup_all_orgs.py --compress
```

#### Decision Matrix: Which Backup Method to Use?

| Scenario | Use YAML | Use JSON Full Backup |
|----------|----------|----------------------|
| Share org template | ✅ | ❌ |
| Create empty org with structure | ✅ | ❌ |
| Backup before major changes | ❌ | ✅ |
| Disaster recovery | ❌ | ✅ |
| Prod → Staging sync | ❌ | ✅ |
| Migrate org to new instance | ❌ | ✅ |
| Preserve KPI values | ❌ | ✅ |
| Quick structure copy | ✅ | ❌ |

---

## Database Migrations

### Migration Workflow

```bash
# 1. Modify model
# Edit app/models/*.py

# 2. Generate migration
flask db revision -m "descriptive message"

# 3. Edit migration file
# migrations/versions/xxx_descriptive_message.py
# Add both upgrade() and downgrade() functions

# 4. Test migration
flask db upgrade  # Apply
flask db downgrade  # Rollback
flask db upgrade  # Re-apply

# 5. Verify schema
psql -d cisknavigator -c "\d table_name"

# 6. Commit BOTH files
git add app/models/*.py migrations/versions/*.py
git commit -m "Add feature X"
```

### Common Migration Patterns

**Add Column (Nullable):**
```python
def upgrade():
    op.add_column('table_name', sa.Column('new_column', sa.String(255), nullable=True))

def downgrade():
    op.drop_column('table_name', 'new_column')
```

**Add Column (NOT NULL with Default):**
```python
def upgrade():
    op.add_column('table_name',
        sa.Column('new_column', sa.Boolean(), nullable=False, server_default='false'))

def downgrade():
    op.drop_column('table_name', 'new_column')
```

**Add Foreign Key:**
```python
def upgrade():
    op.add_column('child_table', sa.Column('parent_id', sa.Integer(), nullable=True))
    op.create_foreign_key('fk_child_parent', 'child_table', 'parent_table', ['parent_id'], ['id'])

def downgrade():
    op.drop_constraint('fk_child_parent', 'child_table', type_='foreignkey')
    op.drop_column('child_table', 'parent_id')
```

**Add Index:**
```python
def upgrade():
    op.create_index('idx_table_column', 'table_name', ['column_name'])

def downgrade():
    op.drop_index('idx_table_column', 'table_name')
```

---

## Version History

- **v1.15.2** (2026-03-10) - SSO encryption, JWT validation, pending users workflow
- **v1.15.1** - Private/Public spaces, smart column filtering
- **v1.15.0** - Snapshot privacy, batch system
- **v1.14.10** - Bug fixes
- **v1.14.9** - UI modernization

---

## Additional Documentation

See also:
- `sso-complete-implementation.md` - SSO setup guide
- `sso-fixes.md` - SSO troubleshooting
- `comment-permissions.md` - Comment system
- `deployment.md` - Production deployment
- `MEMORY.md` - Project memory (auto-updated)

---

**End of Architecture Documentation**
