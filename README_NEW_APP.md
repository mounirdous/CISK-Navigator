# CISK Navigator - Local-first Flask + SQLite Application

A comprehensive web application for managing Organizations, Spaces, Challenges, Initiatives, Systems, and KPIs with consensus-based data entry and upward roll-up aggregation.

## What is CISK Navigator?

CISK Navigator is a local-first business planning and tracking application that allows organizations to:

- **Manage hierarchical business structures**: Organizations → Spaces → Challenges → Initiatives → Systems → KPIs
- **Track multiple value types**: Numeric (cost, CO2, licenses) and qualitative (risk, impact)
- **Consensus-based data entry**: Multiple contributors provide opinions, system calculates consensus
- **Upward roll-up aggregation**: Values automatically aggregate up through the hierarchy
- **Safe deletion with impact preview**: See what will be affected before deleting anything
- **Local-first architecture**: Runs entirely on your Windows machine with SQLite, no cloud required

## Key Features

### Authentication & Authorization
- Bootstrap global administrator account (login: `cisk`, password: `Zurich20`)
- Global Administration for managing users and organizations
- Organization-specific workspaces with role-based access
- Multi-organization user support
- Forced password change on first login

### Business Model
- **Flexible structure**: Spaces (seasons, sites, customers) → Challenges → Initiatives → Systems → KPIs
- **Reusable entities**: One initiative can address multiple challenges; one system can support multiple initiatives
- **Context-specific KPIs**: Same system can have different KPIs in different initiative contexts
- **Organization-specific value types**: Each organization defines its own metrics

### Value Types & Aggregation
- **Numeric types**: Cost, Net Value, CO2, licenses, etc. with configurable units and decimal places
- **Qualitative types**: Risk (!, !!, !!!), Positive Impact (★), Negative Impact (▼)
- **Configurable aggregation**: Sum, Min, Max, Avg formulas
- **Upward roll-ups**: KPI → System → Initiative → Challenge → Space with formula overrides

### Consensus Model
- **Multi-contributor**: Named contributors (no account required) provide opinions
- **Automatic status calculation**: No Data, Pending, Strong Consensus, Weak Consensus, No Consensus
- **Roll-up eligibility**: Only strong consensus values participate in upward aggregation

### Safe Deletion
- **Impact preview**: See exactly what will be deleted before confirming
- **Orphan cleanup**: Automatically removes shared entities that become orphaned
- **Value type protection**: Cannot delete value types that are in use
- **Cascade rules**: Deleting a space cascades through challenges, initiatives, systems, and KPIs

## Installation (Windows)

### Prerequisites
- Python 3.11 or higher
- pip (Python package manager)

### Step 1: Clone or Download

Download the project to your local machine.

### Step 2: Create Virtual Environment

```bash
# Open Command Prompt or PowerShell in the project directory
python -m venv venv
```

### Step 3: Activate Virtual Environment

**Command Prompt:**
```bash
venv\Scripts\activate
```

**PowerShell:**
```bash
venv\Scripts\Activate.ps1
```

(If you get an execution policy error in PowerShell, run: `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser`)

### Step 4: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 5: Set Up Environment Variables (Optional)

Copy `.env.example` to `.env` and customize if needed:

```bash
copy .env.example .env
```

Default values work fine for local development.

### Step 6: Initialize Database

The database is created automatically on first run. The application will:
- Create the SQLite database file (`cisk.db`)
- Run all migrations
- Create the bootstrap global administrator account

### Step 7: Run the Application

```bash
python run.py
```

The application will start on `http://localhost:5003`

## First Login

1. Open your browser and go to `http://localhost:5003/auth/login`
2. Log in with the bootstrap admin account:
   - **Login**: `cisk`
   - **Password**: `Zurich20`
   - **Organization**: Select "Global Administration"
3. You will be prompted to change the password
4. After changing the password, you can create organizations and users

## Basic Workflow

### For Global Administrators

1. **Create Organizations**
   - Go to Global Administration → Organizations
   - Create one or more organizations

