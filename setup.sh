#!/bin/bash
# 🎯 CI/CD Setup Script - Quick Linux/WSL2/WSL Deployment

# 🛡️ SAFETY: Execute with caution, use error handling
# ⚡ SPEED: Fast deployment under 15 minutes
# 🔧 PURPOSE: Quick CI/CD setup for ORION Dashboard

# 🚨 WARNING: This setup script configures HERMES/ORION environment
# ❓ CONFIRMATION: Script requires user confirmation before execution

# 🌍 Environment Loading
if [ -f "./hermes/.bashrc" ]; then
    source "./hermes/.bashrc"
fi

# 🌍 Logging System
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] 🚀 $1"
}

# 🐛 Error Handling
error_handler() {
    log "❌ ERROR: $1"
    log "💡 SUGGESTION: Check system configuration"
    exit 1
}

# 📊 System Validation
validate_ci_setup() {
    log "🔍 Validating CI/CD setup..."
    
    # Check Python availability
    if ! command -v python3 &> /dev/null; then
        error_handler "python3 not found - install Python 3.11+"
    fi
    
    # Check pip availability
    if ! command -v pip3 &> /dev/null; then
        error_handler "pip3 not found - install pip"
    fi
    
    # Check Git availability
    if ! command -v git &> /dev/null; then
        error_handler "git not found - install Git"
    fi
    
    log "✅ CI/CD environment validated"
}

# 🏗️ Main Setup Function
main_setup() {
    log "🚀 Starting CI/CD setup for ORION Dashboard..."
    
    # 🎛 STEP 1: Validate environment
    validate_ci_setup
    
    # 📁 STEP 2: Setup virtual environment
    if [ ! -d ".venv" ]; then
        log "📦 Creating virtual environment .venv..."
        python3 -m venv .venv
        log "✅ Virtual environment created"
    else
        log "✅ Virtual environment already exists"
    fi
    
    # 🔐 STEP 3: Activate virtual environment
    if ! source .venv/bin/activate >/dev/null 2>&1; then
        error_handler ".venv/bin/activate not found"
    fi
    
    # 📦 STEP 4: Install project dependencies
    if [ -f "pyproject.toml" ]; then
        log "📥 Installing dependencies from pyproject.toml..."
        pip3 install -r <(grep -A 20 '\[project\]' pyproject.toml | grep -E "^\s*[^#]" | sed 's/  //')
        log "✅ Dependencies installed"
    elif [ -f "requirements.txt" ]; then
        log "📥 Installing dependencies from requirements.txt..."
        pip3 install -r requirements.txt
        log "✅ Dependencies installed"
    else
        log "⚠️ Warning: No pyproject.toml or requirements.txt found"
        log "💡 Suggestion: Use hermes setup for complete configuration"
    fi
    
    # 🧹 STEP 5: Install CI/CD tools
    log "🛠️ Installing CI/CD tools..."
    pip3 install pytest pytest-cov pytest-timeout ruff security-cli
    log "✅ CI/CD tools installed"
    
    # 🚀 STEP 6: Show helpful commands
    log "📋 Available commands:"
    echo "  👉 ./setup.sh           # Repeat setup"
    echo "  👉 ./scripts/ci_complete.sh  # Full CI/CD pipeline"
    echo "  👉 .venv/bin/python -m pytest tests/ --timeout=180"
    echo "  👉 curl http://localhost:8000/api/health"
    
    log "🎉 CI/CD setup completed successfully!"
    log "⏰ Setup time: $(date '+%Y-%m-%d %H:%M:%S')"
}

# 🔧 Execute the setup
main_setup