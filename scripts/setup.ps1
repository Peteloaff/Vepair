<#
.SYNOPSIS
  One-time VepAIr local development setup.

.DESCRIPTION
  1. Ensures the postgresql-x64-17 service is running and has a `vepair` role/database
     (triggers a UAC prompt the first time — administrator rights are required to manage
     the Windows PostgreSQL service and its auth config).
  2. Creates the Python virtualenv for apps/api and installs dependencies.
  3. Runs database migrations.
  4. Installs frontend dependencies for apps/web.

  Requires PostgreSQL, Python 3.12+, and Node.js already installed and on PATH
  (e.g. via `winget install PostgreSQL.PostgreSQL.17`, `winget install Python.Python.3.12`,
  `winget install OpenJS.NodeJS.LTS`).

  Safe to re-run: skips steps that are already done.
#>

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
$PgBin = "C:\Program Files\PostgreSQL\17\bin"

# --- 1. Ensure Postgres service is running ---
$svc = Get-Service postgresql-x64-17 -ErrorAction SilentlyContinue
if (-not $svc) {
    Write-Error "postgresql-x64-17 service not found. Install with: winget install PostgreSQL.PostgreSQL.17"
}
if ($svc.Status -ne "Running") {
    Write-Host "Starting postgresql-x64-17 (requires admin) ..."
    Start-Process powershell -ArgumentList "-NoProfile -Command Start-Service postgresql-x64-17" -Verb RunAs -Wait
}

# --- 2. Ensure the `vepair` role/database exist ---
$env:PGPASSWORD = "vepair"
$canConnect = & "$PgBin\psql.exe" -h 127.0.0.1 -p 5432 -U vepair -d vepair -tAc "SELECT 1" 2>$null
if ($canConnect -ne "1") {
    Write-Host "Creating 'vepair' role/database (requires admin — a UAC prompt will appear) ..."
    Start-Process powershell -ArgumentList "-NoProfile -ExecutionPolicy Bypass -File `"$PSScriptRoot\_admin_setup_pg.ps1`"" -Verb RunAs -Wait
    $canConnect = & "$PgBin\psql.exe" -h 127.0.0.1 -p 5432 -U vepair -d vepair -tAc "SELECT 1" 2>$null
    if ($canConnect -ne "1") {
        Write-Error "Could not verify the 'vepair' database after admin setup. See %TEMP%\vepair-admin-setup.log"
    }
} else {
    Write-Host "'vepair' role/database already usable."
}

# --- 3. Backend: venv + dependencies ---
$ApiDir = Join-Path $RepoRoot "apps\api"
if (-not (Test-Path (Join-Path $ApiDir ".venv"))) {
    Write-Host "Creating Python virtualenv ..."
    python -m venv (Join-Path $ApiDir ".venv")
}
$Pip = Join-Path $ApiDir ".venv\Scripts\pip.exe"
& $Pip install -e "$ApiDir[dev]" --quiet
& $Pip install -e (Join-Path $RepoRoot "packages\audio-engine") --quiet

if (-not (Test-Path (Join-Path $ApiDir ".env"))) {
    Copy-Item (Join-Path $ApiDir ".env.example") (Join-Path $ApiDir ".env")
}

Write-Host "Running database migrations ..."
Push-Location $ApiDir
& ".venv\Scripts\python.exe" -m alembic upgrade head
Pop-Location

Write-Host "Seeding the Stage 6 exercise library ..."
Push-Location $ApiDir
& ".venv\Scripts\python.exe" "scripts\seed_exercises.py"
Pop-Location

# --- 4. Frontend: dependencies ---
$WebDir = Join-Path $RepoRoot "apps\web"
if (-not (Test-Path (Join-Path $WebDir "node_modules"))) {
    Write-Host "Installing frontend dependencies ..."
    Push-Location $WebDir
    npm install
    Pop-Location
}
if (-not (Test-Path (Join-Path $WebDir ".env.local"))) {
    Copy-Item (Join-Path $WebDir ".env.example") (Join-Path $WebDir ".env.local")
}

Write-Host ""
Write-Host "Setup complete. Next steps:"
Write-Host "  1. cd apps/api; .venv\Scripts\python.exe -m uvicorn app.main:app --reload"
Write-Host "  2. In another terminal: cd apps/web; npm run dev"
Write-Host "  3. Open http://localhost:3000"