2. **Create Users**
   - Go to Global Administration → Users
   - Create users and assign them to organizations
   - Set temporary passwords (users must change on first login)

### For Organization Users

1. **Log in to Organization**
   - Select your organization from the dropdown
   - Enter your credentials

2. **Set Up Business Structure**
   - Go to Administration
   - Create Spaces (e.g., "Q1 2024", "Munich Site")
   - Create Challenges within Spaces
   - Create Initiatives (can be linked to multiple Challenges)
   - Create Systems (can be linked to multiple Initiatives)
   - Create KPIs under specific Initiative-System contexts

3. **Define Value Types**
   - Go to Administration → Value Types
   - Create numeric value types (Cost, CO2, etc.)
   - Create qualitative value types (Risk, Impact, etc.)
   - Assign value types to KPIs

4. **Configure Roll-ups**
   - Set which value types roll upward at each level
   - Choose aggregation formulas (sum, avg, min, max)

5. **Enter Data**
   - In the Workspace, navigate to KPI cells
   - Click on a KPI cell to enter contributor opinions
   - System calculates consensus automatically
   - Values roll upward through the hierarchy

## Running Tests

```bash
pytest
```

To run with coverage:

```bash
pytest --cov=app tests/
```

## Project Structure

```
app/
├── __init__.py              # Application factory
├── config.py                # Configuration
├── extensions.py            # Flask extensions
├── run.py                   # Application entry point
├── models/                  # Database models
│   ├── user.py
│   ├── organization.py
│   ├── space.py
│   ├── challenge.py
│   ├── initiative.py
│   ├── system.py
│   ├── kpi.py
│   ├── value_type.py
│   ├── contribution.py
│   └── rollup_rule.py
├── forms/                   # WTForms
├── routes/                  # Blueprints
│   ├── auth.py
│   ├── global_admin.py
│   ├── organization_admin.py
│   └── workspace.py
├── services/                # Business logic
│   ├── consensus_service.py
│   ├── aggregation_service.py
│   ├── deletion_impact_service.py
│   └── value_type_usage_service.py
├── templates/               # HTML templates
└── static/                  # CSS, JS, images
```

## Database Schema

The application uses SQLite with the following main tables:

- **users**: User accounts and permissions
- **organizations**: Organization definitions
- **user_organization_memberships**: User-to-organization assignments
- **spaces**: Top-level groupings (seasons, sites, etc.)
- **challenges**: Business challenges within spaces
- **initiatives**: Reusable initiatives (many-to-many with challenges)
- **systems**: Reusable systems (many-to-many with initiatives)
- **kpis**: Key performance indicators (context-specific)
- **value_types**: Organization-specific metrics
- **contributions**: Contributor opinions for KPI cells
- **rollup_rules**: Configuration for upward aggregation

## Security Notes

- **Passwords**: Always hashed using Werkzeug's password hashing (PBKDF2)
- **CSRF Protection**: Enabled on all forms via Flask-WTF
- **Foreign Keys**: SQLite foreign keys are explicitly enabled
- **Transactions**: All destructive operations use database transactions
- **Bootstrap Admin**: Must change password on first login

## Troubleshooting

### "Database is locked" error
- Close other applications accessing the database
- Ensure only one instance of the application is running

### Cannot log in after password change
- Clear your browser cookies
- Try logging out completely and logging in again

### Port 5003 already in use
- Edit `run.py` and change the port number
- Or set the `PORT` environment variable

## Future Enhancements

For V2, consider:
- Migrating from SQLite to PostgreSQL for multi-user concurrent access
- Adding REST API for external integrations
- Implementing more granular permissions (read-only, editor roles)
- Adding data export (Excel, CSV)
- Adding visual dashboards and charts
- Implementing drag-and-drop reordering
- Adding audit logs for data changes

## License

MIT License - Free for personal and commercial use

## Support

For technical questions, see the detailed ARCHITECTURE.md file.

---

**Version 1.0** - Local-first Flask + SQLite CISK Navigator
