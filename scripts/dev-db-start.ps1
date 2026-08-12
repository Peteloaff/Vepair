<#
.SYNOPSIS
  Starts the VepAIr development PostgreSQL service.

.DESCRIPTION
  Uses the standard Windows postgresql-x64-17 service on port 5432. Requires the one-time
  admin setup in scripts/setup.ps1 (creates the `vepair` role/database) to have been run,
  and requires administrator rights to start/stop the service.
#>

$ErrorActionPreference = "Stop"

$svc = Get-Service postgresql-x64-17 -ErrorAction SilentlyContinue
if (-not $svc) {
    Write-Error "postgresql-x64-17 service not found. Install PostgreSQL 17 first."
}
if ($svc.Status -ne "Running") {
    Start-Service postgresql-x64-17
    Write-Host "Started postgresql-x64-17."
} else {
    Write-Host "postgresql-x64-17 is already running."
}
