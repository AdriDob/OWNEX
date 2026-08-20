<#
.SYNOPSIS
    OWNEX Windows Launcher - Starts OWNEX backend in WSL2 and opens the desktop shell

.DESCRIPTION
    This launcher:
    1. Checks if OWNEX backend is already running on localhost:8000
    2. If not, starts it inside WSL2 Ubuntu using the repo start_backend.sh
    3. Waits for health check to pass
    4. Opens the OWNEX desktop shell (Tauri exe) if installed, else Edge/Chrome app mode
    5. Is idempotent - won't start duplicate processes

.NOTES
    Run from Windows (PowerShell). Requires WSL2 with Ubuntu installed.
    The launcher auto-detects the WSL project path - no manual configuration needed.
    Uses pure PowerShell syntax - all WSL/Linux commands go through bash -lc.
#>

# ============================================================================
# CONFIGURATION - DEFINED DYNAMICALLY
# ============================================================================

# WSL2 distribution name
$WSL_DISTRO = "Ubuntu"

# Launcher and icon paths (relative to script location)
$LAUNCHER_DIR = Split-Path $PSCommandPath -Parent
# Icon path: try relative (dev) or same dir (installed)
$ICON_PATH = if (Test-Path (Join-Path $LAUNCHER_DIR "assets\logos\ownex-icon-alpha.ico")) {
    Join-Path $LAUNCHER_DIR "assets\logos\ownex-icon-alpha.ico"
} else {
    Join-Path $LAUNCHER_DIR "ownex-icon-alpha.ico"
}

# Backend port
$BACKEND_PORT = 8000
$HEALTH_ENDPOINT = "http://127.0.0.1:$BACKEND_PORT/api/health"
$STARTUP_TIMEOUT = 120  # seconds
$HEALTH_CHECK_INTERVAL = 2  # seconds

# Desktop shell candidates (Tauri exe when available, then browser app-mode)
# These are checked in order; first valid one is used
$SHELL_CANDIDATES = @(
    "$env:ProgramFiles\OWNEX\OWNEX-Desktop-Alpha.exe",
    "$env:LOCALAPPDATA\Programs\OWNEX\OWNEX-Desktop-Alpha.exe",
    "$env:LOCALAPPDATA\Programs\OWNEX OMEGA\OWNEX OMEGA.exe",
    "$env:ProgramFiles\OWNEX OMEGA\OWNEX OMEGA.exe",
    "$PSScriptRoot\OWNEX-Desktop-Alpha.exe",
    "$PSScriptRoot\src-tauri\target\release\OWNEX-Desktop-Alpha.exe",
    "$PSScriptRoot\src-tauri\target\release\OWNEX OMEGA.exe"
)

# Browser preference (Edge preferred for --app mode on Windows)
$BROWSER_COMMANDS = @(
    "msedge.exe",
    "chrome.exe",
    "msedge",
    "chrome"
)

# Well-known install paths (fallback when browsers are not on PATH)
$KNOWN_BROWSER_PATHS = @(
    "${env:ProgramFiles(x86)}\Microsoft\Edge\Application\msedge.exe",
    "${env:ProgramFiles}\Microsoft\Edge\Application\msedge.exe",
    "${env:ProgramFiles}\Google\Chrome\Application\chrome.exe",
    "${env:LOCALAPPDATA}\Google\Chrome\Application\chrome.exe"
)

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

function Write-Log {
    param([string]$Message, [string]$Level = "INFO")
    $timestamp = Get-Date -Format "HH:mm:ss"
    $color = switch ($Level) {
        "ERROR" { "Red" }
        "WARN"  { "Yellow" }
        "OK"    { "Green" }
        default { "White" }
    }
    Write-Host "[$timestamp] [$Level] $Message" -ForegroundColor $color
}

