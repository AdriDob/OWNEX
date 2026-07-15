#!/usr/bin/env bash
# ────────────────────────────────────────────────────────────
# ORION — Bootstrap a new machine for development / bug bounty
# ────────────────────────────────────────────────────────────
set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

log()   { echo -e "${CYAN}[ORION]${NC} $1"; }
ok()    { echo -e "  ${GREEN}✅${NC} $1"; }
warn()  { echo -e "  ${YELLOW}⚠️${NC} $1"; }
fail()  { echo -e "  ${RED}❌${NC} $1"; }

# ── Detect OS ──────────────────────────────────────────────
OS="$(uname -s)"
ARCH="$(uname -m)"
log "Detected: ${OS} ${ARCH}"

# ── 1. Python ──────────────────────────────────────────────
log "\n1/7 Python"
if command -v python3 &>/dev/null; then
    PYVER=$(python3 --version 2>&1)
    ok "$PYVER"
else
    fail "python3 not found — install Python 3.10+"
    exit 1
fi

# ── 2. Node.js ─────────────────────────────────────────────
log "\n2/7 Node.js"
if command -v node &>/dev/null; then
    NODEVER=$(node --version)
    ok "Node $NODEVER"
else
    warn "node not found — needed for frontend build"
    warn "  Install from: https://nodejs.org/"
fi
if command -v npm &>/dev/null; then
    NPMVER=$(npm --version)
    ok "npm v$NPMVER"
else
    warn "npm not found"
fi

# ── 3. Python venv + deps ─────────────────────────────────
log "\n3/7 Python virtual environment"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR"

if [ ! -d ".venv" ]; then
    python3 -m venv .venv
    ok "Created .venv"
else
    ok ".venv already exists"
fi

source .venv/bin/activate
log "Installing Python dependencies..."
pip install -q -r requirements.txt 2>&1 | tail -1
ok "Python dependencies installed"

# ── 4. Frontend ────────────────────────────────────────────
log "\n4/7 Frontend"
if command -v node &>/dev/null && [ -f "frontend/package.json" ]; then
    cd frontend
    if [ ! -d "node_modules" ]; then
        npm install --silent 2>&1 | tail -1
        ok "npm dependencies installed"
    else
        ok "node_modules already exists"
    fi
    if [ ! -d "dist" ]; then
        npm run build --silent 2>&1 | tail -1
        ok "Frontend built (frontend/dist/)"
    else
        ok "frontend/dist/ already exists"
    fi
    cd "$PROJECT_DIR"
else
    warn "Skipping frontend build (node or package.json missing)"
fi

# ── 5. AEGIS tools (Go) ────────────────────────────────────
log "\n5/7 AEGIS scanning tools"
if command -v go &>/dev/null; then
    GOPATH="${GOPATH:-$HOME/go}"
    export PATH="$GOPATH/bin:$PATH"
    GOVER=$(go version 2>&1 | grep -oP 'go\S+')
    ok "Go $GOVER"

    TOOLS=(
        "github.com/projectdiscovery/subfinder/v2/cmd/subfinder@latest"
        "github.com/projectdiscovery/httpx/cmd/httpx@latest"
        "github.com/projectdiscovery/katana/cmd/katana@latest"
        "github.com/projectdiscovery/nuclei/v3/cmd/nuclei@latest"
        "github.com/lc/gau/v2/cmd/gau@latest"
        "github.com/ffuf/ffuf@latest"
        "github.com/hahwul/dalfox/v2@latest"
    )
    for tool in "${TOOLS[@]}"; do
        NAME=$(basename "$tool" | sed 's/@.*//')
        if command -v "$NAME" &>/dev/null; then
            ok "$NAME already installed"
        else
            log "Installing $NAME..."
            go install "$tool" 2>&1 || warn "$NAME install failed (non-fatal)"
        fi
    done
else
    warn "go not found — skipping AEGIS tools install"
    warn "  Install from: https://go.dev/dl/"
fi

# ── 6. System tools ────────────────────────────────────────
log "\n6/7 System tools"
if command -v whois &>/dev/null; then
    ok "whois available"
else
    warn "whois not installed"
fi

# SecLists
SECLISTS="${SECLISTS_PATH:-/usr/share/seclists}"
if [ -d "$SECLISTS" ]; then
    ok "SecLists found at $SECLISTS"
else
    warn "SecLists not found at $SECLISTS"
    warn "  Clone: git clone https://github.com/danielmiessler/SecLists.git /usr/share/seclists"
fi

# Playwright browsers
if python3 -c "import playwright" 2>/dev/null; then
    python3 -m playwright install chromium 2>&1 | tail -1 || true
    ok "Playwright chromium browser installed"
else
    warn "playwright not installed (pip install playwright)"
fi

# ── 7. ORION data directories ──────────────────────────────
log "\n7/7 ORION data directories"
ORION_DIR="${HOME}/.orion"
mkdir -p "$ORION_DIR"/{backups,database,logs,extensions,evidence}
ok "Data directories created at $ORION_DIR"

# ── Summary ────────────────────────────────────────────────
echo ""
echo "╔══════════════════════════════════════════════════════╗"
echo "║           ORION — Setup Complete                     ║"
echo "╚══════════════════════════════════════════════════════╝"
echo ""
echo "  📍 Project:  $PROJECT_DIR"
echo "  📍 Data:     $ORION_DIR"
echo "  📍 Python:   $(python3 --version 2>&1)"
echo "  📍 Venv:     $PROJECT_DIR/.venv"
echo ""

echo "  ── Migrate from another PC ──"
echo "  1. Copy backup ZIP to this machine"
echo "  2. python run.py --migrate <backup.zip>"
echo "  3. python run.py --verify"
echo "  4. python run.py"
echo ""

echo "  ── Fresh start ──"
echo "  1. python run.py --install"
echo "  2. python run.py"
echo ""

echo "  ── Daily use ──"
echo "  source .venv/bin/activate"
echo "  python run.py"
echo ""
