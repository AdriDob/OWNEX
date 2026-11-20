#!/bin/bash
# ─────────────────────────────────────────────────────────────
# OWNEX OMEGA — Preview Start (sin email/sin contraseña)
# Levanta API + Frontend con preview en navegador,
# SIN cargar credenciales de SMTP/mail.
#
# Modo: ideal para desarrollo rápido y demo sin configuración de mail.
#
# Uso:
#   ./start-preview.sh   # API + frontend preview (sin mail)
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

# ── Cargar .env SIN variables de mail ──────────────────────
# Importante: el config usa OWNEX_* con fallback CATEYE_* . Esta función
# sobreescribe las vars de mail con valores vacíos para que el sistema funcione
# sin credenciales de SMTP/email.
load_env_no_mail() {
  if [ -f "$DIR/.env" ]; then
    set -a
    # shellcheck disable=SC1091
    source "$DIR/.env"
    set +a
    # Override mail-related vars with empty values (OWNEX takes precedence over CATEYE_*)
    export OWNEX_SMTP_HOST=""
    export OWNEX_SMTP_PORT=587
    export OWNEX_SMTP_USER=""
    export OWNEX_SMTP_PASSWORD=""
    export OWNEX_SMTP_FROM=""
    export OWNEX_NOTIFICATION_EMAIL=""
    log "✓ .env cargado (modo sin mail — notificaciones desactivadas)"
  else
    log "⚠ .env ausente — usando configuración por defecto"
    # Set defaults for non-mail vars and empty mail vars
    export OWNEX_SMTP_HOST=""
    export OWNEX_SMTP_PORT=587
    export OWNEX_SMTP_USER=""
    export OWNEX_SMTP_PASSWORD=""
    export OWNEX_SMTP_FROM=""
    export OWNEX_NOTIFICATION_EMAIL=""
    export OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
    export OLLAMA_HOST=http://localhost:11434
    export FCC_BASE_URL=http://localhost:8082
    export CATEYE_CSRF_DISABLED=1
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
  echo "  │  OWNEX ONLINE — Preview Mode                  │"
  echo "  │   http://localhost:$WEB_PORT                    │"
  echo "  │   API: http://localhost:$API_PORT/api/health  │"
  echo "  └─────────────────────────────────────────────┘"
  echo
  log "Para detener: ./start-preview.sh --stop"
  log "Modo: Sin credenciales de mail/SMTP"
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
  log "Lanzando vite preview en :$WEB_PORT…"
  # Usar vite preview sin requerir credenciales de mail
  (setsid nohup ./node_modules/.bin/vite preview --port "$WEB_PORT" --host > "$WEB_LOG" 2>&1 &)
  cd "$DIR"
  for i in $(seq 1 20); do
    code=$(curl -s -m 2 -o /dev/null -w "%{http_code}" "http://localhost:$WEB_PORT/" 2>/dev/null)
    [ "$code" = "200" ] && break
    sleep 2
  done
  log "✓ Frontend en :$WEB_PORT (HTTP $code)"
}

# ── API ──────────────────────────────────────────────────────
start_api() {
  if port_in_use "$API_PORT"; then
    log "✓ API ya responde en :$API_PORT"
    return
  fi
  load_env_no_mail

  if [ ! -d .venv ]; then
    log "Creando venv…"
    python3 -m venv .venv || die "No se pudo crear .venv"
  fi
  log "Lanzando API (python -m api.main)…"
  # Pasar modo sin-mail a la API exportando variable de entorno
  export OWNEX_SKIP_MAIL=1
  (setsid nohup ./.venv/bin/python -u -m api.main > "$API_LOG" 2>&1 &)
}

# ── Main ────────────────────────────────────────────────────
for arg in "$@"; do
  case "$arg" in
    --stop) stop_all; exit 0 ;;
    --status) status_now; exit 0 ;;
    *) ;;
  esac
done

log "OWNEX OMEGA — levantando stack (modo preview, sin mail)"
start_api
start_frontend
wait_api