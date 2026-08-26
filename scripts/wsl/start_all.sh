#!/usr/bin/env bash
# OWNEX WSL backend starter — llamado desde Windows vía `wsl -e`.
# Patrón setsid (LESSONS #1): inmune al SIGTERM del proceso padre.
set -u
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO"

mkdir -p data logs

is_up() { curl -s -m 2 -o /dev/null -w "%{http_code}" "$1" 2>/dev/null; }

# API :8000
if [ "$(is_up http://127.0.0.1:8000/api/health)" != "200" ]; then
  setsid nohup "$REPO/.venv/bin/python" -m uvicorn api.main:app \
    --host 127.0.0.1 --port 8000 >> logs/ownex-api.log 2>&1 < /dev/null &
  echo $! > data/ownex-api.pid
fi

# Frontend preview :5173 (puerto 8000 es SOLO-API por guard permanente)
if [ "$(is_up http://127.0.0.1:5173)" != "200" ]; then
  if [ ! -f frontend/dist/index.html ]; then
    ( cd frontend && npm run build >> ../logs/ownex-web-build.log 2>&1 )
  fi
  setsid nohup bash -c "cd '$REPO/frontend' && exec npx vite preview --host 127.0.0.1 --port 5173" \
    >> "$REPO/logs/ownex-web.log" 2>&1 < /dev/null &
  echo $! > data/ownex-web.pid
fi

echo "STARTED"
