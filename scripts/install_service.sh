#!/usr/bin/env bash
set -euo pipefail

# ── CATEYE Service Installer ──
# Installs systemd (Linux) or launchd (macOS) service wrapper.
#
# Usage:
#   sudo ./scripts/install_service.sh          # Install
#   sudo ./scripts/install_service.sh --remove  # Uninstall

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ACTION="${1:-install}"

CATEYE_USER="${CATEYE_USER:-$USER}"
CATEYE_GROUP="${CATEYE_GROUP:-$CATEYE_USER}"
CATEYE_ENV_FILE="${CATEYE_ENV_FILE:-/etc/cateye/cateye.env}"

install_linux() {
    echo "[1/3] Installing systemd service..."

    # Create environment file if it doesn't exist
    if [ ! -f "$CATEYE_ENV_FILE" ]; then
        echo "Creating default environment file: $CATEYE_ENV_FILE"
        mkdir -p "$(dirname "$CATEYE_ENV_FILE")"
        cat > "$CATEYE_ENV_FILE" <<-EOF
# CATEYE environment configuration
CATEYE_PORT=8000
CATEYE_HOST=127.0.0.1
CATEYE_LOG_LEVEL=INFO
CATEYE_BUILD_ENV=production
CATEYE_DESKTOP=0
DATABASE_URL=sqlite:///opt/CATEYE/data/cateye.db
EOF
    fi

    # Install systemd service unit
    echo "Installing systemd unit..."
    sed "s|%i|$CATEYE_USER|g" "$ROOT/scripts/cateye.service" \
        | sudo tee /etc/systemd/system/cateye.service > /dev/null

    # Create data and logs directories
    sudo mkdir -p /opt/CATEYE/data /opt/CATEYE/logs
    sudo chown -R "$CATEYE_USER:$CATEYE_GROUP" /opt/CATEYE

    # Reload systemd and enable
    echo "Enabling service..."
    sudo systemctl daemon-reload
    sudo systemctl enable cateye.service
    sudo systemctl start cateye.service

    echo "[2/3] ✓ systemd service installed and started"
    echo "     Status: systemctl status cateye.service"
    echo "     Logs:   journalctl -u cateye.service -f"
}

remove_linux() {
    echo "[1/2] Removing systemd service..."
    sudo systemctl stop cateye.service 2>/dev/null || true
    sudo systemctl disable cateye.service 2>/dev/null || true
    sudo rm -f /etc/systemd/system/cateye.service
    sudo systemctl daemon-reload
    echo "[2/2] ✓ systemd service removed"
}

install_macos() {
    echo "[1/3] Installing launchd service..."

    # Create environment file
    ENV_DIR="$HOME/.config/CATEYE"
    mkdir -p "$ENV_DIR"
    if [ ! -f "$ENV_DIR/cateye.env" ]; then
        echo "Creating default environment file: $ENV_DIR/cateye.env"
        cat > "$ENV_DIR/cateye.env" <<-EOF
CATEYE_PORT=8000
CATEYE_HOST=127.0.0.1
CATEYE_LOG_LEVEL=INFO
CATEYE_BUILD_ENV=production
CATEYE_DESKTOP=0
EOF
    fi

    # Create logs directory
    mkdir -p /opt/CATEYE/logs

    # Install launchd plist
    echo "Installing launchd plist..."
    cp "$ROOT/scripts/com.cateye.service.plist" "$HOME/Library/LaunchAgents/"
    launchctl load "$HOME/Library/LaunchAgents/com.cateye.service.plist"

    echo "[2/3] ✓ launchd service installed and loaded"
    echo "     Status: launchctl list | grep cateye"
    echo "     Logs:   tail -f /opt/CATEYE/logs/stdout.log"
}

remove_macos() {
    echo "[1/2] Removing launchd service..."
    launchctl unload "$HOME/Library/LaunchAgents/com.cateye.service.plist" 2>/dev/null || true
    rm -f "$HOME/Library/LaunchAgents/com.cateye.service.plist"
    echo "[2/2] ✓ launchd service removed"
}

# ── Main ──

case "$(uname)" in
    Linux)
        if [ "$ACTION" = "--remove" ]; then
            remove_linux
        else
            install_linux
        fi
        ;;
    Darwin)
        if [ "$ACTION" = "--remove" ]; then
            remove_macos
        else
            install_macos
        fi
        ;;
    *)
        echo "Unsupported OS: $(uname)"
        exit 1
        ;;
esac

echo ""
echo "=== DONE ==="
