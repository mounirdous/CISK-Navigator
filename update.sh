#!/bin/bash
# CISK Navigator - Update script
# Pulls latest from GitHub, installs new deps, runs migrations if needed

echo "========================================"
echo "  CISK Navigator - Update"
echo "========================================"

# Snapshot migration files before pull
MIGRATIONS_BEFORE=$(ls migrations/versions/*.py 2>/dev/null | sort)
REQUIREMENTS_BEFORE=$(md5sum requirements.txt 2>/dev/null)

# 1. Pull latest
echo ""
echo "[1/3] Pulling latest from GitHub..."
git pull origin main
if [ $? -ne 0 ]; then
    echo "      ERROR: git pull failed. Resolve conflicts and try again."
    exit 1
fi

# 2. Install new dependencies if requirements.txt changed
REQUIREMENTS_AFTER=$(md5sum requirements.txt 2>/dev/null)
if [ "$REQUIREMENTS_BEFORE" != "$REQUIREMENTS_AFTER" ]; then
    echo ""
    echo "[2/3] requirements.txt changed - installing dependencies..."
    venv/Scripts/pip install -r requirements.txt
else
    echo ""
    echo "[2/3] No dependency changes."
fi

# 3. Run migrations if new migration files appeared
MIGRATIONS_AFTER=$(ls migrations/versions/*.py 2>/dev/null | sort)
if [ "$MIGRATIONS_BEFORE" != "$MIGRATIONS_AFTER" ]; then
    echo ""
    echo "[3/3] New migrations detected - running flask db upgrade..."
    NEW=$(diff <(echo "$MIGRATIONS_BEFORE") <(echo "$MIGRATIONS_AFTER") | grep "^>" | sed 's/> /  + /')
    echo "$NEW"
    FLASK_APP=app.py venv/Scripts/flask db upgrade
    if [ $? -eq 0 ]; then
        echo "      Migrations applied successfully."
    else
        echo "      ERROR: Migration failed! Check the output above."
        exit 1
    fi
else
    echo ""
    echo "[3/3] No new migrations."
fi

echo ""
echo "========================================"
echo "  Update complete. Run ./start.sh to launch."
echo "========================================"
