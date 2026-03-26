# CISK Navigator - Update script
# Pulls latest from GitHub, installs new deps, runs migrations if needed

$PROJECT = $PSScriptRoot

Write-Host "========================================"
Write-Host "  CISK Navigator - Update"
Write-Host "========================================"

# Snapshot migration files and requirements hash before pull
$migrationsBefore = Get-ChildItem "$PROJECT\migrations\versions\*.py" -ErrorAction SilentlyContinue |
    Select-Object -ExpandProperty FullName | Sort-Object
$requirementsBefore = (Get-FileHash "$PROJECT\requirements.txt" -Algorithm MD5 -ErrorAction SilentlyContinue).Hash

# 1. Pull latest
Write-Host ""
Write-Host "[1/3] Pulling latest from GitHub..."
git pull origin main
if ($LASTEXITCODE -ne 0) {
    Write-Host "      ERROR: git pull failed. Resolve conflicts and try again."
    exit 1
}

# 2. Install new dependencies if requirements.txt changed
$requirementsAfter = (Get-FileHash "$PROJECT\requirements.txt" -Algorithm MD5 -ErrorAction SilentlyContinue).Hash
Write-Host ""
if ($requirementsBefore -ne $requirementsAfter) {
    Write-Host "[2/3] requirements.txt changed - installing dependencies..."
    & "$PROJECT\venv\Scripts\pip" install -r "$PROJECT\requirements.txt"
} else {
    Write-Host "[2/3] No dependency changes."
}

# 3. Run migrations if new migration files appeared
$migrationsAfter = Get-ChildItem "$PROJECT\migrations\versions\*.py" -ErrorAction SilentlyContinue |
    Select-Object -ExpandProperty FullName | Sort-Object

$newMigrations = $migrationsAfter | Where-Object { $_ -notin $migrationsBefore }
Write-Host ""
if ($newMigrations) {
    Write-Host "[3/3] New migrations detected - running flask db upgrade..."
    $newMigrations | ForEach-Object { Write-Host "  + $_" }
    $env:FLASK_APP = "app.py"
    & "$PROJECT\venv\Scripts\flask" db upgrade
    if ($LASTEXITCODE -eq 0) {
        Write-Host "      Migrations applied successfully."
    } else {
        Write-Host "      ERROR: Migration failed! Check the output above."
        exit 1
    }
} else {
    Write-Host "[3/3] No new migrations."
}

Write-Host ""
Write-Host "========================================"
Write-Host "  Update complete. Run .\start.ps1 to launch."
Write-Host "========================================"
