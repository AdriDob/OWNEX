#!/usr/bin/env pwsh
<#
.SYNOPSIS
    CATEYE Windows Build — one command to build, package, and deploy.
.DESCRIPTION
    Runs on Windows only. Builds frontend, PyInstaller EXE, and NSIS installer,
    then copies output to the user's OneDrive desktop folder and runs install.bat.
.NOTES
    Version: 3.0.0
    Author: CATEYE Labs
#>

$ErrorActionPreference = "Stop"
$VERSION = "3.0.0"

$PROJECT_DIR = Split-Path -Parent $PSScriptRoot
$DIST_DIR = Join-Path $PROJECT_DIR "dist"
$BUILD_DIR = Join-Path $PROJECT_DIR "build"
$FRONTEND_DIR = Join-Path $PROJECT_DIR "frontend"

# ── Final target (OneDrive desktop) ──
$TARGET_ROOT = "$env:USERPROFILE\OneDrive\Desktop\Yo\privado\windows"
$TARGET_DIR = Join-Path $TARGET_ROOT "CATEYE"

$PADDING = " " * 22

function Log($step, $msg) {
    $ts = Get-Date -Format "HH:mm:ss"
    Write-Host "[$ts] [$($step.PadLeft(20))] $msg"
}

function Check-Command($name, $installMsg) {
    if (-not (Get-Command $name -ErrorAction SilentlyContinue)) {
        Log "PRECHECK" "$name — NOT FOUND"
        Write-Host "  >> $installMsg" -ForegroundColor Yellow
        exit 1
    }
    Log "PRECHECK" "$name — OK"
}

# ═══════════════════════════════════════════════════════════════════
# STEP 0 — Prechecks
# ═══════════════════════════════════════════════════════════════════
Log "BUILD" "CATEYE Windows Builder v$VERSION"
Log "BUILD" "Project: $PROJECT_DIR"

Check-Command "node" "Install from https://nodejs.org (LTS recommended)"
Check-Command "npm" "Comes with Node.js"
Check-Command "python" "Install from https://www.python.org/downloads/ (3.10+)"
Check-Command "pyinstaller" "Run: pip install pyinstaller"
Check-Command "makensis" "Install NSIS from https://nsis.sourceforge.io/Download"

# ═══════════════════════════════════════════════════════════════════
# STEP 1 — Clean previous builds
# ═══════════════════════════════════════════════════════════════════
Log "CLEAN" "Removing dist/ and build/release/ ..."
if (Test-Path $DIST_DIR) { Remove-Item -Recurse -Force $DIST_DIR }
$buildRelease = Join-Path $BUILD_DIR "release"
if (Test-Path $buildRelease) { Remove-Item -Recurse -Force $buildRelease }
Log "CLEAN" "OK"

# ═══════════════════════════════════════════════════════════════════
# STEP 2 — Frontend build
# ═══════════════════════════════════════════════════════════════════
Log "FRONTEND" "Building frontend..."

Set-Location $FRONTEND_DIR
Log "FRONTEND" "npm ci..."
npm ci --silent
if ($LASTEXITCODE -ne 0) { Log "FRONTEND" "FAILED (npm ci)"; exit 1 }

Log "FRONTEND" "npm run build..."
npm run build
if ($LASTEXITCODE -ne 0) { Log "FRONTEND" "FAILED (npm run build)"; exit 1 }

$frontendDist = Join-Path $FRONTEND_DIR "dist"
$htmlFiles = Get-ChildItem -Path $frontendDist -Filter "*.html" -Recurse
if (-not $htmlFiles) { Log "FRONTEND" "FAILED — no index.html"; exit 1 }

$frontendSize = (Get-ChildItem -Path $frontendDist -Recurse | Measure-Object -Property Length -Sum).Sum
$frontendCount = (Get-ChildItem -Path $frontendDist -Recurse).Count
Log "FRONTEND" "OK — $([math]::Round($frontendSize/1KB)) KB in $frontendCount files"

Set-Location $PROJECT_DIR

# ═══════════════════════════════════════════════════════════════════
# STEP 3 — PyInstaller
# ═══════════════════════════════════════════════════════════════════
Log "PYINSTALLER" "Building CATEYE.exe (pyinstaller CATEYE.spec -y)..."
pyinstaller CATEYE.spec -y
if ($LASTEXITCODE -ne 0) { Log "PYINSTALLER" "FAILED"; exit 1 }

$exePath = Join-Path $DIST_DIR "CATEYE" "CATEYE.exe"
if (-not (Test-Path $exePath)) { Log "PYINSTALLER" "FAILED — $exePath not found"; exit 1 }

