#!/usr/bin/env bash
# CATEYE Portable Installer — sets up everything needed to run from this folder
# Usage: ./install.sh [--prefix /path/to/install]
# Default: installs to ./CATEYE/ (portable, self-contained)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTALL_DIR="${1:-${SCRIPT_DIR}/CATEYE}"

echo "=== CATEYE Portable Installer ==="
echo "  Source: ${SCRIPT_DIR}"
echo "  Target: ${INSTALL_DIR}"
echo ""

# ── Create directory structure ──
mkdir -p "${INSTALL_DIR}"
mkdir -p "${INSTALL_DIR}/data/database"
mkdir -p "${INSTALL_DIR}/data/uploads"
mkdir -p "${INSTALL_DIR}/data/evidence"
mkdir -p "${INSTALL_DIR}/config"
mkdir -p "${INSTALL_DIR}/logs"
mkdir -p "${INSTALL_DIR}/backups"
mkdir -p "${INSTALL_DIR}/tools"
mkdir -p "${INSTALL_DIR}/docs"

# ── Build PyInstaller binary ──
if [ ! -f "${SCRIPT_DIR}/dist/CATEYE/CATEYE" ]; then
    echo "[1/4] Building CATEYE binary (PyInstaller)..."
    cd "${SCRIPT_DIR}"
    pip install pyinstaller 2>/dev/null || true
    python desktop/build/build_desktop.py --clean 2>&1 | tail -5
    echo "  Binary built: ${SCRIPT_DIR}/dist/CATEYE/CATEYE"
else
    echo "[1/4] Binary already exists, skipping build"
fi

# ── Copy binary ──
echo "[2/4] Copying binary to ${INSTALL_DIR}..."
if [ -d "${SCRIPT_DIR}/dist/CATEYE" ]; then
    cp -r "${SCRIPT_DIR}/dist/CATEYE"/* "${INSTALL_DIR}/"
    chmod +x "${INSTALL_DIR}/CATEYE" 2>/dev/null || true
fi

# ── Build frontend ──
if [ -d "${SCRIPT_DIR}/frontend" ]; then
    echo "[3/4] Building frontend..."
    cd "${SCRIPT_DIR}/frontend"
    npm install --silent 2>/dev/null
    npm run build 2>&1 | tail -3
    if [ -d "dist" ]; then
        cp -r dist "${INSTALL_DIR}/frontend_dist"
    fi
    cd "${SCRIPT_DIR}"
fi

# ── Copy documentation ──
echo "[4/4] Copying documentation..."
for doc in README.md SYSTEM.md FUNCTIONAL_SPEC.md USER_GUIDE.md DAILY_WORKFLOW.md SETUP_GUIDE.md RELEASE_NOTES_v3.0.0.md CHANGELOG.md LICENSE; do
    if [ -f "${SCRIPT_DIR}/${doc}" ]; then
        cp "${SCRIPT_DIR}/${doc}" "${INSTALL_DIR}/docs/${doc}"
    fi
done

# ── Create launcher ──
cat > "${INSTALL_DIR}/CATEYE.sh" << 'LAUNCHER'
#!/usr/bin/env bash
# CATEYE Launcher — sets CATEYE_DATA_DIR and starts the binary
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export CATEYE_DATA_DIR="${SCRIPT_DIR}/data"
export CATEYE_CSRF_DISABLED=1
exec "${SCRIPT_DIR}/CATEYE" "$@"
LAUNCHER
chmod +x "${INSTALL_DIR}/CATEYE.sh"

# ── Create install log ──
cat > "${INSTALL_DIR}/build_info.txt" << EOF
CATEYE Portable Install
Date: $(date -u +"%Y-%m-%dT%H:%M:%SZ")
Source: ${SCRIPT_DIR}
Target: ${INSTALL_DIR}
Binary: $(file "${INSTALL_DIR}/CATEYE" 2>/dev/null | head -1)
Size: $(du -sh "${INSTALL_DIR}" | cut -f1)
EOF

echo ""
echo "=== Installation Complete ==="
echo ""
echo "  CATEYE installed to: ${INSTALL_DIR}"
echo ""
echo "  To run:"
echo "    cd ${INSTALL_DIR}"
echo "    ./CATEYE.sh"
echo ""
echo "  First run will auto-open the setup wizard."
echo "  All data stays inside ${INSTALL_DIR}/data/"
echo ""

# ── Verify ──
echo "=== Verification ==="
errors=0
for check in "CATEYE" "data/database" "data/uploads" "data/evidence" "config" "logs" "backups" "docs"; do
    if [ -e "${INSTALL_DIR}/${check}" ]; then
        echo "  [OK] ${check}"
    else
        echo "  [MISSING] ${check}"
        errors=$((errors + 1))
    fi
done
if [ "$errors" -eq 0 ]; then
    echo "  All components verified."
else
    echo "  ${errors} component(s) missing — check the build."
fi
echo ""
echo "Done."
