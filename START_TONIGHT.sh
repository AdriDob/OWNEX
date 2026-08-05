#!/bin/bash
# OWNEX OMEGA — Quick Start Tonight
# Sistema completo funcional sin compilar desktop/mobile (usa web)

set -e

echo "╔══════════════════════════════════════════════════════════╗"
echo "║  OWNEX OMEGA — Quick Start v7.0.0                         ║"
echo "║  Web System (Backend + Frontend)                          ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

PROJECT_ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_ROOT"

# Step 1: Backend
echo -e "${YELLOW}[1/3] Backend Setup${NC}"
if [ ! -d ".venv" ]; then
    echo "Creating Python virtual environment..."
    python3 -m venv .venv
fi
source .venv/bin/activate
echo "Installing/updating Python dependencies..."
pip install -q --upgrade pip
pip install -q -r requirements.txt
echo -e "${GREEN}✓ Backend ready${NC}"
echo ""

# Step 2: Frontend
echo -e "${YELLOW}[2/3] Frontend Build${NC}"
cd frontend
if [ ! -d "node_modules" ]; then
    echo "Installing Node dependencies..."
    npm install --silent
fi
echo "Building frontend..."
npm run build
cd ..
echo -e "${GREEN}✓ Frontend built${NC}"
echo ""

# Step 3: Database Init
echo -e "${YELLOW}[3/3] Database Initialization${NC}"
source .venv/bin/activate
python -c "
from database.db import engine, Base
from database.models import *
Base.metadata.create_all(bind=engine)
print('Database initialized')
"
echo -e "${GREEN}✓ Database ready${NC}"
echo ""

# Done
echo "╔══════════════════════════════════════════════════════════╗"
echo "║  OWNEX OMEGA Ready!                                      ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""
echo "To start OWNEX:"
echo "  cd $PROJECT_ROOT"
echo "  source .venv/bin/activate"
echo "  python api/main.py"
echo ""
echo "Then open: http://localhost:8000"
echo ""
echo "Features available:"
echo "  ✓ Mission Control Dashboard"
echo "  ✓ Security Cycle (Bug Bounty)"
echo "  ✓ Opportunity Engine"
echo "  ✓ Multi-Agent Coordinator"
echo "  ✓ Revenue Tracking"
echo "  ✓ Executive Dashboard"
echo "  ✓ Daily Companion"
echo "  ✓ Income Dashboard"
echo ""