$exeSize = (Get-Item $exePath).Length
Log "PYINSTALLER" "OK — $([math]::Round($exeSize/1MB, 1)) MB"

# ═══════════════════════════════════════════════════════════════════
# STEP 4 — NSIS Installer
# ═══════════════════════════════════════════════════════════════════
Log "INSTALLER" "Building NSIS installer..."
$nsiPath = Join-Path $PROJECT_DIR "installer" "cateye.nsi"

Set-Location (Join-Path $PROJECT_DIR "installer")
makensis "/DPRODUCT_VERSION=$VERSION" "cateye.nsi"
if ($LASTEXITCODE -ne 0) { Log "INSTALLER" "FAILED"; exit 1 }

$installerPath = Join-Path $DIST_DIR "CATEYEInstaller.exe"
if (-not (Test-Path $installerPath)) {
    Log "INSTALLER" "FAILED — CATEYEInstaller.exe not found in dist/"
    exit 1
}
$installerSize = (Get-Item $installerPath).Length
Log "INSTALLER" "OK — $([math]::Round($installerSize/1MB, 1)) MB"

Set-Location $PROJECT_DIR

# ═══════════════════════════════════════════════════════════════════
# STEP 5 — Prepare release output
# ═══════════════════════════════════════════════════════════════════
$releaseDir = Join-Path $BUILD_DIR "release"
New-Item -ItemType Directory -Force -Path $releaseDir | Out-Null

Log "RELEASE" "Copying PyInstaller build..."
$cateyeDist = Join-Path $DIST_DIR "CATEYE"
Copy-Item -Recurse -Path $cateyeDist -Destination $releaseDir

Log "RELEASE" "Copying installer..."
Copy-Item -Path $installerPath -Destination $releaseDir

# Documentation
Log "DOCS" "Generating documentation..."
$readme = Join-Path $releaseDir "README.txt"
@"
========================================
         CATEYE v$VERSION
   Automated Security Investigation OS
========================================

  Dashboard:  http://127.0.0.1:8000

--  Getting Started  --

  1. Run CATEYE\CATEYE.exe --tray
  2. Open http://127.0.0.1:8000 in your browser
  3. Right-click tray icon for: Dashboard, Stop, View Logs

--  System Requirements  --

  * Windows 11 64-bit
  * 4 GB RAM (8 GB recommended)
  * No Python or Node.js required

--  v$VERSION - $(Get-Date -Format 'yyyy-MM-dd')  --
"@ | Out-File -FilePath $readme -Encoding utf8

$changelog = Join-Path $releaseDir "CHANGELOG.md"
@"
# Changelog

## v$VERSION ($(Get-Date -Format 'yyyy-MM-dd'))

### Release
- CATEYE v$VERSION Stable
- Build pipeline reproducible
- NSIS installer with Windows 11 support
- PyInstaller single-directory executable
- Watchdog with auto-recovery
- Multi-agent architecture (exploit, research, financial, strategy, validator, coordinator)
- 40+ API routers for security investigation
- Vue 3 + TypeScript frontend
- Service mode (optional, requires pywin32)
- Auto-update framework with safe rollback
"@ | Out-File -FilePath $changelog -Encoding utf8

$versionTxt = Join-Path $releaseDir "VERSION.txt"
"$VERSION`n" | Out-File -FilePath $versionTxt -Encoding utf8

$licenseFile = Join-Path $releaseDir "LICENSE.txt"
@"
CATEYE v$VERSION
Copyright (c) $(Get-Date -Format 'yyyy') CATEYE Labs

All rights reserved.

This software is protected by intellectual property laws.
Unauthorized distribution, modification, or use is prohibited.

For personal use only.
Non-transferable license.
"@ | Out-File -FilePath $licenseFile -Encoding utf8

# ═══════════════════════════════════════════════════════════════════
# STEP 6 — Copy to final destination
# ═══════════════════════════════════════════════════════════════════
Log "DEPLOY" "Copying to: $TARGET_DIR"
if (Test-Path $TARGET_DIR) {
    Remove-Item -Recurse -Force $TARGET_DIR
}
New-Item -ItemType Directory -Force -Path $TARGET_DIR | Out-Null

# Copy CATEYE/ directory contents (the PyInstaller output)
$releaseCateye = Join-Path $releaseDir "CATEYE"
Copy-Item -Recurse -Path $releaseCateye -Destination $TARGET_DIR