function Test-WSL {
    Write-Log "Checking WSL2 availability..."
    try {
        $wslVersion = (wsl.exe --version 2>&1 | Out-String) -replace "`0", ""
        if ($LASTEXITCODE -ne 0) {
            Write-Log "WSL not available or not installed" "ERROR"
            return $false
        }
        Write-Log "WSL available: $($wslVersion.Trim().Substring(0, [Math]::Min(60, $wslVersion.Trim().Length)))" "OK"

        # Check if the distro exists and can run a command
        $distros = (wsl.exe -l -v 2>&1 | Out-String) -replace "`0", ""
        if ($distros -notmatch $WSL_DISTRO) {
            Write-Log "WSL distro '$WSL_DISTRO' not found. Available:" "WARN"
            Write-Host $distros
            return $false
        }

        # Verify the distro actually starts by running a real command
        $probe = (wsl.exe -d $WSL_DISTRO -- echo "OWNEX-WSL-OK" 2>&1 | Out-String) -replace "`0", ""
        if ($LASTEXITCODE -ne 0 -or $probe -notmatch "OWNEX-WSL-OK") {
            Write-Log "WSL distro '$WSL_DISTRO' exists but failed to start a command" "ERROR"
            Write-Host $probe
            return $false
        }
        Write-Log "WSL distro '$WSL_DISTRO' found and responding" "OK"
        return $true
    } catch {
        Write-Log "Error checking WSL: $_" "ERROR"
        return $false
    }
}

function Test-PortInUse {
    param([int]$Port)
    try {
        $listener = [System.Net.Sockets.TcpListener]::new([System.Net.IPAddress]::Loopback, $Port)
        $listener.Start()
        $listener.Stop()
        return $false
    } catch {
        return $true
    }
}

function Invoke-WSLCommand {
    param([string]$Command)
    Write-Log "WSL> $Command" "INFO"
    try {
        $output = & wsl.exe -d $WSL_DISTRO -- bash -lc $Command 2>&1
        if ($LASTEXITCODE -ne 0) {
            Write-Log "WSL command failed (exit $LASTEXITCODE): $output" "ERROR"
            return $null
        }
        return (($output | Out-String) -replace "`0", "").Trim()
    } catch {
        Write-Log "Error running WSL command: $_" "ERROR"
        return $null
    }
}

# Auto-detect the WSL project path by looking for start_backend.sh
function Get-WSLProjectPath {
    # Get the actual WSL username dynamically
    $wslUser = Invoke-WSLCommand "whoami" 2>&1
    if ($wslUser -and $wslUser -notmatch "ERROR") {
        $wslUser = $wslUser.Trim()
        # Check standard project locations for this user
        $testPath = "/home/$wslUser/projects/Rastro/start_backend.sh"
        $exists = Invoke-WSLCommand "test -f '$testPath' && echo exists || echo missing" 2>&1
        if ($exists -eq "exists") {
            return "/home/$wslUser/projects/Rastro"
        }
        # Try alternative location
        $testPath2 = "/home/$wslUser/Rastro/start_backend.sh"
        $exists2 = Invoke-WSLCommand "test -f '$testPath2' && echo exists || echo missing" 2>&1
        if ($exists2 -eq "exists") {
            return "/home/$wslUser/Rastro"
        }
    }

    # Fallback: try searching in all user home directories
    $users = Invoke-WSLCommand "ls /home 2>/dev/null" 2>&1
    if ($users -and $users -notmatch "ERROR") {
        foreach ($user in $users -split "\s+") {
            if ([string]::IsNullOrWhiteSpace($user)) { continue }
            $testPath = "/home/$user/projects/Rastro/start_backend.sh"
            $exists = Invoke-WSLCommand "test -f '$testPath' && echo exists || echo missing" 2>&1
            if ($exists -eq "exists") {
                return "/home/$user/projects/Rastro"
            }
        }
    }

    # Return $null if not found - launcher will use fallback
    return $null
}

# Auto-detect the start_backend.sh script path
$DETECTED_PROJECT_PATH = Get-WSLProjectPath

# Startup script path - uses detected path or falls back
$START_BACKEND_SCRIPT = if ($DETECTED_PROJECT_PATH) {
    "$DETECTED_PROJECT_PATH/start_backend.sh"
} else {
    "$env:USERPROFILE\ownex\start_backend.sh"
}

# ============================================================================
# HELPER FUNCTIONS (continued)
# ============================================================================

