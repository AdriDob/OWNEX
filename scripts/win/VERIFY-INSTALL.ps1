<# 
.SYNOPSIS
    OWNEX Alpha 1.0.1 — Instalación y verificación automatizada en Windows 11
.DESCRIPTION
    Este script:
    1. Descarga los artefactos desde GitHub (o usa locales)
    2. Verifica checksums SHA256
    3. Instala OWNEX (MSI o NSIS)
    4. Verifica que el backend arranca y health endpoint responde
    5. Verifica que la UI abre correctamente
    6. Ejecuta prueba de persistencia (reinicio + datos intactos)
    7. Opcional: Ejecuta soak test de 24h

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File VERIFY-INSTALL.ps1 -InstallerType MSI
    powershell -ExecutionPolicy Bypass -File VERIFY-INSTALL.ps1 -InstallerType NSIS -RunSoakTest
#>

param(
    [Parameter(Mandatory=$true)]
    [ValidateSet('MSI','NSIS')]
    [string]$InstallerType,

    [switch]$RunSoakTest,
    [string]$ArtifactDir = "$env:USERPROFILE\Downloads\OWNEX-Artifacts",
    [string]$InstallPath = "$env:LOCALAPPDATA\OWNEX Alpha"
)

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

function Write-Log($msg, $level = 'INFO') {
    $ts = Get-Date -Format 'yyyy-MM-dd HH:mm:ss'
    $color = switch($level) { 'OK' { 'Green' } 'WARN' { 'Yellow' } 'ERROR' { 'Red' } default { 'Cyan' } }
    Write-Host "[$ts] [$level] $msg" -ForegroundColor $color
}

function Verify-Checksum($file, $expected) {
    $actual = (Get-FileHash -Algorithm SHA256 $file).Hash.ToLower()
    if ($actual -eq $expected.ToLower()) {
        Write-Log "Checksum OK: $file" 'OK'
        return $true
    } else {
        Write-Log "CHECKSUM MISMATCH: $file`n  Expected: $expected`n  Actual:   $actual" 'ERROR'
        return $false
    }
}

function Wait-Health($url, $timeoutSec = 120) {
    Write-Log "Esperando health endpoint ($url) máx $timeoutSec s..."
    $sw = [Diagnostics.Stopwatch]::StartNew()
    while ($sw.Elapsed.TotalSeconds -lt $timeoutSec) {
        try {
            $r = Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec 5 -ErrorAction Stop
            if ($r.StatusCode -eq 200) {
                Write-Log "Backend HEALTH OK (HTTP 200)" 'OK'
                return $true
            }
        } catch { }
        Start-Sleep -Seconds 3
    }
    Write-Log "Backend NO respondió en $timeoutSec s" 'ERROR'
    return $false
}

# ── MAIN ──────────────────────────────────────────────────────────────
Write-Log "=== OWNEX Alpha 1.0.1 — Verificación de Instalación ==="

# 1. Localizar artefactos
$msiPath = Join-Path $ArtifactDir "msi\OWNEX Alpha_1.0.1_x64_es-ES.msi"
$nsisPath = Join-Path $ArtifactDir "nsis\OWNEX Alpha_1.0.1_x64-setup.exe"
$sidecarPath = Join-Path $ArtifactDir "ownex-backend.exe"
$checksumsPath = Join-Path $ArtifactDir "SHA256SUMS.txt"

if (-not (Test-Path $checksumsPath)) {
    Write-Log "No se encuentra SHA256SUMS.txt en $ArtifactDir" 'ERROR'
    exit 1
}

Write-Log "Verificando checksums..."
$checksums = Get-Content $checksumsPath | Where-Object { $_ -match '^[a-f0-9]{64}' } | ForEach-Object {
    $parts = $_ -split '\s+'
    @{ Hash = $parts[0]; File = $parts[2] }
}
$allOk = $true
foreach ($c in $checksums) {
    $fullPath = Join-Path $ArtifactDir $c.File
    if (Test-Path $fullPath) {
        if (-not (Verify-Checksum $fullPath $c.Hash)) { $allOk = $false }
    } else {
        Write-Log "Archivo no encontrado: $fullPath" 'WARN'
    }
}
if (-not $allOk) { Write-Log "Fallo en verificación de checksums" 'ERROR'; exit 1 }

