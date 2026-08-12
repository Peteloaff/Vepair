<#
.SYNOPSIS
  Stops the VepAIr development PostgreSQL service. Requires administrator rights.
#>

$ErrorActionPreference = "Stop"
Stop-Service postgresql-x64-17 -Force
