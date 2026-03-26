# CISK Navigator - Windows startup script
# Starts PostgreSQL, Redis, Celery worker, and Flask

$PGCTL  = "C:\Program Files\PostgreSQL\16\bin\pg_ctl.exe"
$PGDATA = "C:\Program Files\PostgreSQL\16\data"
$REDIS  = "C:\Program Files\Redis\redis-server.exe"
$REDIS_CLI = "C:\Program Files\Redis\redis-cli.exe"
$PROJECT = $PSScriptRoot

Write-Host "========================================"
Write-Host "  CISK Navigator - Starting up..."
Write-Host "========================================"

# 1. PostgreSQL
Write-Host ""
Write-Host "[1/4] PostgreSQL..."
if (Get-Process -Name "postgres" -ErrorAction SilentlyContinue) {
    Write-Host "      Already running."
} else {
    & $PGCTL start -D $PGDATA -l "$PGDATA\pg.log"
    Start-Sleep -Seconds 2
    Write-Host "      Started."
}

# 2. Redis
Write-Host ""
Write-Host "[2/4] Redis..."
$redisPong = & $REDIS_CLI ping 2>$null
if ($redisPong -eq "PONG") {
    Write-Host "      Already running."
} else {
    Start-Process -FilePath $REDIS -WindowStyle Normal
    Start-Sleep -Seconds 1
    $redisPong = & $REDIS_CLI ping 2>$null
    if ($redisPong -eq "PONG") {
        Write-Host "      Started."
    } else {
        Write-Host "      WARNING: Redis did not respond. Celery/test runner will be disabled."
    }
}

# 3. Celery worker
Write-Host ""
Write-Host "[3/4] Celery worker..."
if (Get-Process -Name "celery" -ErrorAction SilentlyContinue) {
    Write-Host "      Already running."
} else {
    $celeryCmd = "cd '$PROJECT'; `$env:FLASK_APP='app.py'; venv\Scripts\celery -A celery_worker worker --loglevel=info --pool=solo"
    Start-Process powershell -ArgumentList "-NoExit", "-Command", $celeryCmd -WindowStyle Normal
    Write-Host "      Started in new window."
}

# 4. Flask
Write-Host ""
Write-Host "[4/4] Flask..."
$flaskCmd = "cd '$PROJECT'; `$env:FLASK_APP='app.py'; venv\Scripts\flask run"
Start-Process powershell -ArgumentList "-NoExit", "-Command", $flaskCmd -WindowStyle Normal
Write-Host "      Started at http://localhost:5000 (new window)"

Write-Host ""
Write-Host "========================================"
Write-Host "  All services started. You can close this window."
Write-Host "========================================"
