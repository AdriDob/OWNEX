# OWNEX Launcher — Windows 11 + WSL2
# Inicia backend+frontend dentro de WSL, espera health y abre la UI en el navegador.
# Uso: powershell -ExecutionPolicy Bypass -File OWNEX-Launcher.ps1
$ErrorActionPreference = "Stop"

$WslRepo = "~/projects/Rastro"
$HealthUrl = "http://localhost:8000/api/health"
$UiUrl = "http://localhost:5173"
$TimeoutSec = 120

function Test-Url($url) {
    try {
        $r = Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec 3
        return ($r.StatusCode -eq 200)
    } catch { return $false }
}

Write-Host "[OWNEX] Verificando WSL..." -ForegroundColor Cyan
wsl -e true
if ($LASTEXITCODE -ne 0) { throw "WSL no disponible. Instalar con: wsl --install" }

if (Test-Url $UiUrl) {
    Write-Host "[OWNEX] Ya corriendo." -ForegroundColor Green
    # App nativa Tauri instalada → ventana propia; sino navegador.
    $tauriExe = "$env:LOCALAPPDATA\OWNEX Alpha\OWNEX Alpha.exe"
    if (Test-Path $tauriExe) { Start-Process $tauriExe } else { Start-Process $UiUrl }
    exit 0
}

Write-Host "[OWNEX] Iniciando servicios en WSL..." -ForegroundColor Cyan
bash -lc "chmod +x $WslRepo/scripts/wsl/*.sh; $WslRepo/scripts/wsl/start_all.sh"
if ($LASTEXITCODE -ne 0) { throw "Fallo el arranque dentro de WSL (ver logs/ownex-api.log)" }

Write-Host "[OWNEX] Esperando backend (max $TimeoutSec s)..." -ForegroundColor Cyan
$sw = [Diagnostics.Stopwatch]::StartNew()
while ($sw.Elapsed.TotalSeconds -lt $TimeoutSec) {
    if (Test-Url $HealthUrl) {
        Write-Host "[OWNEX] Backend READY." -ForegroundColor Green
        break
    }
    Start-Sleep -Seconds 3
}
if (-not (Test-Url $HealthUrl)) {
    bash -lc "tail -30 $WslRepo/logs/ownex-api.log"
    throw "Backend no respondio en $TimeoutSec s"
}

while ($sw.Elapsed.TotalSeconds -lt ($TimeoutSec * 2) -and -not (Test-Url $UiUrl)) {
    Start-Sleep -Seconds 2
}

Write-Host "[OWNEX] Abriendo..." -ForegroundColor Green
# Preferencia: app nativa Tauri (ventana propia) → fallback navegador.
$tauriExe = "$env:LOCALAPPDATA\OWNEX Alpha\OWNEX Alpha.exe"
if (Test-Path $tauriExe) {
    Start-Process $tauriExe
    Write-Host "[OWNEX] App de escritorio abierta." -ForegroundColor Green
} else {
    Start-Process $UiUrl
    Write-Host "[OWNEX] UI abierta en navegador (instalá el MSI para la app nativa)." -ForegroundColor Yellow
}
Write-Host "[OWNEX] Listo. Para detener: OWNEX-Stop.ps1" -ForegroundColor Yellow
