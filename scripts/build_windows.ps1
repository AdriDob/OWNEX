#!/usr/bin/env pwsh
<#
.SYNOPSIS
    OWNEX Windows Build — builds the Tauri desktop bundle + MSI on Windows.
.DESCRIPTION
    Local mirror of .github/workflows/ownex-tauri-windows.yml (job: build-tauri).
    Runs on Windows only. Produces:

      src-tauri\target\release\bundle\msi\*.msi   ← the installable artifact

    Pipeline (same order as CI):
      0. Preflight tools + version
      1. Clean previous build outputs
      2. Frontend build (npm ci + npm run build)
      3. PyInstaller ONEFILE backend → dist\ownex-backend.exe
      4. Sidecar → src-tauri\binaries\ownex-backend-x86_64-pc-windows-msvc.exe
      5. Sidecar smoke test (real /api/health probe)
      6. WebView2 presence check
      7. Tauri build → MSI + SHA256
      8. Verify artifacts exist

    Notes:
      - The NSIS installer (installer\OWNEX-Desktop-Alpha.nsi) is ARCHIVED.
        The maintained Windows path is the Tauri MSI. Do not add NSIS back.
      - Tauri v2 resolves externalBin "binaries/ownex-backend" to
        "binaries/ownex-backend-<target-triple>.exe" at build time. The file on
        disk MUST carry the triple suffix, else build-script-build fails with
        "resource path ... doesn't exist".
.NOTES
    Version: 7.7.7
#>

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$PROJECT_DIR = Split-Path -Parent $PSScriptRoot
$DIST_DIR    = Join-Path $PROJECT_DIR "dist"
$FRONTEND_DIR = Join-Path $PROJECT_DIR "frontend"
$TAURI_DIR   = Join-Path $PROJECT_DIR "src-tauri"
$BINARIES_DIR = Join-Path $TAURI_DIR "binaries"
$BUNDLE_DIR  = Join-Path $TAURI_DIR "target" "release" "bundle"

# Tauri v2 target triple for the maintained Windows build.
$SIDECAR_NAME = "ownex-backend-x86_64-pc-windows-msvc.exe"
$SIDECAR_PATH = Join-Path $BINARIES_DIR $SIDECAR_NAME

# Port used only for the sidecar smoke test (never collides with a real run).
$SMOKE_PORT = 8199

function Log($step, $msg) {
    $ts = Get-Date -Format "HH:mm:ss"
    Write-Host "[$ts] [$($step.PadLeft(10))] $msg"
}

function Fail($step, $msg) {
    Write-Host "[$step] FAIL: $msg" -ForegroundColor Red
    exit 1
}

function Assert-Tool($name, $installMsg) {
    if (-not (Get-Command $name -ErrorAction SilentlyContinue)) {
        Write-Host "  >> $installMsg" -ForegroundColor Yellow
        Fail "PRECHECK" "$name not found"
    }
    Log "PRECHECK" "$name OK"
}

# ═══════════════════════════════════════════════════════════════════
# STEP 0 — Preflight
# ═══════════════════════════════════════════════════════════════════
$versionFile = Join-Path $PROJECT_DIR "VERSION.txt"
if (-not (Test-Path $versionFile)) { Fail "PRECHECK" "VERSION.txt not found at repo root" }
$VERSION = (Get-Content $versionFile -Raw).Trim()
Log "BUILD" "OWNEX Windows Builder — version $VERSION"
Log "BUILD" "Project: $PROJECT_DIR"

if ($PSVersionTable.PSVersion.Major -lt 7) {
    Log "PRECHECK" "Windows PowerShell 5 detected. PowerShell 7+ recommended (pwsh)."
}

Assert-Tool "node"  "Install from https://nodejs.org (LTS 20+)"
Assert-Tool "npm"   "Ships with Node.js"
Assert-Tool "cargo" "Install Rust from https://rustup.rs (needed by Tauri)"

# Windows ships `python`; POSIX uses `python3`. Accept both so the script is
# runnable from WSL/Git Bash too (useful to validate the flow before the
# Windows-only steps).
$pythonCmd = $null
foreach ($c in @("python", "python3", "py")) {
    if (Get-Command $c -ErrorAction SilentlyContinue) { $pythonCmd = $c; break }
}
if (-not $pythonCmd) {
    Write-Host "  >> Install from https://www.python.org/downloads/ (3.11+)" -ForegroundColor Yellow
    Fail "PRECHECK" "no python interpreter found"
}
Log "PRECHECK" "python OK ($pythonCmd)"

