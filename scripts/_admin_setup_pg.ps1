<#
  Elevated one-time setup: configure the Windows postgresql-x64-17 service (port 5432)
  for VepAIr local development. Run only via Start-Process -Verb RunAs (see caller).
#>

$ErrorActionPreference = "Stop"
$LogFile = "$env:TEMP\vepair-admin-setup.log"
Remove-Item $LogFile -ErrorAction SilentlyContinue

function Log($msg) {
    $msg | Tee-Object -FilePath $LogFile -Append
}

try {
    $PgBin = "C:\Program Files\PostgreSQL\17\bin"
    $HbaFile = "C:\Program Files\PostgreSQL\17\data\pg_hba.conf"

    Log "Stopping postgresql-x64-17 service..."
    Stop-Service postgresql-x64-17 -Force
    Start-Sleep -Seconds 2

    Log "Backing up pg_hba.conf..."
    Copy-Item $HbaFile "$HbaFile.bak" -Force

    Log "Temporarily setting local/host auth to trust..."
    (Get-Content $HbaFile) `
        -replace '^(local\s+all\s+all\s+)scram-sha-256', '$1trust' `
        -replace '^(host\s+all\s+all\s+127\.0\.0\.1/32\s+)scram-sha-256', '$1trust' `
        -replace '^(host\s+all\s+all\s+::1/128\s+)scram-sha-256', '$1trust' `
        | Set-Content $HbaFile

    Log "Starting postgresql-x64-17 service..."
    Start-Service postgresql-x64-17
    Start-Sleep -Seconds 3

    Log "Setting postgres superuser password and creating vepair role/database..."
    $env:PGPASSWORD = ""
    & "$PgBin\psql.exe" -U postgres -h 127.0.0.1 -p 5432 -v ON_ERROR_STOP=1 -c "ALTER USER postgres WITH PASSWORD 'postgres';" 2>&1 | ForEach-Object { Log $_ }

    $env:PGPASSWORD = "postgres"
    $roleExists = & "$PgBin\psql.exe" -U postgres -h 127.0.0.1 -p 5432 -tAc "SELECT 1 FROM pg_roles WHERE rolname='vepair'"
    if ($roleExists -ne "1") {
        & "$PgBin\psql.exe" -U postgres -h 127.0.0.1 -p 5432 -v ON_ERROR_STOP=1 -c "CREATE ROLE vepair WITH LOGIN PASSWORD 'vepair';" 2>&1 | ForEach-Object { Log $_ }
    } else {
        Log "Role 'vepair' already exists."
    }

    $dbExists = & "$PgBin\psql.exe" -U postgres -h 127.0.0.1 -p 5432 -tAc "SELECT 1 FROM pg_database WHERE datname='vepair'"
    if ($dbExists -ne "1") {
        & "$PgBin\psql.exe" -U postgres -h 127.0.0.1 -p 5432 -v ON_ERROR_STOP=1 -c "CREATE DATABASE vepair OWNER vepair;" 2>&1 | ForEach-Object { Log $_ }
    } else {
        Log "Database 'vepair' already exists."
    }

    Log "Restoring scram-sha-256 auth..."
    Copy-Item "$HbaFile.bak" $HbaFile -Force
    Remove-Item "$HbaFile.bak"

    Log "Restarting service to apply restored auth config..."
    Restart-Service postgresql-x64-17 -Force
    Start-Sleep -Seconds 3

    Log "Verifying vepair role can connect with password auth..."
    $env:PGPASSWORD = "vepair"
    & "$PgBin\psql.exe" -U vepair -h 127.0.0.1 -p 5432 -d vepair -c "SELECT 'auth ok' AS result;" 2>&1 | ForEach-Object { Log $_ }

    Log "DONE_OK"
}
catch {
    Log "DONE_FAIL: $($_.Exception.Message)"
    # best-effort restore
    if (Test-Path "$HbaFile.bak") {
        Copy-Item "$HbaFile.bak" $HbaFile -Force
        Restart-Service postgresql-x64-17 -Force -ErrorAction SilentlyContinue
    }
}
