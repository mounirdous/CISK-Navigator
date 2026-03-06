# CISK Navigator - Technical Architecture

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
9. [Deletion Rules](#deletion-rules)
10. [Code Organization](#code-organization)

## Overview

CISK Navigator is a Flask monolith application using SQLite as the database. It follows the application factory pattern and uses Flask Blueprints for modular route organization.

The application is designed to be:
- **Local-first**: Runs entirely on a local machine without external dependencies
- **Simple to deploy**: Single SQLite file, no separate database server
- **Migration-ready**: Structured to allow future migration to PostgreSQL
- **Well-tested**: Comprehensive test coverage with pytest

## Technology Stack

### Core Framework
- **Python 3.11+**: Modern Python with type hints support
- **Flask 3.0**: Lightweight WSGI web framework
- **SQLite**: Embedded relational database

### Flask Extensions
- **Flask-SQLAlchemy 3.1**: ORM for database interactions
- **Flask-Migrate 4.0**: Database migration management via Alembic
- **Flask-Login 0.6**: User session management
- **Flask-WTF 1.2**: Form handling and CSRF protection
- **Werkzeug 3.0**: Password hashing and utilities

### Frontend
- **Bootstrap 5**: Responsive UI framework
- **Vanilla JavaScript**: Minimal JavaScript for interactivity

### Testing
- **pytest 7.4**: Testing framework
- **pytest-flask 1.3**: Flask-specific test fixtures

## Application Structure

### Directory Layout

```
app/
├── __init__.py              # Application factory
├── config.py                # Configuration classes
├── extensions.py            # Flask extension instances
├── run.py                   # Application entry point
│
├── models/                  # Database models (SQLAlchemy)
│   ├── __init__.py
│   ├── user.py             # User and authentication
│   ├── organization.py     # Organization and memberships
│   ├── space.py            # Space model
│   ├── challenge.py        # Challenge model
│   ├── initiative.py       # Initiative and ChallengeInitiativeLink
│   ├── system.py           # System and InitiativeSystemLink
│   ├── kpi.py              # KPI model
│   ├── value_type.py       # ValueType and KPIValueTypeConfig
│   ├── contribution.py     # Contribution model
│   └── rollup_rule.py      # RollupRule model
│
├── forms/                   # WTForms for validation
│   ├── __init__.py
│   ├── auth_forms.py       # Login, password change
│   ├── user_forms.py       # User management
│   ├── organization_forms.py
│   ├── space_forms.py
│   ├── challenge_forms.py
│   ├── initiative_forms.py
│   ├── system_forms.py
│   ├── kpi_forms.py
│   ├── value_type_forms.py
│   └── contribution_forms.py
│
├── routes/                  # Flask Blueprints
│   ├── __init__.py
│   ├── auth.py             # Authentication routes
│   ├── global_admin.py     # Global administration
│   ├── organization_admin.py # Organization administration
│   └── workspace.py        # Main workspace and data entry
│
├── services/                # Business logic services
│   ├── __init__.py
│   ├── consensus_service.py        # Consensus calculation
│   ├── aggregation_service.py      # Roll-up aggregation
│   ├── deletion_impact_service.py  # Deletion impact analysis
│   └── value_type_usage_service.py # Value type usage checking
│
├── templates/               # Jinja2 templates
│   ├── base.html           # Base layout
│   ├── auth/               # Authentication templates
│   ├── global_admin/       # Global admin templates
│   ├── organization_admin/ # Org admin templates
│   └── workspace/          # Workspace templates
│
└── static/                  # Static assets
    ├── css/
    └── js/
```

### Application Factory Pattern

The application uses the factory pattern for flexible configuration:

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

    # Bootstrap admin
    with app.app_context():
        db.create_all()
        _bootstrap_admin()

    return app
```

This allows creating different app instances for development, production, and testing.

## Data Model

### Core Principles

1. **Immutable IDs**: Every entity has an immutable technical ID. Names can change.
2. **Many-to-Many Relationships**: Initiatives and Systems are reusable across multiple parents.
3. **Context-Specific Data**: KPIs belong to Initiative-System contexts, not master Systems.
4. **Organization Isolation**: All business data is scoped to organizations.

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
                                │
                                └── (N) Contribution

Challenge (1) ────── (N) RollupRule (for Challenge → Space)
```

### Key Models Explained

#### User
```python
class User:
    id: int                    # Immutable ID
    login: str                 # Unique login
    email: str
    display_name: str
    password_hash: str         # Hashed, never plaintext
    is_active: bool
    is_global_admin: bool
    must_change_password: bool # Forced password change
```

#### Organization
```python
class Organization:
    id: int
    name: str                  # Unique
    description: str
    is_active: bool
```

Organizations are isolated roots. Deleting an organization cascades to all its data.

#### Space
```python
class Space:
    id: int
    organization_id: int       # FK to Organization
    name: str
    description: str
    space_label: str           # Optional: "Season", "Site", etc.
    display_order: int
```

Spaces are flexible groupings like seasons, sites, customers, or suppliers.

#### Challenge
```python
class Challenge:
    id: int
    organization_id: int
    space_id: int              # FK to Space
    name: str
    description: str
    display_order: int
```

Challenges belong to one space.

#### Initiative
```python
class Initiative:
    id: int
    organization_id: int
    name: str
    description: str
```

Initiatives are **reusable** across multiple challenges via `ChallengeInitiativeLink`.

#### ChallengeInitiativeLink
```python
class ChallengeInitiativeLink:
    id: int
    challenge_id: int          # FK to Challenge
    initiative_id: int         # FK to Initiative
    display_order: int

    # Unique constraint: (challenge_id, initiative_id)
```

This is the **many-to-many link** between Challenges and Initiatives. Roll-up rules for Initiative → Challenge are attached here.

#### System
```python
class System:
    id: int
    organization_id: int
    name: str
    description: str
```

Systems are **reusable** across multiple initiatives via `InitiativeSystemLink`.

#### InitiativeSystemLink
```python
class InitiativeSystemLink:
    id: int
    initiative_id: int         # FK to Initiative
    system_id: int             # FK to System
    display_order: int

    # Unique constraint: (initiative_id, system_id)
```

This is the **many-to-many link** between Initiatives and Systems. **KPIs belong here**, not to the master System.

#### KPI
```python
class KPI:
    id: int
    initiative_system_link_id: int  # FK to InitiativeSystemLink
    name: str
    description: str
    display_order: int
```

**Critical**: KPIs are context-specific. The same system in different initiatives can have completely different KPIs.

#### ValueType
```python
class ValueType:
    id: int
    organization_id: int
    name: str
    kind: str                  # 'numeric', 'risk', 'positive_impact', 'negative_impact'
    numeric_format: str        # 'integer' or 'decimal'
    decimal_places: int
    unit_label: str            # '€', 'tCO2e', 'licenses', etc.
    default_aggregation_formula: str  # 'sum', 'min', 'max', 'avg'
    display_order: int
    is_active: bool
```

Value types are organization-specific and define what kind of values can be tracked.

#### KPIValueTypeConfig
```python
class KPIValueTypeConfig:
    id: int
    kpi_id: int                # FK to KPI
    value_type_id: int         # FK to ValueType
    display_order: int
    color_negative: str        # Sign-based colors (KPI-specific)
    color_zero: str
    color_positive: str
```

One KPI can have multiple value types. Sign-based colors are configured per KPI-value-type pair.

#### Contribution
```python
class Contribution:
    id: int
    kpi_value_type_config_id: int  # FK to KPIValueTypeConfig
    contributor_name: str          # Free text, no user account required
    numeric_value: Decimal         # For numeric types
    qualitative_level: int         # 1, 2, or 3 for qualitative types
    comment: str
```

Contributors provide opinions. One contributor per cell (updates replace previous entry).

#### RollupRule
```python
class RollupRule:
    id: int
    source_type: str           # 'initiative_system', 'challenge_initiative', 'challenge'
    source_id: int             # ID of the link or challenge
    value_type_id: int         # FK to ValueType
    rollup_enabled: bool       # Default: False
    formula_override: str      # 'default', 'sum', 'min', 'max', 'avg'
```

Roll-up rules are **context-specific**:
- System → Initiative: attached to `InitiativeSystemLink`
- Initiative → Challenge: attached to `ChallengeInitiativeLink`
- Challenge → Space: attached to `Challenge`

## Business Logic

### Consensus Service

Located in `app/services/consensus_service.py`.

#### Consensus Statuses

1. **No Data**: No contributions exist
2. **Pending Confirmation**: Only one contribution
3. **Strong Consensus**: 2+ contributions, all same value (eligible for roll-up)
4. **Weak Consensus**: 2+ contributions, majority exists but not unanimous
5. **No Consensus**: 2+ contributions, no reliable agreement

#### Roll-up Eligibility

**Only Strong Consensus values participate in upward roll-ups.**

This is intentional and enforces data quality.

```python
def calculate_consensus(contributions):
    if not contributions:
        return {'status': 'no_data', 'is_rollup_eligible': False}

    if len(contributions) == 1:
        return {'status': 'pending', 'is_rollup_eligible': False}

    # Check if all values are the same
    if all values are same:
        return {'status': 'strong', 'is_rollup_eligible': True}

    # Check for majority
    if majority exists:
        return {'status': 'weak', 'is_rollup_eligible': False}

    return {'status': 'no_consensus', 'is_rollup_eligible': False}
```

### Aggregation Service

Located in `app/services/aggregation_service.py`.

#### Roll-up Flow

```
KPI (leaf data)
    ↓ (Value Type default formula)
System (first rolled-up summary)
    ↓ (Configurable via InitiativeSystemLink RollupRule)
Initiative
    ↓ (Configurable via ChallengeInitiativeLink RollupRule)
Challenge
    ↓ (Configurable via Challenge RollupRule)
Space
```

#### Aggregation Formulas

- **sum**: Add all values (not available for qualitative in V1)
- **min**: Minimum value
- **max**: Maximum value
- **avg**: Average (for qualitative, stores raw average, can round for display)

#### Partial Data Handling

If some child rows lack strong consensus:
- Ignore those rows
- Compute parent if at least one valid child exists
- Mark parent cell as "computed from partial data"

```python
def get_kpi_to_system_rollup(initiative_system_link, value_type_id):
    kpis = initiative_system_link.kpis
    eligible_values = []

    for kpi in kpis:
        config = get_config(kpi, value_type_id)
        consensus = ConsensusService.get_cell_value(config)

        if consensus['is_rollup_eligible']:  # Strong consensus only
            eligible_values.append(consensus['value'])

    if not eligible_values:
        return None

    aggregated = aggregate(eligible_values, value_type.default_formula)

    return {
        'value': aggregated,
        'is_complete': len(eligible_values) == total_kpis
    }
```

### Deletion Impact Service

Located in `app/services/deletion_impact_service.py`.

#### Challenge Deletion Logic

When deleting a Challenge:

1. Delete the Challenge record
2. Delete all `ChallengeInitiativeLink` records
3. For each Initiative:
   - Check if it has other Challenge links
   - If no other links, delete the Initiative (orphan cleanup)
   - When deleting an Initiative, delete its `InitiativeSystemLink` records
4. For each System:
   - Check if it has other Initiative links
   - If no other links, delete the System (orphan cleanup)
5. Delete KPIs belonging to removed `InitiativeSystemLink` records
6. Delete KPI configs and contributions cascading from KPIs

**Shared Initiatives and Systems are preserved if they're still used elsewhere.**

#### Impact Preview

Before deletion, the service provides a comprehensive impact report:

```python
def analyze_challenge_deletion(challenge_id):
    return {
        'challenges': 1,
        'challenge_initiative_links': 3,
        'orphaned_initiatives': 1,
        'preserved_initiatives': 2,
        'initiative_system_links': 4,
        'orphaned_systems': 2,
        'preserved_systems': 1,
        'kpis': 11,
        'contributions': 36,
        'rollup_rules': 8
    }
```

This is displayed to the user before confirming deletion.

### Value Type Usage Service

Located in `app/services/value_type_usage_service.py`.

#### Usage Checking

A Value Type cannot be deleted if it's used in:
- Any `KPIValueTypeConfig`
- Any `Contribution`
- Any `RollupRule`

```python
def check_usage(value_type_id):
    kpi_configs = KPIValueTypeConfig.query.filter_by(value_type_id=value_type_id).all()
    contributions_count = sum(len(config.contributions) for config in kpi_configs)
    rollup_rules_count = RollupRule.query.filter_by(value_type_id=value_type_id).count()

    is_used = (len(kpi_configs) > 0 or contributions_count > 0 or rollup_rules_count > 0)

    return {'is_used': is_used, 'usage': detailed_usage_info}
```

If deletion is attempted on an in-use Value Type, the UI shows where it's used.

## Authentication & Authorization

### Two Administration Scopes

1. **Global Administration**: Manages users and organizations
2. **Organization Administration**: Manages business content within one organization

### Login Flow

```
User enters:
- Login
- Password
- Organization (dropdown)

Special option: "Global Administration" (0)

Validation:
1. User exists?
2. Password correct?
3. User active?
4. If Global Administration selected: is user a global admin?
5. If organization selected: does user have access?

On success:
- Set session['organization_id']
- Set session['organization_name']
- Redirect to workspace or global admin area

If must_change_password:
- Force password change before proceeding
```

### Bootstrap Admin

On first startup, if no global admin exists:

```python
def _bootstrap_admin():
    if User.query.filter_by(is_global_admin=True).first():
        return  # Admin already exists

    admin = User(
        login='cisk',
        email='admin@cisk.local',
        is_global_admin=True,
        must_change_password=True
    )
    admin.set_password('Zurich20')  # Hashed immediately
    db.session.add(admin)
    db.session.commit()
```

### Protection Rules

- Last active global admin cannot be deleted
- Users can only access organizations they're assigned to
- Regular users cannot access Global Administration
- Organization context is enforced via decorators

```python
def organization_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get('organization_id') is None:
            flash('Please log in to an organization')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function
```

## Code Organization

### Models (app/models/)

Each model file contains:
- SQLAlchemy model definition
- Relationships
- Helper methods
- Docstrings explaining the model's role

Models use:
- `db.Column` for fields
- `db.ForeignKey` for relationships
- `db.relationship` for ORM navigation
- `db.UniqueConstraint` for composite uniqueness

### Forms (app/forms/)

WTForms provide:
- Field definitions
- Validators
- CSRF protection
- Error messages

Forms are used in both GET (display) and POST (validation) requests.

### Routes (app/routes/)

Blueprints organize routes by functional area:

- **auth.py**: Login, logout, password change
- **global_admin.py**: User and organization management
- **organization_admin.py**: Business content management
- **workspace.py**: Main tree/grid view and data entry

Each route:
1. Checks authentication/authorization
2. Loads data
3. Handles form submission
4. Renders template or redirects

### Services (app/services/)

Business logic is isolated in service classes:

- **ConsensusService**: Pure calculation, no database access needed
- **AggregationService**: Queries database, performs aggregation
- **DeletionImpactService**: Analyzes deletion impact
- **ValueTypeUsageService**: Checks value type usage

Services are stateless and can be tested independently.

### Templates (app/templates/)

Jinja2 templates follow Bootstrap 5 conventions:
- `base.html`: Master layout with navbar
- Nested templates extend base
- Flash messages displayed automatically
- Forms rendered with WTF macros

### Static Assets (app/static/)

- `css/style.css`: Custom styles (consensus badges, roll-up styling)
- `js/`: Minimal JavaScript for tree expand/collapse (future)

## Testing Strategy

### Test Organization

```
tests/
├── conftest.py              # Fixtures
├── test_auth.py             # Authentication tests
├── test_consensus.py        # Consensus calculation tests
├── test_aggregation.py      # Roll-up aggregation tests
├── test_deletion.py         # Deletion impact tests
└── test_value_type.py       # Value type usage tests
```

### Key Fixtures

```python
@pytest.fixture
def app():
    """Test app with in-memory database"""
    app = create_app('testing')
    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()

@pytest.fixture
def global_admin(app):
    """Create a global admin user"""
    admin = User(login='testadmin', is_global_admin=True)
    admin.set_password('TestPass123')
    db.session.add(admin)
    db.session.commit()
    return admin
```

### Test Coverage

Required test coverage:
- Bootstrap admin creation
- Login validation (valid, invalid, inactive, unassigned org)
- Global admin-only access
- Consensus calculation (all statuses)
- Roll-up aggregation (all levels, formulas)
- Deletion impact (challenge, space, initiative, system)
- Value type usage blocking

## Future Migration Path

### Moving to PostgreSQL

The application is structured to make PostgreSQL migration straightforward:

1. **Change database URL** in config:
   ```python
   SQLALCHEMY_DATABASE_URI = 'postgresql://user:pass@localhost/cisk'
   ```

2. **Remove SQLite-specific code**:
   - Foreign key pragma setting (PostgreSQL has them by default)
   - Connection string `check_same_thread=False`

3. **Test migrations**:
   ```bash
   flask db migrate -m "Initial PostgreSQL migration"
   flask db upgrade
   ```

4. **Add connection pooling** if needed for high concurrency

All business logic remains unchanged.

## Conclusion

CISK Navigator is a well-architected Flask application following best practices:

- **Clean separation of concerns**: Models, forms, routes, services, templates
- **Comprehensive business logic**: Consensus, aggregation, deletion rules
- **Secure by design**: Password hashing, CSRF protection, session management
- **Well-documented**: In-code docstrings and external documentation
- **Test coverage**: Pytest tests for critical functionality
- **Migration-ready**: Structured for future PostgreSQL migration

The architecture supports the complex requirements while remaining maintainable and extensible.

---

For implementation questions or clarification, refer to inline code comments and docstrings throughout the codebase.
