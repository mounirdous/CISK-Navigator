# CISK Navigator - Technical Architecture v2.0

**Last Updated**: March 7, 2026
**Version**: 2.0.0

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
10. [Deletion Rules](#deletion-rules)
11. [Code Organization](#code-organization)
12. [Database Migrations](#database-migrations)

## Overview

CISK Navigator is a Flask application using PostgreSQL as the production database. It follows the application factory pattern and uses Flask Blueprints for modular route organization.

### Design Principles

- **Production-Ready**: PostgreSQL for data persistence across deployments
- **Secure by Default**: CSRF protection, password hashing, session management
- **Migration-Friendly**: Flask-Migrate (Alembic) for schema evolution
- **Well-Tested**: Comprehensive test coverage with pytest
- **Multi-Tenant**: Complete organization isolation

### v2.0 Major Changes

1. **Database Migration**: SQLite → PostgreSQL
2. **Color System Refactor**: Colors moved from ValueType to KPIValueTypeConfig level
3. **Driver Upgrade**: psycopg2 → psycopg3 (Python 3.13+ compatible)
4. **Deployment**: Render with persistent PostgreSQL
5. **Automatic Migrations**: Database schema updates on deploy

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
- **Vanilla JavaScript**: Minimal JavaScript for tree expansion

### Deployment
- **Gunicorn 21.2**: Production WSGI server
- **Render**: Cloud platform with managed PostgreSQL

### Testing
- **pytest 7.4**: Testing framework
- **pytest-flask 1.3**: Flask-specific test fixtures

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
│   │   ├── consensus_service.py        # Consensus calculation
│   │   ├── aggregation_service.py      # Roll-up aggregation
│   │   ├── deletion_impact_service.py  # Deletion impact analysis
│   │   └── value_type_usage_service.py # Value type usage checking
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
    kind: str                  # 'numeric', 'risk', 'positive_impact', 'negative_impact'
    numeric_format: str        # 'integer' or 'decimal'
    decimal_places: int        # For decimal format
    unit_label: str            # '€', 'tCO2e', 'licenses', etc.
    default_aggregation_formula: str  # 'sum', 'min', 'max', 'avg'
    display_order: int
    is_active: bool
```

**v2.0 Change**: Color fields removed from ValueType. Colors now configured per KPI.

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

- **sum**: Add all values
- **min**: Minimum value
- **max**: Maximum value
- **avg**: Average value

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
- Examples: ConsensusService, AggregationService

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

- ✅ **PostgreSQL**: Data persistence across deployments
- ✅ **Flexible Colors**: KPI-level color configuration
- ✅ **Automatic Migrations**: Schema evolution on deploy
- ✅ **Multi-Organization**: Complete data isolation
- ✅ **Consensus-Driven**: High-quality data through agreement
- ✅ **Hierarchical Roll-ups**: Automatic aggregation
- ✅ **Well-Architected**: Clean separation of concerns
- ✅ **Production-Ready**: Deployed on Render with managed PostgreSQL

The architecture supports complex requirements while remaining maintainable, testable, and extensible.

---

**For implementation questions**, refer to inline code comments and docstrings throughout the codebase.
