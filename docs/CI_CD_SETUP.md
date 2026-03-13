# CI/CD Setup Guide

## Overview

CISK Navigator has a complete CI/CD pipeline with automated testing, coverage reporting, and code quality checks.

## GitHub Actions Workflow

### When Tests Run
- ✅ Every push to `main` branch
- ✅ Every push to `develop` branch
- ✅ Every pull request to `main` or `develop`

### What Gets Tested
1. **Python 3.11** environment
2. **PostgreSQL 15** database (realistic production-like testing)
3. **All test suites** (unit + integration)
4. **Coverage reporting** to Codecov
5. **Coverage threshold** check (35% minimum)

### Workflow File
Location: `.github/workflows/tests.yml`

### Pipeline Steps
```
1. Checkout code
2. Set up Python 3.11
3. Install dependencies from requirements.txt
4. Start PostgreSQL service
5. Run pytest with coverage
6. Upload coverage to Codecov
7. Check coverage meets threshold
```

## Pre-commit Hooks

### What They Do
Automatically run before each commit to:
- ✅ Format code with **Black** (line length: 120)
- ✅ Sort imports with **isort**
- ✅ Lint code with **flake8**
- ✅ Check YAML/JSON syntax
- ✅ Fix trailing whitespace
- ✅ Fix line endings
- ✅ Check for large files
- ✅ Run fast unit tests

### Installation

```bash
# Quick setup
bash scripts/setup_dev.sh

# Or manually
pip install pre-commit
pre-commit install
```

### Usage

```bash
# Hooks run automatically on commit
git commit -m "Your message"

# Run manually on all files
pre-commit run --all-files

# Skip hooks (not recommended!)
git commit --no-verify
```

### Configuration
Location: `.pre-commit-config.yaml`

## Coverage Reporting

### Local Coverage

```bash
# Generate HTML report
pytest --cov=app --cov-report=html

# Open in browser
open htmlcov/index.html

# Terminal report
pytest --cov=app --cov-report=term-missing
```

### Codecov Integration

Coverage reports are automatically uploaded to Codecov on every CI run.

**Setup Steps:**
1. Sign up at [codecov.io](https://codecov.io)
2. Connect your GitHub repository
3. Add badge to README:
   ```markdown
   ![Coverage](https://codecov.io/gh/YOUR_USERNAME/CISK-Navigator/branch/main/graph/badge.svg)
   ```

### Coverage Configuration
Location: `.coveragerc`

**Exclusions:**
- Tests directory
- Virtual environments
- Migrations
- Configuration files

## Code Quality Standards

### Black Formatter
- Line length: 120 characters
- Python version: 3.11
- Auto-formats on pre-commit

### isort
- Profile: black (compatible with Black)
- Line length: 120
- Auto-sorts imports on pre-commit

### flake8
- Max line length: 120
- Ignores: E203, W503, E501
- Excludes: migrations, venv

## Setting Up for New Developers

### 1. Clone Repository
```bash
git clone https://github.com/YOUR_USERNAME/CISK-Navigator.git
cd CISK-Navigator
```

### 2. Run Setup Script
```bash
bash scripts/setup_dev.sh
```

This script:
- Creates virtual environment
- Installs all dependencies
- Sets up pre-commit hooks
- Creates .env file
- Runs database migrations
- Verifies setup with tests

### 3. Start Development
```bash
# Activate environment
source venv/bin/activate

# Run tests
pytest

# Start server
flask run --port 5003
```

## Troubleshooting

### Pre-commit Hooks Failing

**Problem:** Hooks fail on commit
**Solution:**
```bash
# Run hooks manually to see errors
pre-commit run --all-files

# Fix formatting issues
black app/ tests/
isort app/ tests/

# Then commit again
git commit -m "Your message"
```

### Tests Failing in CI but Passing Locally

**Problem:** Tests pass locally but fail in GitHub Actions
**Possible causes:**
1. **Database differences** - CI uses PostgreSQL, local might use SQLite
2. **Environment variables** - Check CI environment vars
3. **Dependencies** - Ensure requirements.txt is up to date

**Solution:**
```bash
# Test with PostgreSQL locally
export DATABASE_URL=postgresql://localhost/cisk_test
pytest

# Check CI logs in GitHub Actions tab
```

### Coverage Below Threshold

**Problem:** CI fails because coverage dropped below 35%
**Solution:**
```bash
# Check current coverage
pytest --cov=app --cov-report=term-missing

# Add tests for uncovered code
# See TESTING.md for guidelines

# Update threshold in .github/workflows/tests.yml if needed
```

## Continuous Improvement

### Increasing Coverage
1. Run coverage report: `pytest --cov=app --cov-report=html`
2. Open `htmlcov/index.html` to see uncovered lines
3. Add tests for red/yellow highlighted code
4. Focus on:
   - Routes with <40% coverage
   - Services with <50% coverage
   - Critical business logic

### Adding New Tests
1. Write test following guidelines in TESTING.md
2. Run locally: `pytest tests/new_test.py -v`
3. Check coverage: `pytest --cov=app`
4. Commit (pre-commit hooks will run)
5. Push (CI will run full suite)

### Updating CI Configuration
1. Edit `.github/workflows/tests.yml`
2. Test locally if possible
3. Push to feature branch
4. Check GitHub Actions tab for results
5. Merge to main when green

## Best Practices

### Before Committing
```bash
# Run tests
pytest tests/unit/ -x

# Check coverage
pytest --cov=app

# Format code (if not using pre-commit)
black app/ tests/
isort app/ tests/
```

### Before Creating PR
```bash
# Run full test suite
pytest

# Check all pre-commit hooks
pre-commit run --all-files

# Review coverage report
open htmlcov/index.html
```

### When PR Tests Fail
1. Check GitHub Actions logs
2. Reproduce locally
3. Fix the issue
4. Push fix to PR branch
5. CI will automatically re-run

## Monitoring

### GitHub Actions Status
- Go to repository → Actions tab
- See workflow runs for each commit
- Click run to see detailed logs

### Coverage Trends
- Visit Codecov dashboard
- See coverage over time
- Identify coverage drops

### Pre-commit Hook Stats
```bash
# See hook execution times
pre-commit run --all-files --verbose

# Update hooks
pre-commit autoupdate
```

## Resources

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Pre-commit Documentation](https://pre-commit.com/)
- [Codecov Documentation](https://docs.codecov.com/)
- [pytest Documentation](https://docs.pytest.org/)
- [Black Documentation](https://black.readthedocs.io/)
- [Testing Guide](../TESTING.md)
