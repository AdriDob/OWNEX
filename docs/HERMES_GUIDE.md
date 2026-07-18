# MERLIN Agent — Guía de Usuario

> Automation & Operations Agent para ORION Platform. v0.4.0
> (Antes conocido como **Hermes**)

---

## ¿Qué es MERLIN?

MERLIN es el agente de automatización y operaciones de ORION Platform. Ejecuta tareas de mantenimiento, monitoreo y diagnóstico del sistema de forma controlada:

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
# Ver comandos disponibles (MERLIN o Hermes son válidos)
python run.py --merlin help
python run.py --hermes help    # alias legacy

# Health check del sistema
python run.py --merlin health

# Backup (en modo seguro solo recomienda)
python run.py --merlin backup

# Backup (forzar ejecución)
MERLIN_SAFE_MODE=false python run.py --merlin backup

# Diagnóstico completo
python run.py --merlin doctor

# Últimas 30 líneas de logs
python run.py --merlin logs
```

### Desde WSL Ubuntu

```bash
# Misma sintaxis — correr desde el directorio del proyecto
cd ~/projects/Rastro && python run.py --merlin status
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
| `MERLIN_SAFE_MODE` (legacy: `HERMES_SAFE_MODE`) | `true` | Si es true, comandos destructivos solo se recomiendan |
| `MERLIN_LOG_ACTIONS` (legacy: `HERMES_LOG_ACTIONS`) | `true` | Persiste todas las acciones en `~/.orion/merlin_actions.jsonl` |
| `MERLIN_AUTO_BACKUP` (legacy: `HERMES_AUTO_BACKUP`) | `false` | Backup automático programado (requiere Safe Mode = false) |
| `MERLIN_BACKUP_INTERVAL_H` (legacy: `HERMES_BACKUP_INTERVAL_H`) | `24` | Horas entre backups automáticos |

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

MERLIN publica eventos al EventBus del sistema cuando ejecuta acciones:

- `merlin:action_executed` — después de cada comando ejecutado
- `merlin:health_completed` — después de cada health check
- `merlin:backup_completed` — después de cada backup

Estos eventos son visibles en el Dashboard de ORION y quedan registrados en el Decision Journal.

---

## Logs y auditoría

Todas las acciones de MERLIN se registran en:

- **JSONL**: `~/.orion/merlin_actions.jsonl` (legacy: `~/.orion/hermes_actions.jsonl`)
- **EventBus**: Eventos publicados para consumo de otros módulos
- **Decision Journal**: Si está disponible, las acciones se registran allí

---

## Troubleshooting

| Problema | Causa | Solución |
|---|---|---|
| `Unknown command` | Comando mal escrito | Usar `--merlin help` para listar |
| `[SAFE MODE] Action was recommended but not executed` | Safe mode activo | `MERLIN_SAFE_MODE=false python run.py --merlin backup` |
| Backup timeout | Base de datos muy grande | El timeout es 5 minutos. Correr manualmente `python run.py --backup` |
| `Health Center not available` | ORION Core Health Center no cargado | Verificar que `core/health/` esté instalado |
| Logs vacíos | No hay archivos de log | Ejecutar alguna acción primero para generar logs |

---

## Seguridad

- MERLIN **nunca ejecuta** comandos destructivos sin aprobación explícita (Safe Mode)
- MERLIN **nunca modifica** datos financieros, findings o reportes
- MERLIN **nunca auto-envía** reportes a plataformas de bug bounty
- MERLIN **nunca ejecuta** comandos financieros sin supervisión humana
- Todas las acciones quedan registradas en `merlin_actions.jsonl`
- Los comandos disponibles están explícitamente autorizados en `AUTHORIZED_COMMANDS`

Para desactivar el safe mode permanentemente:

```bash
# En .bashrc o .env
export MERLIN_SAFE_MODE=false
```

---

## Próximos pasos

- [ ] Frontend widget en ORION Dashboard
- [ ] API REST endpoint (`/api/merlin/execute`)
- [ ] WebSocket para eventos en tiempo real
- [ ] Automatizaciones programables por el usuario
- [ ] Skills personalizados para tareas específicas
