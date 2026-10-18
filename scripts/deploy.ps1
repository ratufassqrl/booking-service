# Deploy a specific image version from GHCR to the local environment.
# Usage (PowerShell, from the project folder):
#   .\scripts\deploy.ps1 -Image ghcr.io/<your-login>/booking-service -Version 0.1.0
param(
    [Parameter(Mandatory = $true)][string]$Image,
    [Parameter(Mandatory = $true)][string]$Version
)

$ErrorActionPreference = "Stop"
$env:BOOKING_IMAGE = $Image.ToLower()
$env:IMAGE_TAG = $Version

Write-Host "Pulling $($env:BOOKING_IMAGE):$Version ..."
docker compose pull app
if ($LASTEXITCODE -ne 0) { throw "docker compose pull failed" }

Write-Host "Starting environment ..."
docker compose up -d --no-build
if ($LASTEXITCODE -ne 0) { throw "docker compose up failed" }

for ($i = 0; $i -lt 30; $i++) {
    try {
        $health = Invoke-RestMethod http://localhost:8000/health -TimeoutSec 2
        if ($health.status -eq "ok") { break }
    } catch { Start-Sleep -Seconds 1 }
}

$deployed = (Invoke-RestMethod http://localhost:8000/version).version
Write-Host "Deployed version: $deployed"
if ($deployed -ne $Version) { throw "Expected version $Version, got $deployed" }
Write-Host "OK" -ForegroundColor Green
