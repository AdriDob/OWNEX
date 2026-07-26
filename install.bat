#!/bin/bash
# 💻 install.bat — Installation CI/CD para ORION Dashboard (Windows PowerShell)

# 🎯 CONFIGURACIÓN: Setup Windows PowerShell para CI/CD pipeline
# 🛡️ SAFETY: Error handling robust para Windows PowerShell
# 🔧 CONTEXT: Windows PowerShell (pwsh o PowerShell)

# 🚨 WARNING: Este script instalará el entorno Hermes/ORION en Windows
# ❓ CONFIRMATION: No hay prompt - los scripts continúan automáticamente

# 🌍 EXPLANATION: Función de logging para output consistente entre plataformas
log() {
    Write-Host "[$([datetime]::Now.ToString('yyyy-MM-dd HH:mm:ss'))] 🚀 $1"
}

# 🐛 ERROR HANDLING: Función para capturar y reportar errores Windows
error_handler() {
    param(
        [Parameter(Mandatory=$true)][int]$ExitCode,
        [Parameter(Mandatory=$true)][string]$Message
    )
    log "❌ ERROR: Error en Windows PowerShell línea $ExitCode: $Message"
    log "💡 SUGGESTION: Revisar Windows PowerShell logs o ms-settings:other"
    exit $ExitCode
}

# 🏗️ SETUP: Función de setup principal para Windows
main_setup() {
    log "🛠️  Iniciando setup CI/CD para ORION Dashboard..."
    
    # 🎛️ STEP 1: Verificar compatibilidad de PowerShell
    log "🔍 Verificando PowerShell..."
    if (-Not (Get-Command "pwsh" -ErrorAction SilentlyContinue)) {
        log "⚠️ pwsh (PowerShell Core) no disponible - usando Windows PowerShell"
    }
    
    # 📁 STEP 2: Verificar/crear .venv si no existe
    if (-Not (Test-Path ".venv")) {
        log "📦 Creando entorno virtual .venv..."
        python -m venv .venv
        log "✅ Entorno virtual creado"
    } else {
        log "✅ Entorno virtual ya existe"
    }
    
    # 🔐 STEP 3: Activar .venv
    $venvActivatePath = ".venv\Scripts\activate"
    if (Test-Path $venvActivatePath) {
        . $venvActivatePath
        log "✅ Entorno virtual activado"
    } else {
        error_handler "$(echo $?)" ".venv\Scripts\activate no encontrado"
    }
    
    # 📦 STEP 4: Instalar dependencies del proyecto
    if (Test-Path "pyproject.toml") {
        log "📥 Instalando dependencias desde pyproject.toml..."
        pip install -r <(Select-String -Path "pyproject.toml" -Pattern "^\s*([^#\s].*)$" | Where-Object { $_ -match "^\s*(?:fastapi|uvicorn|sqlalchemy|pytest|ruff|pytest-cov|pytest-timeout)" } | ForEach-Object { $_.Matches[0] } | Out-String).Trim()
        log "✅ Dependencias instaladas"
    } elseif (Test-Path "requirements.txt") {
        log "📥 Instalando dependencias desde requirements.txt..."
        pip install -r requirements.txt
        log "✅ Dependencias instaladas"
    } else {
        log "⚠️ Advertencia: No se encontró pyproject.toml ni requirements.txt"
        log "💡 SUGGESTION: Clonar repo de ORION Dashboard para setup completo"
    }
    
    # 🧹 STEP 5: Limpiar cachés anteriores (2 horas) para fresh start
    log "🧹 Limpiando cachés antiguas..."
    Remove-Item -Recurse -Force "__pycache__" -ErrorAction SilentlyContinue
    Remove-Item -Recurse -Force ".pytest_cache" -ErrorAction SilentlyContinue
    Remove-Item -Force "dist" "build" "*.egg-info" ".coverage" -ErrorAction SilentlyContinue
    log "✅ Cachés limpiados"
    
    # 🔍 STEP 6: Instalar tools CI/CD
    log "📦 Instalando herramientas CI/CD..."
    pip install pytest pytest-cov pytest-timeout ruff security-cli
    log "✅ Herramientas CI/CD instaladas"
    
    # 🚀 STEP 7: Verificar compatibilidad del agente Hermes
    log "🤖 Verificando configuración del agente Hermes..."
    if (Get-Command "hermes" -ErrorAction SilentlyContinue) {
        hermes setup --quick
        log "✅ Configuración del agente Hermes completada"
    } else {
        log "⚠️ Agente Hermes no disponible - continuar sin él"
    }
    
    # 🌐 STEP 8: Verificar compatibilidad de red
    log "🌐 Verificando compatibilidad de red..."
    try {
        $healthCheck = Invoke-RestMethod -Uri "http://localhost:8000/api/health" -TimeoutSec 10 -ErrorAction Stop
        log "✅ Backend disponible - $($healthCheck.status)"
    } catch {
        log "⚠️ Backend no disponible - continuar de todos modos"
    }
    
    # 📋 STEP 9: Mostrar comandos útiles
    log "📋 Comandos útiles disponibles:"
    Write-Host "  👉 .\setup.ps1           # Repetir installation"
    Write-Host "  👉 .\install.bat        # Installation alternativa (este script)"
    Write-Host "  👉 .\scripts\ci_complete.ps1 # Pipeline completo"
    Write-Host "  👉 .\scripts\ci_performance_monitor.ps1 # Monitor de métricas"
    Write-Host "  👉 .\scripts\ci_metrics_comparison.ps1 # Comparación histórica"
    Write-Host "  👉 .venv\Scripts\python -m pytest tests/ --timeout=180 --cov=cores"
    Write-Host "  👉 Invoke-WebRequest -Uri 'http://localhost:8000/api/health'"
    
    log "🎉 Installation CI/CD completada exitosamente!"
    log "⏰ Fecha y hora del installation: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
    log "📊 Para monitorear métricas: .\scripts\ci_performance_monitor.ps1"
}

# 🔧 EXECUTION: Ejecutar setup principal
main_setup
