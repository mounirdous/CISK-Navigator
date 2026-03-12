#!/bin/bash
# CISK Navigator startup script

echo "🚀 Starting CISK Navigator..."

# Start PostgreSQL if not running
if ! pgrep -x postgres > /dev/null; then
    echo "📊 Starting PostgreSQL..."
    /opt/homebrew/opt/postgresql@18/bin/pg_ctl -D /opt/homebrew/var/postgresql@18 start -l /opt/homebrew/var/log/postgresql@18.log
    sleep 2
else
    echo "✓ PostgreSQL already running"
fi

# Start Flask on port 5003
echo "🌐 Starting Flask on port 5003..."
source venv/bin/activate
flask run --port 5003
