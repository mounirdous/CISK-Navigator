# 🚀 CISK Navigator v2.0 - Deployment Guide

Complete guide to deploying CISK Navigator v2.0 with PostgreSQL to Render.

**Last Updated**: March 7, 2026
**Version**: 2.0.0

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Local Development Setup](#local-development-setup)
3. [Render Deployment](#render-deployment)
4. [Database Setup](#database-setup)
5. [Environment Configuration](#environment-configuration)
6. [Deployment Process](#deployment-process)
7. [Post-Deployment](#post-deployment)
8. [Troubleshooting](#troubleshooting)

## Prerequisites

### What You Need

- **GitHub Account**: For code repository
- **Render Account**: For hosting (free tier available)
- **Local Development**:
  - Python 3.11+
  - PostgreSQL 16+ (for local testing)
  - Git

### v2.0 Requirements

- ✅ PostgreSQL database (SQLite no longer supported in production)
- ✅ Environment variables for database connection
- ✅ Automatic migrations on deployment

## Local Development Setup

### 1. Install PostgreSQL

**macOS (Homebrew):**
```bash
brew install postgresql@18
brew services start postgresql@18

# Add to PATH
echo 'export PATH="/opt/homebrew/opt/postgresql@18/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc
```

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install postgresql postgresql-contrib
sudo systemctl start postgresql
```

**Windows:**
Download and install from [postgresql.org](https://www.postgresql.org/download/windows/)

### 2. Create Local Database

```bash
# Create database
createdb cisknavigator

# Verify connection
psql -d cisknavigator -c "SELECT version();"
```

### 3. Clone and Setup Project

```bash
# Clone repository
git clone https://github.com/mounirdous/CISK-Navigator.git
cd CISK-Navigator

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 4. Configure Environment

Create `.env` file:

```bash
cp .env.example .env
```

Edit `.env`:

```env
# Database
DATABASE_URL=postgresql://localhost/cisknavigator

# Flask
SECRET_KEY=your-secret-key-here-change-in-production
FLASK_ENV=development
FLASK_DEBUG=True
```

### 5. Run Migrations

```bash
# Initialize migrations (first time only)
flask db init  # Skip if migrations/ folder exists

# Apply migrations
flask db upgrade
```

### 6. Start Development Server

```bash
flask run --port 5003
```

Visit http://localhost:5003

**Default Credentials:**
- Username: `cisk`
- Password: `Zurich20`
- (You'll be prompted to change password on first login)

## Render Deployment

### Why Render?

- ✅ Free tier with persistent PostgreSQL
- ✅ Automatic deployments from GitHub
- ✅ Managed database with backups
- ✅ SSL certificates included
- ✅ Easy environment variable management

### 1. Push to GitHub

```bash
# Add all changes
git add .

# Commit
git commit -m "Ready for deployment"

# Push to GitHub
git push origin main
```

### 2. Create Render Account

1. Go to [render.com](https://render.com)
2. Sign up with GitHub
3. Authorize Render to access your repositories

## Database Setup

### Create PostgreSQL Database on Render

1. **Go to Render Dashboard**
2. **Click "New" → "PostgreSQL"**
3. **Configure Database:**
   - **Name**: `cisk-navigator-db` (or your choice)
   - **Database**: `cisknavigator` (no spaces/hyphens)
   - **User**: (leave blank - auto-generated)
   - **Region**: Oregon (US West) - or closest to your users
   - **PostgreSQL Version**: 16 or later
   - **Instance Type**: Free (suitable for development/small teams)
4. **Click "Create Database"**

5. **Wait for Creation** (~2-3 minutes)

6. **Copy Connection Details:**
   - Go to database → "Info" tab
   - Copy **Internal Database URL** (starts with `postgres://`)
   - Format: `postgres://user:password@host/database`
   - Keep this for step 5

## Environment Configuration

### Web Service Environment Variables

After creating the database, set up the web service environment variables.

**Required Variables:**

| Variable | Value | Description |
|----------|-------|-------------|
| `DATABASE_URL` | `postgres://...` | Internal Database URL from Render PostgreSQL |
| `SECRET_KEY` | (auto-generated) | Flask session encryption key |
| `FLASK_ENV` | `production` | Environment mode |
| `PYTHON_VERSION` | `3.11.9` | Python version |

**Do not set these yet** - wait until after creating the web service.

## Deployment Process

### Step 1: Create Web Service

1. **Go to Render Dashboard**
2. **Click "New" → "Web Service"**
3. **Connect Repository:**
   - Select your GitHub repository
   - Repository: `CISK-Navigator`
   - Click "Connect"

### Step 2: Configure Web Service

Fill in the following:

**Basic Settings:**
- **Name**: `cisk-navigator-app` (or your choice)
- **Region**: Oregon (US West) - **must match database region**
- **Branch**: `main`
- **Runtime**: Python 3

**Build & Deploy:**
- **Build Command**:
  ```bash
  pip install -r requirements.txt && flask db upgrade
  ```
- **Start Command**:
  ```bash
  gunicorn run:app
  ```

**Instance Type:**
- **Plan**: Free (or paid if needed)

**Advanced Options:**
- **Auto-Deploy**: Yes (deploy on every push to main)

### Step 3: Add Environment Variables

**Before clicking "Create Web Service"**, add environment variables:

1. Scroll to "Environment Variables" section
2. **Add Variables:**

```
DATABASE_URL = postgres://cisknavigator_user:YourPassword@dpg-xxx.oregon-postgres.render.com/cisknavigator
```
*Replace with your actual Internal Database URL from Step 4*

```
SECRET_KEY = (click "Generate" button)
```

```
FLASK_ENV = production
```

```
PYTHON_VERSION = 3.11.9
```

### Step 4: Create Web Service

1. **Click "Create Web Service"**
2. **Wait for Deployment** (3-5 minutes first time)
3. **Watch Build Logs:**
   - Installing dependencies
   - Running database migrations
   - Starting gunicorn
   - Service is live!

### Step 5: Verify Deployment

1. **Click on the generated URL** (e.g., `https://cisk-navigator-app.onrender.com`)
2. **You should see the login page**
3. **Test Login:**
   - Username: `cisk`
   - Password: `Zurich20`
4. **Change Password** when prompted

## Post-Deployment

### Initial Setup

1. **Log in as Global Admin**
   - Step 1: Login → `cisk` / `Zurich20`
   - Change password
   - Step 2: Check "Log in as Administrator"

2. **Create Organizations**
   - Global Admin → Organizations → Create Organization
   - Add organization name and description

3. **Create Users**
   - Global Admin → Users → Create User
   - Assign users to organizations

4. **Start Using the App**
   - Log in as organization user
   - Build hierarchy: Spaces → Challenges → Initiatives → Systems → KPIs
   - Define Value Types
   - Enter data and track consensus

### Automatic Deployments

Every time you push to GitHub `main` branch:

1. Render detects the push
2. Runs build command (installs dependencies + migrations)
3. Restarts the app
4. **Data persists** (PostgreSQL is separate)

```bash
# Make changes
git add .
git commit -m "Add new feature"
git push origin main

# Render automatically deploys!
```

### Database Migrations

When you change models:

```bash
# Local: Create migration
flask db migrate -m "Add new field to KPI model"

# Local: Test migration
flask db upgrade

# Commit and push
git add migrations/
git commit -m "Add database migration"
git push origin main

# Render automatically runs: flask db upgrade
```

## Monitoring

### View Logs

**Render Dashboard → Your Service → Logs**

Watch for:
- ✅ `Successfully installed ...`
- ✅ `Running: flask db upgrade`
- ✅ `Starting gunicorn...`
- ✅ `Your service is live`

### Database Monitoring

**Render Dashboard → Your Database**

- **Metrics**: CPU, memory, storage
- **Connections**: Active connections
- **Backups**: Automatic daily backups (paid plans)

## Troubleshooting

### App Won't Start

**Symptom**: Build succeeds but app crashes on start

**Check:**
1. **DATABASE_URL is set correctly**
   ```bash
   # In Render logs, look for:
   # "SQLALCHEMY_DATABASE_URI: postgresql+psycopg://..."
   ```

2. **Migrations ran successfully**
   ```bash
   # In build logs, look for:
   # "Running: flask db upgrade"
   # "INFO  [alembic.runtime.migration] Running upgrade..."
   ```

3. **Python version matches**
   ```bash
   # Should see: "Using Python 3.11.9"
   ```

**Solution:**
- Go to Environment → Check DATABASE_URL
- Re-deploy from Dashboard → Manual Deploy

### Database Connection Errors

**Symptom**: `could not connect to server` or `connection refused`

**Check:**
1. Database and web service in **same region**
2. Using **Internal Database URL** (not External)
3. URL format: `postgres://` (Render format)

**Solution:**
```python
# app/config.py automatically converts to postgresql+psycopg://
# If still issues, check DATABASE_URL value
```

### Migrations Fail

**Symptom**: Build fails with `alembic` errors

**Check:**
```bash
# Local: Verify migrations work
flask db upgrade

# Local: Check migration files
ls migrations/versions/
```

**Solution:**
```bash
# If migrations are broken, stamp current state:
flask db stamp head

# Then create clean migration:
flask db migrate -m "Fix migrations"
```

### Build Command Fails

**Symptom**: `pip install` fails

**Check:**
- `requirements.txt` exists and is correct
- No typos in package names
- Python version compatibility

**Solution:**
```bash
# Test locally first
pip install -r requirements.txt
```

### SSL/HTTPS Issues

**Symptom**: Mixed content warnings

**Solution:**
- Render provides HTTPS automatically
- Ensure all links use `https://`

### Performance Issues

**Symptom**: Slow response times

**Solutions:**
1. **Upgrade Render instance** (free tier has limits)
2. **Optimize queries** (add indexes)
3. **Enable caching** (future enhancement)
4. **Use connection pooling** (built-in with PostgreSQL)

## Scaling

### When to Upgrade

Consider paid plans when:
- More than 50 concurrent users
- Large datasets (>10,000 KPIs)
- Need guaranteed uptime
- Need database backups

### Upgrade Options

**Render Plans:**
- **Free**: 512MB RAM, shared CPU
- **Starter ($7/mo)**: 512MB RAM, dedicated CPU
- **Standard ($25/mo)**: 2GB RAM, dedicated CPU
- **Pro ($85/mo)**: 4GB RAM, high-performance

**Database Plans:**
- **Free**: 1GB storage, shared
- **Starter ($7/mo)**: 1GB storage, 60 connections
- **Standard ($20/mo)**: 10GB storage, 97 connections
- **Pro ($50/mo)**: 25GB storage, 145 connections

## Backup & Recovery

### Database Backups

**Free Tier:**
- Manual exports via Render dashboard
- Export to `.sql` file

**Paid Tiers:**
- Automatic daily backups
- Point-in-time recovery
- One-click restore

### Manual Backup

```bash
# Export database
pg_dump -h dpg-xxx.oregon-postgres.render.com -U user -d cisknavigator > backup.sql

# Restore from backup
psql -h dpg-xxx.oregon-postgres.render.com -U user -d cisknavigator < backup.sql
```

## Custom Domain

### Add Custom Domain to Render

1. **Render Dashboard → Service → Settings**
2. **Custom Domains → Add Domain**
3. **Add your domain:** `app.yourdomain.com`
4. **Add CNAME Record to DNS:**
   - Type: `CNAME`
   - Name: `app`
   - Value: `cisk-navigator-app.onrender.com`
5. **Wait for SSL Certificate** (automatic, ~5 minutes)

## Security Best Practices

### Production Checklist

- ✅ Use strong `SECRET_KEY` (auto-generated by Render)
- ✅ Use `FLASK_ENV=production` (disables debug mode)
- ✅ Keep `DATABASE_URL` secret (never commit to git)
- ✅ Use `.gitignore` for `.env` files
- ✅ Enforce password changes for default admin
- ✅ Regular database backups
- ✅ Monitor logs for suspicious activity
- ✅ Keep dependencies updated

### Update Dependencies

```bash
# Check for security updates
pip list --outdated

# Update specific package
pip install --upgrade flask

# Update requirements.txt
pip freeze > requirements.txt

# Commit and deploy
git add requirements.txt
git commit -m "Update dependencies"
git push origin main
```

## Support

### Getting Help

1. **Check Logs**: Render Dashboard → Logs
2. **Review Documentation**: This guide + ARCHITECTURE.md
3. **GitHub Issues**: Report bugs or ask questions
4. **Render Support**: [render.com/support](https://render.com/support)

### Useful Links

- **Render Docs**: https://render.com/docs
- **Flask Docs**: https://flask.palletsprojects.com/
- **PostgreSQL Docs**: https://www.postgresql.org/docs/
- **SQLAlchemy Docs**: https://docs.sqlalchemy.org/

---

**🎉 Congratulations!** Your CISK Navigator v2.0 is now deployed with persistent PostgreSQL storage.

**What's Next?**
- Create your first organization
- Add users and assign permissions
- Build your organizational hierarchy
- Start collecting KPI data

**Questions?** Open an issue on GitHub or check the documentation.

---

**Made with ❤️ for better decision-making**
