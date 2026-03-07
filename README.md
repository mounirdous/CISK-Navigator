# 🧭 CISK Navigator v2.0

**Production-ready data collection and aggregation system** for tracking KPIs across hierarchical organization structures.

![Version](https://img.shields.io/badge/version-2.0.0-blue)
![Python](https://img.shields.io/badge/python-3.11+-green)
![Database](https://img.shields.io/badge/database-PostgreSQL-blue)
![License](https://img.shields.io/badge/license-MIT-orange)

## ✨ What's New in v2.0

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

### Workspace Features
- **🌲 Interactive Tree/Grid View**: Expandable/collapsible hierarchy
- **✅ Consensus Status**: Visual indicators (✓ complete, ⚠ partial)
- **🎨 Color-Coded Values**: Configurable per KPI for better interpretation
- **📊 Rollup Indicators**: See aggregated values at every level
- **🔍 Quick Navigation**: Expand All / Collapse All buttons

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
- **Frontend**: Bootstrap 5, SortableJS 1.15 (drag-and-drop), Vanilla JavaScript
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
