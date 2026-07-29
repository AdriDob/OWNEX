#!/bin/bash
# Rastro Setup — Install daily use dependencies
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
echo "=== Rastro Setup ===  $(date)"
echo "Project: $PROJECT_DIR"

# ── 1. Python virtual environment ──────────────────────────────────────────
if [ ! -f "$PROJECT_DIR/.venv/bin/python" ]; then
    echo "[1/6] Creating virtual environment..."
    python3 -m venv "$PROJECT_DIR/.venv"
else
    echo "[1/6] Virtual environment exists"
fi
source "$PROJECT_DIR/.venv/bin/activate"

# ── 2. Install Python deps ─────────────────────────────────────────────────
echo "[2/6] Installing Python dependencies..."
cd "$PROJECT_DIR"
pip install --quiet --upgrade pip setuptools wheel
pip install --quiet -e .
if [ -f requirements.txt ]; then
    pip install --quiet -r requirements.txt
fi

# ── 3. Frontend (optional) ──────────────────────────────────────────────────
echo "[3/6] Checking frontend..."
if [ -d frontend/node_modules ]; then
    echo "      Frontend node_modules exists"
elif command -v npm &>/dev/null && [ -f frontend/package.json ]; then
    echo "      Installing frontend..."
    cd "$PROJECT_DIR/frontend"
    npm ci --quiet || npm install --quiet
    cd "$PROJECT_DIR"
else
    echo "      Skipping frontend (npm not found or no package.json)"
fi

# ── 4. Environment file ────────────────────────────────────────────────────
echo "[4/6] Configuring environment..."
if [ ! -f .env ]; then
    if [ -f .env.example ]; then
        cp .env.example .env
        echo "      Created .env from .env.example — review and edit as needed"
    else
        echo "      WARNING: No .env.example found; creating minimal .env"
        cat > .env << 'ENVEOF'
DATABASE_URL=sqlite:///rastro.db
LOG_LEVEL=INFO
ENVEOF
    fi
fi

# ── 5. Start script ────────────────────────────────────────────────────────
echo "[5/6] Creating start script..."
cat > "$PROJECT_DIR/start.sh" << 'STARTEOF'
#!/bin/bash
set -euo pipefail
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$DIR/.venv/bin/activate"
export PYTHONPATH="${PYTHONPATH:-}:$DIR"
cd "$DIR"
echo "Starting Rastro API..."
python -m api.main
STARTEOF
chmod +x "$PROJECT_DIR/start.sh"

# ── 6. Verify ──────────────────────────────────────────────────────────────
echo "[6/6] Verifying installation..."
cd "$PROJECT_DIR"
source .venv/bin/activate
export PYTHONPATH="${PYTHONPATH:-}:$PROJECT_DIR"

echo "  • Python: $(python3 --version)"
echo "  • Ruff: $(python3 -m ruff --version 2>/dev/null || echo 'not installed')"

# Test critical imports
python3 -c "
import sys
mods = [
    'api',
    'api.scheduler',
    'core.sensors.base',
    'core.sensors.observation',
    'core.sensors.observation_engine',
    'core.engine.base',
    'core.capabilities.registry',
    'extensions.playwright.playwright_sensor',
]
for mod in mods:
    try:
        __import__(mod)
        print(f'  ✓ {mod}')
    except Exception as e:
        print(f'  ✗ {mod}: {e}')
        sys.exit(1)
print('All imports OK')
"

echo ""
echo "=== Setup complete! ==="
echo "Start the API:  ./start.sh"
echo ""
