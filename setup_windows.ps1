$ErrorActionPreference = "Stop"

Write-Host "=== OWNEX v5.1.0 - Windows 11 Installer ===" -ForegroundColor Cyan
Write-Host ""

$projectDir = $PSScriptRoot
if (-not $projectDir) {
    $projectDir = Get-Location
}

Write-Host "Project: $projectDir" -ForegroundColor Yellow

# ── 1. Check Python ──
Write-Host "[1/5] Checking Python..." -ForegroundColor Cyan
try {
    $pyVersion = python --version 2>&1
    Write-Host "  ✓ $pyVersion" -ForegroundColor Green
} catch {
    Write-Host "  ✗ Python not found. Install from https://www.python.org/downloads/" -ForegroundColor Red
    exit 1
}

# ── 2. Virtual environment ──
Write-Host "[2/5] Setting up virtual environment..." -ForegroundColor Cyan
if (-not (Test-Path ".venv")) {
    python -m venv .venv
    Write-Host "  ✓ Virtual environment created" -ForegroundColor Green
} else {
    Write-Host "  ✓ Virtual environment exists" -ForegroundColor Green
}

# ── 3. Activate ──
.venv\Scripts\Activate.ps1

# ── 4. Install ──
Write-Host "[3/5] Installing dependencies..." -ForegroundColor Cyan
pip install --quiet --upgrade pip setuptools wheel
pip install --quiet -e .
Write-Host "  ✓ Dependencies installed" -ForegroundColor Green

# ── 5. Environment ──
Write-Host "[4/5] Configuring environment..." -ForegroundColor Cyan
if (-not (Test-Path ".env")) {
    if (Test-Path ".env.example") {
        Copy-Item .env.example .env
        Write-Host "  ✓ Created .env" -ForegroundColor Green
    } else {
        @"
ENVIRONMENT=development
DATABASE_URL=sqlite:///./ownex.db
LOG_LEVEL=INFO
ENABLE_SENSORS=true
ENABLE_PLAYWRIGHT=true
PORT=8000
"@ | Out-File -FilePath .env -Encoding utf8
        Write-Host "  ✓ Created .env" -ForegroundColor Green
    }
}

# ── 6. Start ──
Write-Host "[5/5] Verification..." -ForegroundColor Cyan
python -c "
import sys
mods = ['api', 'core.capabilities.registry', 'core.events.event_bus']
for mod in mods:
    try:
        __import__(mod)
        print(f'  [OK] {mod}')
    except Exception as e:
        print(f'  [FAIL] {mod}: {e}')
        sys.exit(1)
print('All imports OK')
"

Write-Host ""
Write-Host "=== Installation complete! ===" -ForegroundColor Green
Write-Host "  Start: python -m api.main" -ForegroundColor White
Write-Host "  Doctor: python scripts\ownex_doctor.py" -ForegroundColor White
Write-Host "  API Docs: http://localhost:8000/docs" -ForegroundColor White
Write-Host ""