$pyinstallerCmd = $null
if (Get-Command "pyinstaller" -ErrorAction SilentlyContinue) {
    $pyinstallerCmd = "pyinstaller"
} else {
    foreach ($p in @(
        (Join-Path $PROJECT_DIR ".venv\Scripts\pyinstaller.exe"),
        (Join-Path $PROJECT_DIR ".venv\bin\pyinstaller")
    )) {
        if (Test-Path $p) { $pyinstallerCmd = $p; break }
    }
}
if (-not $pyinstallerCmd) {
    Write-Host "  >> pip install pyinstaller  (or create a .venv with requirements.txt)" -ForegroundColor Yellow
    Fail "PRECHECK" "pyinstaller not found"
}
$PYINSTALLER = $pyinstallerCmd
Log "PRECHECK" "pyinstaller OK ($PYINSTALLER)"

$rustcVersion = (& rustc --version)
Log "PRECHECK" "$rustcVersion"

Set-Location $PROJECT_DIR

# ═══════════════════════════════════════════════════════════════════
# STEP 1 — Clean previous outputs
# ═══════════════════════════════════════════════════════════════════
Log "CLEAN" "Removing dist\, src-tauri\binaries\ownex-backend-*.exe and bundle\"
if (Test-Path $DIST_DIR) { Remove-Item -Recurse -Force $DIST_DIR }
if (Test-Path $BUNDLE_DIR) { Remove-Item -Recurse -Force $BUNDLE_DIR }
if (Test-Path $BINARIES_DIR) {
    Get-ChildItem $BINARIES_DIR -Filter "ownex-backend-*.exe" -ErrorAction SilentlyContinue |
        Remove-Item -Force
}
Log "CLEAN" "OK"

# ═══════════════════════════════════════════════════════════════════
# STEP 2 — Frontend build
# ═══════════════════════════════════════════════════════════════════
Log "FRONTEND" "Installing dependencies (root workspace)..."
Set-Location $PROJECT_DIR
npm ci --no-audit --no-fund
if ($LASTEXITCODE -ne 0) { Fail "FRONTEND" "npm ci failed at repo root" }

Set-Location $FRONTEND_DIR
Log "FRONTEND" "npm run build..."
npm run build
if ($LASTEXITCODE -ne 0) { Fail "FRONTEND" "npm run build failed" }

$frontendDist = Join-Path $FRONTEND_DIR "dist"
if (-not (Test-Path (Join-Path $frontendDist "index.html"))) {
    Fail "FRONTEND" "dist\index.html missing — frontend build produced nothing usable"
}
$frontendSize = (Get-ChildItem $frontendDist -Recurse | Measure-Object -Property Length -Sum).Sum
Log "FRONTEND" "OK — $([math]::Round($frontendSize/1KB)) KB in $frontendDist"

Set-Location $PROJECT_DIR

# ═══════════════════════════════════════════════════════════════════
# STEP 3 — PyInstaller backend (ONEFILE)
# ═══════════════════════════════════════════════════════════════════
Log "PYINSTALLER" "Building backend sidecar (ONEFILE)..."
& $PYINSTALLER OWNEX-Backend.spec --clean --noconfirm
if ($LASTEXITCODE -ne 0) { Fail "PYINSTALLER" "pyinstaller failed" }

$exePath = Join-Path $DIST_DIR "ownex-backend.exe"
if (-not (Test-Path $exePath)) { Fail "PYINSTALLER" "expected $exePath" }
$exeSize = (Get-Item $exePath).Length
if ($exeSize -lt 50MB) { Fail "PYINSTALLER" "sidecar suspiciously small ($([math]::Round($exeSize/1MB,2)) MB)" }
Log "PYINSTALLER" "OK — $([math]::Round($exeSize/1MB,1)) MB"

# ═══════════════════════════════════════════════════════════════════
# STEP 4 — Prepare Tauri sidecar (triple suffix REQUIRED)
# ═══════════════════════════════════════════════════════════════════
Log "SIDECAR" "Copying to $SIDECAR_NAME"
if (-not (Test-Path $BINARIES_DIR)) { New-Item -ItemType Directory -Path $BINARIES_DIR -Force | Out-Null }
Copy-Item $exePath $SIDECAR_PATH -Force
if (-not (Test-Path $SIDECAR_PATH)) { Fail "SIDECAR" "copy failed — Tauri would fail with 'resource path ... doesn't exist'" }
Log "SIDECAR" "OK — $SIDECAR_PATH"

