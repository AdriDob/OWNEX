<#
.SYNOPSIS
    ORION Desktop Tools — Universal Installer
    Installs 30+ essential tools via winget (primary), choco (fallback), scoop (portable).
.DESCRIPTION
    Categories: Development, Security, AI, Productivity, Media, System, Gaming
    Run: powershell -ExecutionPolicy Bypass -File install_desktop_tools.ps1
#>

$ErrorActionPreference = "Continue"
$categories = @{}

# ── Tool definitions ────────────────────────────────────────────

$tools = @(
    # ── Development ──
    @{name="Git"; winget="Git.Git"; category="Development"; essential=$true},
    @{name="Python 3"; winget="Python.Python.3.13"; category="Development"; essential=$true},
    @{name="Node.js"; winget="OpenJS.NodeJS.LTS"; category="Development"; essential=$true},
    @{name="Rust"; winget="Rustlang.Rustup"; category="Development"; essential=$false},
    @{name="Go"; winget="GoLang.Go"; category="Development"; essential=$false},
    @{name="Docker Desktop"; winget="Docker.DockerDesktop"; category="Development"; essential=$true},
    @{name="VS Code"; winget="Microsoft.VisualStudioCode"; category="Development"; essential=$true},
    @{name="Windows Terminal"; winget="Microsoft.WindowsTerminal"; category="Development"; essential=$true},
    @{name="WSL"; winget="Microsoft.WSL"; category="Development"; essential=$true},
    @{name="PowerShell 7"; winget="Microsoft.PowerShell"; category="Development"; essential=$false},
    @{name="Oh My Posh"; winget="JanDeDobbeleer.OhMyPosh"; category="Development"; essential=$false},
    @{name="Nushell"; scoop="nushell"; category="Development"; essential=$false},

    # ── Security / Bug Bounty ──
    @{name="Burp Suite"; winget="PortSwigger.BurpSuite.Community"; category="Security"; essential=$true},
    @{name="Wireshark"; winget="WiresharkFoundation.Wireshark"; category="Security"; essential=$false},
    @{name="Proxyman"; winget="Proxyman.Proxyman"; category="Security"; essential=$false},

    # ── AI / LLM ──
    @{name="Ollama"; winget="Ollama.Ollama"; category="AI"; essential=$true},
    @{name="Pinokio"; winget="Pinokio.Pinokio"; category="AI"; essential=$false},

    # ── Productivity ──
    @{name="PowerToys"; winget="Microsoft.PowerToys"; category="Productivity"; essential=$true},
    @{name="Everything"; winget="voidtools.Everything"; category="Productivity"; essential=$true},
    @{name="Obsidian"; winget="Obsidian.Obsidian"; category="Productivity"; essential=$true},
    @{name="AutoHotkey"; winget="Lexikos.AutoHotkey"; category="Productivity"; essential=$false},
    @{name="ShareX"; winget="ShareX.ShareX"; category="Productivity"; essential=$false},
    @{name="KeePassXC"; winget="KeePassXCTeam.KeePassXC"; category="Productivity"; essential=$false},
    @{name="Syncthing"; winget="Syncthing.Syncthing"; category="Productivity"; essential=$false},
    @{name="DevToys"; winget="DevToys.DevToys"; category="Productivity"; essential=$false},

    # ── Media ──
    @{name="OBS Studio"; winget="OBSProject.OBSStudio"; category="Media"; essential=$false},
    @{name="FFmpeg"; winget="FFmpeg.FFmpeg"; category="Media"; essential=$false},

    # ── System ──
    @{name="Process Hacker"; winget="ProcessHacker.ProcessHacker"; category="System"; essential=$false},
    @{name="BleachBit"; winget="BleachBit.BleachBit"; category="System"; essential=$false},
    @{name="WinDirStat"; winget="WinDirStat.WinDirStat"; category="System"; essential=$false},
    @{name="Notepad++"; winget="Notepad++.Notepad++"; category="System"; essential=$false},
    @{name="7-Zip"; winget="7zip.7zip"; category="System"; essential=$true},
    @{name="EarTrumpet"; winget="File-New-Project.EarTrumpet"; category="System"; essential=$false},
    @{name="Flameshot"; winget="Flameshot.Flameshot"; category="System"; essential=$false},

    # ── Gaming ──
    @{name="Steam"; winget="Valve.Steam"; category="Gaming"; essential=$false}
)

