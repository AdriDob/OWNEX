# Hermes Agent v1 — Guía de Usuario

> Automation Agent seguro para ORION Platform. v0.1.0

---

## ¿Qué es Hermes?

Hermes es el agente de automatización transversal de ORION Platform. Ejecuta tareas repetitivas y de mantenimiento del sistema de forma controlada:

- **Backup** automático de base de datos y configuración
- **Health Check** de todos los servicios del sistema
- **System Doctor** con diagnóstico de integridad DB, disco, procesos
- **Status** de todos los módulos ORION
- **Logs** recientes de auditoría y scheduler

Por defecto opera en **modo seguro**: solo recomienda acciones destructivas sin ejecutarlas.

---

## Inicio rápido

### Desde terminal (recomendado)

```bash
# Ver comandos disponibles
python run.py --hermes help

# Health check del sistema
python run.py --hermes health

# Backup (en modo seguro solo recomienda)
python run.py --hermes backup

# Backup (forzar ejecución)
HERMES_SAFE_MODE=false python run.py --hermes backup

# Diagnóstico completo
python run.py --hermes doctor

# Últimas 30 líneas de logs
python run.py --hermes logs
```

### Desde WSL Ubuntu

```bash
# Misma sintaxis — correr desde el directorio del proyecto
cd ~/projects/Rastro && python run.py --hermes status
```

---

## Comandos disponibles

| Comando | Descripción | Riesgo | Destructivo | Safe mode |
|---|---|---|---|---|
| `help` | Lista todos los comandos disponibles | none | No | Normal |
| `status` | Reporta estado del sistema y módulos cargados | none | No | Normal |
| `health` | Ejecuta health check completo vía Health Center | none | No | Normal |
| `logs` | Muestra últimas N líneas de audit.jsonl y logs | none | No | Normal |
| `doctor` | Diagnóstico: tamaño DB, disco, versión Python | low | No | Normal |
| `backup` | Ejecuta backup de DB y config vía run.py --backup | low | Sí | **Recomienda solo** |

---

## Configuración (variables de entorno)

| Variable | Default | Descripción |
|---|---|---|
| `HERMES_SAFE_MODE` | `true` | Si es true, comandos destructivos solo se recomiendan |
| `HERMES_LOG_ACTIONS` | `true` | Persiste todas las acciones en `~/.orion/hermes_actions.jsonl` |
| `HERMES_AUTO_BACKUP` | `false` | Backup automático programado (requiere Safe Mode = false) |
| `HERMES_BACKUP_INTERVAL_H` | `24` | Horas entre backups automáticos |

---

## Acceso directo Windows

### Opción A — Acceso directo WSL (Recomendada)

1. Crear archivo `Hermes.bat` en el escritorio:

```batch
@echo off
wsl -d Ubuntu -- cd ~/projects/Rastro && python run.py --hermes help
pause
```

2. Cambiar icono: Click derecho → Propiedades → Acceso directo → Cambiar icono
3. Usar icono personalizado de Hermes/ORION (PNG convertido a .ico)

### Opción B — Pin en barra de tareas

1. Crear acceso directo a `Hermes.bat`
2. Arrastrar a barra de tareas
3. Para evitar ventana CMD persistente, crear un `.vbs` launcher:

```vbscript
' HermesLauncher.vbs
Set WshShell = CreateObject("WScript.Shell")
WshShell.Run "wsl -d Ubuntu -- cd ~/projects/Rastro && python run.py --hermes health", 0, False
```

---

## Integración con EventBus

Hermes publica eventos al EventBus del sistema cuando ejecuta acciones:

- `hermes:action_executed` — después de cada comando ejecutado
- `hermes:health_completed` — después de cada health check
- `hermes:backup_completed` — después de cada backup

Estos eventos son visibles en el Dashboard de ORION y quedan registrados en el Decision Journal.

---

## Logs y auditoría

Todas las acciones de Hermes se registran en:

- **JSONL**: `~/.orion/hermes_actions.jsonl` (formato append-only, JSON por línea)
- **EventBus**: Eventos publicados para consumo de otros módulos
- **Decision Journal**: Si está disponible, las acciones se registran allí

---

## Troubleshooting

| Problema | Causa | Solución |
|---|---|---|
| `Unknown command` | Comando mal escrito | Usar `--hermes help` para listar |
| `[SAFE MODE] Action was recommended but not executed` | Safe mode activo | `HERMES_SAFE_MODE=false python run.py --hermes backup` |
| Backup timeout | Base de datos muy grande | El timeout es 5 minutos. Correr manualmente `python run.py --backup` |
| `Health Center not available` | ORION Core Health Center no cargado | Verificar que `core/health/` esté instalado |
| Logs vacíos | No hay archivos de log | Ejecutar alguna acción primero para generar logs |

---

## Seguridad

- Hermes **nunca ejecuta** comandos destructivos sin aprobación explícita (Safe Mode)
- Hermes **nunca modifica** datos financieros, findings o reportes
- Hermes **nunca auto-envía** reportes a plataformas de bug bounty
- Hermes **nunca ejecuta** comandos financieros sin supervisión humana
- Todas las acciones quedan registradas en `hermes_actions.jsonl`
- Los comandos disponibles están explícitamente autorizados en `AUTHORIZED_COMMANDS`

Para desactivar el safe mode permanentemente:

```bash
# En .bashrc o .env
export HERMES_SAFE_MODE=false
```

---

## Próximos pasos (v0.2.0)

- [ ] Frontend widget en ORION Dashboard
- [ ] API REST endpoint (`/api/hermes/execute`)
- [ ] WebSocket para eventos en tiempo real
- [ ] Automatizaciones programables por el usuario
- [ ] Skills personalizados para tareas específicas
