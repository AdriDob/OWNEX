# Troubleshooting — Provider Issues

## Tabla de diagnóstico rápido

| Síntoma | Causa probable | Solución |
|---------|---------------|----------|
| OmniRoute no responde | Container caído | `docker start omniroute` |
| OmniRoute no responde | Puerto 20128 ocupado | `docker logs omniroute` |
| "No active credentials" | OmniRoute sin providers configurados | Entrar a `http://localhost:20128/` y configurar API keys |
| FCC no responde | fcc-server caído | Ir a `/home/adrie/free-claude-code` y ejecutar `./start_proxy.sh` |
| FCC "Invalid auth token" | Token incorrecto | Verificar `ANTHROPIC_AUTH_TOKEN` en `.env` del FCC |
| Ollama no responde | Ollama caído | `systemctl start ollama` |
| OpenCode API fails | API directa caída | Usar via OmniRoute proxy |
| OpenCode CLI error | Snap problem | `opencode --version` / `snap restart opencode` |

## Comandos de verificación rápida

```bash
# Ver todos los procesos relevantes
ps aux | grep -E "omniroute|fcc-server|ollama|opencode|hermes" | grep -v grep

# Ver puertos en uso
ss -tlnp | grep -E "8000|8082|11434|20128"

# Test OmniRoute
curl -s http://localhost:20128/v1/models | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'{len(d[\"data\"])} models OK')"

# Test FCC
curl -s http://localhost:8082/health

# Test Ollama
curl -s http://localhost:11434/api/tags | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'{len(d[\"models\"])} models OK')"
```

## Provider Health Monitor

```bash
# Ejecutar diagnóstico completo
python3 -c "
import asyncio
from core.orion.health.provider_monitor import get_provider_monitor
report = asyncio.run(get_provider_monitor().check_all())
print(report.dashboard())
"
```

## Logs

| Componente | Location |
|------------|----------|
| OmniRoute | `docker logs omniroute` |
| FCC | Logs a stdout (journald si es systemd) |
| OWNEX API | `logs/` en el proyecto |
| OpenCode | `~/.opencode/logs/` |

## Fallback automático

El orden de failover es:

```
OmniRoute (primary)
  → FCC Proxy (fallback)
    → Ollama (local)
      → OpenCode free (tertiary)
```

Si un provider falla 3+ veces consecutivas, el sistema lo deshabilita
automáticamente y busca el siguiente disponible.
