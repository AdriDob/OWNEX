# OmniRoute — AI Gateway

## Estado: OK (Docker container running)

OmniRoute es un AI Gateway multi-provider que corre como contenedor Docker.

## Conexión

| Item | Valor |
|------|-------|
| URL | `http://localhost:20128/v1` |
| API Key | `omniroute` (local, sin valor real) |
| Puerto | 20128 |
| Container | `diegosouzapw/omniroute:latest` |
| Estado | `docker ps` debe mostrar `omniroute` como `healthy` |

## Modelos disponibles

- `auto/best-coding` — coding tasks, 1M contexto
- `auto/best-reasoning` — reasoning/analysis, 1M contexto
- `auto/best-fast` — chat rápido, 1M contexto
- `auto/smart` — auto-selección
- `auto/claude-sonnet` — Claude via OmniRoute
- `auto/claude-opus` — Claude Opus via OmniRoute
- `auto/gemini` — Gemini via OmniRoute
- `auto/gpt-5` — GPT-5 via OmniRoute
- `oc/deepseek-v4-flash-free` — OpenCode free model via proxy
- `oc/qwen3.6-plus-free` — Qwen free via proxy

## Iniciar

```bash
docker start omniroute
```

## Detener

```bash
docker stop omniroute
```

## Verificar estado

```bash
curl -s http://localhost:20128/v1/models | python3 -m json.tool | head -20
```

## Ver logs

```bash
docker logs -f omniroute
```

## Variables necesarias

| Variable | Valor |
|----------|-------|
| `OMNIROUTE_API_KEY` | `omniroute` |
| `OMNIROUTE_BASE_URL` | `http://localhost:20128/v1` |

## Notas

- OmniRoute es un router que a su vez conecta a proveedores upstream (OpenAI, Anthropic, Google, Groq, etc.)
- Las credenciales de los proveedores upstream se configuran dentro del dashboard de OmniRoute en `http://localhost:20128/`
- No requiere API key real para uso local porque el tráfico se rutea internally
- Es el proveedor **primario** recomendado para OWNEX