# ── UI ──────────────────────────────────────────────────────────

function Write-Banner {
    $colors = @{Development="Cyan"; Security="Red"; AI="Magenta"; Productivity="Green"; Media="Yellow"; System="Blue"; Gaming="White"}
    Write-Host "╔══════════════════════════════════════════════════╗" -ForegroundColor DarkCyan
    Write-Host "║     ORION Desktop Tools — Universal Installer   ║" -ForegroundColor DarkCyan
    Write-Host "╚══════════════════════════════════════════════════╝" -ForegroundColor DarkCyan
    Write-Host "Total tools: $($tools.Count)" -ForegroundColor Gray
    Write-Host ""
}

function Write-ProgressBar {
    param($Current, $Total)
    $pct = [math]::Round($Current / $Total * 100)
    Write-Progress -Activity "Installing tools..." -Status "$Current / $Total" -PercentComplete $pct
}

# ── Install logic ───────────────────────────────────────────────

function Install-Tool {
    param($tool)
    $name = $tool.name
    $category = $tool.category
    if (-not $categories.ContainsKey($category)) { $categories[$category] = @{ok=0; fail=0; skip=0} }

    if ($tool.ContainsKey("winget")) {
        $id = $tool.winget
        Write-Host "  → Installing $name..." -ForegroundColor Gray -NoNewline
        $r = & winget install --id $id --silent --accept-package-agreements --accept-source-agreements 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Host " OK" -ForegroundColor Green
            $categories[$category].ok++
        } else {
            Write-Host " FAIL" -ForegroundColor Red
            $categories[$category].fail++
        }
    } elseif ($tool.ContainsKey("scoop")) {
        $app = $tool.scoop
        Write-Host "  → Installing $name (scoop)..." -ForegroundColor Gray -NoNewline
        $r = & scoop install $app 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Host " OK" -ForegroundColor Green
            $categories[$category].ok++
        } else {
            Write-Host " FAIL" -ForegroundColor Red
            $categories[$category].fail++
        }
    }
}

# ── Main ────────────────────────────────────────────────────────

Write-Banner

# Check winget
$hasWinget = Get-Command winget -ErrorAction SilentlyContinue
if (-not $hasWinget) {
    Write-Host "✗ winget not found. This script requires Windows 11 or winget." -ForegroundColor Red
    exit 1
}

Write-Host "Installing tools by category..." -ForegroundColor Cyan
Write-Host ""

$total = $tools.Count
$current = 0

foreach ($tool in $tools) {
    $current++
    Write-ProgressBar -Current $current -Total $total
    Install-Tool $tool
}

Write-Host ""
Write-Host "╔══════════════════════════════════════════════════╗" -ForegroundColor DarkCyan
Write-Host "║                 Installation Report              ║" -ForegroundColor DarkCyan
Write-Host "╚══════════════════════════════════════════════════╝" -ForegroundColor DarkCyan

$totalOk = 0; $totalFail = 0
foreach ($cat in $categories.Keys | Sort-Object) {
    $s = $categories[$cat]
    Write-Host "  $cat : $($s.ok) ok, $($s.fail) failed" -ForegroundColor $(if ($s.fail -eq 0){"Green"}else{"Yellow"})
    $totalOk += $s.ok; $totalFail += $s.fail
}

Write-Host ""
Write-Host "Total : $totalOk installed, $totalFail failed" -ForegroundColor $(if ($totalFail -eq 0){"Green"}else{"Yellow"})
Write-Host ""
if ($totalFail -gt 0) {
    Write-Host "Some installations failed. You can retry manually:" -ForegroundColor Yellow
    Write-Host "  winget install <id> --silent" -ForegroundColor Gray
}
Write-Host "Done." -ForegroundColor Cyan
