# FCC Proxy — Free Claude Code Proxy

## Estado: OK (fcc-server running)

FCC es un proxy ligero que expone un endpoint compatible con OpenAI/Anthropic
y lo redirige a proveedores upstream (OpenRouter, Ollama, etc.).

## Conexión

| Item | Valor |
|------|-------|
| URL | `http://localhost:8082` |
| Auth Token | `orion-dev-local` |
| Puerto | 8082 |
| Proceso | `fcc-server` (Python) |
| Origen | `/home/adrie/free-claude-code/` |

## Modelos disponibles

Lista completa: 200+ modelos via OpenRouter + Ollama local.

Los más usados:

| ID | Upstream |
|----|----------|
| `claude-sonnet-4-5` | OpenRouter → Claude Sonnet |
| `claude-haiku-4-5` | OpenRouter → Claude Haiku |
| `claude-opus-4-5` | OpenRouter → Claude Opus |
| `ollama/qwen2.5:3b-instruct` | Ollama local |
| `open_router/anthropic/claude-opus-5` | OpenRouter directo |
| `open_router/google/gemini-3.5-flash-lite` | Gemini via OpenRouter |

## Ruteo por tier

Configurado en `/home/adrie/free-claude-code/.env`:

```
MODEL="ollama/qwen2.5:3b-instruct"
MODEL_HAIKU="ollama/qwen2.5:3b-instruct"
MODEL_SONNET="open_router/google/gemini-3.5-flash-lite"
MODEL_OPUS="open_router/anthropic/claude-opus-5"
MODEL_FABLE="open_router/google/gemini-3.5-flash-lite"
```

## Iniciar

```bash
cd /home/adrie/free-claude-code && ./start_proxy.sh
```

O si no existe el script:

```bash
cd /home/adrie/free-claude-code && source .venv/bin/activate && fcc-server
```

## Verificar estado

```bash
curl -s http://localhost:8082/health
# → {"status":"healthy"}
```

## Variables necesarias

| Variable | Valor |
|----------|-------|
| `ANTHROPIC_AUTH_TOKEN` | `orion-dev-local` |
| `FCC_BASE_URL` | `http://localhost:8082` |
| `FCC_AUTH_TOKEN` | `orion-dev-local` |

## Notas

- FCC es el proveedor **fallback** recomendado para OWNEX
- Usa OpenRouter para modelos premium (Claude, Gemini, etc.)
- Los modelos locales (Ollama) no requieren API key
- El token de autenticación `orion-dev-local` es interno, no es una API key real
