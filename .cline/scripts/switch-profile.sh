#!/usr/bin/env bash
# =============================================================
# cline-switch — Cambia perfil de Cline (Local / Cloud / Emergency)
# Uso: cline-switch [local|cloud|emergency]
# =============================================================

set -euo pipefail

CLINE_SETTINGS="${HOME}/.cline/data/settings/global-settings.json"
PROVIDERS_FILE="${HOME}/.cline/data/settings/providers.json"

die() { echo "❌ $1"; exit 1; }
ok()  { echo "✅ $1"; }

case "${1:-}" in
  local)
    cat > "$PROVIDERS_FILE" <<- 'JSON'
{
  "apiProvider": "ollama",
  "ollamaBaseUrl": "http://localhost:11434",
  "ollamaModel": "freehuntx/qwen3-coder:8b",
  "contextWindow": 32768
}
JSON
    ok "Perfil LOCAL activado: freehuntx/qwen3-coder:8b via Ollama"
    ;;

  cloud)
    cat > "$PROVIDERS_FILE" <<- 'JSON'
{
  "apiProvider": "openrouter",
  "openRouterApiKey": "",
  "openRouterModel": "google/gemini-2.0-flash-exp:free",
  "contextWindow": 32768
}
JSON
    ok "Perfil CLOUD activado: Gemini 2.0 Flash Free via OpenRouter"
    echo ""
    echo "⚠️  Abre Cline → ⚙️ → pega tu OpenRouter API Key"
    ;;

  emergency)
    cat > "$PROVIDERS_FILE" <<- 'JSON'
{
  "apiProvider": "openrouter",
  "openRouterApiKey": "",
  "openRouterModel": "google/gemini-2.5-flash",
  "contextWindow": 32768
}
JSON
    ok "Perfil EMERGENCIA activado: Gemini 2.5 Flash via OpenRouter"
    echo ""
    echo "⚠️  Abre Cline → ⚙️ → pega tu OpenRouter API Key"
    ;;

  *)
    echo "Uso: cline-switch [local|cloud|emergency]"
    echo ""
    echo "  local     — Ollama + freehuntx/qwen3-coder:8b"
    echo "  cloud     — OpenRouter + Gemini 2.0 Flash (free)"
    echo "  emergency — OpenRouter + Gemini 2.5 Flash"
    exit 0
    ;;
esac
