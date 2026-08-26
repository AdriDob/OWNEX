# Troubleshooting

> Soluciones a los problemas más comunes. Cada entrada: síntoma → causa → fix → verificación.

## OWNEX no arranca

### Backend no responde en :8000

**Síntoma**: `curl http://localhost:8000/api/health` no responde o connection refused.

**Causas comunes**: puerto ocupado por proceso zombi; dependencias faltantes; DB corrupta.

```bash
# 1. Verificar qué ocupa el puerto
lsof -i :8000          # Linux
netstat -ano | findstr :8000   # Windows

# 2. Matar proceso previo si existe
kill -9 $(lsof -t -i :8000)   # Linux

# 3. Arrancar limpio
python run.py
```

**Verificación**: `curl http://localhost:8000/api/health` → `{"status": "..."}`.

---

### Error `no such table` al abrir

**Síntoma**: dashboard vacío, logs muestran `sqlite3.OperationalError: no such table: targets`.

**Causa**: base de datos no inicializada (instalación fresca sin boot del server).

```bash
python -c "from database.db import init_db; init_db()"
python run.py
```

En instalaciones desktop (PyInstaller/Tauri), el schema se inicializa automáticamente al primer arranque.

---

## Frontend no carga

### Página en blanco / errores CORS

**Síntoma**: consola del browser muestra errores CORS hacia `localhost:8000`.

```bash
cd frontend && npm ci && npm run dev
```

El backend debe estar corriendo ANTES de abrir el frontend. Verifica que `api/main.py` tenga tu origen en la lista CORS (por defecto acepta `localhost:5173` y orígenes Tauri).

---

## IA no disponible

### "IA OFFLINE — modo reglas" en AI Center

**Síntoma**: badge rojo en `/ai`, modo `offline_ai`.

**Causa**: ningún provider LLM healthy (Ollama caído, sin red, cuotas agotadas).

```bash
# 1. Verificar Ollama local
ollama list                    # ¿está corriendo?
curl http://localhost:11434/api/tags | head -5

# 2. Verificar estado detallado
curl http://localhost:8000/oar/status | python -m json.tool | grep -A5 resilience

# 3. Diagnóstico completo
curl http://localhost:8000/oar/doctor
```

**Nota**: OWNEX continúa funcionando en modo reglas deterministas. El LLM es opcional para scoring, payment-compat y barriers.

---

### Provider específico caído (ej. OpenCode)

**Síntoma**: `oar/status` muestra ese provider como unhealthy, fallback_rate alto.

**Causa**: API key inválida, servicio externo caído, o cuota agotada.

```bash
# Ver clasificación del error
curl http://localhost:8000/oar/status | python -c "
import json,sys
data = json.load(sys.stdin)
for pid, h in data.get('health', {}).items():
    print(f'{pid}: {h[\"status\"]} — {h.get(\"last_error\", \"\")[:80]}')
"
```

OWNEX hace fallback automático. Si el circuit breaker abrió, se recupera solo tras el cooldown (default 300s).

---

## Scheduler detenido

**Síntoma**: jobs no se ejecutan, Mission Control muestra scheduler stopped.

```bash
curl http://localhost:8000/api/scheduler/status
```

Si está parado tras un crash: reiniciar el backend lo recupera (los jobs usan croniter y retoman su schedule). Los scans interrumpidos se marcan como `failed` al boot (`recover_stale_scans`, umbral 6h).

---

## Puerto en conflicto

**Síntoma**: `[Errno 48] Address already in use` al arrancar.

```bash
# Encontrar el proceso
sudo ss -tlnp | grep 8000     # Linux
# Cambiar puerto (backend)
UVICORN_PORT=8001 python run.py --port 8001
```

---

## Base de datos

### ¿Dónde viven mis datos?

| Entorno | Path |
|---|---|
| Dev (WSL/Linux) | `<repo>/database/catseye.db` |
| Desktop Windows | `%LOCALAPPDATA%/OWNEX/database/catseye.db` |
| Override | Variable `DATABASE_URL` |

### Backup

```bash
python run.py --backup
```

### Reset completo (destruye datos)

```bash
rm database/catseye.db && python -c "from database.db import init_db; init_db()"
```

⚠️ **Irreversible** — hacer backup primero.

---

## Tests fallan masivamente

**Síntoma**: cientos de errores de colección (`ImportError`).

**Causa más común**: conflicto de módulos shadowing stdlib (`cores/platform/` vs stdlib `platform`). Importar siempre desde el root del repo:

```bash
cd /home/adriel/projects/Rastro    # ← root, nunca subdirectorios
.venv/bin/python -m pytest tests/test_scoring.py -q
```

Si un solo archivo rompe toda la colección: `git checkout HEAD -- <archivo>` para descartar cambios locales corruptos.

---

## Windows específico

### SmartScreen bloquea el instalador

Click en **Más información** → **Ejecutar de todas formas**. El instalador no está firmado con certificado de código.

### Datos después de reinstalar

Los datos persisten en `%LOCALAPPDATA%/OWNEX` — sobreviven desinstalaciones. Para reset completo, borrar esa carpeta manualmente.

---

## Comandos de diagnóstico rápido

```bash
# Salud general
curl http://localhost:8000/api/health

# Estado completo del sistema
curl http://localhost:8000/api/system/health

# IA
curl http://localhost:8000/oar/doctor

# Scheduler
curl http://localhost:8000/api/scheduler/status

# Tests rápidos
make test-fast
```
