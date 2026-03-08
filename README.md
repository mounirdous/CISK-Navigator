# 🧭 CISK Navigator v1.14.1

**Production-ready data collection and aggregation system** for tracking KPIs across hierarchical organization structures.

![Version](https://img.shields.io/badge/version-1.14.1-blue)
![Python](https://img.shields.io/badge/python-3.11+-green)
![Database](https://img.shields.io/badge/database-PostgreSQL-blue)
![License](https://img.shields.io/badge/license-MIT-orange)

## ✨ What's New in v1.14 (March 2026)

### 🐛 **Bug Fixes** (v1.14.1)
- **Level Toggle Fixes**: Pills now properly toggle colors (blue/gray) and rows hide/show correctly
- **Dark Mode Improvements**: Better contrast and restored indentation hierarchy for readability
- **CSRF Error Fix**: Governance body creation now works without 500 errors

### 🎨 **Modern Workspace UI** (v1.14.0)
- **True Dark Mode**: Deep background with high contrast for reduced eye strain
- **Modern Toolbar**: Compact design with gradient background and pill-shaped interactive filters
- **Level Visibility Controls**: Toggle display of any hierarchy level (Spaces, Challenges, Initiatives, Systems, KPIs)
- **Visual Hierarchy**: Icons (🏢🎯💡⚙️📊) and color-coded borders for each level
- **Enhanced UX**: Sticky headers, smooth animations, rollup indicators (Σ symbol)
- **Smart Filters**: Governance bodies and archive filters with instant feedback
- **Quick Stats**: Real-time display of active filters and entity counts

## ✨ What's New in v1.13 (March 2026)

### 🏛️ **Governance Bodies** (v1.13.0)
- **Committee/Board Management**: Create and manage governance bodies that oversee KPIs
- **Visual Identity**: Each body has name, abbreviation, color, and description
- **Many-to-Many Links**: KPIs can belong to multiple governance bodies
- **Workspace Filtering**: Filter KPIs by governance body with color-coded pill badges
- **Default Body**: Every organization gets a "General" governance body (renamable, not deletable)
- **Permissions**: New `can_manage_governance_bodies` permission control
- **Drag-to-Reorder**: Customize display order of governance bodies
- **Full CRUD**: Create, edit, delete (except default) with complete audit trail

### 🗄️ **KPI Archiving** (v1.13.0)
- **Archive Inactive KPIs**: Preserve historical data without cluttering workspace
- **Audit Trail**: Tracks who archived and when
- **Read-Only Mode**: Archived KPIs cannot accept new contributions
- **Toggle Visibility**: "Show Archived KPIs" filter to view when needed
- **Visual Distinction**: Grayed out with archive badge
- **Easy Restore**: Unarchive anytime to make KPI active again
- **Data Preservation**: All contributions, snapshots, and comments retained

## ✨ What's New in v1.12 (March 2026)

### 🔐 **Per-Organization User Permissions** (v1.12.0)
- **Granular Access Control**: Control what users can create/edit/delete on a per-organization basis
- **6 Permission Types**: Spaces, Value Types, Challenges, Initiatives, Systems, KPIs
- **Organization-Specific**: Same user can have different permissions in different organizations
- **UI Integration**: Buttons automatically hidden when user lacks permission
- **URL Protection**: Direct URL access blocked with friendly error message
- **Global Admin Bypass**: Global administrators always have full access
- **Easy Management**: Checkbox interface during user creation/editing
- **Backward Compatible**: All existing users get full permissions by default

### 👤 **User Profile Management** (v1.11.9-v1.11.10)
- **Profile Page**: View and edit display name and email
- **Password Management**: Improved password change flow with manual "Force Password Change" control
- **Bug Fixes**: Fixed password auto-population issue that caused unintended resets
- **Better UX**: Organization assignment now uses checkboxes instead of multi-select dropdown

## ✨ What's New in v1.11 (March 2026)

### 🔄 **Smart Value Entry** (v1.10.0+)
- **Intelligent Mode Selection**: When entering a value on a cell with existing consensus, choose your intent:
  - **"NEW data (time evolved)"**: Auto-creates snapshot of current value, then replaces all contributions with new value
  - **"Contributing to CURRENT period"**: Adds contribution normally without creating snapshot
- **Automatic Snapshot Creation**: Historical values preserved when time moves forward
- **Clean Value Evolution**: Single contributor can update values without creating "low consensus"
- **No Data Loss**: Every value change optionally preserved in snapshot history

### 🎯 **Target Tracking** (v1.11.0+)
- **Set Targets**: Optional target value and date for any KPI
- **Visual Progress**: Progress indicator (🎯 X%) displayed in workspace grid
- **Chart Integration**: Target shown as horizontal dashed red line on trend charts
- **Flexible Tracking**: Different targets for different KPIs, even with same value type
- **Baseline Support**: Reference snapshot as starting point for progress measurement

### 🗑️ **Delete Functionality** (v1.10.1+)
- **Complete CRUD**: Delete operations for KPIs, Systems, Initiatives, and Challenges
- **Inline Deletion**: Delete buttons directly in list views
- **Confirmation Dialogs**: Prevents accidental deletions
- **Cascade Handling**: Related entities handled appropriately

### 📊 **Chart Improvements** (v1.11.6-v1.11.7)
- **Current Value Included**: Charts now show historical snapshots + current value
- **Same-Day Snapshots**: Multiple snapshots on same day display as separate points
- **Full Timestamps**: Uses HH:MM:SS for precise time series display
- **Better History**: Up to 50 data points displayed on charts

## ✨ What's New in v2.1 (March 2026)

### 📊 **Dashboard & Overview**
- **Interactive Dashboard**: Statistics cards, quick actions, recent activity
- **Recent Snapshots Widget**: Last 5 snapshots with View/Compare buttons
- **Recent Comments Widget**: Latest discussions across all KPIs
- **Quick Actions**: One-click access to create snapshots, export data, view mentions

### 📈 **Time-Series Tracking**
- **Snapshots**: Capture KPI values at specific points in time
- **Historical View**: View workspace state as of any snapshot date
- **Trend Indicators**: Automatic ↗️↘️→ indicators on KPI cells
- **Snapshot Comparison**: Side-by-side comparison of any two snapshots
- **Labels**: Organize snapshots with custom labels ("Q1 2026", "Sprint 5", "Baseline")

### 📉 **Charts & Visualization**
- **Trend Charts**: Interactive line charts showing KPI history over time (Chart.js)
- **Tooltips**: Hover for exact values and dates
- **Auto-refresh**: Update charts with latest snapshot data
- **Responsive Design**: Charts adapt to screen size

### 💬 **Comments & Collaboration**
- **Cell-Level Comments**: Discuss KPI values with your team
- **@Mention System**: Notify users with @username autocomplete
- **Threaded Replies**: Full conversation threading with indentation
- **Resolve Discussions**: Mark conversations as complete
- **Unread Mentions**: Bell notification (🔔) with unread count
- **Real-time Updates**: See latest comments on dashboard

### 🎨 **Enhanced Navigation**
- **Three-Tier Nav**: Dashboard → Workspace → Administration
- **Bootstrap Icons**: Visual cues for all navigation items
- **Logo Redirect**: Click logo to return to Dashboard
- **Contextual Buttons**: Dashboard button on every page

## ✨ What's in v2.0

### 🎨 **Flexible Color System**
- Colors configured per KPI, not per value type
- Same value type (e.g., "Cost") can have different meanings in different KPIs
- Colors propagate through all rollup levels automatically

### 🗄️ **PostgreSQL Database**
- Data persists across deployments
- Production-ready for real use
- Support for concurrent users
- Automatic migrations

### 📊 **Enhanced Aggregation**
- **6 Aggregation Formulas**: sum, min, max, avg, median (outlier-resistant), count (quantities)
- **Median**: Better than average when data has outliers
- **Count**: Track "how many" metrics (e.g., number of systems integrated)

### 🎭 **New Value Types**
- **Level (●●●)**: Generic 3-level for readiness, maturity, quality, preparedness
- **Sentiment (☹️😐😊)**: Emotional states for morale, satisfaction, stakeholder feelings
- **3-Level Design**: Easier consensus than 5-level scales

### 📤 **Export & Backup**
- **Excel Export**: Hierarchical with row grouping and color coding (outline levels 1-5)
- **YAML Export/Import**: Complete structure backup and restore
- **Organization Cloning**: Create test/training environments from production

### 🎯 **Enhanced UX**
- **Drag-and-Drop Reordering**: Reorder value types to control workspace column order
- **Smart Deletion**: Impact preview before deleting (shows orphaned vs. preserved entities)
- **Visual Hierarchy**: Improved tree navigation with expand/collapse

### 🛡️ **Data Loss Prevention**
- Multi-layer safety checks to prevent accidental database resets
- Startup validation of DATABASE_URL in production
- Database creation guards (no SQLite in production)
- Automatic migration enforcement

### 🚀 **Production Deployment**
- Deployed on Render with persistent PostgreSQL
- Zero downtime deployments
- Automatic database migrations

## 🎯 Features

### Core Capabilities
- **📊 Hierarchical Data Model**: Spaces → Challenges → Initiatives → Systems → KPIs
- **👥 Consensus-Based Input**: Multiple contributors, automatic consensus calculation
- **📈 Automatic Roll-ups**: Values aggregate up the hierarchy with 6 formulas (sum, avg, min, max, median, count)
- **🎨 Flexible Color Configuration**: Sign-based colors (positive/negative/zero) per KPI
- **🔢 6 Value Types**: Numeric, Risk, Positive/Negative Impact, Level, Sentiment
- **🏢 Multi-Organization**: Complete data isolation between organizations
- **👤 User Management**: Global admins, organization members, access control
- **📤 Export Options**: Excel (hierarchical), YAML (structure backup), Organization cloning
- **🎯 Smart Deletion**: Impact preview showing what will be deleted vs. preserved

### Dashboard & Overview
- **📊 Statistics Dashboard**: Overview of Spaces, Challenges, Initiatives, Systems, KPIs, Value Types
- **🚀 Quick Actions**: Create snapshots, export data, view mentions - all one click away
- **📸 Recent Snapshots**: Last 5 snapshots with View/Compare functionality
- **💬 Recent Comments**: Latest 10 discussions across organization
- **🔔 Unread Mentions**: Alert for new @mentions with count badge

### Workspace Features
- **🌲 Interactive Tree/Grid View**: Expandable/collapsible hierarchy
- **✅ Consensus Status**: Visual indicators (✓ complete, ⚠ partial)
- **🎨 Color-Coded Values**: Configurable per KPI for better interpretation
- **📊 Rollup Indicators**: See aggregated values at every level
- **🔍 Quick Navigation**: Expand All / Collapse All buttons
- **💬 Comment Icons**: Click 💬 on any KPI cell to open discussions
- **↗️ Trend Indicators**: Automatic trend arrows when snapshots exist

### Time-Series & Analytics
- **📸 Snapshots**: Capture current state with custom labels
- **📅 Historical View**: View workspace as of any snapshot date
- **📈 Trend Analysis**: Automatic calculation of value changes over time
- **📊 Comparison View**: Side-by-side snapshot comparison with % change
- **📉 Trend Charts**: Interactive line charts (Chart.js) showing KPI history with current value
- **🏷️ Labels**: Organize snapshots ("Q1 2026", "Baseline", "Sprint 5")
- **🔄 Smart Value Entry**: Choose between "new data" (creates snapshot) or "contributing" mode
- **🎯 Target Tracking**: Set target values with progress indicators and chart visualization

### Collaboration & Communication
- **💬 Cell Comments**: Discussion threads on any KPI cell
- **@Mentions**: Notify users with autocomplete dropdown
- **🧵 Threading**: Full reply nesting with indentation
- **✅ Resolve**: Mark discussions as complete
- **🔔 Notifications**: Bell icon shows unread mention count
- **👥 User Search**: Type @ to see all organization members
- **⌨️ Keyboard Nav**: Arrow keys + Enter in mention dropdown

### Value Types (6 Kinds)
- **Numeric**: Cost, CO2 emissions, licenses, people, time, etc.
  - Integer or decimal format
  - Configurable decimal places (e.g., €1,234.56)
  - Unit labels (€, tCO2e, licenses, days, etc.)
  - Sign-based colors per KPI (positive/negative/zero)
- **Risk**: 3 levels (!, !!, !!!) - Low, Medium, High risk
- **Positive Impact**: 3 levels (★, ★★, ★★★) - Impact magnitude
- **Negative Impact**: 3 levels (▼, ▼▼, ▼▼▼) - Negative consequences
- **Level**: 3 levels (●, ●●, ●●●) - Generic scale for readiness, maturity, quality
- **Sentiment**: 3 levels (☹️, 😐, 😊) - Emotional states, satisfaction, morale

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- PostgreSQL 16+ (local development)
- Git

### Local Development Setup

```bash
# Clone repository
git clone https://github.com/mounirdous/CISK-Navigator.git
cd CISK-Navigator

# Install PostgreSQL (macOS with Homebrew)
brew install postgresql@18
brew services start postgresql@18

# Create database
createdb cisknavigator

# Create Python virtual environment
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create environment file
cp .env.example .env
# Edit .env to set DATABASE_URL=postgresql://localhost/cisknavigator

# Run database migrations
flask db upgrade

# Start development server
flask run --port 5003

# Open browser
open http://localhost:5003
```

### Default Credentials

```
Username: cisk
Password: Zurich20
```

**⚠️ You will be prompted to change the password on first login.**

## 📖 Documentation

- **[ARCHITECTURE.md](ARCHITECTURE.md)** - Technical architecture and data model
- **[app/SPECIFICATIONS.md](app/SPECIFICATIONS.md)** - Functional specifications
- **[DEPLOYMENT.md](DEPLOYMENT.md)** - Deployment guide for Render

## 🏗️ Architecture Overview

### Technology Stack
- **Backend**: Python 3.11, Flask 3.0, SQLAlchemy 2.0
- **Database**: PostgreSQL 16+ (psycopg3 driver)
- **Migrations**: Flask-Migrate (Alembic)
- **Authentication**: Flask-Login, Werkzeug password hashing
- **Forms**: Flask-WTF with CSRF protection
- **Frontend**: Bootstrap 5, Bootstrap Icons, SortableJS 1.15 (drag-and-drop), Chart.js 4.4 (charts), Vanilla JavaScript
- **Export**: openpyxl (Excel), PyYAML (structure files)

### Data Model

```
Organization
├── Spaces (flexible grouping: seasons, sites, customers)
│   └── Challenges
│       └── Challenge-Initiative Links
│           └── Initiatives (reusable)
│               └── Initiative-System Links
│                   ├── Systems (reusable)
│                   └── KPIs (context-specific)
│                       └── KPI-ValueType Configs
│                           └── Contributions (from users)
└── Value Types (organization-wide definitions)
```

**Key Principles:**
- **Reusability**: Initiatives and Systems are reusable across multiple parents
- **Context-Specific KPIs**: KPIs belong to Initiative-System pairs
- **Consensus-Driven**: Multiple contributors, automatic consensus calculation
- **Hierarchical Roll-ups**: Values aggregate upward with configurable formulas

## 💡 Use Cases

- **Enterprise Architecture**: Map systems, initiatives, and business challenges
- **Digital Transformation**: Track transformation KPIs across the organization
- **Portfolio Management**: Manage initiative portfolios with multiple value dimensions
- **Strategic Planning**: Link strategic initiatives to business challenges
- **Technology Governance**: Track technical systems and their business impact
- **Sustainability Tracking**: Aggregate CO2, cost, and impact metrics

## 🔄 Version History

### v1.11.7 (March 8, 2026)
- 🐛 **Fixed**: Current value now included in trend charts
- 🐛 **Fixed**: Same-day snapshots display as separate points using timestamps
- 📊 **Improved**: Chart displays complete time series progression

### v1.11.6 (March 8, 2026)
- 🐛 **Fixed**: Chart API mismatch (snapshots vs history key)
- 🐛 **Fixed**: Charts now render properly when snapshots exist
- 📊 **Added**: Debug flash messages for snapshot creation

### v1.11.5 (March 8, 2026)
- ✨ **Restored**: Baseline snapshot feature (without FK constraint)
- 🔧 **Changed**: Baseline implemented as property for flexibility

### v1.11.0-1.11.4 (March 8, 2026)
- ✨ **Added**: Target tracking feature with progress indicators
- 🐛 **Fixed**: Multiple circular foreign key relationship issues
- 🗄️ **Migration**: Added target_value, target_date fields

### v1.10.2 (March 8, 2026)
- 🐛 **Fixed**: Smart Value Entry snapshot creation bugs
- 🐛 **Fixed**: Form auto-submission after modal
- 🐛 **Fixed**: Snapshot deduplication on same day
- 🐛 **Fixed**: CSRF token errors in templates

### v1.10.1 (March 7, 2026)
- ✨ **Added**: Editable list views for challenges, initiatives, and systems
- 🎨 **Improved**: Navigation and management interface

### v1.10.0 (March 8, 2026)
- ✨ **Added**: Smart Value Entry feature with mode selection modal
- ✨ **Added**: Automatic snapshot creation for time evolution
- 📊 **Enhanced**: KPI cell detail page with entry mode choice

### v1.9.5 (February 2026)
- ✨ **Added**: Decimal places editing
- 🐛 **Fixed**: Value formatting issues

### v2.1.0 (March 2026) - **Major Feature Release**

**Dashboard & Overview:**
- ✨ Interactive dashboard with statistics cards and widgets
- ✨ Recent snapshots widget with View/Compare buttons
- ✨ Recent comments widget showing latest discussions
- ✨ Quick actions for common tasks
- ✨ Getting started guide for new users

**Time-Series Tracking:**
- ✨ Snapshot system for capturing KPI values over time
- ✨ Historical view to see workspace state as of any date
- ✨ Automatic trend indicators (↗️↘️→) on KPI cells
- ✨ Snapshot comparison with side-by-side analysis
- ✨ Custom labels for organizing snapshots

**Charts & Visualization:**
- ✨ Interactive line charts using Chart.js 4.4
- ✨ Trend visualization on KPI detail pages
- ✨ Tooltips showing exact values and dates
- ✨ Responsive design adapting to screen size
- ✨ Auto-refresh capability

**Collaboration Features:**
- ✨ Cell-level comments on any KPI
- ✨ @Mention system with autocomplete (type @ for dropdown)
- ✨ Threaded replies with full nesting support
- ✨ Resolve/unresolve discussions
- ✨ Unread mentions tracking with bell notification (🔔)
- ✨ Keyboard navigation in mention dropdown (arrows + Enter)
- ✨ Real-time mention rendering with highlighted names

**Enhanced Navigation:**
- ✨ Dashboard as new home page (replaces workspace)
- ✨ Three-tier navigation: Dashboard → Workspace → Administration
- ✨ Bootstrap Icons for visual clarity
- ✨ Logo click redirects to Dashboard
- ✨ Contextual buttons on all pages

**Database Schema:**
- 🗄️ New tables: kpi_snapshots, rollup_snapshots, cell_comments, mention_notifications
- 🗄️ Proper indexes and foreign key relationships
- 🗄️ Migration ID: 498afb934c2e

**API Endpoints (15 new routes):**
- GET /workspace/dashboard - Dashboard page
- GET /workspace/snapshots/compare - Snapshot comparison
- POST /workspace/snapshots/create - Create snapshot
- GET /workspace/snapshots/list - List snapshots
- GET /workspace/snapshots/view/<date> - Historical view
- GET /workspace/api/kpi/<id>/trend - Trend data
- GET /workspace/api/kpi/<id>/history - Value history
- GET/POST /workspace/api/cell/<id>/comments - Comments CRUD
- PUT/DELETE /workspace/api/comments/<id> - Edit/delete comments
- POST /workspace/api/comments/<id>/resolve - Resolve discussion
- POST /workspace/api/comments/<id>/unresolve - Unresolve discussion
- GET /workspace/api/mentions/unread - Get unread mentions
- POST /workspace/api/mentions/<id>/read - Mark as read
- POST /workspace/api/mentions/mark-all-read - Clear all
- GET /workspace/api/org/users/search - User autocomplete

### v2.0.0 (March 2026) - **Major Release**

**Database & Infrastructure:**
- ✨ Migrated from SQLite to PostgreSQL for data persistence
- ✨ Deployed on Render with persistent database
- ✨ Automatic migrations on deployment
- ✨ psycopg3 driver for Python 3.13+ compatibility
- 🛡️ Multi-layer data loss prevention with safety checks

**Color System Refactor:**
- ✨ Color configuration moved from ValueType to KPI level
- ✨ Colors propagate through all rollup levels
- 🐛 Fixed rollup color inheritance

**New Aggregation Features:**
- ✨ Added median formula (outlier-resistant aggregation)
- ✨ Added count formula (quantity tracking)
- ✨ Total of 6 aggregation formulas available

**New Value Types:**
- ✨ Added Level type (●●●) - generic 3-level scale
- ✨ Added Sentiment type (☹️😐😊) - emotional states
- ✨ All qualitative types use 3-level scale for easier consensus

**Export & Backup:**
- ✨ Excel export with hierarchical row grouping (outline levels 1-5)
- ✨ YAML export for complete structure backup
- ✨ YAML import with ID reuse logic for initiatives/systems
- ✨ Organization cloning for testing/training environments

**UX Improvements:**
- ✨ Drag-and-drop value type reordering (controls column order)
- ✨ Smart deletion with impact preview
- ✨ Improved visual hierarchy in workspace
- 🐛 Fixed duplicate flash/redirect in edit routes
- 🐛 Fixed redirect loop between login and workspace

### v1.10.1 (March 2026)
- ✨ Add editable list views for challenges, initiatives, and systems
- 🎨 Improved navigation and management interface

### v1.10.0 (February 2026)
- ✨ Add color picker feature for numeric value types
- 🎨 Sign-based color configuration (positive/negative/zero)

### v1.9.5 (February 2026)
- ✨ Add decimal places editing
- 🐛 Fix value formatting issues

## 🤝 Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

MIT License - Free for personal and commercial use.

See [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

Built for strategic business planning, digital transformation tracking, and collaborative data collection across complex organizational hierarchies.

---

**Made with ❤️ for better decision-making**