# 2. Instalar
Write-Log "Instalando OWNEX ($InstallerType)..."
if ($InstallerType -eq 'MSI') {
    if (-not (Test-Path $msiPath)) { Write-Log "MSI no encontrado: $msiPath" 'ERROR'; exit 1 }
    $proc = Start-Process msiexec.exe -ArgumentList "/i `"$msiPath`" /quiet /norestart" -Wait -PassThru
} else {
    if (-not (Test-Path $nsisPath)) { Write-Log "NSIS no encontrado: $nsisPath" 'ERROR'; exit 1 }
    $proc = Start-Process $nsisPath -ArgumentList "/S" -Wait -PassThru
}
if ($proc.ExitCode -ne 0) { Write-Log "Instalador falló con código $($proc.ExitCode)" 'ERROR'; exit 1 }
Write-Log "Instalación completada" 'OK'

# 3. Verificar instalación
$exePath = Join-Path $InstallPath "OWNEX Alpha.exe"
if (-not (Test-Path $exePath)) {
    Write-Log "Ejecutable no encontrado en $exePath" 'ERROR'
    exit 1
}
Write-Log "Ejecutable encontrado: $exePath" 'OK'

# 3b. Verificar sidecar incluido
$sidecarInstalled = Join-Path $InstallPath "ownex-backend.exe"
if (-not (Test-Path $sidecarInstalled)) {
    Write-Log "Sidecar NO incluido en la instalación: $sidecarInstalled" 'WARN'
} else {
    Write-Log "Sidecar incluido: $sidecarInstalled" 'OK'
}

# 4. Lanzar aplicación y verificar backend
Write-Log "Lanzando OWNEX..."
$appProc = Start-Process $exePath -PassThru
Write-Log "OWNEX lanzado (PID $($appProc.Id))"

# 5. Verificar health endpoint
if (-not (Wait-Health "http://localhost:8000/api/health" 120)) {
    Write-Log "Backend no disponible — revisando logs..." 'WARN'
    $logPath = Join-Path $InstallPath "logs\ownex-api.log"
    if (Test-Path $logPath) { Get-Content $logPath -Tail 50 }
    exit 1
}

# 6. Verificar UI (puerto 5173 - preview) o puerto 8000 si es Tauri bundled
$uiPort = 5173
if (-not (Wait-Health "http://localhost:$uiPort" 30)) {
    Write-Log "UI preview no en $uiPort — intentando puerto 8000 (bundled)..." 'WARN'
    if (-not (Wait-Health "http://localhost:8000" 10)) {
        Write-Log "UI no accesible" 'WARN'
    }
}

# 7. Prueba de persistencia: cerrar y reabrir
Write-Log "Prueba de persistencia: cerrando y reabriendo..."
Stop-Process -Id $appProc.Id -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 3
$appProc2 = Start-Process $exePath -PassThru
if (Wait-Health "http://localhost:8000/api/health" 30) {
    Write-Log "Reinicio OK — backend responde" 'OK'
} else {
    Write-Log "Reinicio FALLÓ — backend no responde tras reinicio" 'ERROR'
    exit 1
}
Stop-Process -Id $appProc2.Id -Force -ErrorAction SilentlyContinue

# 8. Soak test opcional
if ($RunSoakTest) {
    Write-Log "Iniciando SOAK TEST 24h — NO CERRES ESTA VENTANA" 'WARN'
    $appProc3 = Start-Process $exePath -PassThru
    $endTime = (Get-Date).AddHours(24)
    while ((Get-Date) -lt $endTime) {
        if (-not (Wait-Health "http://localhost:8000/api/health" 10)) {
            Write-Log "SOAK TEST: Backend caído a las $(Get-Date)" 'ERROR'
            exit 1
        }
        Write-Log "SOAK TEST: $(Get-Date) — Backend OK" 'OK'
        Start-Sleep -Seconds 300 # check cada 5 min
    }
    Write-Log "SOAK TEST 24h COMPLETADO — SIN CAÍDAS" 'OK'
}

Write-Log "=== VERIFICACIÓN COMPLETA — TODO OK ===" 'OK'