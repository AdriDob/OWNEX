# Fix VS Code "Access denied to C:\Users\adrie\AppData" error
# Run this in PowerShell as Administrator

Write-Host "=== Fixing VS Code 'Access denied to C:\Users\adrie\AppData' ===" -ForegroundColor Cyan

# 1. Close VS Code first
Write-Host "Closing VS Code..." -ForegroundColor Yellow
Stop-Process -Name "Code" -Force -ErrorAction SilentlyContinue
Start-Sleep 2

# 2. Clean VS Code caches
$pathsToClean = @(
    "$env:APPDATA\Code\Cache",
    "$env:APPDATA\Code\CachedData",
    "$env:APPDATA\Code\CachedExtensions",
    "$env:APPDATA\Code\Cache",
    "$env:LOCALAPPDATA\Code\Cache",
    "$env:LOCALAPPDATA\Code\CachedData",
    "$env:LOCALAPPDATA\Code\CachedExtensions",
    "$env:APPDATA\Code\User\workspaceStorage",
    "$env:APPDATA\Code\User\History"
)

foreach ($path in $pathsToClean) {
    if (Test-Path $path) {
        Write-Host "Cleaning: $path" -ForegroundColor Yellow
        Remove-Item $path -Recurse -Force -ErrorAction SilentlyContinue
    }
}

# 3. Clean Python caches (if Python extension is causing issues)
$pythonCaches = @(
    "$env:APPDATA\Python",
    "$env:LOCALAPPDATA\pip\Cache",
    "$env:LOCALAPPDATA\Python\pip\Cache"
)

foreach ($path in $pythonCaches) {
    if (Test-Path $path) {
        Write-Host "Cleaning Python cache: $path" -ForegroundColor Yellow
        Remove-Item $path -Recurse -Force -ErrorAction SilentlyContinue
    }
}

# 4. Check VS Code global settings for hardcoded paths
$settingsPath = "$env:APPDATA\Code\User\settings.json"
if (Test-Path $settingsPath) {
    $content = Get-Content $settingsPath -Raw
    if ($content -match "adrie|C:\\Users\\adrie") {
        Write-Host "WARNING: Found 'adrie' in global settings.json!" -ForegroundColor Red
        Write-Host "Path: $settingsPath" -ForegroundColor Yellow
        # Backup and clean
        Copy-Item $settingsPath "$settingsPath.backup_$(Get-Date -Format 'yyyyMMdd_HHmmss')" -Force
        $content = $content -replace 'C:\\\\Users\\\\adrie', '$env:USERPROFILE'
        $content = $content -replace 'adrie', $env:USERNAME
        Set-Content $settingsPath $content -Encoding UTF8
        Write-Host "Fixed settings.json" -ForegroundColor Green
    }
}

# 5. Clean workspace storage (may have old paths)
$workspaceStorage = "$env:APPDATA\Code\User\workspaceStorage"
if (Test-Path $workspaceStorage) {
    Get-ChildItem $workspaceStorage -Recurse -File -Filter "*.json" | ForEach-Object {
        $content = Get-Content $_.FullName -Raw
        if ($content -match "adrie|C:\\Users\\adrie") {
            Write-Host "Found old path in: $($_.FullName)" -ForegroundColor Yellow
            $content = $content -replace 'C:\\\\Users\\\\adrie', "$env:USERPROFILE"
            $content = $content -replace 'adrie', $env:USERNAME
            Set-Content $_.FullName $content -Encoding UTF8
        }
    }
}

# 6. Restart VS Code
Write-Host "Restarting VS Code..." -ForegroundColor Cyan
Start-Process "code"

Write-Host "=== Done! ===" -ForegroundColor Green
Write-Host "If error persists, check VS Code Output panel (View > Output > Log (Window))" -ForegroundColor Yellow
