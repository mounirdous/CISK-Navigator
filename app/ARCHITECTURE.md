# CISK Navigator - Technical Architecture

**Last Updated**: April 6, 2026
**Version**: 7.15.0

This document provides a comprehensive technical overview of the CISK Navigator application architecture, data models, business logic, and implementation details.

## Table of Contents

1. [Overview](#overview)
2. [Technology Stack](#technology-stack)
3. [Application Structure](#application-structure)
4. [Data Model](#data-model)
5. [Business Logic](#business-logic)
6. [Authentication & Authorization](#authentication--authorization)
7. [Consensus Model](#consensus-model)
8. [Roll-up Aggregation](#roll-up-aggregation)
9. [Color Configuration System](#color-configuration-system)
10. [Excel Export](#excel-export)
11. [YAML Export/Import](#yaml-exportimport)
12. [Full Backup & Restore](#full-backup--restore)
13. [Selective Import](#selective-import)
14. [Organization Cloning](#organization-cloning)
15. [Workspace Labels & Profiles](#workspace-labels--profiles)
16. [Governance Body Sharing](#governance-body-sharing)
17. [Duplicate Detector](#duplicate-detector)
18. [Shared Entities Management](#shared-entities-management)
19. [Entity Branding](#entity-branding)
20. [Drag-and-Drop Value Type Reordering](#drag-and-drop-value-type-reordering)
21. [Deletion Rules](#deletion-rules)
22. [Code Organization](#code-organization)
23. [Database Migrations](#database-migrations)
24. [Production Deployment](#production-deployment)
25. [Testing Strategy](#testing-strategy)

## Overview

CISK Navigator is a Flask application using PostgreSQL as the production database. It follows the application factory pattern and uses Flask Blueprints for modular route organization.

### Design Principles

- **Production-Ready**: PostgreSQL for data persistence across deployments
- **Secure by Default**: CSRF protection, password hashing, session management
- **Migration-Friendly**: Flask-Migrate (Alembic) for schema evolution
- **Well-Tested**: Comprehensive test coverage with pytest
- **Multi-Tenant**: Complete organization isolation

### v7.19–7.21 Recent Changes (April 28, 2026)

1. **Cross-workspace Logo Gallery on Branding Manager** — `/org-admin/branding` cards (organization, space, challenge, initiative, system, kpi) gained a "Choose from Existing" button alongside Upload/Template. New endpoints `GET /org-admin/branding/logo-gallery` (catalog of every accessible logo) and `POST /org-admin/branding/copy-logo` (copy bytes into target slot). Sources span every workspace the user has access to (super/global admins see all): the workspace logo, every `EntityTypeDefault.default_logo`, every per-entity override (Space/Challenge/Initiative/System/KPI). Filterable by workspace + source-kind + free text. KPI sources reached via `InitiativeSystemLink → Initiative` since `KPI` has no direct `organization_id`. New `/api/logo/entity-default/<id>` route serves `EntityTypeDefault.default_logo_data` as raw image bytes.
2. **Excel Export — full rewrite** (`/workspace/export-excel`). Single sheet → five-sheet workbook: **Overview** (workspace counts + RAG distribution), **Tree** (hierarchical with `outlinePr.summaryBelow=False` so the +/- toggle sits on each parent row, RAG-filled KPI cells, autofilter, no hyperlinks in tree text), **KPIs** (flat row per KPI/value-type pair with target / current / Δ% / RAG / direction / target date / tolerance / last update / contributor), **Action Items** (priority + status colour coded), **Settings** (value types, impact levels with colour swatches, pillars, GBs, geography). KPI value cells now store **numbers** (with unit-aware `number_format`) instead of strings — Excel sort/filter works natively. RAG computed from `target_value × target_direction × target_tolerance_pct`.
3. **Standalone HTML snapshot export** (`/workspace/export-html`, new richtext button next to Excel) — generates a single self-contained `.html` file by **invoking the live `workspace.index()` view** to capture the exact Alpine.js page, then post-processing: every `/static/` CSS+JS reference is inlined; CDN libraries (Bootstrap, BS Icons, Alpine, FontAwesome) stay as `https://...` so recipients online get the exact look. A pre-Alpine shim installs a `fetch()` interceptor that serves the `_build_workspace_data()` blob on `/workspace/data` requests and stubs every other backend `/api/*` with `{}` so the page boots without errors. Form submits are blocked. Server-only chrome is hidden in the snapshot **only** (live template untouched): top navbar, ga-subnav, load/save preset bar, edit-mode toggle, snapshot floating controls, inline quick-add modal (`.ws-iadd-*`), comments / mentions, maintenance banners, live-search dropdown. `editMode` is force-reset to `false` at boot so per-row create/edit/delete chrome never appears. **Porter / Strategy / Lenses / SWOT links open in-page modals** populated from data embedded at export time (porters fields, `StrategicPillar` rows, `valueTypes`, per-space SWOT) — zero server round-trips on click. Other relative links resolve to the live deployment via `<base href>`.
4. **Stale-org-id session guard** — global `before_request` hook in `app/__init__.py` clears `session["organization_id"]` (plus `_name`/`_logo`) if the org no longer exists in the DB, preventing cascading FK failures (e.g. `audit_logs` insert) for users whose current workspace was hard-deleted. `AuditService.log_action` also re-validates the session org before attaching it to audit log inserts.
5. **Edit Organization branding** — `/global-admin/organizations/<id>/edit` name-field icon now renders the workspace's actual logo via the standard chain (org logo → `EntityTypeDefault` default logo → default emoji icon → `bi-building` fallback), and renaming the currently-active workspace refreshes `session["organization_name"]` on commit so the navbar brand updates immediately.
6. **`docs/SAMPLE_IMPORT.json` regenerated to v9.0 backup format** — added the `metadata` block (`db_schema_version="1.0"`) without which `FullRestoreService` rejected the file. Added working examples of every top-level section the restore consumes: `organization` (porters / impact method / decision/action tags / value-type categories / strategy toggle), `entity_branding`, `governance_bodies`, `impact_levels`, `strategic_pillars`, `geography` (regions/countries/sites). Existing CIO first-year hierarchy preserved.

### v7.13–7.15 Recent Changes (April 6, 2026)

1. **Responsive Navbar** — Navbar collapses at xl (1200px) breakpoint; search bar uses flexible width; user profile icon always accessible
2. **Full Backup & Restore Improvements** — Organization-level links now included in backup exports; restore is order-independent (auto-creates missing global GBs); action items always restored as workspace-scoped; governance body deduplication during restore; redirect to Organizations page after restore
3. **Selective Import** — New Workspace Admin tool to browse a backup JSON and selectively import data with duplicate detection; starting with workspace-level links, extensible for future entity types
4. **Duplicate Detector** — Super Admin tool scanning 9 entity types for case-insensitive name duplicates within each workspace; impact analysis per record; parent context display; workspace filter
5. **Shared Entities Management** — Super Admin page to view and bulk unshare (set `is_global=false`) governance bodies and action items; entity type filter tabs
6. **Workspace Labels & Profiles** — Action scope setting (`workspace` or `all`) in profiles controls whether global action items from other workspaces appear in the Action Register; label badge colors use hex data attributes for correct toggle rendering; Workspaces menu updates instantly on label toggle
7. **Entity Branding from DB** — Entity mention icons on action items, dashboard, search, and create pages use workspace branding (logo/icon/color) from the Branding Manager instead of hardcoded symbols
8. **Org Delete Cascade Fix** — `passive_deletes=True` on ImpactLevel, StrategicPillar, and OrganizationSSOConfig relationships; bulk delete commits per-org to avoid worker timeouts
9. **Owning Workspace Badge** — Action item view page shows the owning workspace name

### v5.3.1 Previous Changes (March 28, 2026)

1. **Impact Level System** — 3-level configurable impact scale per org (symbol, weight, color); `impact_level` on all entities; true importance computed via Simple Product, Geometric Mean, or Toyota QFD method; editable QFD matrix
2. **Decision Log** — structured decisions in progress updates [{what, who, tag, mentions}]; Decision Register page (`/workspace/decisions`) with search, entity filtering, xmas tree detail levels
3. **Entity Mentions in Decisions** — searchable entity picker; bi-directional links (entity→decisions, decision→entities)
4. **3-Level Xmas Tree** — progressive detail disclosure on Workspace, Action Register, Initiative Review, Map Dashboard, Decision Register (minimal/standard/full)
5. **Strategic Pillars** — editable strategy with icon picker, view page, backup/restore
6. **Value Dimensions** — card view of value types with descriptions
7. **Impact Documentation** — standalone page explaining all 3 compounding methods with formulas, examples, comparison table
8. **Sequential Entity Navigation** — prev/next arrows on all 7 entity edit pages, scoped to siblings
9. **Initiative Review Focus Mode** — sort by impact level with visual separators
10. **Mobile-Friendly Info Windows** — click-based multi-window system replacing hover tooltips; draggable

### v4.2.1 Previous Changes (March 27, 2026)

1. **Unified Presets System** — Single `PresetManager` JS module + `_preset_bar.html` macro for save/load across workspace, action items, search, and pivot charts; `/api/user-presets` API (GET/POST/DELETE); auto-restore with URL-match guard to prevent infinite loops; overwrite prompt on duplicate names
2. **Map KPI Marker Clustering** — Replaced 156+ DOM markers with Mapbox native GPU-accelerated GeoJSON clustering; cluster circles with count badges (indigo/purple/pink by count); click-to-expand or popup KPI list for same-location clusters; continuous `render` event coloring for all countries; `map.loaded()` check to prevent race condition in production
3. **Branding Logos Globally Available** — Context processor now includes `logo` (base64 data URL) alongside `color` and `icon` for all entity types; Action Register CISK Entity view shows custom branding logos (16px constrained) instead of generic text icons
4. **Dashboards Menu Restructured** — Removed Overview and CISK Theory; Executive, Analytics, Snapshot Analysis are beta-only (with BETA badge); removed standalone Beta nav item; Map View available to all
5. **Workspace FABs Fixed** — Snapshot/export floating action buttons moved outside `workspace-v2` container for correct `position: fixed` behavior; visible on all screen sizes (36px on mobile)
6. **Workspace Dirty Flag** — Cleared on fresh server fetch (was persisting across sessions)
7. **Timeline Fit-All** — Always fits all items on initial timeline load; zoom presets only apply on explicit user selection

### v2.20.1 Previous Changes (March 2026)

1. **Action Register — Duplicate Detection** — "Find Duplicates" button scans all visible items using Jaccard title similarity, exact match, prefix match, and combined title+description similarity; groups results with a differences table (status, priority, owner, due date, governance bodies, links — only differing fields shown), smart pre-selection for deletion, and a Show/Hide differences toggle
2. **Global Search — Exact Match** — Checkbox toggle on the search page disables Levenshtein fuzzy matching and restricts results to substring matches only; badge shown in results when active
3. **Backup Format v3.0** — Action items and memos now included in full backup/restore (owner matched by login, governance body links by name, entity mentions resolved by entity name)

### v2.17.7 Previous Changes (March 2026)

1. **Workspace Collapse/Expand Fixed** — Alpine.js reactivity issue in nested `x-for` loops fixed; collapse at any level (space/challenge/initiative/system) now immediately hides all descendants; collapse state preserved across background data reloads
2. **System Edit Link** — Workspace pencil icon on systems navigates to `edit_system` page; `edit_url` added to system data in `get_data` API response
3. **Per-Instance Branding on Edit Pages** — Space, Challenge, Initiative, System, KPI edit pages show per-instance logo first, then entity-type default, then icon
4. **Action Item Governance Bodies** — Many-to-many join table `action_item_governance_body`; multi-select per action in register and Generate Actions modal; GB filter on Action Register page
5. **Generate Actions from Success Criteria** — Lightning button now parses both deliverables and success criteria rows with source badge (Del./Step)
6. **Action Register Modernized** — Gradient header, stat cards, multi-status filter (checkboxes), GB filter pills, stats update dynamically with filters

### v2.16.0 Changes (March 2026)

1. **Generate Actions from Deliverables & Steps** — Initiative form lightning button parses deliverable rows and success criteria rows into action items with smart date parsing, dedup detection, and bulk creation
2. **List Value Type** — New "list" kind for choice-based KPIs (Yes/No, status, categories) with per-option colors and Mode aggregation
3. **Initiative Form Redesign** — Dynamic font sizing, left-aligned content, tight padding, branding icons for system/KPI entries
4. **Backup/Restore Completeness** — Initiative form fields, Porter's Five Forces, and Action Items/Memos now included in full backup/restore (backup format v3.0)
5. **Aggregation Formula Consistency** — `ValueType.get_valid_formulas()` used across all 3 formula-selection surfaces
6. **Test Suite Runner** — Celery + Redis async test execution from Health Dashboard (v2.14.0)
7. **Demo Data Generator** — Three pre-built demo organizations for testing (v2.11.0)

### v2.0 Foundation

1. **Database Migration**: SQLite → PostgreSQL for production persistence
2. **Color System Refactor**: Colors moved from ValueType to KPIValueTypeConfig level
3. **Driver Upgrade**: psycopg2 → psycopg3 (Python 3.13+ compatible)
4. **Deployment**: Render with persistent PostgreSQL
5. **Automatic Migrations**: Database schema updates on deploy
6. **New Aggregation Formulas**: Added median (outlier-resistant) and count (quantity tracking)
7. **New Value Types**: Added level (generic 3-level) and sentiment (emotional states)
8. **Excel Export**: Hierarchical export with row grouping and color coding
9. **YAML Export/Import**: Complete structure backup and restore capability
10. **Organization Cloning**: Create test/training environments from production
11. **Drag-and-Drop Reordering**: Reorder value types to control workspace columns
12. **Data Loss Prevention**: Multiple safety checks to prevent accidental database resets

## Technology Stack

### Core Framework
- **Python 3.11+**: Modern Python with type hints
- **Flask 3.0**: Lightweight WSGI web framework
- **PostgreSQL 16+**: Production relational database
- **psycopg 3.3**: Modern PostgreSQL adapter

### Flask Extensions
- **Flask-SQLAlchemy 3.1**: ORM for database interactions
- **Flask-Migrate 4.0**: Database migration management (Alembic)
- **Flask-Login 0.6**: User session management
- **Flask-WTF 1.2**: Form handling and CSRF protection
- **Werkzeug 3.0**: Password hashing and utilities

### Frontend
- **Bootstrap 5**: Responsive UI framework
- **Bootstrap Icons**: Icon library
- **SortableJS 1.15**: Drag-and-drop library (loaded from CDN)
- **Chart.js 4.4**: Interactive charts (trends, coverage, test history)
- **Vanilla JavaScript**: Tree expansion, form interactions, AJAX polling

### Background Processing
- **Celery**: Async task queue for long-running operations (test runner)
- **Redis**: Message broker for Celery (managed Redis on Render)

### Deployment
- **Gunicorn 21.2**: Production WSGI server
- **Render**: Cloud platform with managed PostgreSQL and Redis

### Testing
- **pytest 7.4**: Testing framework
- **pytest-flask 1.3**: Flask-specific test fixtures
- **pytest-cov**: Code coverage reporting

## Application Structure

### Directory Layout

```
CISK-Navigator/
├── app/
│   ├── __init__.py              # Application factory
│   ├── config.py                # Configuration (dev/prod)
│   ├── extensions.py            # Flask extension instances
│   │
│   ├── models/                  # SQLAlchemy models
│   │   ├── __init__.py
│   │   ├── user.py             # User and authentication
│   │   ├── organization.py     # Organization and memberships
│   │   ├── space.py            # Space model
│   │   ├── challenge.py        # Challenge model
│   │   ├── initiative.py       # Initiative and ChallengeInitiativeLink
│   │   ├── system.py           # System and InitiativeSystemLink
│   │   ├── kpi.py              # KPI model
│   │   ├── value_type.py       # ValueType and KPIValueTypeConfig
│   │   ├── contribution.py     # Contribution model
│   │   └── rollup_rule.py      # RollupRule model
│   │
│   ├── forms/                   # WTForms validation
│   │   ├── auth_forms.py       # Login, password change
│   │   ├── user_forms.py       # User management
│   │   ├── organization_forms.py
│   │   ├── space_forms.py
│   │   ├── challenge_forms.py
│   │   ├── initiative_forms.py
│   │   ├── system_forms.py
│   │   ├── kpi_forms.py
│   │   ├── value_type_forms.py
│   │   └── contribution_forms.py
│   │
│   ├── routes/                  # Flask Blueprints
│   │   ├── auth.py             # Authentication
│   │   ├── global_admin.py     # Global administration
│   │   ├── organization_admin.py # Organization administration
│   │   └── workspace.py        # Main workspace
│   │
│   ├── services/                # Business logic services
│   │   ├── consensus_service.py         # Consensus calculation (supports list/numeric/qualitative)
│   │   ├── aggregation_service.py       # Roll-up aggregation (sum/min/max/avg/median/count/mode)
│   │   ├── deletion_impact_service.py   # Deletion impact analysis
│   │   ├── value_type_usage_service.py  # Value type usage checking
│   │   ├── excel_export_service.py      # Excel export with grouping
│   │   ├── yaml_export_service.py       # YAML structure export
│   │   ├── yaml_import_service.py       # YAML structure import
│   │   ├── organization_clone_service.py # Organization cloning
│   │   ├── full_backup_service.py       # Full JSON backup (includes initiative form fields, Porter's)
│   │   ├── full_restore_service.py      # Full JSON restore
│   │   ├── action_items_service.py      # Action items quality dashboard
│   │   ├── action_item_service.py       # Action item CRUD helpers
│   │   └── test_runner_service.py       # Async pytest execution via Celery
│   │
│   ├── templates/               # Jinja2 templates
│   │   ├── base.html           # Base layout
│   │   ├── auth/               # Authentication pages
│   │   ├── global_admin/       # Global admin pages
│   │   ├── organization_admin/ # Org admin pages
│   │   └── workspace/          # Workspace pages
│   │
│   └── static/                  # Static assets
│       ├── css/style.css       # Custom styles
│       └── js/                 # JavaScript files
│
├── migrations/                  # Alembic migrations
│   ├── versions/               # Migration scripts
│   ├── alembic.ini
│   └── env.py
│
├── tests/                       # Test suite
│   ├── conftest.py
│   ├── test_auth.py
│   ├── test_consensus.py
│   ├── test_aggregation.py
│   └── test_deletion.py
│
├── run.py                       # Application entry point
├── requirements.txt             # Python dependencies
├── .env.example                 # Environment variables template
├── Procfile                     # Render start command
└── render.yaml                  # Render configuration
```

### Application Factory Pattern

```python
# app/__init__.py
def create_app(config_name=None):
    app = Flask(__name__)
    app.config.from_object(config[config_name])

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)

    # Register blueprints
    app.register_blueprint(auth.bp)
    app.register_blueprint(global_admin.bp)
    app.register_blueprint(organization_admin.bp)
    app.register_blueprint(workspace.bp)

    # Register Jinja2 filters
    @app.template_filter('format_value')
    def format_value_filter(value, value_type):
        # Value formatting logic
        pass

    @app.template_filter('default_value_color')
    def default_value_color_filter(value):
        # Default color logic for rollups
        pass

    # Bootstrap admin on first run
    with app.app_context():
        db.create_all()
        _bootstrap_admin()

    return app
```

## Data Model

### Core Principles

1. **Immutable IDs**: Every entity has an immutable technical ID
2. **Many-to-Many Relationships**: Initiatives and Systems are reusable
3. **Context-Specific Data**: KPIs belong to Initiative-System contexts
4. **Organization Isolation**: All business data scoped to organizations
5. **Color Configuration**: Sign-based colors configured per KPI (not per value type)

### Entity Relationship Diagram

```
Organization (1) ──────┬─────── (N) Space
                       ├─────── (N) Challenge
                       ├─────── (N) Initiative
                       ├─────── (N) System
                       ├─────── (N) ValueType
                       └─────── (N) UserOrganizationMembership ──── (1) User

Space (1) ────────── (N) Challenge

Challenge (1) ────── (N) ChallengeInitiativeLink ────── (1) Initiative
                                │
                                └── (N) RollupRule

Initiative (1) ───── (N) InitiativeSystemLink ────────── (1) System
                                │
                                ├── (N) KPI
                                └── (N) RollupRule

KPI (1) ──────────── (N) KPIValueTypeConfig ────────── (1) ValueType
                                │                             │
                                │                             ├── color_positive
                                │                             ├── color_zero
                                │                             └── color_negative
                                │
                                └── (N) Contribution

Challenge (1) ────── (N) RollupRule (for Challenge → Space)
```

### Key Models

#### User
```python
class User(db.Model):
    id: int                    # Primary key
    login: str                 # Unique login
    email: str                 # Optional email
    display_name: str
    password_hash: str         # Werkzeug hashed
    is_active: bool
    is_global_admin: bool
    must_change_password: bool
```

#### Organization
```python
class Organization(db.Model):
    id: int
    name: str                  # Unique
    description: str
    is_active: bool
```

**Cascade behavior**: Deleting an organization deletes all its data.

#### Space
```python
class Space(db.Model):
    id: int
    organization_id: int       # FK to Organization
    name: str
    description: str
    space_label: str           # Optional: "Season", "Site", etc.
    display_order: int

    # Methods
    def get_rollup_value(value_type_id)
    def get_color_config(value_type_id)  # v2.0: Find representative KPI colors
```

Spaces are flexible groupings (seasons, sites, customers, etc.).

#### Challenge
```python
class Challenge(db.Model):
    id: int
    organization_id: int
    space_id: int              # FK to Space
    name: str
    description: str
    display_order: int

    # Methods
    def get_rollup_value(value_type_id)
    def get_color_config(value_type_id)  # v2.0: Inherit from descendant KPIs
```

#### Initiative
```python
class Initiative(db.Model):
    id: int
    organization_id: int
    name: str
    description: str

    # Methods
    def get_rollup_value(value_type_id)
    def get_color_config(value_type_id)  # v2.0: Inherit from descendant KPIs
```

**Reusable**: Initiatives can address multiple challenges via `ChallengeInitiativeLink`.

#### System
```python
class System(db.Model):
    id: int
    organization_id: int
    name: str
    description: str
```

**Reusable**: Systems can support multiple initiatives via `InitiativeSystemLink`.

#### InitiativeSystemLink
```python
class InitiativeSystemLink(db.Model):
    id: int
    initiative_id: int         # FK to Initiative
    system_id: int             # FK to System
    display_order: int

    # Unique constraint: (initiative_id, system_id)

    # Methods
    def get_rollup_value(value_type_id)
    def get_color_config(value_type_id)  # v2.0: Find first KPI with this value type
```

**Critical**: KPIs belong here, not to the master System. This allows context-specific KPIs.

#### KPI
```python
class KPI(db.Model):
    id: int
    initiative_system_link_id: int  # FK to InitiativeSystemLink
    name: str
    description: str
    display_order: int
```

KPIs are context-specific to an initiative-system pair.

#### ValueType
```python
class ValueType(db.Model):
    id: int
    organization_id: int
    name: str
    kind: str                  # 'numeric', 'risk', 'positive_impact', 'negative_impact', 'level', 'sentiment'
    numeric_format: str        # 'integer' or 'decimal' (for numeric types)
    decimal_places: int        # For decimal format
    unit_label: str            # '€', 'tCO2e', 'licenses', etc.
    default_aggregation_formula: str  # 'sum', 'min', 'max', 'avg', 'median', 'count'
    display_order: int         # Order in workspace columns (drag-to-reorder)
    is_active: bool
```

**Value Type Kinds:**
- `numeric`: Numerical values (cost, emissions, time, counts)
- `risk`: Risk levels (!, !!, !!!) - 3 levels
- `positive_impact`: Positive outcomes (★, ★★, ★★★) - 3 levels
- `negative_impact`: Negative outcomes (▼, ▼▼, ▼▼▼) - 3 levels
- `level`: Generic 3-level (●, ●●, ●●●) - for morale, readiness, maturity, quality
- `sentiment`: Emotional states (☹️, 😐, 😊) - for satisfaction, happiness, sentiment

**v2.0 Change**: Color fields removed from ValueType. Colors now configured per KPI.

**Display Order**: Value types can be reordered via drag-and-drop in the admin interface, controlling the column order in the workspace.

#### KPIValueTypeConfig
```python
class KPIValueTypeConfig(db.Model):
    id: int
    kpi_id: int                # FK to KPI
    value_type_id: int         # FK to ValueType
    display_order: int

    # v2.0: Sign-based colors configured here (per KPI-value type pair)
    color_negative: str        # Color for negative values
    color_zero: str            # Color for zero/null values
    color_positive: str        # Color for positive values

    # Methods
    def get_consensus_value()
    def get_value_color(value)  # v2.0: Returns appropriate color based on value sign
```

**v2.0 Major Change**: Colors moved from ValueType to here. This allows the same value type (e.g., "Cost") to have different color meanings in different KPIs:
- KPI 1: Lower cost is better → negative = green, positive = red
- KPI 2: Revenue → positive = green, negative = red

#### Contribution
```python
class Contribution(db.Model):
    id: int
    kpi_value_type_config_id: int  # FK to KPIValueTypeConfig
    contributor_name: str          # Free text, no user account required
    numeric_value: Decimal         # For numeric types
    qualitative_level: int         # 1, 2, or 3 for qualitative types
    comment: str
    created_at: datetime
    updated_at: datetime
```

One contribution per contributor per cell. Updates replace previous entry.

#### RollupRule
```python
class RollupRule(db.Model):
    id: int
    source_type: str           # 'initiative_system', 'challenge_initiative', 'challenge'
    source_id: int             # ID of the link or challenge
    value_type_id: int         # FK to ValueType
    rollup_enabled: bool       # Default: False
    formula_override: str      # 'default', 'sum', 'min', 'max', 'avg'
```

Roll-up rules are context-specific and attached to:
- System → Initiative: `InitiativeSystemLink`
- Initiative → Challenge: `ChallengeInitiativeLink`
- Challenge → Space: `Challenge`

## Business Logic

### Consensus Service

Located in `app/services/consensus_service.py`.

#### Consensus Statuses

1. **no_data**: No contributions exist
2. **pending_confirmation**: Only one contribution
3. **strong_consensus**: 2+ contributions, all same value (**eligible for roll-up**)
4. **weak_consensus**: 2+ contributions, majority exists but not unanimous
5. **no_consensus**: 2+ contributions, no reliable agreement

#### Roll-up Eligibility

**Only Strong Consensus values participate in upward roll-ups.**

```python
def get_cell_value(kpi_value_type_config):
    contributions = kpi_value_type_config.contributions

    if not contributions:
        return {'status': 'no_data', 'is_rollup_eligible': False}

    if len(contributions) == 1:
        return {
            'status': 'pending_confirmation',
            'value': contributions[0].get_value(),
            'is_rollup_eligible': False
        }

    # Count occurrences
    value_counts = Counter(c.get_value() for c in contributions)

    if len(value_counts) == 1:  # All same
        return {
            'status': 'strong_consensus',
            'value': list(value_counts.keys())[0],
            'is_rollup_eligible': True  # ✓ Eligible
        }

    # Check for majority
    total = len(contributions)
    max_count = max(value_counts.values())
    if max_count > total / 2:
        majority_value = [v for v, c in value_counts.items() if c == max_count][0]
        return {
            'status': 'weak_consensus',
            'value': majority_value,
            'is_rollup_eligible': False  # ✗ Not eligible
        }

    return {'status': 'no_consensus', 'is_rollup_eligible': False}
```

### Aggregation Service

Located in `app/services/aggregation_service.py`.

#### Roll-up Flow

```
KPI (leaf data, contributors)
    ↓ (Value Type default formula)
System (first aggregation level)
    ↓ (Configurable via InitiativeSystemLink RollupRule)
Initiative
    ↓ (Configurable via ChallengeInitiativeLink RollupRule)
Challenge
    ↓ (Configurable via Challenge RollupRule)
Space
```

#### Aggregation Formulas

- **sum**: Add all values together (e.g., total cost across systems)
- **min**: Minimum value (e.g., best-case scenario, shortest time)
- **max**: Maximum value (e.g., worst-case scenario, highest risk)
- **avg**: Average value (e.g., typical performance, mean sentiment)
- **median**: Middle value when sorted - resistant to outliers (e.g., typical delivery time ignoring extremes)
- **count**: Number of values - useful for "how many" questions (e.g., number of systems, initiatives completed)

**Median Implementation:**
```python
from statistics import median

elif formula == 'median':
    # Median: middle value when sorted, ignores outliers
    return median(values)
```

**Count Implementation:**
```python
elif formula == 'count':
    # Count: number of values (useful for "how many" questions)
    return len(values)
```

**Use Cases:**
- **Median**: Better than average when data has outliers (e.g., delivery times where most are 5 days but one took 100 days)
- **Count**: Track quantity metrics (e.g., "How many systems have been integrated?", "How many teams are ready?")

#### Partial Data Handling

If some child rows lack strong consensus:
- Ignore those rows
- Compute parent if at least one valid child exists
- Mark parent as "computed from partial data" (⚠ indicator)

```python
def get_kpi_to_system_rollup(initiative_system_link, value_type_id):
    kpis = initiative_system_link.kpis
    eligible_values = []

    for kpi in kpis:
        config = kpi.value_type_configs.filter_by(value_type_id=value_type_id).first()
        if not config:
            continue

        consensus = ConsensusService.get_cell_value(config)

        if consensus.get('is_rollup_eligible'):  # Strong consensus only
            eligible_values.append(consensus['value'])

    if not eligible_values:
        return None

    # Apply formula
    value_type = ValueType.query.get(value_type_id)
    formula = value_type.default_aggregation_formula

    if formula == 'sum':
        result = sum(eligible_values)
    elif formula == 'min':
        result = min(eligible_values)
    elif formula == 'max':
        result = max(eligible_values)
    elif formula == 'avg':
        result = sum(eligible_values) / len(eligible_values)

    return {
        'value': result,
        'is_complete': len(eligible_values) == len(kpis)  # All KPIs contributed?
    }
```

## Color Configuration System

### v2.0 Architecture

**Before v2.0**: Colors were defined on `ValueType` level. All KPIs using that value type inherited the same colors.

**v2.0**: Colors are defined on `KPIValueTypeConfig` level. Each KPI can interpret values differently.

### Why This Matters

Same value type, different meanings:

| Scenario | Value Type | KPI 1 (Expenses) | KPI 2 (Revenue) |
|----------|-----------|------------------|-----------------|
| Positive value | Cost (€) | Red (bad) | Green (good) |
| Negative value | Cost (€) | Green (savings!) | Red (loss) |
| Zero value | Cost (€) | Gray (neutral) | Gray (neutral) |

### Implementation

#### Model Level

```python
class KPIValueTypeConfig(db.Model):
    color_positive: str  # e.g., '#28a745' (green)
    color_zero: str      # e.g., '#6c757d' (gray)
    color_negative: str  # e.g., '#dc3545' (red)

    def get_value_color(self, value):
        """Get color for a numeric value based on its sign"""
        if not self.value_type.is_numeric() or value is None:
            return None

        try:
            numeric_value = float(value)
            if numeric_value > 0:
                return self.color_positive or '#28a745'
            elif numeric_value < 0:
                return self.color_negative or '#dc3545'
            else:
                return self.color_zero or '#6c757d'
        except (ValueError, TypeError):
            return None
```

#### Rollup Color Inheritance

Each rollup level (Space, Challenge, Initiative, System) has a `get_color_config(value_type_id)` method that finds a representative KPI configuration:

```python
class InitiativeSystemLink(db.Model):
    def get_color_config(self, value_type_id):
        """Get a representative KPIValueTypeConfig for coloring rollups"""
        for kpi in self.kpis:
            for config in kpi.value_type_configs:
                if config.value_type_id == value_type_id:
                    return config  # Use first match
        return None  # Fall back to default colors
```

#### Template Usage

```jinja2
{# KPI level - use config colors #}
{% set config = kpi.value_type_configs | selectattr('value_type_id', 'equalto', vt.id) | first %}
<span style="color: {{ config.get_value_color(consensus.value) }};">
    {{ consensus.value }}
</span>

{# Rollup level - inherit from descendant KPIs #}
{% set rollup = system.get_rollup_value(vt.id) %}
{% set color_config = system.get_color_config(vt.id) %}
{% if color_config %}
    <span style="color: {{ color_config.get_value_color(rollup.value) }};">
        {{ rollup.value }}
    </span>
{% else %}
    {# Fall back to default filter #}
    <span style="color: {{ rollup.value|default_value_color }};">
        {{ rollup.value }}
    </span>
{% endif %}
```

### UI for Color Configuration

#### KPI Creation
- Checkbox list of value types
- For each selected numeric value type: 3 color pickers (positive, zero, negative)
- JavaScript shows/hides color pickers based on checkbox state

#### KPI Editing
- Shows all value types configured for this KPI
- Color pickers pre-filled with current values
- Changes apply immediately to KPI and propagate to rollups

## Excel Export

Located in `app/services/excel_export_service.py`. Rewritten in **v7.20.0** from a single bare sheet into a **five-sheet workbook**. Triggered by `/workspace/export-excel` (the green spreadsheet button on the workspace toolbar).

### Sheets

| # | Name | Contents |
|---|------|----------|
| 1 | **Overview** | Workspace title + description, generated timestamp + user, structure counts (spaces / challenges / unique initiatives / unique systems / KPIs), KPI RAG distribution (🟢 ≥90% to target / 🟡 60–89% / 🔴 <60% / ⚪ no target), action-item / governance-body / pillar / value-type counts. |
| 2 | **Tree** | Hierarchical Space → Challenge → Initiative → System → KPI with Excel outline (1–4 expand/collapse levels). `outlinePr.summaryBelow=False` so the +/- toggle sits on each parent row. Per-level icons drawn from `EntityTypeDefault`, level-tinted backgrounds, autofilter, freeze panes. **No hyperlinks in tree text** (kept the helper for other sheets). KPI value cells store **numbers** (with unit-aware `number_format` like `0.00 "kg"`) so Excel sort/filter works natively, and each cell gets a **RAG fill** computed from `target_value × target_direction × target_tolerance_pct`. |
| 3 | **KPIs** | Every KPI/value-type pair as a flat row: full path · current · target · Δ% · RAG · direction · target date · tolerance · last update · last contributor. Frozen panes + autofilter. RAG-filled Δ% and RAG-status cells. |
| 4 | **Action Items** | type · title · description · status · priority · due · completed · owner · creator · visibility · mentions · governance bodies · created. Priority and status colour-coded; frozen panes + autofilter. |
| 5 | **Settings** | Value types, impact levels (with weight + colour swatches), strategic pillars, governance bodies, geography (region › country › site). |

### RAG computation

```python
def _compute_rag(value, target, direction, tolerance_pct):
    direction = direction or "maximize"
    if direction == "minimize":
        progress = (target / value) * 100 if value != 0 else 100
    elif direction == "exact":
        tol_abs = abs(target) * (tolerance_pct or 10) / 100
        diff = abs(value - target)
        progress = 100 if diff <= tol_abs else max(0, 100 - ((diff - tol_abs) / abs(target) * 100))
    else:  # maximize
        progress = (value / target) * 100 if target != 0 else 0
    return ("green", progress) if progress >= 90 else ("amber", progress) if progress >= 60 else ("red", progress)
```

### Usage

```python
# app/routes/workspace.py
@bp.route("/export-excel")
@login_required
@organization_required
def export_excel():
    org_id = session.get("organization_id")
    org_name = session.get("organization_name")
    excel_file = ExcelExportService.export_workspace(
        org_id,
        base_url=request.url_root.rstrip("/"),  # for any future hyperlinks
        generated_by=current_user.login if current_user.is_authenticated else None,
    )
    return send_file(excel_file,
                     mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                     as_attachment=True,
                     download_name=f"Workspace_{org_name}.xlsx")
```


## Standalone HTML Snapshot Export

Located in `app/services/standalone_html_export_service.py`. Triggered by `/workspace/export-html` (the blue rich-text button next to the Excel one). Added in **v7.21.0**, redesigned in **v7.21.1** to **render the live page** rather than a custom static renderer, and refined through 7.21.3.

### What it produces

A **single self-contained `.html` file** (~900KB-2MB depending on logo count) that, when opened in a browser:

- Looks and behaves like the live `/workspace/` page — same CSS, same Alpine.js, same icons, same xmas-tree level cycle (🌱/🌲/🎄), same per-row expand/collapse, same click-for-description popup.
- Loads its data from an **embedded JSON blob**, never the network.
- Opens **Porter / Strategy / Lenses / SWOT** clicks as in-page modals populated from data embedded at export time (also no network).

### Strategy: render-and-inline (NOT custom renderer)

```python
def export_workspace(organization_id, *, base_url, generated_by):
    # 1. Build the same data the live page consumes.
    ws_data = _build_workspace_data(organization_id).get_json()

    # 2. Render the actual live workspace page in the current request context.
    rendered = workspace.index()
    html = rendered.get_data(as_text=True)

    # 3. Inline every /static/*.css and /static/*.js into <style>/<script> blocks.
    html = _inline_local_assets(html)

    # 4. Inject a pre-Alpine shim: fetch() interceptor + extras for inline modals.
    extras = {"porters": {...}, "pillars": [...], "strategy_enabled": ...}
    html = _inject_shim(html, ws_data, snapshot_meta=meta, base_url=base_url, extras=extras)
    return BytesIO(html.encode("utf-8"))
```

CDN-hosted libraries (Bootstrap, BS Icons, Alpine, FontAwesome) stay as `https://...` links — recipients online get pixel-identical look; offline they degrade gracefully but stay readable.

### The injected shim

A single `<script>` injected at the top of `<head>` that:

- Stores the workspace data as `window.__SNAPSHOT_DATA__` and the extras (porters, pillars) as `window.__SNAPSHOT_EXTRAS__`.
- Patches `window.fetch`: any call to `/workspace/data*` resolves with `__SNAPSHOT_DATA__`; calls to `/api/*`, `/workspace/api/*`, `/global-admin/api/*`, `/workspace/contribute*` resolve with `{}` (so the live page boots without errors).
- Blocks all form submissions in capture phase.
- Walks `[x-data]` roots on `DOMContentLoaded` and forces `editMode = false`, even if Alpine restored it from `localStorage`.
- **Click interceptor** matches links by URL pattern and shows in-page modals instead of navigating:
  - `/org-admin/porters` → 5 Porter forces text blocks
  - `/strategy` (or `/workspace/strategy`) → strategic pillars list
  - `/dimensions` (or `/workspace/dimensions`) → value-types table (Lenses)
  - `/spaces/<id>/swot` → that space's S/W/O/T quadrants
- A `<base href="{base_url}/">` makes any other relative link the user might click resolve against the deployed app instead of `file:///`.

### CSS hidden in the snapshot only (live template untouched)

```css
.navbar, nav.navbar, .ga-subnav            { display: none !important; }
.preset-bar, [class*="preset-bar"]         { display: none !important; }
#wsEditModeBtn, .ws-edit-mode-toggle       { display: none !important; }
.snapshot-controls                         { display: none !important; }
.ws-iadd-overlay, [class*="ws-iadd"]       { display: none !important; }
.comments-panel, [class*="comments-section"] { display: none !important; }
.maintenance-banner, .live-search-results  { display: none !important; }
```

### Asset inlining

Two regex passes against the rendered HTML:

```python
# CSS: <link rel="stylesheet" href="/static/...">  →  <style>{contents}</style>
# JS : <script src="/static/..."></script>          →  <script>{contents}</script>
```

External (`https://...`) assets are deliberately left untouched.

### What the recipient experiences

- Open the file in any modern browser — page renders identically to `/workspace/`.
- Tree expand/collapse, badge mode (xmas tree level), description popup all work offline.
- Porter / Strategy / Lenses / SWOT click → in-page modal, no network.
- Edit/contribute UI is hidden, so there are no "broken" buttons.
- No "Static snapshot" badge or watermark.

## YAML Export/Import

### YAML Export Service

Located in `app/services/yaml_export_service.py`.

**Purpose**: Export complete organizational structure to YAML format for backup, version control, or transferring to another instance.

#### Friendly ID Generation

Generates human-readable IDs during export:
- **Spaces**: S1, S2, S3...
- **Challenges**: C1, C2, C3...
- **Initiatives**: I1, I2, I3...
- **Systems**: SYS1, SYS2, SYS3...

These IDs are used by the import service to detect reusable entities (same initiative/system used in multiple places).

#### Export Structure

```yaml
# Value Types (organization-wide)
value_types:
  - name: "Cost"
    kind: numeric
    numeric_format: decimal
    decimal_places: 2
    unit_label: "€"
    default_aggregation_formula: sum

# Hierarchical Structure
spaces:
  - id: S1
    name: "Season 1 - Foundation"
    space_label: "Season"
    challenges:
      - id: C1
        name: "Digital Transformation"
        initiatives:
          - id: I1
            name: "Value streams & standard E2E processes"
            systems:
              - id: SYS1
                name: "Core ERP (SAP S/4HANA)"
                kpis:
                  - name: "Lead time reduction"
                    value_types:
                      - name: "Time to Deliver"
                        colors:
                          positive: "#dc3545"  # Red
                          zero: "#6c757d"
                          negative: "#28a745"  # Green
```

#### What's Exported

- ✅ Value Types (kinds, formats, units, formulas)
- ✅ Spaces (with labels and descriptions)
- ✅ Challenges (hierarchy and order)
- ✅ Initiatives (reusable across challenges)
- ✅ Systems (reusable across initiatives)
- ✅ KPIs (with value type associations)
- ✅ Color Configurations (per KPI-value type pair)
- ❌ User Memberships (not exported)
- ❌ Contributed Data (not exported)
- ❌ Consensus Values (not exported)

### YAML Import Service

Located in `app/services/yaml_import_service.py`.

**Purpose**: Import organizational structure from YAML files, creating complete hierarchies with proper relationships.

#### ID Reuse Logic

The import service uses friendly IDs to detect when the same initiative or system appears multiple times:

```python
# First occurrence of I1 - creates the initiative
initiatives['I1'] = Initiative(name="...", organization_id=org_id)

# Second occurrence of I1 - reuses existing initiative
initiative = initiatives['I1']  # Already exists
```

This enables:
- Same initiative addressing multiple challenges
- Same system supporting multiple initiatives
- Proper many-to-many relationships

#### Import Process

1. **Validate YAML**: Check structure and required fields
2. **Create Value Types**: Organization-wide definitions
3. **Create Master Entities**: All initiatives and systems (deduplicated by ID)
4. **Create Hierarchy**: Spaces → Challenges → Links → KPIs
5. **Configure Colors**: KPI-level color assignments
6. **Commit Transaction**: All-or-nothing import

#### Error Handling

```python
try:
    result = YAMLImportService.import_from_yaml(yaml_content, org_id)
    flash(f"Import successful! Created {result['spaces']} spaces, {result['kpis']} KPIs.", 'success')
except ValidationError as e:
    flash(f"Import failed: {e.message}", 'danger')
except Exception as e:
    db.session.rollback()
    flash(f"Import error: {str(e)}", 'danger')
```

## Full Backup & Restore

Full backup creates a comprehensive JSON snapshot of an organization including all hierarchy data, contributions, users, governance bodies, entity links, branding, logos, geography, stakeholders, action items, and decisions.

### Backup Format (JSON)

```
{
  "format_version": "3.0",
  "organization": { name, description, Porter's, logo, links, ... },
  "entity_branding": [ { entity_type, color, icon, logo } ],
  "governance_bodies": [ { name, abbreviation, is_global, color, ... } ],
  "value_types": [ { name, kind, unit, formula, config, ... } ],
  "users": [ { login, email, display_name, permissions } ],
  "spaces": [ { name, SWOT, challenges: [ { initiatives: [ { systems: [ { kpis } ] } ] } ] } ],
  "action_items": [ { title, type, status, mentions, governance_bodies } ],
  "stakeholders": [ { name, role, relationships, entity_links } ],
  "decisions": [ { what, who, tag, governance_body, entity_mentions } ]
}
```

### Restore Flow

1. Upload JSON → detect users needing mapping, governance bodies, portal orgs
2. User mapping page (if unmapped users found)
3. Governance body mapping page (auto-selects exact name matches, shows cross-org toggle)
4. Execute restore with `FullRestoreService.restore_from_json()`

### Order-Independent Restore

Governance bodies referenced by KPIs but not in the backup's `governance_bodies` list (e.g., a global GB owned by another workspace) are handled at KPI restore time:
1. Look for existing global GB by name
2. Look for same-org GB by name
3. Auto-create as global if not found (with warning)

This allows workspaces to be restored in any order without losing GB-KPI mappings.

### Key Rules

- Action items always restored as `is_global=False` (workspace-scoped)
- Existing GBs with same name in target org are reused (no duplicates)
- Global GBs from other orgs are matched by name
- Organization-level entity links are included in backup

## Selective Import

Route: `/org-admin/selective-import`

A Workspace Admin tool to browse a backup JSON file and selectively import data into the current workspace.

### 3-Step Flow

1. **Upload** — drag & drop or browse a `.json` backup file
2. **Preview** — server parses the JSON, returns available categories with duplicate detection (existing URLs matched case-insensitively)
3. **Import** — selected items are imported; duplicates skipped; results shown with counts

### Architecture

- **Preview endpoint** (`POST /org-admin/selective-import/preview`) — stores backup in temp file, analyzes categories, returns JSON with `records` and `is_duplicate` flags
- **Execute endpoint** (`POST /org-admin/selective-import/execute`) — reads temp file, imports selected items, cleans up
- **Client-side** — file upload via `FormData`, category rendering with select/deselect, AJAX import

### Currently Supported

- **Organization-level links** — with URL-based duplicate detection

### Extensible For

- Spaces, challenges, initiatives, governance bodies, value types, stakeholders (future)

## Workspace Labels & Profiles

### Labels

- Per-user color-coded tags assigned to workspaces (`WorkspaceLabel` model)
- Many-to-many with `Organization` via `organization_label` join table
- Managed on Profile page Workspaces tab

### Profiles

- `UserWorkspaceProfile` model with JSON `config` column
- Properties: `label_ids`, `space_visibility` (`all`/`public`), `action_scope` (`all`/`workspace`)
- One active profile per user; controls Workspaces menu filtering and Action Register scope
- **Action scope**: when set to `workspace`, `ActionItemService.get_items_for_user()` excludes `is_global=True` items from other orgs

### Navbar Integration

- Workspaces menu items have `data-org-id` and `data-label-ids` attributes
- `refreshWorkspacesMenu()` JS function updates visibility without page reload when labels are toggled

## Governance Body Sharing

Governance bodies support cross-workspace visibility via `is_global` flag.

### Behavior

- `GovernanceBody.for_org(org_id)` returns own-org GBs + all `is_global=True` GBs
- Global GBs appear in KPI governance assignment across all workspaces
- `KPIGovernanceBodyLink` can reference a GB from any org if it's global

### Shared Entities Page

Route: `/super-admin/shared-entities`

- Lists all `is_global=True` governance bodies and action items
- Shows owning workspace, KPI count, which workspaces use each GB
- Bulk "Unshare" sets `is_global=False` on selected entities
- Entity type filter tabs (All / Governance Bodies / Action Items)

## Duplicate Detector

Route: `/super-admin/duplicate-detector`

Scans the database for case-insensitive name duplicates within each workspace.

### Scanned Entity Types

Governance Bodies, Spaces, Challenges, Initiatives, Systems, Value Types, Action Items, Stakeholders, Users (9 types)

### Features

- **Summary cards** — clickable per-entity-type counts
- **Workspace filter** — scope scan to single org
- **Impact analysis** — dependent data counts per record (KPIs linked, challenges, contributions, etc.)
- **Parent context** — shows Space for challenges, Challenge for initiatives, etc.
- **Safe delete** — green button for zero-dependency records, yellow warning for cascading deletes
- **Delete endpoint** — `POST /super-admin/duplicate-detector/delete/<type>/<id>`

## Shared Entities Management

Route: `/super-admin/shared-entities`

Provides visibility and bulk control over cross-workspace (`is_global=True`) entities.

### Supported Entity Types

- **Governance Bodies** — with KPI count, owning workspace, and list of workspaces using them
- **Action Items** — with type, status, and owning workspace

### Actions

- Select all / none per entity type
- Bulk unshare (sets `is_global=False`)
- Entity type filter tabs

## Entity Branding

Entity type branding is managed per-workspace via the Branding Manager (`/org-admin/branding`).

### Model

`EntityTypeDefault` stores per-org defaults: `default_color`, `default_icon`, `default_logo_data` (binary), `default_logo_mime_type`.

### Context Processor

`inject_entity_defaults()` in `app/__init__.py` provides `entity_defaults` dict to all templates with `color`, `icon`, and `logo` (base64 data URL) per entity type.

### Usage Pattern

Templates check for logo first, then fall back to icon:
```html
{% if entity_defaults.get('challenge', {}).get('logo') %}
    <img src="{{ entity_defaults['challenge']['logo'] }}" style="width:24px;height:24px;">
{% else %}
    <span>{{ entity_defaults.get('challenge', {}).get('icon', 'f') }}</span>
{% endif %}
```

## Organization Cloning

Located in `app/services/organization_clone_service.py`.

**Purpose**: Create a complete copy of an organization's structure for testing, training, or scenario planning without risking production data.

### What Gets Cloned

- ✅ Value Types (all configurations)
- ✅ Spaces, Challenges, Initiatives, Systems
- ✅ All many-to-many relationships (ChallengeInitiativeLink, InitiativeSystemLink)
- ✅ KPIs with value type configurations
- ✅ Color configurations (per KPI)
- ✅ Rollup rules (with formula overrides)
- ❌ User Memberships (not cloned)
- ❌ Contributed Data (not cloned)
- ❌ User Contributions (not cloned)

### Benefits

1. **Safe Testing**: Test structural changes without affecting production
2. **Training Environment**: Create sandbox organizations for user training
3. **Scenario Planning**: Clone and modify to explore "what-if" scenarios
4. **Template Creation**: Create template organizations to clone for new customers

### Implementation

```python
@staticmethod
def clone_organization(source_org_id, new_org_name, new_org_description=None):
    source_org = Organization.query.get(source_org_id)

    # Create new organization
    new_org = Organization(
        name=new_org_name,
        description=new_org_description or f"Clone of {source_org.name}",
        is_active=True
    )
    db.session.add(new_org)
    db.session.flush()

    # Clone all value types
    value_type_map = {}
    for vt in source_org.value_types:
        new_vt = ValueType(
            organization_id=new_org.id,
            name=vt.name,
            kind=vt.kind,
            # ... all fields ...
        )
        db.session.add(new_vt)
        db.session.flush()
        value_type_map[vt.id] = new_vt.id

    # Clone hierarchy with ID mappings
    # ... (similar mapping for all entities)

    db.session.commit()
    return new_org
```

### Usage

```python
# In routes/global_admin.py
@bp.route('/organizations/<int:org_id>/clone', methods=['POST'])
@login_required
@global_admin_required
def clone_organization(org_id):
    new_name = request.form.get('new_name')
    new_org = OrganizationCloneService.clone_organization(org_id, new_name)
    flash(f'Organization cloned successfully as "{new_name}"', 'success')
    return redirect(url_for('global_admin.organizations'))
```

## Drag-and-Drop Value Type Reordering

Located in `app/templates/organization_admin/value_types.html`.

**Purpose**: Allow administrators to reorder value types via drag-and-drop, controlling the column order in the workspace.

### Technology Stack

- **Frontend**: SortableJS library
- **Backend**: AJAX endpoint for persistence
- **Visual Feedback**: Drag handle (⋮⋮) and ghost element during drag

### Implementation

#### Frontend (JavaScript)

```javascript
const tbody = document.querySelector('table tbody');
const sortable = Sortable.create(tbody, {
    animation: 150,
    handle: '.drag-handle',
    ghostClass: 'sortable-ghost',
    onEnd: function(evt) {
        // Get new order
        const rows = tbody.querySelectorAll('tr[data-id]');
        const order = Array.from(rows).map(row => parseInt(row.dataset.id));

        // Save to server
        fetch('{{ url_for("organization_admin.reorder_value_types") }}', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ order: order })
        })
        .then(response => response.json())
        .then(data => {
            if (!data.success) {
                alert('Failed to save order');
                location.reload();  // Revert on error
            }
        });
    }
});
```

#### Backend (Route)

```python
@bp.route('/value-types/reorder', methods=['POST'])
@login_required
@organization_required
def reorder_value_types():
    org_id = session.get('organization_id')
    data = request.get_json()
    order = data.get('order', [])

    # Update display_order for each value type
    for index, vt_id in enumerate(order):
        vt = ValueType.query.filter_by(id=vt_id, organization_id=org_id).first()
        if vt:
            vt.display_order = index

    db.session.commit()
    return jsonify({'success': True})
```

### Security

- **No CSRF Token Required**: Endpoint protected by `@login_required` and `@organization_required`
- **Organization Isolation**: Only reorder value types belonging to current organization
- **Validation**: Checks that value type IDs exist and belong to organization

### User Experience

1. **Visual Indicator**: Drag handle (⋮⋮) appears on hover
2. **Smooth Animation**: 150ms animation during drag
3. **Ghost Element**: Semi-transparent copy shows where item will drop
4. **Immediate Persistence**: Order saved to database as soon as drag completes
5. **Workspace Updates**: New order immediately reflected in workspace columns (requires refresh)

## Deletion Rules

Located in `app/services/deletion_impact_service.py`.

**Purpose**: Provide smart cascade deletion with impact preview, protecting reusable entities while cleaning up orphaned data.

### Core Principles

1. **Reusable Entities Protected**: Initiatives and Systems used in multiple places are preserved
2. **Orphan Cleanup**: Entities used in only one place are cascaded for deletion
3. **Impact Preview**: Users see exactly what will be deleted before confirming
4. **Data Loss Visibility**: Count of contributions and configurations that will be lost

### Entity Deletion Behavior

#### Space Deletion
**Deletes:**
- The space itself
- All challenges within the space
- Challenge-initiative links
- Orphaned initiatives (used only in this space)
- Orphaned systems (used only in this space's initiatives)
- All KPIs, configurations, contributions in orphaned entities
- All rollup rules for deleted entities

**Preserves:**
- Initiatives linked to challenges in other spaces
- Systems linked to initiatives in other challenges/spaces

#### Challenge Deletion
**Deletes:**
- The challenge itself
- All challenge-initiative links
- Orphaned initiatives (linked only to this challenge)
- Orphaned systems (used only by this challenge's initiatives)
- All KPIs and data in orphaned entities

**Preserves:**
- Initiatives linked to other challenges
- Systems linked to other initiatives

#### Initiative Deletion
**Options:**
1. **Detach from Challenge**: Removes only the link, preserves initiative and all data
2. **Full Deletion** (if not linked elsewhere):
   - The initiative
   - All initiative-system links
   - Orphaned systems (used only by this initiative)
   - All KPIs and data

**Preserves:**
- Systems used by other initiatives

#### System Deletion
**Options:**
1. **Detach from Initiative**: Removes only the link, all KPIs and data for this context are deleted
2. **Full Deletion** (if not linked elsewhere):
   - The system
   - All initiative-system links
   - All KPIs and data across all contexts

### Deletion Impact Analysis

The service provides detailed counts before deletion:

```python
# Example impact for challenge deletion
{
    'challenges': 1,
    'challenge_initiative_links': 3,
    'orphaned_initiatives': 1,      # Will be deleted
    'preserved_initiatives': 2,      # Will remain (used elsewhere)
    'initiative_system_links': 5,
    'orphaned_systems': 2,           # Will be deleted
    'preserved_systems': 3,          # Will remain (used elsewhere)
    'kpis': 12,
    'kpi_value_type_configs': 36,
    'contributions': 85,             # User data that will be lost!
    'rollup_rules': 8
}
```

### Implementation Example

```python
# Analyze before deleting
impact = DeletionImpactService.analyze_challenge_deletion(challenge_id)

# Show user the impact
flash(f"Warning: This will delete {impact['contributions']} contributions!", 'warning')
flash(f"Orphaned: {impact['orphaned_initiatives']} initiatives, "
      f"{impact['orphaned_systems']} systems", 'info')
flash(f"Preserved: {impact['preserved_initiatives']} initiatives, "
      f"{impact['preserved_systems']} systems", 'success')

# User confirms → proceed with deletion
if confirmed:
    db.session.delete(challenge)
    db.session.commit()
```

### Cascade Deletion Rules (SQLAlchemy)

```python
# Example from models
class Challenge(db.Model):
    initiative_links = db.relationship(
        'ChallengeInitiativeLink',
        backref='challenge',
        cascade='all, delete-orphan'  # Delete links when challenge is deleted
    )

class InitiativeSystemLink(db.Model):
    kpis = db.relationship(
        'KPI',
        backref='initiative_system_link',
        cascade='all, delete-orphan'  # Delete KPIs when link is deleted
    )
```

### User Experience

1. **Deletion Button**: User clicks delete on entity
2. **Impact Analysis**: Service calculates what will be affected
3. **Confirmation Dialog**: Shows impact summary
   - "This will delete 85 contributions from users"
   - "2 initiatives will be removed (orphaned)"
   - "2 initiatives will remain (used elsewhere)"
4. **User Decision**: Confirm or cancel
5. **Execution**: Database transaction (all-or-nothing)

### Safety Considerations

- **Contribution Data**: Always shown prominently in impact preview
- **Transaction Safety**: All deletions in single database transaction
- **No Partial Deletion**: Either everything succeeds or nothing changes
- **Audit Trail**: Could be enhanced with deletion logging (not currently implemented)

## Authentication & Authorization

### Two Administration Scopes

1. **Global Administration**: Manages users and organizations
2. **Organization Administration**: Manages business content

### Login Flow

```
Step 1: Username/Password
    ↓
Step 2: Organization Selection
    ↓
    ├─ "Global Administration" (if user.is_global_admin)
    │   → session['organization_id'] = None
    │   → Redirect to /global-admin
    │
    └─ Select organization
        → session['organization_id'] = org.id
        → session['organization_name'] = org.name
        → Redirect to /workspace
```

### Bootstrap Admin

On first startup:
```python
def _bootstrap_admin():
    if User.query.filter_by(is_global_admin=True).first():
        return  # Admin exists

    admin = User(
        login='cisk',
        email='admin@cisk.local',
        is_global_admin=True,
        must_change_password=True
    )
    admin.set_password('Zurich20')
    db.session.add(admin)
    db.session.commit()
```

### Protection Decorators

```python
@login_required
def protected_route():
    pass  # User must be logged in

@organization_required
def org_route():
    pass  # User must have selected an organization
```

## Database Migrations

### Flask-Migrate Setup

```bash
# Initialize migrations (first time only)
flask db init

# Create a migration after model changes
flask db migrate -m "Add color fields to KPIValueTypeConfig"

# Apply migrations
flask db upgrade

# Rollback if needed
flask db downgrade
```

### Render Auto-Migrations

In `render.yaml`:
```yaml
buildCommand: pip install -r requirements.txt && flask db upgrade
```

Migrations run automatically on every deployment.

### Migration Best Practices

1. **Always test migrations locally first**
2. **Create descriptive migration messages**
3. **Review generated migration scripts before applying**
4. **Use `flask db stamp head` to mark initial state**
5. **Never edit applied migrations** - create new ones

## Code Organization

### Models (`app/models/`)
- One file per entity (or logical group)
- SQLAlchemy models with relationships
- Helper methods for business logic
- Comprehensive docstrings

### Forms (`app/forms/`)
- WTForms for validation
- Field-level validators
- CSRF tokens included automatically

### Routes (`app/routes/`)
- Flask Blueprints by functional area
- Decorated with `@login_required`, `@organization_required`
- Thin layer - delegates to services

### Services (`app/services/`)
- Stateless business logic
- No direct request/response handling
- Easily testable
- Examples: `ConsensusService`, `AggregationService`, `RollupComputeService`, `FullBackupService`, `FullRestoreService`, `YAMLExportService`, `YAMLImportService`, `ExcelExportService` (5-sheet workbook), `StandaloneHtmlExportService` (single-file workspace snapshot via render-and-inline), `AuditService`, `DemoDataService`, `OrganizationCloneService`, `DeletionImpactService`, `ImpactService`

### Templates (`app/templates/`)
- Jinja2 with Bootstrap 5
- Base template with navbar
- Flash messages
- Form rendering macros

## Production Deployment

### Environment Configuration

```python
# app/config.py
class ProductionConfig(Config):
    DEBUG = False

    # Database URL handling (Render compatibility)
    database_url = os.environ.get('DATABASE_URL')
    if database_url:
        # Convert postgres:// to postgresql://
        if database_url.startswith('postgres://'):
            database_url = database_url.replace('postgres://', 'postgresql://', 1)
        # Use psycopg3 driver
        if 'postgresql://' in database_url and '+' not in database_url:
            database_url = database_url.replace('postgresql://', 'postgresql+psycopg://', 1)
    SQLALCHEMY_DATABASE_URI = database_url

    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
        'pool_recycle': 300,
    }
```

### Render Configuration

```yaml
# render.yaml
services:
  - type: web
    name: cisk-navigator-app
    env: python
    region: oregon
    buildCommand: pip install -r requirements.txt && flask db upgrade
    startCommand: gunicorn run:app
    envVars:
      - key: PYTHON_VERSION
        value: 3.11.9
      - key: DATABASE_URL
        sync: false  # Set manually via Render dashboard
      - key: SECRET_KEY
        generateValue: true
      - key: FLASK_ENV
        value: production
```

### Data Loss Prevention

**Critical Issue Prevented**: User data was being reset on Render deployments because migrations were missing and SQLite fallback was creating empty databases.

#### Multi-Layer Safety Checks

**Layer 1: Configuration Validation**
```python
# app/config.py - ProductionConfig
if os.environ.get('FLASK_ENV') == 'production' and not database_url:
    raise RuntimeError(
        "CRITICAL ERROR: DATABASE_URL environment variable is not set in production! "
        "This would create a new SQLite database and DESTROY all your data. "
        "Please set DATABASE_URL in your Render environment variables."
    )
```

**Layer 2: Startup Logging**
```python
# app/__init__.py - create_app()
db_uri = app.config.get('SQLALCHEMY_DATABASE_URI', '')
flask_env = app.config.get('FLASK_ENV', 'development')

print("=" * 80)
print(f"FLASK_ENV: {flask_env}")
if 'postgresql' in db_uri:
    safe_uri = db_uri.split('@')[1] if '@' in db_uri else db_uri
    print(f"✓ USING POSTGRESQL: {safe_uri}")
elif 'sqlite' in db_uri:
    print(f"⚠ USING SQLITE: {db_uri}")
    if flask_env == 'production':
        print("❌ ERROR: SQLite should NEVER be used in production!")
print("=" * 80)
```

**Layer 3: Database Creation Guard**
```python
# app/__init__.py - create_app()
# Only create tables for SQLite in development/testing
if app.config.get('TESTING') or (app.config.get('SQLALCHEMY_DATABASE_URI', '').startswith('sqlite:///')):
    if flask_env == 'production':
        raise RuntimeError("CRITICAL: Attempted to use SQLite in production! Check DATABASE_URL!")
    db.create_all()
```

**Layer 4: Migration Requirement**
```yaml
# render.yaml - buildCommand
buildCommand: pip install -r requirements.txt && flask db upgrade
```

This ensures migrations run on every deployment, and the app will fail to start if DATABASE_URL is missing.

### Database Connection

```python
# run.py
from dotenv import load_dotenv
load_dotenv()  # Load .env for local development

from app import create_app

app = create_app()
```

### Health Checks

Render automatically monitors the `/` endpoint. The login page returns HTTP 200, confirming the app is healthy.

## Testing Strategy

### Test Organization

```
tests/
├── conftest.py              # Pytest fixtures
├── test_auth.py             # Authentication
├── test_consensus.py        # Consensus calculation
├── test_aggregation.py      # Roll-up aggregation
├── test_deletion.py         # Deletion impact
└── test_colors.py           # v2.0: Color configuration
```

### Key Fixtures

```python
@pytest.fixture
def app():
    """Test app with in-memory SQLite"""
    app = create_app('testing')
    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()

@pytest.fixture
def client(app):
    return app.test_client()

@pytest.fixture
def global_admin(app):
    admin = User(login='admin', is_global_admin=True)
    admin.set_password('Test123')
    db.session.add(admin)
    db.session.commit()
    return admin
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/test_consensus.py

# Run specific test
pytest tests/test_consensus.py::test_strong_consensus
```

## Conclusion

CISK Navigator v2.0 is a production-ready Flask application with:

### Core Infrastructure
- ✅ **PostgreSQL**: Data persistence across deployments
- ✅ **Automatic Migrations**: Schema evolution on deploy
- ✅ **Data Loss Prevention**: Multi-layer safety checks
- ✅ **Production-Ready**: Deployed on Render with managed PostgreSQL

### Data Management
- ✅ **Flexible Colors**: KPI-level color configuration (v2.0)
- ✅ **Multi-Organization**: Complete data isolation
- ✅ **Consensus-Driven**: High-quality data through agreement
- ✅ **Hierarchical Roll-ups**: Automatic aggregation with 6 formulas

### Value Types & Aggregation
- ✅ **6 Value Type Kinds**: numeric, risk, impact (pos/neg), level, sentiment
- ✅ **6 Aggregation Formulas**: sum, min, max, avg, median, count
- ✅ **3-Level Qualitative**: Easier consensus for soft metrics

### Export & Backup
- ✅ **Excel Export**: Hierarchical with row grouping and color coding
- ✅ **YAML Export/Import**: Complete structure backup and restore
- ✅ **Organization Cloning**: Safe testing and training environments

### User Experience
- ✅ **Drag-and-Drop Reordering**: Control workspace column order
- ✅ **Visual Hierarchy**: Tree-based workspace with expand/collapse
- ✅ **Responsive UI**: Bootstrap 5 with mobile support

### Code Quality
- ✅ **Well-Architected**: Clean separation of concerns
- ✅ **Comprehensive Testing**: pytest with fixtures
- ✅ **Service Layer**: Stateless, testable business logic
- ✅ **Type Safety**: Modern Python with type hints

The architecture supports complex requirements while remaining maintainable, testable, and extensible.

---

**For implementation questions**, refer to inline code comments and docstrings throughout the codebase.
