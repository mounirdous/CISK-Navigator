# 🚀 QUICK START - Database & Flask

**For rapid development startup - no BS, just commands**

---

## Prerequisites Check

```bash
# Check PostgreSQL is running
pg_isready

# Check Python version
python --version  # Should be 3.14+

# Check virtual environment exists
ls -la venv/
```

---

## 1. Start PostgreSQL Database

### macOS (Homebrew)
```bash
# Start PostgreSQL service
brew services start postgresql@18

# OR if already running, restart
brew services restart postgresql@18

# Verify it's running
pg_isready
# Should output: /tmp:5432 - accepting connections
```

### Linux
```bash
sudo systemctl start postgresql
sudo systemctl status postgresql
```

---

## 2. Activate Virtual Environment

**CRITICAL: Always activate venv first!**

```bash
cd /Users/mounir.dous/projects/CISK-Navigator
source venv/bin/activate

# Verify you're in venv (prompt should show (venv))
which python
# Should show: /Users/mounir.dous/projects/CISK-Navigator/venv/bin/python
```

---

## 3. Start Flask Application

### Development Server (Default)
```bash
# Simple start
flask run --port 5003

# OR with auto-reload (recommended for development)
flask run --port 5003 --reload --debug

# Flask app runs at: http://localhost:5003
```

### Production-like (Gunicorn)
```bash
gunicorn -w 4 -b 0.0.0.0:5003 "app:create_app()"
```

---

## 4. Verify Everything Works

```bash
# In browser, visit:
http://localhost:5003

# Check database connection
flask shell
>>> from app.extensions import db
>>> db.engine.execute("SELECT 1").scalar()
# Should return: 1
>>> exit()
```

---

## Common Database Commands

### Check Database Connection
```bash
# Test connection
psql -d cisknavigator -c "SELECT version();"

# List all databases
psql -l

# Connect to cisknavigator database
psql cisknavigator
```

### Inside psql
```sql
-- List all tables
\dt

-- Check specific table
SELECT COUNT(*) FROM organizations;

-- Check entity defaults
SELECT entity_type, default_color, default_icon FROM entity_type_defaults WHERE organization_id = 1;

-- Exit psql
\q
```

---

## Database Migrations

```bash
# Check current migration status
flask db current

# Run pending migrations
flask db upgrade

# Rollback one migration
flask db downgrade

# Create new migration (after model changes)
flask db migrate -m "Description of changes"
```

---

## Troubleshooting

### PostgreSQL Not Starting
```bash
# Check if PostgreSQL is installed
which psql

# Check PostgreSQL logs
tail -f /usr/local/var/log/postgresql@18.log

# Force stop and restart
brew services stop postgresql@18
brew services start postgresql@18
```

### Flask Import Errors
```bash
# Verify venv is activated
echo $VIRTUAL_ENV
# Should show: /Users/mounir.dous/projects/CISK-Navigator/venv

# Reinstall dependencies if needed
pip install -r requirements.txt
```

### Database Connection Errors
```bash
# Check DATABASE_URL environment variable
echo $DATABASE_URL
# Should show: postgresql+psycopg://localhost/cisknavigator

# If not set, set it
export DATABASE_URL="postgresql+psycopg://localhost/cisknavigator"

# Test connection
flask shell
>>> from app.extensions import db
>>> db.engine.connect()
```

### Port Already in Use
```bash
# Find process using port 5003
lsof -ti:5003

# Kill process
kill -9 $(lsof -ti:5003)

# Or use different port
flask run --port 5004
```

---

## One-Liner Startup (Copy-Paste)

```bash
cd /Users/mounir.dous/projects/CISK-Navigator && source venv/bin/activate && brew services start postgresql@18 && flask run --port 5003 --reload --debug
```

---

## Stop Everything

```bash
# Stop Flask (Ctrl+C in terminal where it's running)
^C

# Stop PostgreSQL
brew services stop postgresql@18

# Deactivate virtual environment
deactivate
```

---

## Environment Variables (if needed)

```bash
# .env file (create if doesn't exist)
DATABASE_URL=postgresql+psycopg://localhost/cisknavigator
FLASK_ENV=development
FLASK_DEBUG=1
SECRET_KEY=dev-secret-key-change-in-production
```

Load with:
```bash
export $(cat .env | xargs)
```

---

## Quick Health Check

```bash
# All-in-one health check
pg_isready && echo "✅ PostgreSQL OK" || echo "❌ PostgreSQL DOWN"
source venv/bin/activate && python -c "from app import create_app; app=create_app(); print('✅ Flask OK')" 2>/dev/null || echo "❌ Flask ERROR"
```

---

## Development Workflow

### Typical Session:
1. `cd /Users/mounir.dous/projects/CISK-Navigator`
2. `source venv/bin/activate`
3. `brew services start postgresql@18` (if not running)
4. `flask run --port 5003 --reload --debug`
5. Open http://localhost:5003 in browser
6. Make changes, Flask auto-reloads
7. Ctrl+C to stop Flask when done
8. `deactivate` to exit venv

### Before Pushing Code:
1. Run tests: `pytest`
2. Check coverage: `pytest --cov=app --cov-report=html`
3. Verify migrations: `flask db current`
4. Commit and push

---

**Last Updated:** 2026-03-14 (v1.31.0)
