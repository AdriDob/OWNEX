# ORION Platform — Guía de Operación Diaria

> v4.1.0 — Julio 2026

---

## 1. Abrir ORION

```bash
# Desde el directorio del proyecto
python run.py

# O en modo desarrollo (hot reload)
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

Una vez iniciado, abrir: http://localhost:8000

---

## 2. Verificar salud del sistema

```bash
curl http://localhost:8000/api/health
```

Respuesta esperada: JSON con `status: "healthy"`, score, checks por categoría.

Para un diagnóstico más profundo:

```bash
python run.py --hermes doctor
```

---

## 3. Revisar notificaciones y estado

### CATEYE (Bug Bounty)

```bash
# Ver findings pendientes
curl http://localhost:8000/api/findings?status=open

# Ver oportunidades activas
curl http://localhost:8000/api/opportunities
```

### ATLAS (Inversiones)

```bash
# Dashboard financiero unificado
curl http://localhost:8000/api/financial/dashboard

# Estado de integraciones
curl http://localhost:8000/api/financial/integrations/status
```

### Hermes (Automatización)

```bash
# Estado del agente
python run.py --hermes status

# Health check
python run.py --hermes health

# Últimas acciones
python run.py --hermes logs
```

---

## 4. Rutina diaria recomendada

### Mañana (5 min)

```bash
# 1. Verificar que el sistema está vivo
curl http://localhost:8000/api/health

# 2. Revisar findings pendientes
curl http://localhost:8000/api/findings?status=open

# 3. Ver estado financiero
curl http://localhost:8000/api/financial/dashboard

# 4. Check Hermes
python run.py --hermes health
```

### Tarde (10 min)

```bash
# 1. Validar findings nuevos
#    (usar PATCH /api/findings/{id}/status)

# 2. Verificar integraciones
curl http://localhost:8000/api/financial/integrations/status

# 3. Revisar oportunidades priorizadas por ORION
curl http://localhost:8000/api/opportunities?sort=priority
```

### Noche (2 min)

```bash
# Backup automático
python run.py --backup

# Resumen del día
python run.py --hermes status
```

---

## 5. Mantenimiento semanal

```bash
# Backup completo
python run.py --backup

# Diagnóstico del sistema
python run.py --hermes doctor

# Revisar logs de auditoría
less ~/.orion/audit.jsonl

# Revisar acciones de Hermes
less ~/.orion/hermes_actions.jsonl
```

---

## 6. Troubleshooting rápido

| Síntoma | Causa probable | Solución |
|---|---|---|
| `Connection refused` en :8000 | Backend no iniciado | `python run.py` |
| Findings no aparecen | DB no inicializada | `python run.py` inicia automáticamente |
| CoinGecko prices en 0 | Sin conexión a API | Verificar internet |
| Takenos sin balance | Sin datos cargados | Usar balance manual o CSV |
| Hermes recomienda pero no ejecuta | Safe Mode activo | `HERMES_SAFE_MODE=false` |
| Frontend no carga | Build no generado | `cd frontend && npm run build` |
| CSRF 403 | Token faltante | Usar `fetch()` con credentials |
| `useUIStore` error | Cache de Vite | Borrar `node_modules/.vite` |

---

## 7. Comandos útiles

```bash
# Iniciar sistema
python run.py

# Backup
python run.py --backup

# Hermes
python run.py --hermes help

# Tests
.venv/bin/python -m pytest --timeout=60

# Lint
.venv/bin/python -m ruff check .

# Frontend build
cd frontend && npm run build

# Ver procesos
ps aux | grep uvicorn
```
