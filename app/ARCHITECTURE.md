# CISK Navigator - Technical Architecture

**Version 1.8**
**Date: March 6, 2026**

## Table of Contents

1. [Overview](#overview)
2. [Technology Stack](#technology-stack)
3. [Application Structure](#application-structure)
4. [Data Model](#data-model)
5. [Business Logic Services](#business-logic-services)
6. [Route Organization](#route-organization)
7. [Authentication Flow](#authentication-flow)
8. [Frontend Architecture](#frontend-architecture)
9. [Database Schema](#database-schema)
10. [Deployment Architecture](#deployment-architecture)

## Overview

CISK Navigator is a Flask-based web application following the **application factory pattern** with modular blueprints. It uses SQLite for local development with a clear migration path to PostgreSQL for production.

### Architectural Principles
- **Separation of Concerns**: Models, forms, routes, services, templates are cleanly separated
- **Service Layer**: Business logic isolated in stateless service classes
- **Blueprint-Based**: Routes organized by functional area
- **ORM-First**: All database access through SQLAlchemy ORM
- **Template-Based**: Server-side rendering with Jinja2
- **Progressive Enhancement**: JavaScript for interactivity, works without JS

## Technology Stack

### Backend
```
Python 3.11+
├── Flask 3.0.0              # Web framework
├── Flask-SQLAlchemy 3.1.1   # ORM
├── Flask-Migrate 4.0.5      # Database migrations
├── Flask-Login 0.6.3        # Session management
├── Flask-WTF 1.2.1          # Forms & CSRF
├── SQLAlchemy 2.0.48        # Database toolkit
├── Werkzeug 3.0.0           # Password hashing
└── Gunicorn 20.1.0          # Production server
```

### Frontend
```
Bootstrap 5.3.0              # UI framework (CDN)
Vanilla JavaScript           # Interactivity (tree expand/collapse)
HTML5 + Jinja2               # Templates
CSS3                         # Custom styles
```

### Database
```
Development: SQLite 3
Production: PostgreSQL 13+ (migration-ready)
```

### Development Tools
```
Python venv                  # Virtual environment
Flask CLI                    # Development server
Flask-Migrate                # Schema migrations
```

## Application Structure

### Directory Layout
```
app/
├── __init__.py                    # Application factory
├── config.py                      # Configuration classes
├── extensions.py                  # Extension instances
│
├── models/                        # SQLAlchemy models
│   ├── __init__.py               # Model exports
│   ├── user.py                   # User, UserOrganizationMembership
│   ├── organization.py           # Organization
│   ├── space.py                  # Space
│   ├── challenge.py              # Challenge
│   ├── initiative.py             # Initiative, ChallengeInitiativeLink
│   ├── system.py                 # System, InitiativeSystemLink
│   ├── kpi.py                    # KPI
│   ├── value_type.py             # ValueType, KPIValueTypeConfig
│   ├── contribution.py           # Contribution
│   └── rollup_rule.py            # RollupRule
│
├── forms/                         # WTForms
│   ├── __init__.py
│   ├── auth_forms.py             # LoginForm, ChangePasswordForm
│   ├── user_forms.py             # UserCreateForm, UserEditForm
│   ├── organization_forms.py    # OrganizationCreateForm, OrganizationEditForm
│   ├── space_forms.py            # SpaceCreateForm, SpaceEditForm
│   ├── challenge_forms.py        # ChallengeCreateForm, ChallengeEditForm
│   ├── initiative_forms.py       # InitiativeCreateForm, InitiativeEditForm
│   ├── system_forms.py           # SystemCreateForm, SystemEditForm
│   ├── kpi_forms.py              # KPICreateForm, KPIEditForm
│   ├── value_type_forms.py       # ValueTypeCreateForm, ValueTypeEditForm
│   └── contribution_forms.py     # ContributionForm
│
├── routes/                        # Flask Blueprints
│   ├── __init__.py
│   ├── auth.py                   # /auth/* - Authentication
│   ├── global_admin.py           # /global-admin/* - User & org management
│   ├── organization_admin.py    # /org-admin/* - Structure management
│   └── workspace.py              # /workspace/* - Tree/grid & data entry
│
├── services/                      # Business logic
│   ├── __init__.py
│   ├── consensus_service.py      # Consensus calculation
│   ├── aggregation_service.py    # Roll-up aggregation
│   ├── deletion_impact_service.py # Deletion analysis
│   └── value_type_usage_service.py # Usage checking
│
├── templates/                     # Jinja2 templates
│   ├── base.html                 # Master layout
│   ├── auth/
│   │   ├── login.html            # Step 1: Username/password
│   │   ├── login_step2.html      # Step 2: Organization selection
│   │   └── change_password.html
│   ├── global_admin/
│   │   ├── index.html
│   │   ├── users.html
│   │   ├── create_user.html
│   │   ├── edit_user.html
│   │   ├── organizations.html
│   │   ├── create_organization.html
│   │   └── edit_organization.html
│   ├── organization_admin/
│   │   ├── index.html
│   │   ├── spaces.html           # Full hierarchy view
│   │   ├── create_space.html
│   │   ├── edit_space.html
│   │   ├── create_challenge.html
│   │   ├── edit_challenge.html
│   │   ├── create_initiative.html
│   │   ├── edit_initiative.html
│   │   ├── create_system.html
│   │   ├── edit_system.html
│   │   ├── create_kpi.html
│   │   ├── edit_kpi.html
│   │   ├── value_types.html
│   │   ├── create_value_type.html
│   │   └── delete_value_type_check.html
│   └── workspace/
│       ├── index.html            # Tree/grid workspace
│       └── kpi_cell_detail.html  # KPI data entry
│
└── static/
    └── css/
        └── style.css             # Custom styles
```

### Application Factory

Located in `app/__init__.py`:

```python
def create_app(config_name='default'):
    app = Flask(__name__)

    # Load configuration
    app.config.from_object(config[config_name])

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)

    # Configure login manager
    login_manager.login_view = 'auth.login'

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # Register blueprints
    from app.routes import auth, global_admin, organization_admin, workspace
    app.register_blueprint(auth.bp)
    app.register_blueprint(global_admin.bp)
    app.register_blueprint(organization_admin.bp)
    app.register_blueprint(workspace.bp)

    # Create tables and bootstrap admin
    with app.app_context():
        db.create_all()
        _bootstrap_admin()

    return app
```

### Configuration

Located in `app/config.py`:

```python
class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key'
    SQLALCHEMY_DATABASE_URI = 'sqlite:///cisk_navigator.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'connect_args': {'check_same_thread': False},
        'pool_pre_ping': True,
    }

class DevelopmentConfig(Config):
    DEBUG = True

class ProductionConfig(Config):
    DEBUG = False
    # PostgreSQL in production:
    # SQLALCHEMY_DATABASE_URI = 'postgresql://user:pass@localhost/cisk'

class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
```

## Data Model

### Entity-Relationship Overview

```
User ←──────┐
            │
            ├─→ UserOrganizationMembership ──→ Organization
            │                                       │
            │                                       ├─→ Space
            │                                       │    └─→ Challenge
            │                                       │         └─→ ChallengeInitiativeLink ──→ Initiative
            │                                       │                                              │
            │                                       │                                              └─→ InitiativeSystemLink ──→ System
            │                                       │                                                       │
            │                                       ├─→ ValueType ←──────────────────────────┐             └─→ KPI
            │                                       │                                         │                  │
            │                                       ├─→ Initiative                            └─→ KPIValueTypeConfig
            │                                       │                                                      │
            │                                       └─→ System                                             └─→ Contribution
```

### Core Models

#### User
```python
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    login = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), nullable=True)
    display_name = db.Column(db.String(120), nullable=True)
    password_hash = db.Column(db.String(255), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    is_global_admin = db.Column(db.Boolean, default=False)
    must_change_password = db.Column(db.Boolean, default=False)

    # Relationships
    organization_memberships = db.relationship('UserOrganizationMembership', ...)
```

#### Organization
```python
class Organization(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), unique=True, nullable=False)
    description = db.Column(db.Text)
    is_active = db.Column(db.Boolean, default=True)

    # Relationships to all organization-scoped entities
    spaces = db.relationship('Space', back_populates='organization', cascade='all, delete-orphan')
    challenges = db.relationship('Challenge', ...)
    initiatives = db.relationship('Initiative', ...)
    systems = db.relationship('System', ...)
    value_types = db.relationship('ValueType', ...)
```

#### Space → Challenge → Initiative → System → KPI Chain

**Space**:
```python
class Space(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    organization_id = db.Column(db.Integer, db.ForeignKey('organizations.id'), nullable=False)
    name = db.Column(db.String(200), nullable=False)
    space_label = db.Column(db.String(100))  # "Season", "Site", etc.
    display_order = db.Column(db.Integer, default=0)

    challenges = db.relationship('Challenge', back_populates='space')
```

**Challenge**:
```python
class Challenge(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    organization_id = db.Column(db.Integer, db.ForeignKey('organizations.id'))
    space_id = db.Column(db.Integer, db.ForeignKey('spaces.id'))
    name = db.Column(db.String(200), nullable=False)
    display_order = db.Column(db.Integer, default=0)

    space = db.relationship('Space', back_populates='challenges')
    initiative_links = db.relationship('ChallengeInitiativeLink', ...)
```

**ChallengeInitiativeLink** (Many-to-Many):
```python
class ChallengeInitiativeLink(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    challenge_id = db.Column(db.Integer, db.ForeignKey('challenges.id'))
    initiative_id = db.Column(db.Integer, db.ForeignKey('initiatives.id'))
    display_order = db.Column(db.Integer, default=0)

    __table_args__ = (
        db.UniqueConstraint('challenge_id', 'initiative_id'),
    )

    challenge = db.relationship('Challenge', back_populates='initiative_links')
    initiative = db.relationship('Initiative', back_populates='challenge_links')
```

**Initiative**:
```python
class Initiative(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    organization_id = db.Column(db.Integer, db.ForeignKey('organizations.id'))
    name = db.Column(db.String(200), nullable=False)

    challenge_links = db.relationship('ChallengeInitiativeLink', ...)
    system_links = db.relationship('InitiativeSystemLink', ...)
```

**InitiativeSystemLink** (Many-to-Many):
```python
class InitiativeSystemLink(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    initiative_id = db.Column(db.Integer, db.ForeignKey('initiatives.id'))
    system_id = db.Column(db.Integer, db.ForeignKey('systems.id'))
    display_order = db.Column(db.Integer, default=0)

    __table_args__ = (
        db.UniqueConstraint('initiative_id', 'system_id'),
    )

    initiative = db.relationship('Initiative', back_populates='system_links')
    system = db.relationship('System', back_populates='initiative_links')
    kpis = db.relationship('KPI', back_populates='initiative_system_link')  # ← KPIs here!
```

**System**:
```python
class System(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    organization_id = db.Column(db.Integer, db.ForeignKey('organizations.id'))
    name = db.Column(db.String(200), nullable=False)

    initiative_links = db.relationship('InitiativeSystemLink', ...)
```

**KPI** (Context-Specific):
```python
class KPI(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    initiative_system_link_id = db.Column(db.Integer,
        db.ForeignKey('initiative_system_links.id'), nullable=False)
    name = db.Column(db.String(200), nullable=False)
    display_order = db.Column(db.Integer, default=0)

    initiative_system_link = db.relationship('InitiativeSystemLink', back_populates='kpis')
    value_type_configs = db.relationship('KPIValueTypeConfig', ...)
```

#### Value Type System

**ValueType**:
```python
class ValueType(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    organization_id = db.Column(db.Integer, db.ForeignKey('organizations.id'))
    name = db.Column(db.String(200), nullable=False)
    kind = db.Column(db.String(50), nullable=False)  # 'numeric', 'risk', 'positive_impact', 'negative_impact'
    numeric_format = db.Column(db.String(20))  # 'integer', 'decimal'
    decimal_places = db.Column(db.Integer, default=2)
    unit_label = db.Column(db.String(50))  # '€', 'tCO2e', etc.
    default_aggregation_formula = db.Column(db.String(20), default='sum')
    display_order = db.Column(db.Integer, default=0)
    is_active = db.Column(db.Boolean, default=True)

    kpi_configs = db.relationship('KPIValueTypeConfig', ...)
```

**KPIValueTypeConfig**:
```python
class KPIValueTypeConfig(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    kpi_id = db.Column(db.Integer, db.ForeignKey('kpis.id'))
    value_type_id = db.Column(db.Integer, db.ForeignKey('value_types.id'))
    display_order = db.Column(db.Integer, default=0)

    kpi = db.relationship('KPI', back_populates='value_type_configs')
    value_type = db.relationship('ValueType', back_populates='kpi_configs')
    contributions = db.relationship('Contribution', ...)

    def get_consensus_value(self):
        """Get consensus calculation for this KPI cell"""
        from app.services import ConsensusService
        return ConsensusService.get_cell_value(self)
```

**Contribution**:
```python
class Contribution(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    kpi_value_type_config_id = db.Column(db.Integer,
        db.ForeignKey('kpi_value_type_configs.id'))
    contributor_name = db.Column(db.String(200), nullable=False)
    numeric_value = db.Column(db.Numeric(precision=18, scale=4))
    qualitative_level = db.Column(db.Integer)  # 1, 2, or 3
    comment = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)

    kpi_value_type_config = db.relationship('KPIValueTypeConfig', back_populates='contributions')
```

## Business Logic Services

### ConsensusService

Located in `app/services/consensus_service.py`.

**Responsibility**: Calculate consensus status from contributions.

```python
class ConsensusService:
    STATUS_NO_DATA = 'no_data'
    STATUS_PENDING = 'pending'
    STATUS_STRONG = 'strong'
    STATUS_WEAK = 'weak'
    STATUS_NO_CONSENSUS = 'no_consensus'

    @staticmethod
    def calculate_consensus(contributions):
        """
        Returns:
            {
                'status': str,
                'value': numeric or int or None,
                'count': int,
                'is_rollup_eligible': bool
            }
        """
        # Implementation: See SPECIFICATIONS.md
```

**Key Rule**: Only `STATUS_STRONG` with `is_rollup_eligible=True` participates in roll-ups.

### AggregationService

Located in `app/services/aggregation_service.py`.

**Responsibility**: Roll up values through hierarchy levels.

```python
class AggregationService:
    @staticmethod
    def get_kpi_to_system_rollup(initiative_system_link, value_type_id):
        """Roll up KPI values to system level"""

    @staticmethod
    def get_system_to_initiative_rollup(initiative_id, value_type_id):
        """Roll up system values to initiative level"""

    @staticmethod
    def get_initiative_to_challenge_rollup(challenge_id, value_type_id):
        """Roll up initiative values to challenge level"""

    @staticmethod
    def get_challenge_to_space_rollup(space_id, value_type_id):
        """Roll up challenge values to space level"""
```

Uses Value Type's `default_aggregation_formula` (sum, min, max, avg).

### DeletionImpactService

Located in `app/services/deletion_impact_service.py`.

**Responsibility**: Analyze deletion impact before actual deletion.

```python
class DeletionImpactService:
    @staticmethod
    def analyze_challenge_deletion(challenge_id):
        """Returns dict with counts of affected entities"""

    @staticmethod
    def analyze_space_deletion(space_id):
        """Returns dict with counts of affected entities"""
```

Handles orphan cleanup: If an Initiative or System becomes orphaned after deletion, it's also deleted.

### ValueTypeUsageService

Located in `app/services/value_type_usage_service.py`.

**Responsibility**: Check if ValueType can be safely deleted.

```python
class ValueTypeUsageService:
    @staticmethod
    def can_delete(value_type_id):
        """Returns (can_delete: bool, reason: str)"""

    @staticmethod
    def check_usage(value_type_id):
        """Returns detailed usage info"""
```

## Route Organization

### Blueprint Structure

#### auth.bp (`/auth`)
- `/login` GET, POST - Two-step login
- `/logout` GET - Logout
- `/change-password` GET, POST - Forced password change

#### global_admin.bp (`/global-admin`)
- `/` - Dashboard
- `/users` - List users
- `/users/create` - Create user
- `/users/<id>/edit` - Edit user
- `/users/<id>/delete` - Delete user
- `/organizations` - List organizations
- `/organizations/create` - Create organization
- `/organizations/<id>/edit` - Edit organization

#### organization_admin.bp (`/org-admin`)
- `/` - Dashboard with stats
- `/spaces` - List spaces (full hierarchy view)
- `/spaces/create` - Create space
- `/spaces/<id>/edit` - Edit space
- `/spaces/<id>/delete` - Delete space
- `/spaces/<space_id>/challenges/create` - Create challenge
- `/challenges/<id>/edit` - Edit challenge
- `/challenges/<challenge_id>/initiatives/create` - Create initiative (linked)
- `/initiatives/<id>/edit` - Edit initiative
- `/initiatives/<initiative_id>/systems/create` - Create system (linked)
- `/systems/<id>/edit` - Edit system
- `/initiative-system-links/<link_id>/kpis/create` - Create KPI
- `/kpis/<id>/edit` - Edit KPI
- `/value-types` - List value types
- `/value-types/create` - Create value type
- `/value-types/<id>/delete-check` - Check deletion impact

#### workspace.bp (`/workspace`)
- `/` - Tree/grid workspace
- `/kpi/<kpi_id>/value-type/<vt_id>` - KPI cell detail & data entry
- `/api/rollup/<entity_type>/<entity_id>/<value_type_id>` - Roll-up API

## Authentication Flow

### Two-Step Login (v1.8)

**Step 1: Username/Password** (`/auth/login` GET)
```
User → Enter username & password → POST → Validate credentials
                                              ↓
                                    Store user_id in session['_temp_user_id']
                                              ↓
                                         Redirect to Step 2
```

**Step 2: Organization Selection** (`/auth/login` GET with `_temp_user_id`)
```
Load user from temp session
    ↓
Filter organizations by user access
    ↓
Render selection form
    ↓
User selects organization OR checks "admin" checkbox
    ↓
POST → Validate access → login_user() → Clear temp session
                              ↓
                    Redirect to workspace or global admin
```

### Session State
```python
session['_temp_user_id']       # Temporary during 2-step login
session['organization_id']     # Current org ID or None for global admin
session['organization_name']   # Display name
current_user                   # Flask-Login user object
```

### Route Protection

**Login Required**:
```python
@bp.route('/some-route')
@login_required  # Flask-Login decorator
def some_route():
    # current_user is authenticated
```

**Organization Context Required**:
```python
@bp.route('/workspace')
@login_required
@organization_required  # Custom decorator
def workspace():
    org_id = session.get('organization_id')  # Guaranteed not None
```

## Frontend Architecture

### Template Inheritance

```
base.html                      # Master template
    ├── Navbar (dynamic based on role)
    ├── Flash messages
    ├── Content block
    └── JavaScript libraries

auth/login.html extends base
auth/login_step2.html extends base
workspace/index.html extends base
organization_admin/spaces.html extends base
... etc
```

### JavaScript Components

**Tree Expand/Collapse** (`workspace/index.html`):
```javascript
// Handle expand/collapse icons
document.querySelectorAll('.expand-icon').forEach(icon => {
    icon.addEventListener('click', function(e) {
        // Toggle icon ▶ ↔ ▼
        // Show/hide children via data attributes
        // Recursive collapse for nested children
    });
});

// Expand All button
document.getElementById('expand-all').addEventListener('click', () => {
    // Expand all levels
});

// Collapse All button
document.getElementById('collapse-all').addEventListener('click', () => {
    // Collapse all levels
});
```

**Edit Contribution Pre-fill** (`workspace/kpi_cell_detail.html`):
```javascript
document.querySelectorAll('.edit-contrib').forEach(button => {
    button.addEventListener('click', function() {
        // Extract data from button attributes
        // Pre-populate form fields
        // Scroll to form
    });
});
```

**Dynamic Form Fields** (`organization_admin/create_value_type.html`):
```javascript
const kindSelect = document.getElementById('kind-select');

kindSelect.addEventListener('change', function() {
    const isNumeric = this.value === 'numeric';
    // Show/hide numeric-only fields
    document.querySelectorAll('.numeric-only').forEach(field => {
        field.style.display = isNumeric ? 'block' : 'none';
    });
});
```

### CSS Architecture

**Custom Styles** (`static/css/style.css`):
```css
/* Consensus badges */
.consensus-strong { background-color: #198754 !important; }
.consensus-weak { background-color: #ffc107 !important; }
.consensus-pending { background-color: #0dcaf0 !important; }
.consensus-no_consensus { background-color: #dc3545 !important; }
.consensus-no-data { background-color: #6c757d !important; }

/* KPI cell hover effect */
.kpi-cell:hover {
    background-color: #fff3cd !important;
    transition: background-color 0.2s;
}
```

## Database Schema

### Foreign Key Relationships

```
organizations (1) ─────┬──────→ (N) spaces
                       ├──────→ (N) challenges
                       ├──────→ (N) initiatives
                       ├──────→ (N) systems
                       ├──────→ (N) value_types
                       └──────→ (N) user_organization_memberships

spaces (1) ────────────→ (N) challenges

challenges (1) ────────→ (N) challenge_initiative_links (M:N table)

challenge_initiative_links:
    - challenge_id (FK)
    - initiative_id (FK)
    - UNIQUE (challenge_id, initiative_id)

initiatives (1) ───────→ (N) initiative_system_links (M:N table)

initiative_system_links:
    - initiative_id (FK)
    - system_id (FK)
    - UNIQUE (initiative_id, system_id)
    └──────────────────→ (N) kpis  ← KPIs belong here!

kpis (1) ──────────────→ (N) kpi_value_type_configs

kpi_value_type_configs:
    - kpi_id (FK)
    - value_type_id (FK)
    └──────────────────→ (N) contributions

users (1) ─────────────→ (N) user_organization_memberships
```

### Cascade Delete Rules

```
Organization DELETE → CASCADE all owned entities
Space DELETE → CASCADE challenges
Challenge DELETE → CASCADE challenge_initiative_links
                → ORPHAN CHECK initiatives
Initiative DELETE → CASCADE initiative_system_links
                  → ORPHAN CHECK systems
InitiativeSystemLink DELETE → CASCADE kpis
KPI DELETE → CASCADE kpi_value_type_configs
KPIValueTypeConfig DELETE → CASCADE contributions
```

### Indexes

```
users.login               # UNIQUE INDEX (for fast login lookup)
organizations.name        # UNIQUE INDEX
challenge_initiative_links (challenge_id, initiative_id)  # UNIQUE COMPOSITE
initiative_system_links (initiative_id, system_id)        # UNIQUE COMPOSITE
```

## Deployment Architecture

### Development
```
Flask Development Server
├── Port: 5003
├── Debug: True
├── Database: SQLite (cisk_navigator.db)
└── Auto-reload: True
```

### Production
```
Gunicorn (WSGI Server)
├── Workers: 4
├── Port: 5003
├── Database: PostgreSQL
└── Reverse Proxy: Nginx (optional)
```

### Migration to PostgreSQL

**Step 1**: Update config
```python
SQLALCHEMY_DATABASE_URI = 'postgresql://user:pass@localhost/cisk_navigator'
```

**Step 2**: Remove SQLite-specific settings
```python
# Remove:
# 'check_same_thread': False
```

**Step 3**: Create PostgreSQL database
```bash
createdb cisk_navigator
```

**Step 4**: Run migrations
```bash
flask db upgrade
```

All business logic remains unchanged.

### Environment Variables

```bash
# Required
SECRET_KEY=random-secret-key-here

# Optional (defaults to SQLite)
DATABASE_URL=postgresql://user:pass@host/db

# Optional (defaults to 'default')
FLASK_CONFIG=production
```

## Code Quality & Best Practices

### Models
- Use `__tablename__` explicitly
- Add docstrings explaining entity purpose
- Use `db.relationship` for ORM navigation
- Enforce constraints at database level

### Forms
- One form per create/edit operation
- Use appropriate validators (DataRequired, Length, etc.)
- Use `InputRequired()` for fields that can be 0 or falsy

### Routes
- Keep routes thin - delegate to services
- Use decorators for authorization
- Flash messages for user feedback
- Redirect after POST to prevent re-submission

### Services
- Stateless classes
- Static methods
- No direct Flask context (no `session`, `request`)
- Pure business logic

### Templates
- Extend `base.html`
- Use Bootstrap 5 classes
- Minimal inline JavaScript
- Auto-escape enabled (XSS protection)

### Security
- Password hashing with Werkzeug
- CSRF protection on all forms (Flask-WTF)
- Session-based authentication (Flask-Login)
- SQL injection prevention (SQLAlchemy ORM)
- Organization isolation enforced at query level

## Testing Strategy

### Unit Tests
- Services (consensus, aggregation)
- Models (relationships, methods)
- Forms (validation)

### Integration Tests
- Authentication flow
- CRUD operations
- Deletion impact
- Consensus calculation with database

### Fixtures
```python
@pytest.fixture
def app():
    app = create_app('testing')
    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()

@pytest.fixture
def client(app):
    return app.test_client()
```

## Performance Considerations

### Query Optimization
- Use `db.relationship` with lazy loading
- Eager load when needed: `.options(joinedload(...))`
- Index foreign keys
- Avoid N+1 queries

### Caching (Future)
- Roll-up results caching
- Session-based organization context
- Template fragment caching

### Scalability
- SQLite adequate for single-organization use
- PostgreSQL for multi-tenant production
- Connection pooling for high concurrency
- Consider read replicas for reporting

## Monitoring & Logging

### Logging
```python
# Debug login flow
current_app.logger.info("LOGIN ATTEMPT")
current_app.logger.error("VALIDATION FAILED")
```

### Metrics (Future)
- Request duration
- Database query time
- Consensus calculation time
- User activity tracking

## Future Architecture Enhancements

1. **API Layer**: RESTful API for integrations
2. **Async Tasks**: Celery for background jobs
3. **Real-time Updates**: WebSockets for live collaboration
4. **Multi-tenancy**: Schema per tenant or shared schema with tenant_id
5. **Microservices**: Split consensus/aggregation into separate service
6. **Caching**: Redis for roll-up results
7. **Search**: Elasticsearch for full-text search
8. **Analytics**: Data warehouse integration

---

**Document Version**: 1.8
**Last Updated**: March 6, 2026
**Maintained By**: CISK Navigator Team
