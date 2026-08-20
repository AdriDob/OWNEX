#!/bin/bash
# Auto-detect project directory by locating this script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$SCRIPT_DIR"

export PYTHONPATH="$PROJECT_DIR:$PYTHONPATH"
LOG_DIR="$PROJECT_DIR/logs"
mkdir -p "$LOG_DIR"

if curl -s -m 2 http://127.0.0.1:8000/api/health 2>/dev/null | grep -q '"status":"ok"'; then
    echo "$(date -Is) backend already running on 8000 - skip" >> "$LOG_DIR/backend.log"
    exit 0
fi

# Detect Python venv (try .venv, venv, or system python)
if [ -d "$PROJECT_DIR/.venv" ]; then
    PYTHON="$PROJECT_DIR/.venv/bin/python"
elif [ -d "$PROJECT_DIR/venv" ]; then
    PYTHON="$PROJECT_DIR/venv/bin/python"
else
    PYTHON="python3"
fi

nohup "$PYTHON" -m uvicorn api.main:app --host 127.0.0.1 --port 8000 --log-level warning > "$LOG_DIR/backend.log" 2>&1 &
echo $! > "$LOG_DIR/backend.pid"
