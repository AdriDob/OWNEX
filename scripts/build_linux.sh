#!/usr/bin/env bash
set -euo pipefail

# ── Build CATEYE Linux executable via PyInstaller ──
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "=== Building CATEYE for Linux ==="

# 1. Install Python dependencies
echo "[1/4] Installing Python dependencies..."
pip install -q -r requirements.txt
pip install -q pyinstaller

# 2. Build frontend
echo "[2/4] Building frontend..."
cd frontend
npm ci --silent
npm run build --silent
cd "$ROOT"

# 3. PyInstaller
echo "[3/4] Building executable..."
pyinstaller CATEYE.spec -y

# 4. Verify
BINARY="dist/CATEYE/CATEYE"
if [ -f "$BINARY" ]; then
    SIZE=$(du -h "$BINARY" | cut -f1)
    echo "[4/4] ✓ Binary: $BINARY ($SIZE)"
else
    echo "ERROR: $BINARY not found"
    exit 1
fi

echo ""
echo "=== BUILD COMPLETE ==="
echo "  Binary: $ROOT/$BINARY"
echo "  Run:    $ROOT/$BINARY"