function Start-BackendInWSL {
    Write-Log "Starting OWNEX backend in WSL..."
    Write-Log "Checking backend startup script exists..."
    
    # Use the detected project path, or fallback gracefully
    $scriptPath = if ($DETECTED_PROJECT_PATH) {
        "$DETECTED_PROJECT_PATH/start_backend.sh"
    } else {
        "$env:USERPROFILE\ownex\start_backend.sh"
    }
    
    $check = Invoke-WSLCommand "test -f '$scriptPath' && echo exists || echo missing"
    if ($check -ne "exists") {
        Write-Log "start_backend.sh missing in WSL: $scriptPath" "ERROR"
        return $false
    }
    Write-Log "Executing start_backend.sh in WSL..."
    $result = Invoke-WSLCommand "chmod +x '$scriptPath' && '$scriptPath'"
    if ($null -eq $result) {
        Write-Log "Failed to execute start_backend.sh in WSL" "ERROR"
        return $false
    }
    Write-Log "Backend startup script executed in WSL" "OK"
    return $true
}

function Wait-ForHealth {
    Write-Log "Waiting for backend health check at $HEALTH_ENDPOINT..."
    $stopwatch = [System.Diagnostics.Stopwatch]::StartNew()

    while ($stopwatch.Elapsed.TotalSeconds -lt $STARTUP_TIMEOUT) {
        try {
            $response = Invoke-RestMethod -Uri $HEALTH_ENDPOINT -Method Get -TimeoutSec 5 -ErrorAction Stop
            if ($response.status -eq "ok") {
                Write-Log "Backend health check PASSED" "OK"
                return $true
            }
        } catch {
            # Not ready yet, continue waiting
        }

        Start-Sleep -Seconds $HEALTH_CHECK_INTERVAL
        Write-Host "." -NoNewline -ForegroundColor Gray
    }

    Write-Host ""  # newline
    Write-Log "Health check TIMEOUT after ${STARTUP_TIMEOUT}s" "ERROR"

    # Show recent logs for debugging
    Write-Log "Recent backend logs:" "WARN"
    $logs = Invoke-WSLCommand "tail -50 '$($DETECTED_PROJECT_PATH or $env:USERPROFILE\ownex)\logs/backend.log' 2>/dev/null || echo 'No logs found'"
    if ($logs) {
        Write-Host $logs
    }

    return $false
}

function Get-BrowserCommand {
    $candidates = @()
    $candidates += $KNOWN_BROWSER_PATHS
    foreach ($browser in $BROWSER_COMMANDS) {
        try {
            $path = (Get-Command $browser -ErrorAction Stop).Source
            if ($path) { $candidates += $path }
        } catch { }
    }
    foreach ($path in $candidates) {
        if ($path -and (Test-Path $path)) {
            Write-Log "Using browser: $path" "OK"
            return $path
        }
    }
    Write-Log "No suitable browser found (Edge/Chrome required for --app mode)" "WARN"
    return $null
}

function Get-DesktopShell {
    foreach ($candidate in $SHELL_CANDIDATES) {
        if ($candidate -and (Test-Path $candidate)) {
            Write-Log "Found desktop shell: $candidate" "OK"
            return $candidate
        }
    }
    Write-Log "No OWNEX desktop shell installed yet - falling back to browser app mode" "WARN"
    return $null
}

function Open-Dashboard {
    param([string]$BrowserPath)
    $url = "http://127.0.0.1:$BACKEND_PORT"
    Write-Log "Opening dashboard in app mode: $url"

    # Use --app mode for app-like experience (no address bar, tabs)
    $args = "--app=$url --new-window"

    try {
        Start-Process -FilePath $BrowserPath -ArgumentList $args -WindowStyle Normal
        Write-Log "Dashboard opened successfully" "OK"
        return $true
    } catch {
        Write-Log "Failed to open browser: $_" "ERROR"
        # Fallback: open in default browser
        try {
            Start-Process $url
            Write-Log "Opened in default browser (fallback)" "WARN"
            return $true
        } catch {
            Write-Log "Fallback also failed: $_" "ERROR"
            return $false
        }
    }
}