# ═══════════════════════════════════════════════════════════════════
# STEP 5 — Sidecar smoke test (REAL probe, no mocks)
# ═══════════════════════════════════════════════════════════════════
Log "SMOKE" "Starting sidecar on port $SMOKE_PORT and probing /api/health ..."
$errFile = Join-Path $env:TEMP "ownex_sidecar_err.txt"
$outFile = Join-Path $env:TEMP "ownex_sidecar_out.txt"
$proc = Start-Process $exePath -ArgumentList "--port", "$SMOKE_PORT", "--log-level", "INFO" `
    -PassThru -RedirectStandardError $errFile -RedirectStandardOutput $outFile

$healthy = $false
for ($i = 0; $i -lt 90; $i++) {
    Start-Sleep -Seconds 2
    if ($proc.HasExited) { break }
    try {
        $resp = Invoke-RestMethod "http://127.0.0.1:$SMOKE_PORT/api/health" -TimeoutSec 5
        $healthy = $true
        break
    } catch { }
}

if (-not $proc.HasExited) { Stop-Process -Id $proc.Id -Force }
if (-not $healthy) {
    Write-Host "=== sidecar stderr ===" -ForegroundColor Red
    Get-Content $errFile -Tail 60 -ErrorAction SilentlyContinue | ForEach-Object { $_ }
    Write-Host "=== sidecar stdout ===" -ForegroundColor Red
    Get-Content $outFile -Tail 60 -ErrorAction SilentlyContinue | ForEach-Object { $_ }
    Fail "SMOKE" "sidecar did not answer /api/health on port $SMOKE_PORT"
}
Log "SMOKE" "OK — sidecar healthy (status=$($resp.status), version=$($resp.version))"

# ═══════════════════════════════════════════════════════════════════
# STEP 6 — WebView2 (Tauri needs it at runtime)
# ═══════════════════════════════════════════════════════════════════
$webview2Key = "HKLM:\SOFTWARE\WOW6432Node\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}"
if (Test-Path $webview2Key) {
    $wv = (Get-ItemProperty $webview2Key).pv
    Log "WEBVIEW2" "installed (version $wv)"
} else {
    Log "WEBVIEW2" "NOT detected — the installer will fetch the bootstrapper (needs internet)"
}

# ═══════════════════════════════════════════════════════════════════
# STEP 7 — Tauri build → MSI
# ═══════════════════════════════════════════════════════════════════
Log "TAURI" "Building desktop bundle (this takes several minutes)..."
Set-Location $PROJECT_DIR
$env:RUST_BACKTRACE = "1"
npx tauri build --verbose
if ($LASTEXITCODE -ne 0) { Fail "TAURI" "npx tauri build failed" }

# ═══════════════════════════════════════════════════════════════════
# STEP 8 — Verify artifacts
# ═══════════════════════════════════════════════════════════════════
Log "VERIFY" "Checking bundle output..."
$msi = Get-ChildItem (Join-Path $BUNDLE_DIR "msi") -Filter "*.msi" -ErrorAction SilentlyContinue
if (-not $msi) { Fail "VERIFY" "no .msi found in $BUNDLE_DIR\msi" }

foreach ($f in $msi) {
    $sha = (Get-FileHash $f.FullName -Algorithm SHA256).Hash.ToLower()
    "$sha  $($f.Name)" | Out-File -FilePath "$($f.FullName).sha256" -Encoding ascii
    Log "VERIFY" "[OK] $($f.Name) — $([math]::Round($f.Length/1MB,1)) MB"
    Log "VERIFY" "     sha256: $sha"
}

Log "BUILD" ("─" * 56)
Log "BUILD" "BUILD COMPLETE — version $VERSION"
Log "BUILD" "Installer: $($msi[0].FullName)"
Log "BUILD" "Install it, then launch 'OWNEX Alpha' from the Start menu."
Log "BUILD" "Backend sidecar + logs: %LOCALAPPDATA%\OWNEX"
Log "BUILD" "DONE"
