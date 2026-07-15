# ORION Operations Manual — Manual de Piloto

> **Version**: 4.3.2 STABLE  
> **Última actualización**: Julio 2026  
> **Propósito**: Guía de operación diaria del sistema ORION como plataforma personal de inteligencia.

---

## Tabla de Contenidos

1. [Arquitectura General](#1-arquitectura-general)
2. [Inicio y Parada del Sistema](#2-inicio-y-parada-del-sistema)
3. [Interfaz de Misión](#3-interfaz-de-misión)
4. [CATEYE / AEGIS — Operaciones de Bug Bounty](#4-cateye--aegis--operaciones-de-bug-bounty)
5. [COPILOT — Centro de Decisiones](#5-copilot--centro-de-decisiones)
6. [ATLAS — Centro Financiero](#6-atlas--centro-financiero)
7. [HERMES — Automatización del Sistema](#7-hermes--automatización-del-sistema)
8. [ODYSSEY — Investigación](#8-odyssey--investigación)
9. [CLI y Comandos Rápidos](#9-cli-y-comandos-rápidos)
10. [API Reference](#10-api-reference)
11. [Mantenimiento](#11-mantenimiento)
12. [Troubleshooting](#12-troubleshooting)

---

## 1. Arquitectura General

ORION es un sistema monolítico modular. Todos los módulos comparten la misma base de datos y se comunican via EventBus.

```
┌─────────────────────────────────────────────────────┐
│                     ORION CORE                       │
│  ┌──────────┐  ┌──────────┐  ┌───────────────────┐  │
│  │ EventBus │  │   DB     │  │  System State     │  │
│  └──────────┘  └──────────┘  └───────────────────┘  │
├─────────────────────────────────────────────────────┤
│  ┌───────────────────────────────────────────────┐  │
│  │              COPILOT (cerebro)                │  │
│  │  Planner · Executor · Analyzer · Recommender  │  │
│  │  SystemContext · Memory · Evidence Graph      │  │
│  └───────────────────────────────────────────────┘  │
├──────────┬──────────┬──────────┬────────────────────┤
│  CATEYE  │  ATLAS   │ ODYSSEY  │      HERMES        │
│  AEGIS   │  Crypto  │ Research │  Automation        │
│  Bounty  │  Stocks  │ Markets  │  Scheduler         │
└──────────┴──────────┴──────────┴────────────────────┘
```

### Stack

| Capa | Tecnología |
|---|---|
| Backend | Python 3.11+, FastAPI, SQLAlchemy |
| Frontend | Vue 3, TypeScript, Tailwind CSS v4, Vite, ShadCN Vue |
| Base de datos | SQLite (dev) / PostgreSQL (prod) |
| Desktop | Tauri (shell) |
| Workers | asyncio + scheduler interno |

### Módulos

| Módulo | Función | Puerto |
|---|---|---|
| **CATEYE** | Bug bounty, pentesting, OSINT | API `/api/aegis` |
| **ATLAS** | Finanzas, trading, crypto | API `/api/financial` |
| **ODYSSEY** | Investigación, predicción | API `/api/odyssey` |
| **HERMES** | Automatización del sistema | CLI via `run.py --hermes` |
| **COPILOT** | Inteligencia transversal | API `/api/copilot` |

---

## 2. Inicio y Parada del Sistema

### Inicio rápido

```bash
# 1. Activar entorno virtual
source .venv/bin/activate

# 2. Iniciar backend (servidor API + scheduler + agentes)
python run.py --serve

# 3. (Opcional) Iniciar frontend en modo desarrollo
cd frontend && npm run dev

# 4. (Opcional) Build desktop
python run.py --build-desktop
```

### Verificar que está funcionando

```bash
# Health check básico
curl http://localhost:8000/api/health

# Respuesta esperada:
# {"status":"healthy","version":"4.3.2","uptime_seconds":123}
```

### Parada segura

```bash
# Ctrl+C en la terminal donde corre el backend
# ORION ejecuta shutdown hooks que:
# 1. Detienen el scheduler
# 2. Cierran conexiones DB
# 3. Checkpoint WAL
# 4. Guardan estado
```

### Modos de ejecución

```bash
# Servidor completo (backend + scheduler + agentes)
python run.py --serve

# Solo backend (sin scheduler)
python run.py --serve --no-scheduler

# Solo scheduler (para debug)
python run.py --scheduler-only

# Backup y salir
python run.py --backup
```

---

## 3. Interfaz de Misión

La interfaz principal es **Mission Control**, accesible en `http://localhost:5173` (dev) o desde el desktop build.

### Command Center

Accesible con `Ctrl+K` o `Cmd+K`. Scopos:

| Prefijo | Busca | Ejemplo |
|---|---|---|
| `>` | Comandos del sistema | `> backup`, `> health` |
| `/` | Navegación a páginas | `/ targets`, `/ findings` |
| `@` | Targets | `@ fintech.com` |
| `#` | Findings | `# IDOR` |
| `$` | Reportes | `$ report` |

### Mission Control Dashboard

Sección principal al abrir ORION:

```
┌─────────────────────────────────────────────────┐
│  🟢 Sistema saludable    │  Activos: 14 targets │
│  ────────────────────────│──────────────────────│
│  Findings: 8 (3 abiertos)│  Reportes: 2         │
│  Aprendizajes: 47        │  Bounty: $4,200      │
└─────────────────────────────────────────────────┘
```

---

## 4. CATEYE / AEGIS — Operaciones de Bug Bounty

### Pipeline Automático

El scheduler ejecuta 5 etapas en ciclo continuo:

```
DISCOVER → RECON → HYPOTHESIS → VALIDATE → REPORT
```

Cada etapa se ejecuta según su intervalo configurado:

| Etapa | Intervalo | Descripción |
|---|---|---|
| DISCOVER | 1 hora | Scrapea plataformas de bug bounty |
| RECON | 30 min | Reconocimiento pasivo de targets |
| HYPOTHESIS | 15 min | Genera hipótesis de vulnerabilidades |
| VALIDATE | 2 horas | Ejecuta pruebas controladas |
| REPORT | 1 hora | Genera reportes de findings confirmados |

### Añadir un target manualmente

```bash
# Via CLI
python run.py --add-target "EmpresaX" --domain "empresa.com"

# Via API
curl -X POST http://localhost:8000/api/targets \
  -H "Content-Type: application/json" \
  -d '{"name": "EmpresaX", "domain": "empresa.com"}'
```

### Deep Study Mode

Análisis profundo de un target como investigador de seguridad:

```bash
curl -X POST http://localhost:8000/api/aegis/deep-study/1
```

Respuesta:
```json
{
  "status": "ok",
  "study": {
    "score": 8.5,
    "technologies": ["Spring Boot", "React", "GraphQL"],
    "hypotheses": ["Actuator leak", "GraphQL introspection", "IDOR"],
    "playbook_actions": [
      {"action": "check_actuator", "risk": 0.6},
      {"action": "check_introspection", "risk": 0.5}
    ],
    "recommendations": [
      "HIGH PRIORITY: Spring Boot detected — prioritize actuator review"
    ]
  }
}
```

### Herramientas de Reconocimiento

| Herramienta | Comando CLI | Uso |
|---|---|---|
| **Naabu** | `naabu -host target.com` | Escaneo de puertos |
| **Amass** | `amass enum -d target.com` | Descubrimiento de subdominios |
| **Subfinder** | `subfinder -d target.com` | Subdominios pasivos |
| **Httpx** | `httpx -l urls.txt` | Fingerprinting HTTP |
| **Nuclei** | `nuclei -t templates/` | Escaneo de vulnerabilidades |
| **Katana** | `katana -u target.com` | Crawling de URLs |
| **FFUF** | `ffuf -u domain/FUZZ` | Fuzzing de directorios |
| **Dalfox** | `dalfox -u target.com` | Detección de XSS |
| **Shodan** | API (no CLI) | Inteligencia de exposición |
| **Uncover** | `uncover -q domain` | Búsqueda multi-engine |

---

## 5. COPILOT — Centro de Decisiones

COPILOT es la capa de inteligencia transversal. No es un chat — es un **sistema operativo de decisiones**.

### Endpoints

```bash
# Estado del agente
curl http://localhost:8000/api/copilot/status

# Recomendaciones del sistema
curl http://localhost:8000/api/copilot/recommendations
```

Respuesta de recomendaciones:
```json
{
  "status": "ok",
  "recommendations": [
    {
      "action": "validate_findings",
      "count": 3,
      "priority": 5,
      "reason": "3 findings pending validation"
    },
    {
      "action": "deep_study_targets",
      "count": 2,
      "priority": 5,
      "reason": "2 high-value targets ready for deep analysis"
    }
  ]
}
```

### Cómo interpretar las recomendaciones

| Prioridad | Acción | Significado |
|---|---|---|
| 5 | `validate_findings` | Findings listos para verificación humana |
| 5 | `deep_study_targets` | Targets con alto score listos para análisis |
| 4 | `generate_reports` | Findings confirmados listos para reporte |
| 3 | `recon_targets` | Targets medianos que necesitan más recon |
| 2 | `discover_targets` | Sistema necesita nuevos targets |

### Integración en Scheduler

Después de cada etapa del pipeline, COPILOT registra recomendaciones:

```
[COPILOT] After recon: deep_study_targets (prio=5) — 2 high-value targets ready
[COPILOT] After validate: generate_reports (prio=4) — 1 finding ready for reporting
```

---

## 6. ATLAS — Centro Financiero

### Dashboard Financiero

```bash
curl http://localhost:8000/api/financial/dashboard
```

### Integraciones

```bash
curl http://localhost:8000/api/financial/integrations/status
```

Muestra estado 🟢🟡🔴 de cada integración:
- CoinGecko (precios crypto)
- Takenos (USDC)
- Coinbase (HMAC)
- Kraken (portfolio)

### Comandos Hermes para finanzas

```bash
python run.py --hermes portfolio
python run.py --hermes prices
```

---

## 7. HERMES — Automatización del Sistema

### Comandos disponibles

```bash
python run.py --hermes backup      # Backup completo del sistema
python run.py --hermes status      # Estado general
python run.py --hermes health      # Health check detallado
python run.py --hermes logs        # Últimos logs
python run.py --hermes doctor      # Diagnóstico del sistema
python run.py --hermes help        # Lista de comandos
```

### Automatización programada

HERMES registra un job `hermes_health_check` en el AppRegistry que ejecuta health checks periódicos.

---

## 8. ODYSSEY — Investigación

### Predicciones

Cada predicción registra:
- Hipótesis
- Fecha
- Probabilidad estimada
- Resultado real
- Aprendizaje

### Uso

```bash
# Investigación de un tema
python run.py --odyssey research "tema"

# Ver predicciones activas
python run.py --odyssey predictions
```

---

## 9. CLI y Comandos Rápidos

### run.py

| Flag | Descripción |
|---|---|
| `--serve` | Inicia backend + scheduler |
| `--backup` | Ejecuta backup y sale |
| `--add-target <name> --domain <d>` | Añade target manualmente |
| `--hermes <command>` | Ejecuta comando Hermes |
| `--build-desktop` | Build de desktop |
| `--version` | Muestra versión |

### Atajos útiles

```bash
# Health check
curl http://localhost:8000/api/health

# Ver targets
curl http://localhost:8000/api/targets

# Ver findings
curl http://localhost:8000/api/findings

# Recomendaciones COPILOT
curl http://localhost:8000/api/copilot/recommendations

# Deep study de target específico
curl -X POST http://localhost:8000/api/aegis/deep-study/1

# Estado del scheduler
curl http://localhost:8000/api/system/health
```

---

## 10. API Reference

### Endpoints principales

| Método | Ruta | Descripción |
|---|---|---|
| GET | `/api/health` | Health check |
| GET | `/api/copilot/status` | Estado de COPILOT |
| GET | `/api/copilot/recommendations` | Recomendaciones del sistema |
| POST | `/api/targets` | Crear target |
| GET | `/api/targets` | Listar targets |
| GET | `/api/targets/{id}` | Detalle de target |
| POST | `/api/targets/{id}/scan` | Iniciar scan |
| GET | `/api/targets/{id}/summary` | Score del target |
| POST | `/api/aegis/deep-study/{id}` | Deep study completo |
| GET | `/api/aegis/deep-study/{id}` | Metadata de deep study |
| GET | `/api/aegis/health` | Health de AEGIS |
| POST | `/api/evidence/upload` | Subir evidencia |
| GET | `/api/financial/dashboard` | Dashboard financiero |
| GET | `/api/financial/integrations/status` | Estado de integraciones |
| GET | `/api/system/health` | Health del sistema |

---

## 11. Mantenimiento

### Backup

```bash
# Backup completo (DB + config + logs)
python run.py --backup

# Los backups se guardan en:
# ~/.orion/backups/orion_backup_YYYYMMDD_HHMMSS/
```

### Logs

```
~/.orion/logs/cateye.log
~/.orion/audit.jsonl       (eventos de seguridad)
~/.orion/hermes_actions.jsonl  (acciones de Hermes)
```

Rotación automática de `audit.jsonl` cada 10MB (3 backups).

### Base de datos

```bash
# WAL checkpoint manual (se ejecuta automáticamente en cada ciclo)
python -c "from database import db; db.SessionLocal().execute(text('PRAGMA wal_checkpoint(TRUNCATE);'))"
```

### Limpieza de cooldowns

El scheduler purga automáticamente entradas de cooldown mayores a 2 horas.

### Health Checks automáticos

Health Center ejecuta checks cada 5 minutos:
- Backend: HTTP 200
- Base de datos: query `SELECT 1`
- Agentes: estado de cada agente
- Integraciones: conexión con servicios externos
- Memoria: RSS < 1GB

---

## 12. Troubleshooting

### Problema: Backend no inicia

```bash
# Verificar que el puerto no esté ocupado
lsof -i :8000

# Verificar entorno virtual
source .venv/bin/activate
python -c "import cores; print('OK')"

# Verificar base de datos
python -c "from database import db; db.init_db(); print('DB OK')"
```

### Problema: Scheduler no ejecuta etapas

```bash
# Verificar estado
curl http://localhost:8000/api/system/health

# Verificar logs
tail -f ~/.orion/logs/cateye.log | grep SCHEDULER
```

### Problema: COPILOT no disponible

```bash
curl http://localhost:8000/api/copilot/status
# Si devuelve "unavailable", verificar:
# 1. Dependencias instaladas
# 2. Logs de inicialización
```

### Problema: Herramienta de reconocimiento no funciona

```bash
# Verificar instalación
which naabu
naabu --version

# Verificar hint de instalación
python -c "from cores.tools.naabu import NaabuTool; print(NaabuTool.install_hint)"
```

### Problema: Shodan no devuelve datos

```bash
# Verificar API key
echo $SHODAN_API_KEY

# Configurar si es necesario
export SHODAN_API_KEY="tu_key_aquí"
```

### Problema: Base de datos corrupta

```bash
# Restaurar del último backup
python run.py --backup  # primero hacer backup del estado actual
# Luego restaurar manualmente desde ~/.orion/backups/
```

### Problema: Frontend no compila

```bash
cd frontend
npm install
npm run build
# Errores comunes: tipos incorrectos, imports faltantes
```

### Logs de diagnóstico rápidos

```bash
# Últimos 50 logs del sistema
python run.py --hermes logs

# Health check detallado
python run.py --hermes doctor

# Ver procesos activos
python run.py --hermes status
```

---

## Apéndice A: Enlaces Útiles

- `http://localhost:8000/docs` — Documentación interactiva de la API (Swagger)
- `http://localhost:5173` — Frontend en desarrollo
- `~/.orion/` — Directorio de datos del sistema
- `docs/HERMES_GUIDE.md` — Guía detallada de Hermes
- `.ai/AGENT_CHARTER.md` — Constitución del sistema

---

## Apéndice B: Rutina Diaria Recomendada

### Mañana (30 min)

```bash
# 1. Health check
curl http://localhost:8000/api/health

# 2. Recomendaciones COPILOT
curl http://localhost:8000/api/copilot/recommendations

# 3. Revisar findings abiertos
curl http://localhost:8000/api/findings
```

### Trabajo profundo (2-4 horas)

```
1. Priorizar targets según COPILOT
2. Ejecutar Deep Study en targets de alto score
3. Validar findings manualmente
4. Generar reportes
```

### Tarde (30 min)

```
1. Registrar feedback de findings validados
2. Revisar métricas de la semana
3. Ejecutar backup si es necesario
```

---

*Este manual se actualiza con cada versión mayor de ORION. Mantenelo sincronizado con el estado real del sistema.*
