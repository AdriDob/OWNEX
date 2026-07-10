#!/usr/bin/env bash
# =============================================================
# cline-switch — Cambia perfil de Cline
# Uso: cline-switch [github|google|openrouter-free|local|emergency]
# =============================================================

set -euo pipefail

CLINE_SETTINGS="${HOME}/.cline/data/settings/global-settings.json"
PROVIDERS_FILE="${HOME}/.cline/data/settings/providers.json"

die() { echo "❌ $1"; exit 1; }
ok()  { echo "✅ $1"; }
info() { echo "ℹ️  $1"; }

case "${1:-}" in
  github)
    cat > "$PROVIDERS_FILE" <<- 'JSON'
{
  "apiProvider": "openai",
  "openAiApiKey": "",
  "openAiModel": "gpt-4o",
  "openAiBaseUrl": "https://models.inference.ai.azure.com",
  "contextWindow": 128000
}
JSON
    ok "Perfil GITHUB MODELS activado: GPT-4o via GitHub Models (100% gratis)"
    info "No requiere tarjeta de crédito — solo un GitHub Personal Access Token"
    echo ""
    echo "  1. Ve a https://github.com/settings/tokens"
    echo "  2. Generá un token clásico con scope 'read:user'"
    echo "  3. Abrí Cline → ⚙️ → pega el token en 'OpenAI API Key'"
    echo ""
    echo "  Límites: 10 req/min, 50 req/día para GPT-4o"
    echo "  También disponibles: gpt-4o-mini, Llama 3.3 70B, Phi-4, Mistral"
    ;;

  google)
    cat > "$PROVIDERS_FILE" <<- 'JSON'
{
  "apiProvider": "google",
  "googleApiKey": "",
  "googleModel": "gemini-2.5-flash",
  "contextWindow": 1048576
}
JSON
    ok "Perfil GOOGLE AI STUDIO activado: Gemini 2.5 Flash (100% gratis)"
    info "No requiere tarjeta de crédito"
    echo ""
    echo "  1. Ve a https://aistudio.google.com/apikey"
    echo "  2. Creá una API Key (sin tarjeta de crédito)"
    echo "  3. Abrí Cline → ⚙️ → pega la key en 'Google Gemini API Key'"
    echo ""
    echo "  Límites: 500 req/día, 15 RPM — 1M tokens de contexto"
    echo "  Mejor modelo gratis para coding: Gemini 2.5 Flash"
    ;;

  openrouter-free)
    cat > "$PROVIDERS_FILE" <<- 'JSON'
{
  "apiProvider": "openrouter",
  "openRouterApiKey": "",
  "openRouterModel": "openrouter/free",
  "contextWindow": 200000
}
JSON
    ok "Perfil OPENROUTER FREE activado: router automático (27+ modelos gratis)"
    info "Usa 'openrouter/free' — elige el mejor modelo disponible automáticamente"
    echo ""
    echo "  1. Ve a https://openrouter.ai/keys"
    echo "  2. Creá una API Key (sin tarjeta de crédito)"
    echo "  3. Abrí Cline → ⚙️ → pega la key en 'OpenRouter API Key'"
    echo ""
    echo "  Límites: 20 req/min, 50 req/día"
    echo "  Modelos disponibles: Nemotron 3, GPT-OSS, Llama 4, Gemma 4, Laguna M.1"
    echo ""
    echo "  💡 Si un modelo específico funciona mejor, cambialo a:"
    echo "     nvidia/nemotron-3-super-120b-a12b:free"
    echo "     openai/gpt-oss-120b:free"
    ;;

  local)
    cat > "$PROVIDERS_FILE" <<- 'JSON'
{
  "apiProvider": "ollama",
  "ollamaBaseUrl": "http://localhost:11434",
  "ollamaModel": "freehuntx/qwen3-coder-32b-a3b:q4_k_m",
  "contextWindow": 32768
}
JSON
    ok "Perfil LOCAL activado: Qwen3 Coder 32B via Ollama"
    info "Totalmente offline, 0 costo, 0 límites"
    echo ""
    echo "  Para instalar el modelo:"
    echo "    ollama pull freehuntx/qwen3-coder-32b-a3b:q4_k_m"
    echo ""
    echo "  Alternativas más ligeras (8B):"
    echo "    ollama pull qwen3-coder:8b"
    echo "    ollama pull deepseek-coder-v2:16b"
    ;;

  emergency)
    cat > "$PROVIDERS_FILE" <<- 'JSON'
{
  "apiProvider": "openrouter",
  "openRouterApiKey": "",
  "openRouterModel": "google/gemini-2.5-flash",
  "contextWindow": 1048576
}
JSON
    ok "Perfil EMERGENCIA activado: Gemini 2.5 Flash (pago ~$0.30/M tok)"
    info "Este perfil requiere créditos en OpenRouter (~$10 única vez)"
    echo ""
    echo "  Solo usalo cuando los perfiles gratis se queden cortos."
    echo "  Los $10 mínimos en OpenRouter NO expiran y suben el límite"
    echo "  de free models de 50 a 1000 req/día."
    ;;

  *)
    echo "Uso: cline-switch [github|google|openrouter-free|local|emergency]"
    echo ""
    echo "  PERFILES 100% GRATIS (sin tarjeta de crédito):"
    echo "  ─────────────────────────────────────────────────"
    echo "  github          GPT-4o via GitHub Models — MEJOR PARA CODING"
    echo "                  Solo necesita GitHub PAT. 50 req/día."
    echo ""
    echo "  google          Gemini 2.5 Flash via Google AI Studio"
    echo "                  500 req/día, 1M contexto. Muy generoso."
    echo ""
    echo "  openrouter-free Router automático: 27+ modelos gratis"
    echo "                  Nemotron 3, GPT-OSS, Llama 4, Gemma 4"
    echo ""
    echo "  PERFILES LOCALES:"
    echo "  ────────────────"
    echo "  local           Ollama + Qwen3 Coder 32B (offline, 0$)"
    echo ""
    echo "  PERFILES DE PAGO:"
    echo "  ────────────────"
    echo "  emergency       Gemini 2.5 Flash via OpenRouter (~$0.30/M tok)"
    echo ""
    echo "  RECOMENDACIÓN:"
    echo "  github → mejor calidad (GPT-4o gratis)"
    echo "  google → más requests (500/día Gemini 2.5 Flash)"
    echo "  openrouter-free → más modelos disponibles"
    echo "  local → cuando no hay internet"
    ;;
esac
