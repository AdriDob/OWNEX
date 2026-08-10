#!/bin/bash
# ─────────────────────────────────────────────────────────────
# OWNEX OMEGA — Quick Start
# Levanta API (:8000) + Frontend (:5173) en un solo comando,
# cargando el .env (incluye SMTP de notificaciones).
#
# Uso:
#   ./start.sh              # API + frontend (vite preview sobre dist)
#   ./start.sh --build      # rebuild frontend y luego arranca
#   ./start.sh --dev        # frontend en modo desarrollo (vite dev)
#   ./start.sh --daemon     # API via run.py --daemon (modo 24/7)
#   ./start.sh --stop       # detiene API + frontend
#   ./start.sh --status     # muestra qué proceso está vivo
# ─────────────────────────────────────────────────────────────
set -uo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR"

API_HOST=127.0.0.1
API_PORT=8000
WEB_PORT=5173
API_LOG="$DIR/logs/api.log"
WEB_LOG="$DIR/logs/web.log"
PID_API="$DIR/logs/.api.pid"
PID_WEB="$DIR/logs/.web.pid"

mkdir -p "$DIR/logs"

log() { echo -e "  \e[1;36m[ownex]\e[0m $*"; }
die() { echo -e "  \e[1;31m[ownex]\e[0m ERROR: $*"; exit 1; }

# ── Cargar .env (mail SMTP, etc.) ──────────────────────────
load_env() {
  if [ -f "$DIR/.env" ]; then
    set -a
    # shellcheck disable=SC1091
    source "$DIR/.env"
    set +a
    # El app password de Gmail se escribe SIEMPRE sin espacios
    if [[ -n "${OWNNEX_MAIL_PASSWORD:-}" ]]; then
      export OWNNEX_MAIL_PASSWORD="${OWNNEX_MAIL_PASSWORD// /}"
    fi
    log "✓ .env cargado (SMTP: ${OWNNEX_MAIL_SMTP_HOST:-no configurado})"
  else
    log "⚠ .env ausente — mail deshabilitado (modo local). Copiá .env.example a .env"
  fi
}

port_in_use() { ss -lnt 2>/dev/null | grep -q ":$1 "; }

stop_all() {
  if [ -f "$PID_API" ]; then kill -9 "$(cat "$PID_API")" 2>/dev/null; rm -f "$PID_API"; fi
  if [ -f "$PID_WEB" ]; then kill -9 "$(cat "$PID_WEB")" 2>/dev/null; rm -f "$PID_WEB"; fi
  pkill -9 -f "api.main" 2>/dev/null
  pkill -9 -f "run.py --daemon" 2>/dev/null
  pkill -9 -f "vite preview" 2>/dev/null
  pkill -9 -f "vite dev" 2>/dev/null
  sleep 1
  log "✓ Procesos detenidos"
}

status_now() {
  local api web
  api=$(curl -s -m 2 -o /dev/null -w "%{http_code}" "http://$API_HOST:$API_PORT/api/health" 2>/dev/null)
  web=$(curl -s -m 2 -o /dev/null -w "%{http_code}" "http://localhost:$WEB_PORT/" 2>/dev/null)
  log "API  :$API_PORT  -> HTTP ${api:-000}"
  log "Web  :$WEB_PORT  -> HTTP ${web:-000}"
}

wait_api() {
  log "Esperando API en :$API_PORT (el primer boot tarda 30-90s)…"
  local waited=0
  for i in $(seq 1 60); do
    code=$(curl -s -m 2 -o /dev/null -w "%{http_code}" "http://$API_HOST:$API_PORT/api/health" 2>/dev/null)
    if [ "$code" = "200" ]; then
      log "✓ API lista (~${waited}s)"
      break
    fi
    sleep 5
    waited=$((waited + 5))
  done
  display_status
}

display_status() {
  status_now
  echo
  echo "  ┌─────────────────────────────────────────────┐"
  echo "  │  OWNEX ONLINE                                │"
  echo "  │   http://localhost:$WEB_PORT                    │"
  echo "  │   API: http://localhost:$API_PORT/api/health  │"
  echo "  └─────────────────────────────────────────────┘"
  echo
  log "Para detener: ./start.sh --stop"
}

# ── Frontend ────────────────────────────────────────────────
start_frontend() {
  if port_in_use "$WEB_PORT"; then
    log "✓ Frontend ya está en :$WEB_PORT"
    return
  fi
  cd "$DIR/frontend"
  if [ ! -d node_modules ]; then
    log "Instalando dependencias frontend…"
    npm install --silent || die "npm install falló"
  fi
  if [ "${MODE_DEV:-0}" = "1" ]; then
    log "Lanzando vite dev en :$WEB_PORT…"
    (setsid nohup npm run dev -- --host > "$WEB_LOG" 2>&1 &)
  else
    if [ ! -f dist/index.html ] || [ "${MODE_BUILD:-0}" = "1" ]; then
      log "Buildeando frontend…"
      npm run build || die "vite build falló"
    fi
    log "Lanzando vite preview en :$WEB_PORT…"
    (setsid nohup ./node_modules/.bin/vite preview --port "$WEB_PORT" --host > "$WEB_LOG" 2>&1 & web_pid=$!)
  fi
  cd "$DIR"
  for i in $(seq 1 20); do
    code=$(curl -s -m 2 -o /dev/null -w "%{http_code}" "http://localhost:$WEB_PORT/" 2>/dev/null)
    [ "$code" = "200" ] && break
    sleep 2
  done
  log "✓ Frontend en :$WEB_PORT (HTTP $code)"
}

# ── API ────────────────────────────────────────────────────
start_api() {
  if port_in_use "$API_PORT"; then
    log "✓ API ya responde en :$API_PORT"
    return
  fi
  if [ ! -d .venv ]; then
    log "Creando venv…"
    python3 -m venv .venv || die "No se pudo crear .venv"
  fi
  load_env

  if [ "${MODE_DAEMON:-0}" = "1" ]; then
    log "Lanzando run.py --daemon (modo 24/7)…"
    (setsid nohup ./.venv/bin/python -u "$DIR/run.py" --daemon > "$API_LOG" 2>&1 &)
  else
    log "Lanzando API (python -m api.main)…"
    (setsid nohup ./.venv/bin/python -u -m api.main > "$API_LOG" 2>&1 &)
  fi
}

# ── Main ────────────────────────────────────────────────────
PORT_WEB="$WEB_PORT"; PORT_API="$API_PORT"
for arg in "$@"; do
  case "$arg" in
    --dev) MODE_DEV=1 ;;
    --build) MODE_BUILD=1 ;;
    --daemon) MODE_DAEMON=1 ;;
    --stop) stop_all; exit 0 ;;
    --status) status_now; exit 0 ;;
    *) die "Argumento desconocido: $arg" ;;
  esac
done

log "OWNEX OMEGA — levantando stack"
start_api
start_frontend
wait_api