#!/bin/bash
# Development environment setup script for CISK Navigator

set -e

echo "=== CISK Navigator Development Setup ==="
echo

# Check Python version
python_version=$(python3 --version 2>&1 | awk '{print $2}')
echo "✓ Python version: $python_version"

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
    echo "✓ Virtual environment created"
else
    echo "✓ Virtual environment already exists"
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip > /dev/null

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

echo "✓ Dependencies installed"

# Install pre-commit hooks
echo "Installing pre-commit hooks..."
pre-commit install

echo "✓ Pre-commit hooks installed"

# Create .env file if it doesn't exist
if [ ! -f ".env" ]; then
    echo "Creating .env file..."
    cat > .env << EOF
FLASK_ENV=development
FLASK_APP=run.py
SECRET_KEY=$(python3 -c 'import secrets; print(secrets.token_hex(32))')
DATABASE_URL=postgresql://localhost/cisknavigator
PORT=5003
EOF
    echo "✓ .env file created"
else
    echo "✓ .env file already exists"
fi

# Run database migrations
echo
echo "Running database migrations..."
flask db upgrade

echo "✓ Database migrations complete"

# Run tests to verify setup
echo
echo "Running test suite to verify setup..."
pytest tests/unit/ -v --tb=short

echo
echo "=== Setup Complete! ==="
echo
echo "To start development:"
echo "  1. Activate venv: source venv/bin/activate"
echo "  2. Run tests: pytest"
echo "  3. Start server: flask run --port 5003"
echo "  4. Run pre-commit manually: pre-commit run --all-files"
echo
