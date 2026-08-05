#!/bin/bash
# OWNEX OMEGA — Installation Script v7.0.0
# Instala el proyecto completo: Backend + Frontend + Desktop + Mobile

set -e

echo "╔══════════════════════════════════════════════════════════╗"
echo "║  OWNEX OMEGA — Complete Installation v7.0.0              ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Step 1: Backend Installation
echo -e "${YELLOW}[1/5] Backend Installation${NC}"
if [ ! -d ".venv" ]; then
    echo "Creating Python virtual environment..."
    python3 -m venv .venv
fi
echo "Activating virtual environment..."
source .venv/bin/activate
echo "Installing Python dependencies..."
pip install -q --upgrade pip
pip install -q -r requirements.txt
echo -e "${GREEN}✓ Backend installed${NC}"
echo ""

# Step 2: Frontend Build
echo -e "${YELLOW}[2/5] Frontend Build${NC}"
cd frontend
echo "Installing Node dependencies..."
npm install --silent
echo "Building frontend for production..."
npm run build
cd ..
echo -e "${GREEN}✓ Frontend built${NC}"
echo ""

# Step 3: Desktop Build (Tauri)
echo -e "${YELLOW}[3/5] Desktop Build (Tauri)${NC}"
if command -v cargo &> /dev/null; then
    echo "Building Tauri desktop application..."
    cd src-tauri
    cargo build --release
    cd ..
    echo -e "${GREEN}✓ Desktop built${NC}"
else
    echo -e "${RED}✗ Rust/Cargo not found. Skipping desktop build.${NC}"
    echo "  Install Rust: https://rustup.rs/"
fi
echo ""

# Step 4: Mobile Build (Android)
echo -e "${YELLOW}[4/5] Mobile Build (Android)${NC}"
if [ -d "android" ] && command -v java &> /dev/null; then
    echo "Building Android APK..."
    cd android
    ./gradlew assembleDebug
    cd ..
    echo -e "${GREEN}✓ Android APK built${NC}"
else
    echo -e "${RED}✗ Android build skipped (missing Java or android directory)${NC}"
fi
echo ""

# Step 5: Verification
echo -e "${YELLOW}[5/5] Verification${NC}"
echo "Running quick tests..."
source .venv/bin/activate
python -m pytest tests/test_scheduler_jobs.py -q --timeout=30
echo -e "${GREEN}✓ Tests passed${NC}"
echo ""

# Summary
echo "╔══════════════════════════════════════════════════════════╗"
echo "║  Installation Complete!                                  ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""
echo "To start OWNEX:"
echo "  Backend:  .venv/bin/python api/main.py"
echo "  Desktop:  src-tauri/target/release/orion_desktop (or run via cargo tauri dev)"
echo "  Android:  android/app/build/outputs/apk/debug/app-debug.apk"
echo ""
echo "Web interface: http://localhost:8000"
echo ""
