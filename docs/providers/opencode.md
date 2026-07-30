# OpenCode — Free Tier Provider

## Estado: OK (via OmniRoute proxy)

OpenCode provee modelos gratuitos (deepseek, qwen, nemotron, etc.)
accesibles via API HTTP o CLI.

## Conexión

| Item | Valor |
|------|-------|
| API URL | `http://localhost:20128/v1` (via OmniRoute) |
| API Key | `omniroute` |
| CLI | `opencode` (snap) v1.18.8 |
| CLI Config | `~/.config/opencode/config.json` |

## Modelos gratuitos disponibles

| ID | Descripción |
|----|-------------|
| `oc/deepseek-v4-flash-free` | DeepSeek V4 Flash |
| `oc/qwen3.6-plus-free` | Qwen 3.6 Plus |
| `oc/minimax-m3-free` | MiniMax M3 |
| `oc/nemotron-3-ultra-free` | NVIDIA Nemotron 3 Ultra |

## Uso con CLI

```bash
opencode run --model oc/deepseek-v4-flash-free -p "tu pregunta"
```

## Uso con API (via OmniRoute)

```bash
curl -X POST http://localhost:20128/v1/chat/completions \
  -H "Authorization: Bearer omniroute" \
  -H "Content-Type: application/json" \
  -d '{"model":"oc/deepseek-v4-flash-free","messages":[{"role":"user","content":"Hola"}],"stream":false}'
```

## Variables necesarias

| Variable | Valor |
|----------|-------|
| `OPENCODE_API_KEY` | `omniroute` |
| `OPENCODE_BASE_URL` | `http://localhost:20128/v1` |

## Notas

- OpenCode free API directa (`api.opencode.ai`) no siempre responde correctamente
- Se recomienda acceder via OmniRoute proxy para mejor confiabilidad
- Es el proveedor **terciario** (free tier), para tareas simples
- No requiere API key real para modelos free
