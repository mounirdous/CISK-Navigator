# CISK Navigator - Data Dictionary

**Version:** v1.15.2
**Last Updated:** 2026-03-10
**Purpose:** Complete reference for all database tables and columns

---

## Table of Contents

1. [Core Entity Tables](#core-entity-tables)
2. [Relationship Tables](#relationship-tables)
3. [Authentication Tables](#authentication-tables)
4. [System Tables](#system-tables)
5. [Column Type Reference](#column-type-reference)
6. [Index Reference](#index-reference)

---

## Core Entity Tables

### `organizations`

Multi-tenant container for all organizational data.

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| `id` | INTEGER | NO | PK | Primary key |
| `name` | VARCHAR(255) | NO | - | Organization name |
| `is_active` | BOOLEAN | NO | true | Soft delete flag |
| `created_at` | TIMESTAMP | NO | now() | Creation timestamp |
| `updated_at` | TIMESTAMP | YES | now() | Last update timestamp |

**Indexes:**
- PRIMARY KEY on `id`
- INDEX on `is_active`

**Relationships:**
- 1:N with `spaces`, `challenges`, `initiatives`, `systems`, `kpis`, `value_types`, `governance_bodies`
- M:N with `users` via `user_organization_memberships`

---

### `spaces`

Strategic groupings or domains within an organization.

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| `id` | INTEGER | NO | PK | Primary key |
| `organization_id` | INTEGER | NO | FK | Parent organization |
| `name` | VARCHAR(255) | NO | - | Space name |
| `description` | TEXT | YES | NULL | Optional description |
| `is_private` | BOOLEAN | NO | false | Privacy flag (v1.15.1+) |
| `display_order` | INTEGER | NO | 0 | Sort order in UI |
| `created_at` | TIMESTAMP | NO | now() | Creation timestamp |
| `updated_at` | TIMESTAMP | YES | now() | Last update timestamp |

**Indexes:**
- PRIMARY KEY on `id`
- FOREIGN KEY `organization_id` → `organizations(id)`
- INDEX on `organization_id, is_private`

**Relationships:**
- N:1 with `organizations`
- 1:N with `challenges`

---

### `challenges`

Problem statements or strategic objectives within a space.

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| `id` | INTEGER | NO | PK | Primary key |
| `organization_id` | INTEGER | NO | FK | Parent organization |
| `space_id` | INTEGER | NO | FK | Parent space |
| `name` | VARCHAR(255) | NO | - | Challenge name |
| `description` | TEXT | YES | NULL | Challenge description |
| `display_order` | INTEGER | NO | 0 | Sort order in UI |
| `created_at` | TIMESTAMP | NO | now() | Creation timestamp |
| `updated_at` | TIMESTAMP | YES | now() | Last update timestamp |

**Indexes:**
- PRIMARY KEY on `id`
- FOREIGN KEY `organization_id` → `organizations(id)`
- FOREIGN KEY `space_id` → `spaces(id)`
- INDEX on `organization_id, space_id`

**Relationships:**
- N:1 with `spaces`
- M:N with `initiatives` via `challenge_initiative_links`

---

### `initiatives`

Solutions or action plans addressing challenges.

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| `id` | INTEGER | NO | PK | Primary key |
| `organization_id` | INTEGER | NO | FK | Parent organization |
| `name` | VARCHAR(255) | NO | - | Initiative name |
| `description` | TEXT | YES | NULL | Initiative description |
| `display_order` | INTEGER | NO | 0 | Sort order in UI |
| `created_at` | TIMESTAMP | NO | now() | Creation timestamp |
| `updated_at` | TIMESTAMP | YES | now() | Last update timestamp |

**Indexes:**
- PRIMARY KEY on `id`
- FOREIGN KEY `organization_id` → `organizations(id)`
- INDEX on `organization_id`

**Relationships:**
- M:N with `challenges` via `challenge_initiative_links`
- M:N with `systems` via `initiative_system_links`

---

### `systems`

Implementation components or technical systems.

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| `id` | INTEGER | NO | PK | Primary key |
| `organization_id` | INTEGER | NO | FK | Parent organization |
| `name` | VARCHAR(255) | NO | - | System name |
| `description` | TEXT | YES | NULL | System description |
| `display_order` | INTEGER | NO | 0 | Sort order in UI |
| `created_at` | TIMESTAMP | NO | now() | Creation timestamp |
| `updated_at` | TIMESTAMP | YES | now() | Last update timestamp |

**Indexes:**
- PRIMARY KEY on `id`
- FOREIGN KEY `organization_id` → `organizations(id)`
- INDEX on `organization_id`

**Relationships:**
- M:N with `initiatives` via `initiative_system_links`
- 1:N with `kpis`

---

### `kpis`

Key Performance Indicators - measurable metrics.

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| `id` | INTEGER | NO | PK | Primary key |
| `organization_id` | INTEGER | NO | FK | Parent organization |
| `system_id` | INTEGER | NO | FK | Parent system |
| `name` | VARCHAR(255) | NO | - | KPI name |
| `description` | TEXT | YES | NULL | KPI description |
| `display_order` | INTEGER | NO | 0 | Sort order in UI |
| `is_archived` | BOOLEAN | NO | false | Soft delete flag |
| `created_at` | TIMESTAMP | NO | now() | Creation timestamp |
| `updated_at` | TIMESTAMP | YES | now() | Last update timestamp |

**Indexes:**
- PRIMARY KEY on `id`
- FOREIGN KEY `organization_id` → `organizations(id)`
- FOREIGN KEY `system_id` → `systems(id)`
- INDEX on `organization_id, is_archived`
- INDEX on `system_id`

**Relationships:**
- N:1 with `systems`
- M:N with `value_types` via `kpi_value_type_configs`
- M:N with `governance_bodies` via `kpi_governance_body_links`
- 1:N with `contributions`
- 1:N with `cell_comments`
- 1:N with `kpi_snapshots`

---

### `value_types`

Dimensions of value measurement (e.g., Revenue, Time Saved).

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| `id` | INTEGER | NO | PK | Primary key |
| `organization_id` | INTEGER | NO | FK | Parent organization |
| `name` | VARCHAR(255) | NO | - | Value type name |
| `unit` | VARCHAR(50) | YES | NULL | Measurement unit (e.g., "$", "hours") |
| `description` | TEXT | YES | NULL | Value type description |
| `display_order` | INTEGER | NO | 0 | Column order in grid |
| `created_at` | TIMESTAMP | NO | now() | Creation timestamp |
| `updated_at` | TIMESTAMP | YES | now() | Last update timestamp |

**Indexes:**
- PRIMARY KEY on `id`
- FOREIGN KEY `organization_id` → `organizations(id)`
- INDEX on `organization_id`

**Relationships:**
- M:N with `kpis` via `kpi_value_type_configs`
- 1:N with `contributions`

---

### `contributions`

Actual value measurements (the "cells" in the KPI grid).

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| `id` | INTEGER | NO | PK | Primary key |
| `kpi_id` | INTEGER | NO | FK | Parent KPI |
| `value_type_id` | INTEGER | NO | FK | Value type dimension |
| `value` | NUMERIC(15,2) | YES | NULL | Measured value |
| `note` | TEXT | YES | NULL | Optional explanation |
| `created_at` | TIMESTAMP | NO | now() | Creation timestamp |
| `updated_at` | TIMESTAMP | YES | now() | Last update timestamp |
| `updated_by` | INTEGER | YES | FK | Last editor user ID |

**Indexes:**
- PRIMARY KEY on `id`
- FOREIGN KEY `kpi_id` → `kpis(id)` ON DELETE CASCADE
- FOREIGN KEY `value_type_id` → `value_types(id)` ON DELETE CASCADE
- FOREIGN KEY `updated_by` → `users(id)`
- UNIQUE constraint on `(kpi_id, value_type_id)` (one value per cell)
- INDEX on `kpi_id`
- INDEX on `value_type_id`

**Relationships:**
- N:1 with `kpis`
- N:1 with `value_types`
- N:1 with `users` (updated_by)

---

### `governance_bodies`

Committees, boards, or teams responsible for KPIs.

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| `id` | INTEGER | NO | PK | Primary key |
| `organization_id` | INTEGER | NO | FK | Parent organization |
| `name` | VARCHAR(255) | NO | - | Body name |
| `description` | TEXT | YES | NULL | Body description |
| `created_at` | TIMESTAMP | NO | now() | Creation timestamp |
| `updated_at` | TIMESTAMP | YES | now() | Last update timestamp |

**Indexes:**
- PRIMARY KEY on `id`
- FOREIGN KEY `organization_id` → `organizations(id)`
- INDEX on `organization_id`

**Relationships:**
- M:N with `kpis` via `kpi_governance_body_links`

---

### `rollup_rules`

Aggregation formulas for summarizing contributions.

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| `id` | INTEGER | NO | PK | Primary key |
| `organization_id` | INTEGER | NO | FK | Parent organization |
| `name` | VARCHAR(255) | NO | - | Rule name |
| `description` | TEXT | YES | NULL | Rule description |
| `aggregation_type` | VARCHAR(50) | NO | - | 'sum', 'avg', 'count', etc. |
| `filters` | JSONB | YES | NULL | Filter criteria |
| `created_at` | TIMESTAMP | NO | now() | Creation timestamp |
| `updated_at` | TIMESTAMP | YES | now() | Last update timestamp |

**Indexes:**
- PRIMARY KEY on `id`
- FOREIGN KEY `organization_id` → `organizations(id)`
- INDEX on `organization_id`

**Relationships:**
- 1:N with `rollup_snapshots`

---

### `kpi_snapshots`

Point-in-time captures of KPI state.

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| `id` | INTEGER | NO | PK | Primary key |
| `organization_id` | INTEGER | NO | FK | Parent organization |
| `kpi_id` | INTEGER | NO | FK | Captured KPI |
| `batch_id` | VARCHAR(50) | NO | - | Groups snapshots taken together |
| `snapshot_name` | VARCHAR(255) | NO | - | User-defined label |
| `snapshot_date` | TIMESTAMP | NO | now() | When captured |
| `data` | JSONB | NO | {} | Frozen contribution values |
| `is_public` | BOOLEAN | NO | false | Privacy flag (v1.15.0+) |
| `owner_user_id` | INTEGER | YES | FK | Creator (v1.15.0+) |
| `created_at` | TIMESTAMP | NO | now() | Creation timestamp |

**Indexes:**
- PRIMARY KEY on `id`
- FOREIGN KEY `organization_id` → `organizations(id)`
- FOREIGN KEY `kpi_id` → `kpis(id)`
- FOREIGN KEY `owner_user_id` → `users(id)`
- INDEX on `batch_id`
- INDEX on `organization_id, is_public`

**Relationships:**
- N:1 with `kpis`
- N:1 with `organizations`
- N:1 with `users` (owner)

---

### `rollup_snapshots`

Aggregated snapshot results from rollup rules.

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| `id` | INTEGER | NO | PK | Primary key |
| `organization_id` | INTEGER | NO | FK | Parent organization |
| `rollup_rule_id` | INTEGER | NO | FK | Source rule |
| `batch_id` | VARCHAR(50) | NO | - | Matches kpi_snapshots batch |
| `snapshot_name` | VARCHAR(255) | NO | - | Matches kpi_snapshots name |
| `snapshot_date` | TIMESTAMP | NO | now() | When calculated |
| `data` | JSONB | NO | {} | Aggregated results |
| `is_public` | BOOLEAN | NO | false | Privacy flag (v1.15.0+) |
| `owner_user_id` | INTEGER | YES | FK | Creator (v1.15.0+) |
| `created_at` | TIMESTAMP | NO | now() | Creation timestamp |

**Indexes:**
- PRIMARY KEY on `id`
- FOREIGN KEY `organization_id` → `organizations(id)`
- FOREIGN KEY `rollup_rule_id` → `rollup_rules(id)`
- FOREIGN KEY `owner_user_id` → `users(id)` ON DELETE SET NULL
- FOREIGN KEY `value_type_id` → `value_types(id)` ON DELETE CASCADE
- INDEX on `batch_id`
- INDEX on `organization_id, is_public`

---

### `cell_comments`

Discussion threads on KPI cells.

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| `id` | INTEGER | NO | PK | Primary key |
| `kpi_id` | INTEGER | NO | FK | KPI being discussed |
| `value_type_id` | INTEGER | NO | FK | Value type column |
| `user_id` | INTEGER | NO | FK | Comment author |
| `comment` | TEXT | NO | - | Comment text |
| `parent_id` | INTEGER | YES | FK | Parent comment for threading |
| `created_at` | TIMESTAMP | NO | now() | Creation timestamp |
| `updated_at` | TIMESTAMP | YES | now() | Last edit timestamp |

**Indexes:**
- PRIMARY KEY on `id`
- FOREIGN KEY `kpi_id` → `kpis(id)` ON DELETE CASCADE
- FOREIGN KEY `value_type_id` → `value_types(id)`
- FOREIGN KEY `user_id` → `users(id)`
- FOREIGN KEY `parent_id` → `cell_comments(id)`
- INDEX on `kpi_id, value_type_id`
- INDEX on `user_id`

**Relationships:**
- N:1 with `kpis`
- N:1 with `value_types`
- N:1 with `users`
- Self-referencing for threading

---

### `mention_notifications`

User mention tracking in comments.

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| `id` | INTEGER | NO | PK | Primary key |
| `comment_id` | INTEGER | NO | FK | Source comment |
| `mentioned_user_id` | INTEGER | NO | FK | Mentioned user |
| `is_read` | BOOLEAN | NO | false | Read status |
| `created_at` | TIMESTAMP | NO | now() | Creation timestamp |

**Indexes:**
- PRIMARY KEY on `id`
- FOREIGN KEY `comment_id` → `cell_comments(id)` ON DELETE CASCADE
- FOREIGN KEY `mentioned_user_id` → `users(id)`
- INDEX on `mentioned_user_id, is_read`

---

## Relationship Tables

### `challenge_initiative_links`

Many-to-many relationship between challenges and initiatives.

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| `id` | INTEGER | NO | PK | Primary key |
| `challenge_id` | INTEGER | NO | FK | Challenge |
| `initiative_id` | INTEGER | NO | FK | Initiative |

**Indexes:**
- PRIMARY KEY on `id`
- FOREIGN KEY `challenge_id` → `challenges(id)` ON DELETE CASCADE
- FOREIGN KEY `initiative_id` → `initiatives(id)` ON DELETE CASCADE
- UNIQUE constraint on `(challenge_id, initiative_id)`

---

### `initiative_system_links`

Many-to-many relationship between initiatives and systems.

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| `id` | INTEGER | NO | PK | Primary key |
| `initiative_id` | INTEGER | NO | FK | Initiative |
| `system_id` | INTEGER | NO | FK | System |

**Indexes:**
- PRIMARY KEY on `id`
- FOREIGN KEY `initiative_id` → `initiatives(id)` ON DELETE CASCADE
- FOREIGN KEY `system_id` → `systems(id)` ON DELETE CASCADE
- UNIQUE constraint on `(initiative_id, system_id)`

---

### `kpi_value_type_configs`

Many-to-many configuration between KPIs and value types.

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| `id` | INTEGER | NO | PK | Primary key |
| `kpi_id` | INTEGER | NO | FK | KPI |
| `value_type_id` | INTEGER | NO | FK | Value type |
| `is_enabled` | BOOLEAN | NO | true | Whether to show in grid |

**Indexes:**
- PRIMARY KEY on `id`
- FOREIGN KEY `kpi_id` → `kpis(id)` ON DELETE CASCADE
- FOREIGN KEY `value_type_id` → `value_types(id)` ON DELETE CASCADE
- UNIQUE constraint on `(kpi_id, value_type_id)`

---

### `kpi_governance_body_links`

Many-to-many relationship between KPIs and governance bodies.

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| `id` | INTEGER | NO | PK | Primary key |
| `kpi_id` | INTEGER | NO | FK | KPI |
| `governance_body_id` | INTEGER | NO | FK | Governance body |

**Indexes:**
- PRIMARY KEY on `id`
- FOREIGN KEY `kpi_id` → `kpis(id)` ON DELETE CASCADE
- FOREIGN KEY `governance_body_id` → `governance_bodies(id)` ON DELETE CASCADE
- UNIQUE constraint on `(kpi_id, governance_body_id)`

---

## Authentication Tables

### `users`

User accounts for authentication and authorization.

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| `id` | INTEGER | NO | PK | Primary key |
| `login` | VARCHAR(100) | NO | - | Username (unique) |
| `email` | VARCHAR(255) | YES | NULL | Email address |
| `display_name` | VARCHAR(255) | YES | NULL | Full name |
| `password_hash` | VARCHAR(255) | YES | NULL | Bcrypt hash (NULL for SSO users) |
| `is_active` | BOOLEAN | NO | true | Account status |
| `is_super_admin` | BOOLEAN | NO | false | System-wide admin flag |
| `is_global_admin` | BOOLEAN | NO | false | Multi-org admin flag |
| `must_change_password` | BOOLEAN | NO | false | Force password change |
| `dark_mode` | BOOLEAN | NO | false | UI theme preference |
| `default_organization_id` | INTEGER | YES | FK | Preferred org on login |
| `sso_provider` | VARCHAR(50) | YES | NULL | SSO provider type |
| `sso_subject_id` | VARCHAR(255) | YES | NULL | IdP user identifier |
| `sso_email` | VARCHAR(255) | YES | NULL | Email from SSO |
| `last_sso_login` | TIMESTAMP | YES | NULL | Last SSO login time |
| `created_at` | TIMESTAMP | NO | now() | Creation timestamp |
| `updated_at` | TIMESTAMP | YES | now() | Last update timestamp |

**Indexes:**
- PRIMARY KEY on `id`
- UNIQUE on `login`
- FOREIGN KEY `default_organization_id` → `organizations(id)` ON DELETE SET NULL
- INDEX on `email`
- INDEX on `sso_provider, sso_subject_id`

**Relationships:**
- M:N with `organizations` via `user_organization_memberships`

---

### `user_organization_memberships`

User access and permissions within organizations.

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| `id` | INTEGER | NO | PK | Primary key |
| `user_id` | INTEGER | NO | FK | User |
| `organization_id` | INTEGER | NO | FK | Organization |
| `can_manage_spaces` | BOOLEAN | NO | false | Permission flag |
| `can_manage_challenges` | BOOLEAN | NO | false | Permission flag |
| `can_manage_initiatives` | BOOLEAN | NO | false | Permission flag |
| `can_manage_systems` | BOOLEAN | NO | false | Permission flag |
| `can_manage_kpis` | BOOLEAN | NO | false | Permission flag |
| `can_manage_value_types` | BOOLEAN | NO | false | Permission flag |
| `can_manage_governance_bodies` | BOOLEAN | NO | false | Permission flag |
| `can_view_comments` | BOOLEAN | NO | true | Permission flag |
| `can_add_comments` | BOOLEAN | NO | false | Permission flag |
| `created_at` | TIMESTAMP | NO | now() | Creation timestamp |

**Indexes:**
- PRIMARY KEY on `id`
- FOREIGN KEY `user_id` → `users(id)` ON DELETE CASCADE
- FOREIGN KEY `organization_id` → `organizations(id)` ON DELETE CASCADE
- UNIQUE constraint on `(user_id, organization_id)`

---

### `sso_config`

Instance-wide SSO configuration (singleton table).

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| `id` | INTEGER | NO | PK | Primary key (always 1) |
| `provider_type` | VARCHAR(50) | NO | - | 'google', 'azure', 'okta', 'oidc' |
| `is_enabled` | BOOLEAN | NO | false | Master SSO toggle |
| `client_id` | VARCHAR(255) | YES | NULL | OAuth client ID |
| `client_secret` | TEXT | YES | NULL | **Encrypted** OAuth client secret |
| `discovery_url` | VARCHAR(500) | YES | NULL | OIDC discovery endpoint |
| `authorization_endpoint` | VARCHAR(500) | YES | NULL | OAuth authorize URL |
| `token_endpoint` | VARCHAR(500) | YES | NULL | OAuth token URL |
| `userinfo_endpoint` | VARCHAR(500) | YES | NULL | OIDC userinfo URL |
| `jwks_uri` | VARCHAR(500) | YES | NULL | JWT signing keys URL |
| `auto_provision_users` | BOOLEAN | NO | true | JIT provisioning flag |
| `default_permissions` | JSONB | YES | NULL | Default user permissions |
| `created_at` | TIMESTAMP | NO | now() | Creation timestamp |
| `updated_at` | TIMESTAMP | YES | now() | Last update timestamp |
| `updated_by` | INTEGER | YES | FK | Last editor user ID |

**Indexes:**
- PRIMARY KEY on `id`
- FOREIGN KEY `updated_by` → `users(id)`

**Note:** `client_secret` is encrypted at rest using Fernet symmetric encryption.

---

## System Tables

### `system_settings`

Global system settings (key-value store).

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| `id` | INTEGER | NO | PK | Primary key |
| `category` | VARCHAR(100) | NO | - | Setting category |
| `key` | VARCHAR(255) | NO | - | Setting key (unique) |
| `value` | TEXT | YES | NULL | Setting value |
| `description` | TEXT | YES | NULL | Setting description |
| `created_at` | TIMESTAMP | NO | now() | Creation timestamp |
| `updated_at` | TIMESTAMP | YES | now() | Last update timestamp |
| `updated_by` | INTEGER | YES | FK | Last editor user ID |

**Indexes:**
- PRIMARY KEY on `id`
- UNIQUE on `key`
- FOREIGN KEY `updated_by` → `users(id)`
- INDEX on `category`

**Common Keys:**
- `maintenance_mode` - System read-only flag
- `session_timeout` - Session lifetime (minutes)

---

### `alembic_version`

Database migration version tracking (managed by Alembic).

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| `version_num` | VARCHAR(32) | NO | PK | Current migration revision |

**Note:** Do not modify manually - managed by Flask-Migrate.

---

## Column Type Reference

| Type | PostgreSQL Type | Description |
|------|-----------------|-------------|
| `INTEGER` | `integer` | 4-byte signed integer |
| `VARCHAR(n)` | `character varying(n)` | Variable-length string (max n chars) |
| `TEXT` | `text` | Unlimited length string |
| `BOOLEAN` | `boolean` | True/false |
| `NUMERIC(p,s)` | `numeric(p,s)` | Decimal number (p digits, s after decimal) |
| `TIMESTAMP` | `timestamp without time zone` | Date and time |
| `JSONB` | `jsonb` | Binary JSON (indexable) |

---

## Index Reference

### When to Add Indexes:

1. **Foreign Keys:** Almost always
2. **Unique Constraints:** Automatically indexed
3. **Frequently Filtered Columns:** `WHERE`, `JOIN` conditions
4. **Sort Columns:** `ORDER BY`
5. **Composite Indexes:** Multi-column filters

### Index Types:

```sql
-- B-tree (default)
CREATE INDEX idx_name ON table(column);

-- Multi-column
CREATE INDEX idx_name ON table(col1, col2);

-- Partial index (filtered)
CREATE INDEX idx_name ON table(column) WHERE condition;

-- JSONB index
CREATE INDEX idx_name ON table USING GIN(jsonb_column);
```

### Check Existing Indexes:

```sql
-- All indexes on a table
SELECT indexname, indexdef FROM pg_indexes WHERE tablename = 'kpis';

-- Index usage stats
SELECT schemaname, tablename, indexname, idx_scan
FROM pg_stat_user_indexes
ORDER BY idx_scan ASC;
```

---

## Cascade Delete Reference

### ON DELETE CASCADE:

These relationships automatically delete child records when parent is deleted:

```
organizations (DELETE)
  └─> CASCADE: All child entities

spaces (DELETE)
  └─> CASCADE: challenges

kpis (DELETE)
  ├─> CASCADE: contributions
  ├─> CASCADE: cell_comments
  ├─> CASCADE: kpi_snapshots
  └─> CASCADE: kpi_value_type_configs

value_types (DELETE)
  └─> CASCADE: contributions (CRITICAL!)

challenge_initiative_links (DELETE challenge or initiative)
  └─> CASCADE: link row only

user_organization_memberships (DELETE user or organization)
  └─> CASCADE: membership row
```

---

## JSONB Column Schemas

### `sso_config.default_permissions`

```json
{
  "can_manage_spaces": false,
  "can_manage_challenges": false,
  "can_manage_initiatives": false,
  "can_manage_systems": false,
  "can_manage_kpis": false,
  "can_manage_value_types": false,
  "can_manage_governance_bodies": false,
  "can_view_comments": true,
  "can_add_comments": false
}
```

### `kpi_snapshots.data`

```json
{
  "kpi_id": 123,
  "kpi_name": "Customer Satisfaction",
  "system_name": "CRM",
  "contributions": {
    "1": {  // value_type_id
      "value": 95.5,
      "note": "Q4 results",
      "value_type_name": "Score"
    },
    "2": {
      "value": 1200,
      "note": "Survey responses",
      "value_type_name": "Count"
    }
  }
}
```

### `rollup_snapshots.data`

```json
{
  "rule_name": "Total Revenue",
  "aggregation_type": "sum",
  "results": {
    "1": {  // value_type_id
      "total": 5000000,
      "count": 25,
      "value_type_name": "Revenue"
    }
  }
}
```

### `rollup_rules.filters`

```json
{
  "space_ids": [1, 2, 3],
  "governance_body_ids": [5],
  "include_archived": false
}
```

---

## Query Examples

### Get full hierarchy for a KPI:

```sql
SELECT
    o.name as organization,
    s.name as space,
    c.name as challenge,
    i.name as initiative,
    sys.name as system,
    k.name as kpi
FROM kpis k
JOIN systems sys ON k.system_id = sys.id
JOIN initiative_system_links isl ON sys.id = isl.system_id
JOIN initiatives i ON isl.initiative_id = i.id
JOIN challenge_initiative_links cil ON i.id = cil.initiative_id
JOIN challenges c ON cil.challenge_id = c.id
JOIN spaces s ON c.space_id = s.id
JOIN organizations o ON k.organization_id = o.id
WHERE k.id = <KPI_ID>;
```

### Get all contributions for a KPI:

```sql
SELECT
    vt.name as value_type,
    c.value,
    c.note,
    u.display_name as updated_by,
    c.updated_at
FROM contributions c
JOIN value_types vt ON c.value_type_id = vt.id
LEFT JOIN users u ON c.updated_by = u.id
WHERE c.kpi_id = <KPI_ID>
ORDER BY vt.display_order;
```

---

**End of Data Dictionary**
