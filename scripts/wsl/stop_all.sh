#!/usr/bin/env bash
# OWNEX WSL stop — mata backend + frontend de forma limpia.
set -u
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
for f in ownex-web ownex-api; do
  if [ -f "$REPO/data/$f.pid" ]; then
    PID="$(cat "$REPO/data/$f.pid")"
    kill -TERM "-$PID" 2>/dev/null || kill -TERM "$PID" 2>/dev/null || true
    rm -f "$REPO/data/$f.pid"
  fi
done
pkill -TERM -f "uvicorn api.main:app.*--port 8000" 2>/dev/null || true
pkill -TERM -f "vite preview.*--port 5173" 2>/dev/null || true
echo "STOPPED"
