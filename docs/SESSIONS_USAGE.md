# 📋 OWNEX — Sistema de Sesiones y Autoguardado

OWNEX guarda automáticamente tu progreso de trabajo para que **nunca pierdas dónde estabas**, incluso si cierras el equipo, reinicias o el sistema se detiene inesperadamente.

---

## 🎯 Qué hace

| Función | Descripción |
|---------|-------------|
| **Autoguardado** | Cada vez que guardas una tarea o progreso, se escribe en SQLite y en un respaldo JSON |
| **Restauración automática** | Al arrancar OWNEX, se recupera la última sesión activa (tarea en curso, notas, evidencia, momentum) |
| **Historial** | Puedes ver todas las sesiones previas con su enfoque, objetivo y estado |
| **Persistencia cruzada** | Funciona igual en Windows, Linux y WSL |

---

## 🚀 Cómo usar

### 1. Iniciar una sesión de trabajo

```bash
curl -X POST http://localhost:8000/api/session/start \
  -H "Content-Type: application/json" \
  -d '{
    "focus": "bounty",
    "daily_goal": "Subir 2 reports a HackerOne",
    "notes": "Enfocado en web apps de fintech"
  }'
```

El `focus` puede ser: `bounty`, `skill`, `pulse`, `recon`, `writeup`, `setup`, `otro`

### 2. Guardar la tarea en curso

```bash
curl -X POST http://localhost:8000/api/session/task \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Validar hallazgo X en HackerOne",
    "status": "in_progress",
    "priority": "high",
    "notes": "Revisando screenshots de /api/verdicts",
    "linked_type": "target",
    "linked_id": 12,
    "momentum": 7
  }'
```

### 3. Guardar progreso (autoguardado incremental)

Cada vez que avances, guarda el progreso sin crear una tarea nueva:

```bash
curl -X POST http://localhost:8000/api/session/progress \
  -H "Content-Type: application/json" \
  -d '{
    "notes": "Avanzando en el análisis del endpoint /api/targets",
    "momentum": 8,
    "evidence_item": {
      "url": "https://hackerone.com/reports/12345",
      "note": "Hallazgo de IDOR en endpoint de perfil"
    },
    "targets_referenced": [12, 42]
  }'
```

### 4. Ver el estado actual (dashboard)

```bash
curl http://localhost:8000/api/session/status
```

Respuesta:
```json
{
  "success": true,
  "has_active_session": true,
  "session_id": "wrk-1792708832262",
  "focus": "bounty",
  "daily_goal": "Subir 2 reports a HackerOne",
  "status": "active",
  "current_task": {
    "title": "Validar hallazgo X en HackerOne",
    "status": "in_progress",
    "momentum": 8,
    "notes": "Avanzando en el análisis..."
  }
}
```

### 5. Ver historial de sesiones

```bash
curl http://localhost:8000/api/session/recent?limit=10
```

### 6. Cerrar una sesión

```bash
curl -X POST http://localhost:8000/api/session/complete
```

---

## 🏥 Sistema de salud del sistema

OWNEX incluye monitoreo de salud para verificar que todo funciona antes de empezar a trabajar:

```bash
# Resumen general (0-100)
curl http://localhost:8000/api/system/health

# Detalle de cada health check
curl http://localhost:8000/api/system/health/checks

# Estado del motor de recuperación
curl http://localhost:8000/api/system/health/recovery

# Estado de circuit breakers
curl http://localhost:8000/api/system/health/circuits

# Métricas del sistema (CPU, RAM, disco)
curl http://localhost:8000/api/system/health/metrics

# Forzar recuperación de componentes fallidos
curl -X POST http://localhost:8000/api/system/health/recover
```

---

## 💾 Dónde se guardan los datos

| Tipo | Ubicación |
|------|-----------|
| Sesiones y tareas | SQLite (misma BD de OWNEX) |
| Respaldo JSON | `~/.config/ownex/session/state.json` |
| Logs del backend | `%LOCALAPPDATA%/OWNEX/logs/` (Windows) o `~/.local/share/OWNEX/logs/` (Linux) |

El respaldo JSON se actualiza en cada cambio, así que incluso si la base de datos no está disponible, puedes recuperar el último estado conocido.

---

## 🔄 Flujo de trabajo diario recomendado

```
1. Abrir OWNEX → la última sesión se restaura automáticamente
2. Revisar /api/session/status → ¿en qué tarea estabas?
3. Si es una nueva tarea → POST /api/session/task con el título
4. Cada vez que avances → POST /api/session/progress con notas y evidencia
5. Al terminar el día → POST /api/session/complete
6. Mañana siguiente → todo sigue exactamente donde lo dejaste
```

---

## ⚠️ Notas importantes

- **No se guardan credenciales ni tokens** en las sesiones. Solo notas de progreso y evidencia descriptiva.
- El momentum es una puntuación de 1-10 que indica tu energía/foco en la tarea.
- Las sesiones completadas se mantienen en el historial para referencia futura.
- Si no hay sesión activa al arrancar, OWNEX crea una nueva automáticamente con enfoque "bounty".