function Ensure-LogsDirectory {
    if ($DETECTED_PROJECT_PATH) {
        $null = Invoke-WSLCommand "mkdir -p '$($DETECTED_PROJECT_PATH)/logs'"
    } else {
        $null = Invoke-WSLCommand "mkdir -p '$env:USERPROFILE\ownex\logs'"
    }
}

# ============================================================================
# MAIN EXECUTION
# ============================================================================

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "              OWNEX Windows Launcher                         " -ForegroundColor Cyan
Write-Host "         Autonomous Intelligence Platform                     " -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

# 1. Verify WSL
if (-not (Test-WSL)) {
    Write-Log "WSL2 with Ubuntu is required but not available." "ERROR"
    Write-Log "Please install WSL2: wsl --install -d Ubuntu" "ERROR"
    exit 1
}

# 2. Ensure logs directory exists
Ensure-LogsDirectory

# 3. Check if backend is already running
Write-Log "Checking if backend is already running on port $BACKEND_PORT..."
$backendAlreadyRunning = $false
if (Test-PortInUse $BACKEND_PORT) {
    Write-Log "Port $BACKEND_PORT is in use - checking health endpoint..." "WARN"

    # Could be our backend or something else - verify health (with retries,
    # the first probe may hit a cold loopback right after the VM wakes)
    $healthOk = $false
    for ($attempt = 1; $attempt -le 3; $attempt++) {
        try {
            $response = Invoke-RestMethod -Uri $HEALTH_ENDPOINT -Method Get -TimeoutSec 5 -ErrorAction Stop
            if ($response.status -eq "ok") {
                $healthOk = $true
                break
            }
        } catch { }
        if ($attempt -lt 3) {
            Write-Host "." -NoNewline -ForegroundColor Gray
            Start-Sleep -Seconds 2
        }
    }
    if ($healthOk) {
        Write-Log "Backend already running and healthy!" "OK"
        $backendAlreadyRunning = $true
    } else {
        Write-Log "Port in use but OWNEX backend not responding (after 3 attempts)" "WARN"
        $backendAlreadyRunning = $false
    }
} else {
    Write-Log "Port $BACKEND_PORT is free" "OK"
    $backendAlreadyRunning = $false
}

# 4. Start backend if not running
if (-not $backendAlreadyRunning) {
    if (-not (Start-BackendInWSL)) {
        Write-Log "Failed to start backend in WSL" "ERROR"
        exit 1
    }

    # Wait for health
    if (-not (Wait-ForHealth)) {
        Write-Log "Backend failed to become healthy. Check logs at:" "ERROR"
        # Use detected path or fallback for log display
        $logPath = if ($DETECTED_PROJECT_PATH) {
            "$DETECTED_PROJECT_PATH/logs/backend.log"
        } else {
            "$env:USERPROFILE\ownex\logs/backend.log"
        }
        Write-Log "  WSL: $logPath" "ERROR"
        write-Log "  Manual: wsl -d $WSL_DISTRO -- bash -lc '$START_BACKEND_SCRIPT'" "ERROR"
        exit 1
    }
} else {
    Write-Log "Reusing existing backend instance" "OK"
}

# 5. Launch the desktop shell (Tauri exe preferred, browser app-mode as fallback)
$shell = Get-DesktopShell
if ($shell) {
    Write-Log "Launching OWNEX desktop shell..."
    try {
        Start-Process -FilePath $shell
        Write-Log "OWNEX desktop shell launched" "OK"
    } catch {
        Write-Log "Failed to launch desktop shell: $_ - falling back to browser" "WARN"
        $browser = Get-BrowserCommand
        if ($browser) {
            Open-Dashboard $browser
        } else {
            Start-Process "http://127.0.0.1:$BACKEND_PORT"
        }
    }
} else {
    $browser = Get-BrowserCommand
    if ($browser) {
        Open-Dashboard $browser
    } else {
        Write-Log "No Edge/Chrome found. Opening in default browser..." "WARN"
        Start-Process "http://127.0.0.1:$BACKEND_PORT"
    }
}

# Done - OWNEX is running, exit launcher
Write-Log "Startup complete - OWNEX is now running" "OK"
