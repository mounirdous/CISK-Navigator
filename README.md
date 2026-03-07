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

### 🚀 **Production Deployment**
- Deployed on Render with persistent PostgreSQL
- Zero downtime deployments
- Automatic database migrations

## 🎯 Features

### Core Capabilities
- **📊 Hierarchical Data Model**: Spaces → Challenges → Initiatives → Systems → KPIs
- **👥 Consensus-Based Input**: Multiple contributors, automatic consensus calculation
- **📈 Automatic Roll-ups**: Values aggregate up the hierarchy
- **🎨 Flexible Color Configuration**: Sign-based colors (positive/negative/zero) per KPI
- **🔢 Multiple Value Types**: Numeric (with decimals), Risk levels, Impact indicators
- **🏢 Multi-Organization**: Complete data isolation between organizations
- **👤 User Management**: Global admins, organization members, access control

### Workspace Features
- **🌲 Interactive Tree/Grid View**: Expandable/collapsible hierarchy
- **✅ Consensus Status**: Visual indicators (✓ complete, ⚠ partial)
- **🎨 Color-Coded Values**: Configurable per KPI for better interpretation
- **📊 Rollup Indicators**: See aggregated values at every level
- **🔍 Quick Navigation**: Expand All / Collapse All buttons

### Value Types
- **Numeric**: Cost, CO2 emissions, licenses, people, etc.
  - Integer or decimal format
  - Configurable decimal places (e.g., €1,234.56)
  - Unit labels (€, tCO2e, licenses, etc.)
  - Sign-based colors per KPI
- **Qualitative**:
  - **Risk**: Levels 1-3 (!, !!, !!!)
  - **Positive Impact**: Levels 1-3 (★, ★★, ★★★)
  - **Negative Impact**: Levels 1-3 (▼, ▼▼, ▼▼▼)

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
- **Frontend**: Bootstrap 5, Vanilla JavaScript

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
- ✨ Migrated from SQLite to PostgreSQL for data persistence
- ✨ Color configuration moved from ValueType to KPI level
- ✨ Colors propagate through all rollup levels
- ✨ Deployed on Render with persistent database
- ✨ Automatic migrations on deployment
- ✨ psycopg3 driver for Python 3.13+ compatibility
- 🐛 Fixed rollup color inheritance
- 🐛 Fixed duplicate flash/redirect in edit routes

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
