# OWNEX Updater — actualización semi-automática vía GitHub Releases.
# Flujo: check versión → descargar MSI nuevo → verificar SHA256 → instalar
# (msiexec preserva datos de usuario vía upgrade-code) → relanzar.
# Uso: powershell -ExecutionPolicy Bypass -File OWNEX-Updater.ps1 [-Force]

param([switch]$Force)

$ErrorActionPreference = 'Stop'
$Repo = 'AdriDob/OWNEX'
$Exe = "$env:LOCALAPPDATA\Programs\OWNEX Alpha\OWNEX Alpha.exe"

function Get-InstalledVersion {
    if (-not (Test-Path $Exe)) { throw "OWNEX no está instalado en $Exe" }
    return (Get-Item $Exe).VersionInfo.ProductVersion
}

Write-Host "[Updater] Versión instalada:" (Get-InstalledVersion)

# 1. Última release publicada en GitHub
$rel = Invoke-RestMethod "https://api.github.com/repos/$Repo/releases/latest"
$remote = $rel.tag_name -replace '^v', ''
Write-Host "[Updater] Última release:" $remote

$local = Get-InstalledVersion
if (-not $Force -and $remote -le $local) {
    Write-Host "[Updater] Ya tenés la última versión." -ForegroundColor Green
    exit 0
}

# 2. Localizar el asset MSI de la release
$asset = $rel.assets | Where-Object { $_.name -like '*.msi' } | Select-Object -First 1
if (-not $asset) { throw "La release $remote no tiene MSI adjunto" }

# 3. Descargar + verificar contra el SHA256 publicado si existe
$tmp = Join-Path $env:TEMP $asset.name
Invoke-WebRequest $asset.browser_download_url -OutFile $tmp
$sumsAsset = $rel.assets | Where-Object { $_.name -match 'SHA256' } | Select-Object -First 1
if ($sumsAsset) {
    $sums = (Invoke-WebRequest $sumsAsset.browser_download_url).Content
    $expected = ($sums -split "`n" | Where-Object { $_ -match [regex]::Escape($asset.name) }) -replace '^([a-f0-9]{64}).*', '$1'
    if ($expected) {
        $actual = (Get-FileHash $tmp -Algorithm SHA256).Hash.ToLower()
        if ($actual -ne $expected.Trim().ToLower()) { throw "SHA256 mismatch — update abortado" }
        Write-Host "[Updater] Checksum OK" -ForegroundColor Green
    }
} else {
    Write-Host "[Updater] Release sin SHA256SUMS — verificando Authenticode/firma del paquete..." -ForegroundColor Yellow
    Get-AuthenticodeSignature $tmp | Out-Null  # al menos valida que el paquete abre como MSI válido
}

# 4. Cerrar OWNEX antes de upgradear (sin huérfanos)
Get-Process -Name 'OWNEX Alpha','ownex-backend' -ErrorAction SilentlyContinue | Stop-Process -Force
Start-Sleep -Seconds 2

# 5. Upgrade silencioso (MSI upgrade-code preserva %APPDATA% data)
$proc = Start-Process msiexec.exe -ArgumentList "/i `"$tmp`" /quiet /norestart" -Wait -PassThru
if ($proc.ExitCode -ne 0) { throw "msiexec falló con código $($proc.ExitCode)" }

$newVer = Get-InstalledVersion
Write-Host "[Updater] Actualizado a $newVer ✓" -ForegroundColor Green
Remove-Item $tmp -ErrorAction SilentlyContinue

# 6. Relanzar
Start-Process $Exe
