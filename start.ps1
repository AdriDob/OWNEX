$ErrorActionPreference = "Stop"
Write-Host "=== OWNEX v5.1.0 - Starting ===" -ForegroundColor Cyan

if (-not (Test-Path ".venv")) {
    Write-Host "Creating virtual environment..." -ForegroundColor Yellow
    python -m venv .venv
}

& .venv\Scripts\Activate.ps1
Write-Host "Virtual environment activated." -ForegroundColor Green

Write-Host "Installing dependencies..." -ForegroundColor Yellow
pip install -e . --quiet

Write-Host "Starting OWNEX API..." -ForegroundColor Green
python -m api.main