# Copy supporting files
foreach ($f in @("README.txt", "CHANGELOG.md", "VERSION.txt", "LICENSE.txt", "CATEYEInstaller.exe")) {
    $src = Join-Path $releaseDir $f
    if (Test-Path $src) { Copy-Item -Path $src -Destination $TARGET_DIR }
}

# Copy install.bat (from scripts/install_portable.bat → target install.bat)
$installBatSrc = Join-Path $PROJECT_DIR "scripts" "install_portable.bat"
if (Test-Path $installBatSrc) {
    Copy-Item -Path $installBatSrc -Destination (Join-Path $TARGET_DIR "install.bat")
}

# Copy run.bat
$runBatSrc = Join-Path $PROJECT_DIR "scripts" "run_portable.bat"
if (Test-Path $runBatSrc) {
    Copy-Item -Path $runBatSrc -Destination (Join-Path $TARGET_DIR "run.bat")
}

Log "DEPLOY" "OK — files deployed to $TARGET_DIR"

# ═══════════════════════════════════════════════════════════════════
# STEP 7 — Verify
# ═══════════════════════════════════════════════════════════════════
Log "VERIFY" "Verifying deployment..."

$checks = @(
    @{Path = "CATEYE.exe"; Label = "Binary"}
    @{Path = "CATEYEInstaller.exe"; Label = "Installer"}
    @{Path = "README.txt"; Label = "README"}
    @{Path = "CHANGELOG.md"; Label = "Changelog"}
    @{Path = "VERSION.txt"; Label = "Version"}
    @{Path = "LICENSE.txt"; Label = "License"}
    @{Path = "install.bat"; Label = "Install script"}
    @{Path = "run.bat"; Label = "Run script"}
)

$allOk = $true
foreach ($check in $checks) {
    $fullPath = Join-Path $TARGET_DIR $check.Path
    if (Test-Path $fullPath) {
        $size = (Get-Item $fullPath).Length
        $sizeStr = if ($size -gt 1MB) { "$([math]::Round($size/1MB, 1)) MB" } else { "$([math]::Round($size/1KB)) KB" }
        Log "VERIFY" "  [OK] $($check.Path) ($sizeStr)"
    } else {
        Log "VERIFY" "  [MISSING] $($check.Path)"
        $allOk = $false
    }
}

# Check frontend dist inside PyInstaller
$internalFrontend = Join-Path $TARGET_DIR "_internal" "frontend_dist" "index.html"
if (Test-Path $internalFrontend) {
    Log "VERIFY" "  [OK] _internal/frontend_dist/index.html"
} else {
    $directFrontend = Join-Path $TARGET_DIR "frontend_dist" "index.html"
    if (Test-Path $directFrontend) {
        Log "VERIFY" "  [OK] frontend_dist/index.html"
    } else {
        Log "VERIFY" "  [WARN] Frontend assets not found"
    }
}

$totalSize = (Get-ChildItem -Path $TARGET_DIR -Recurse | Measure-Object -Property Length -Sum).Sum
Log "VERIFY" "Total size: $([math]::Round($totalSize/1MB, 1)) MB in $(@(Get-ChildItem -Path $TARGET_DIR -Recurse).Count) files"

if (-not $allOk) {
    Log "VERIFY" "Some files are missing — check output above"
    exit 1
}

# ═══════════════════════════════════════════════════════════════════
# STEP 8 — Run install.bat
# ═══════════════════════════════════════════════════════════════════
Log "INSTALL" "Running install.bat..."

$installBat = Join-Path $TARGET_DIR "install.bat"
if (Test-Path $installBat) {
    Set-Location $TARGET_DIR
    & cmd /c "install.bat"
    if ($LASTEXITCODE -eq 0) {
        Log "INSTALL" "OK — CATEYE quedo configurado correctamente."
    } else {
        Log "INSTALL" "WARN — install.bat returned exit code $LASTEXITCODE"
    }
    Set-Location $PROJECT_DIR
} else {
    Log "INSTALL" "SKIP — install.bat not found"
}

# ═══════════════════════════════════════════════════════════════════
# DONE
# ═══════════════════════════════════════════════════════════════════
Log "BUILD" ("─" * 50)
Log "BUILD" "BUILD COMPLETE"
Log "BUILD" "  Output:  $releaseDir"
Log "BUILD" "  Target:  $TARGET_DIR"
Log "BUILD" "  To launch: run.bat or CATEYE.exe --tray"
Log "BUILD" "  Dashboard: http://127.0.0.1:8000"
Log "BUILD" "DONE"
