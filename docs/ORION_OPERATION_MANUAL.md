# ORION Operations Manual — Manual de Piloto

> **Version**: v4.6.0 STABLE
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
7. [Capital Dashboard](#7-capital-dashboard)
8. [Revenue Pipeline](#8-revenue-pipeline)
9. [HERMES — Automatización del Sistema](#9-hermes--automatización-del-sistema)
10. [CLI y Comandos Rápidos](#10-cli-y-comandos-rápidos)
11. [API Reference](#11-api-reference)
12. [Rutina Diaria Recomendada](#12-rutina-diaria-recomendada)
13. [Mantenimiento](#13-mantenimiento)
14. [Troubleshooting](#14-troubleshooting)
15. [Extensions & Desktop](#15-extensions--desktop)

---

## 1. Arquitectura General

ORION es un sistema monolítico modular. Todos los módulos comparten la misma base de datos y se comunican via EventBus.

```
┌──────────────────────────────────────────────────────┐
│                      ORION CORE                       │
│  ┌──────────┐  ┌──────────┐  ┌───────────────────┐  │
│  │ EventBus │  │    DB    │  │  System State     │  │
│  └──────────┘  └──────────┘  └───────────────────┘  │
├──────────────────────────────────────────────────────┤
│  ┌────────────────────────────────────────────────┐  │
│  │              COPILOT (cerebro)                  │  │
│  │  Planner · Executor · Analyzer · Recommender   │  │
│  │  SystemContext · Memory · Evidence Graph       │  │
│  └────────────────────────────────────────────────┘  │
├──────────┬──────────┬──────────┬─────────────────────┤
│  CATEYE  │  ATLAS   │ ODYSSEY  │      HERMES         │
│  AEGIS   │  Crypto  │ Research │  Automation         │
│  Bounty  │  Stocks  │ Markets  │  Scheduler          │
└──────────┴──────────┴──────────┴─────────────────────┘
```

### Stack

| Capa | Tecnología |
|------|-----------|
| Backend | Python 3.11+, FastAPI, SQLAlchemy 2.0+, Pydantic v2 |
| Frontend | Vue 3.5+, TypeScript, Tailwind CSS v4, Vite 6.4+, ShadCN Vue |
| Base de datos | SQLite WAL (dev) / PostgreSQL (prod) |
| Desktop | Tauri (Rust+WebView) |
| Seguridad | Cryptography · AES-256-GCM · Ed25519 · CSRF · Rate Limiting |

### Módulos

| Módulo | Función | API |
|--------|---------|-----|
| **CATEYE** | Bug bounty, pentesting, OSINT | `/api/aegis` |
| **ATLAS** | Finanzas, trading, crypto | `/api/financial` |
| **ODYSSEY** | Investigación, predicción | `/api/odyssey` |
| **HERMES** | Automatización del sistema | CLI via `run.py --hermes` |
| **COPILOT** | Inteligencia transversal | `/api/copilot` |
| **Revenue** | Pipeline de ingresos | `/api/revenue` |
| **Financial Hub** | Payouts, KYC, rutas, impuestos | `/api/financial-hub` |

---

## 2. Inicio y Parada del Sistema

### Inicio rápido

```bash
# 1. Activar entorno virtual
source .venv/bin/activate

# 2. Iniciar backend (servidor API + scheduler + agentes)
python run.py --serve

# 3. (Opcional) Modo desarrollo con hot reload
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000

# 4. (Opcional) Iniciar frontend en modo desarrollo
cd frontend && npm run dev
```

### Verificar que está funcionando

```bash
curl http://localhost:8000/api/health

# Respuesta esperada:
# {"status":"healthy","version":"4.6.0","uptime_seconds":123}
```

Para un diagnóstico completo:

```bash
python run.py --hermes doctor
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

| Modo | Comando | Descripción |
|------|---------|-------------|
| Servidor completo | `python run.py --serve` | Backend + scheduler + agentes |
| Solo backend | `python run.py --serve --no-scheduler` | Sin pipeline automático |
| Solo scheduler | `python run.py --scheduler-only` | Para debug |
| Modo caza | `python run.py --hunt` | Ejecuta pipeline completo una vez |
| Backup | `python run.py --backup` | Backup y salir |
| SPA (production) | `python run.py --spa` | Sirve frontend build desde FastAPI |

---

## 3. Interfaz de Misión

La interfaz principal es **Mission Control**, accesible en `http://localhost:5173` (dev) o desde el desktop build.

### Command Center

Accesible con `Ctrl+K` o `Cmd+K`. Scopos:

| Prefijo | Busca | Ejemplo |
|---------|-------|---------|
| `>` | Comandos del sistema | `> backup`, `> health` |
| `/` | Navegación a páginas | `/ targets`, `/ findings` |
| `@` | Targets | `@ fintech.com` |
| `#` | Findings | `# IDOR` |
| `$` | Reportes | `$ report` |

### Mission Control Dashboard

Sección principal al abrir ORION:

```
┌──────────────────────────────────────────────────┐
│  🟢 Sistema saludable   │  Activos: 14 targets  │
│  ───────────────────────│───────────────────────│
│  Findings: 8 (3 abiertos)│  Reportes: 2         │
│  Aprendizajes: 47       │  Bounty: $4,200      │
└──────────────────────────────────────────────────┘
```

### Páginas principales

| Ruta | App | Descripción |
|------|-----|-------------|
| `/` | Dashboard | Mission Control central |
| `/targets` | CATEYE | Targets de bug bounty |
| `/findings` | CATEYE | Findings generados |
| `/reports` | CATEYE | Reportes generados |
| `/mission-control` | CATEYE | Dashboard operativo |
| `/revenue` | ATLAS | Dashboard de ingresos y pipeline |
| `/revenue-multiplier` | ATLAS | Revenue Multiplier |
| `/capital` | ATLAS | Capital Dashboard |
| `/trading` | ATLAS | Trading y wallets |
| `/investment` | ATLAS | Investment Hub |
| `/wallets` | ATLAS | Gestión de wallets |
| `/financial-hub` | ATLAS | Centro de pagos, KYC, impuestos |
| `/intel` | ODYSSEY | Intelligence Hub |
| `/knowledge-graph` | Sistema | Grafo de conocimiento |
| `/logs` | Sistema | System Logs |
| `/baby-mode` | UX | Baby Mode |

---

## 4. CATEYE / AEGIS — Operaciones de Bug Bounty

### Pipeline Automático

El scheduler ejecuta 5 etapas en ciclo continuo:

```
DISCOVER → RECON → HYPOTHESIS → VALIDATE → REPORT
```

Cada etapa se ejecuta según su intervalo configurado:

| Etapa | Intervalo | Descripción |
|-------|-----------|-------------|
| DISCOVER | 1 hora | Scrapea plataformas de bug bounty |
| RECON | 30 min | Reconocimiento pasivo de targets |
| HYPOTHESIS | 15 min | Genera hipótesis de vulnerabilidades |
| VALIDATE | 2 horas | Ejecuta pruebas controladas |
| REPORT | 1 hora | Genera reportes de findings confirmados |

### Attack Pipeline — De Hipótesis a Evidencia

El Attack Pipeline cierra el gap crítico: convertir hipótesis en evidencia reproducible.

```
Hypothesis → AttackPlanner.plan() → TestPlan → ProbeEngine.execute_plan()
→ Response Comparison → Detection + Confidence Scoring → Evidence Composer
→ Finding Promotion → Report Quality Gate → Revenue Pipeline
```

**Tipos de ataque soportados**: IDOR, SSRF, XSS, SQLi, Auth Bypass (+ Web3)

### Añadir un target manualmente

```bash
# Via CLI
python run.py --add-target "EmpresaX" --domain "empresa.com"

# Via API
curl -X POST http://localhost:8000/api/targets \
  -H "Content-Type: application/json" \
  -d '{"name": "EmpresaX", "domain": "empresa.com"}'
```

### Ver findings

```bash
curl http://localhost:8000/api/findings?status=open
curl http://localhost:8000/api/findings/stats
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

| Herramienta | Uso |
|-------------|-----|
| **Naabu** | Escaneo de puertos |
| **Amass** | Descubrimiento de subdominios |
| **Subfinder** | Subdominios pasivos |
| **Httpx** | Fingerprinting HTTP |
| **Nuclei** | Escaneo de vulnerabilidades |
| **Katana** | Crawling de URLs |
| **FFUF** | Fuzzing de directorios |
| **Dalfox** | Detección de XSS |
| **Shodan** | Inteligencia de exposición (API) |
| **Uncover** | Búsqueda multi-engine |
| **Slither** | Análisis estático de Smart Contracts |

---

## 5. COPILOT — Centro de Decisiones

COPILOT es la capa de inteligencia transversal con 5 niveles de autoridad.

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
    {"action": "validate_findings", "count": 3, "priority": 5, "reason": "3 findings pending validation"}
  ]
}
```

### Prioridades

| Prioridad | Acción | Significado |
|-----------|--------|-------------|
| 5 | `validate_findings` | Findings listos para verificación humana |
| 5 | `deep_study_targets` | Targets con alto score listos para análisis |
| 4 | `generate_reports` | Findings confirmados listos para reporte |
| 3 | `recon_targets` | Targets medianos que necesitan más recon |
| 2 | `discover_targets` | Sistema necesita nuevos targets |

---

## 6. ATLAS — Centro Financiero

### Dashboard Financiero

```bash
curl http://localhost:8000/api/financial/dashboard
```

### Estado de Integraciones

```bash
curl http://localhost:8000/api/financial/integrations/status
```

Muestra estado 🟢🟡🔴 de cada integración:

| Integración | Función | Estado |
|-------------|---------|--------|
| CoinGecko | Precios crypto (30+ monedas) | 🟢 |
| Takenos | USDC balance, CSV import | 🟢 |
| Coinbase | Portfolio via HMAC-SHA256 | 🟢 |
| Kraken | Portfolio via HMAC-SHA512 | 🟢 |

### Financial Hub — Centro de Pagos

El Financial Hub unifica la gestión de pagos, KYC, impuestos y rutas de retiro.

```bash
# Ruta de retiro óptima para $X desde plataforma Y
curl "http://localhost:8000/api/financial-hub/route-optimizer/optimize?amount=1000&source_platform=hackerone"

# Estado de verificación KYC por plataforma
curl http://localhost:8000/api/financial-hub/verifications/progress

# Documentos pendientes
curl http://localhost:8000/api/financial-hub/verifications/pending

# Checklist de documentos
curl http://localhost:8000/api/financial-hub/documents

# Notas impositivas por país
curl http://localhost:8000/api/financial-hub/tax-notes?country=AR

# Estado de KYC por plataforma
curl http://localhost:8000/api/financial-hub/kyc/list
```

### Financial Intelligence

Sistema multi-agente (ATLAS, MIDAS, Risk, Portfolio, F1) para scoring de oportunidades financieras, riesgo y PnL.

```bash
# Estado del pipeline F1
curl http://localhost:8000/api/financial-intelligence/status
```

### Comandos Hermes para finanzas

```bash
python run.py --hermes portfolio
python run.py --hermes prices
```

---

## 7. Capital Dashboard

El Capital Dashboard unifica la visión de capital generado, pipeline de findings, tipos de vulnerabilidad y ROI por programa.

```bash
curl http://localhost:8000/api/revenue/capital-dashboard
```

Respuesta incluye:

**Payout Summary**: total, count, avg, pending, by-platform, by-currency
**Monthly Revenue**: breakdown por mes, count, by-platform
**ROI by Program**: total_payout, count, platforms, last_payout, sorted desc
**ROI by Vuln Type**: total_payout, count, total_programs, avg_payout
**Acceptance Rate**: by platform, acceptance_rate, pending, rejected
**Time Metrics**: avg_days_to_acceptance, avg_days_to_payout
**Finding Pipeline**: total, confirmed, rejected, open, confirmation_rate
**Capital**: total_findings, recent_30d, critical/high count, critical/high rate
**Program Ranking**: top 10 programs por ROI score
**Hot Targets**: top 5 targets por expected value

---

## 8. Revenue Pipeline

Pipeline completo: Finding → Evidence → Report → Platform → Payout

```bash
# Enviar finding como reporte
curl -X POST http://localhost:8000/api/revenue/submit \
  -H "Content-Type: application/json" \
  -d '{"finding_id": 1, "platform": "hackerone", "program": "example"}'

# Ver submissions
curl http://localhost:8000/api/revenue/submissions

# Registrar payout manual
curl -X POST http://localhost:8000/api/revenue/payouts \
  -H "Content-Type: application/json" \
  -d '{"platform": "hackerone", "amount": 500, "currency": "USD"}'

# Resumen de ingresos
curl http://localhost:8000/api/revenue/summary

# Capital Dashboard completo
curl http://localhost:8000/api/revenue/capital-dashboard
```

### Economic Memory

Memoria de ingresos por programa y tipo de vulnerabilidad, con ROI scoring y ranking.

Actualización automática vía scheduler. Acceso programático:

```python
from core.revenue.economic_memory import EconomicMemory

econ = EconomicMemory()
econ.get_summary()  # Resumen global
econ.rank_programs()  # Programas rankeados por ROI
econ.get_program("name")  # Score de un programa específico
```

---

## 9. HERMES — Automatización del Sistema

### Comandos disponibles

```bash
python run.py --hermes backup      # Backup completo del sistema
python run.py --hermes status      # Estado general
python run.py --hermes health      # Health check detallado
python run.py --hermes logs        # Últimos logs
python run.py --hermes doctor      # Diagnóstico del sistema
python run.py --hermes portfolio   # Portfolio financiero
python run.py --hermes prices      # Precios crypto
python run.py --hermes help        # Lista de comandos
python run.py --hunt               # Pipeline completo modo caza
```

---

## 10. CLI y Comandos Rápidos

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

# Capital Dashboard
curl http://localhost:8000/api/revenue/capital-dashboard

# PR des Systeme
curl http://localhost:8000/api/system/status
```

### run.py flags

| Flag | Descripción |
|------|-------------|
| `--serve` | Inicia backend + scheduler |
| `--backup` | Ejecuta backup y sale |
| `--hunt` | Ejecuta pipeline completo una vez |
| `--add-target <name> --domain <d>` | Añade target manualmente |
| `--hermes <command>` | Ejecuta comando Hermes |
| `--build-desktop` | Build de desktop |
| `--version` | Muestra versión |
| `--spa` | Sirve frontend build desde FastAPI |

---

## 11. API Reference

### Endpoints principales

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/api/health` | Health check (no auth) |
| GET | `/api/system/status` | Estado detallado del sistema |
| GET | `/api/system/state` | Estado completo con servicios |
| GET | `/api/copilot/status` | Estado de COPILOT |
| GET | `/api/copilot/recommendations` | Recomendaciones del sistema |
| POST | `/api/targets` | Crear target |
| GET | `/api/targets` | Listar targets |
| POST | `/api/targets/{id}/scan` | Iniciar scan |
| POST | `/api/aegis/deep-study/{id}` | Deep study completo |
| GET | `/api/findings` | Listar findings |
| GET | `/api/reports` | Listar reportes |
| POST | `/api/reports` | Crear reporte |
| GET | `/api/revenue/capital-dashboard` | Capital Dashboard |
| POST | `/api/revenue/submit` | Enviar finding a plataforma |
| GET | `/api/revenue/summary` | Resumen de ingresos |
| GET | `/api/financial/dashboard` | Dashboard financiero |
| GET | `/api/financial/integrations/status` | Estado de integraciones |
| GET | `/api/financial-hub/kyc/list` | Estado KYC por plataforma |
| GET | `/api/financial-hub/documents` | Checklist de documentos |
| GET | `/api/financial-hub/route-optimizer/optimize` | Optimizar ruta de retiro |
| GET | `/api/financial-hub/tax-notes` | Notas impositivas |
| GET | `/api/financial/opportunities` | Oportunidades activas |
| GET | `/api/financial-intelligence/status` | Estado F1 pipeline |
| GET | `/api/knowledge-graph/nodes` | Nodos del grafo de conocimiento |
| POST | `/api/knowledge-graph/query` | Query al grafo de conocimiento |
| GET | `/api/core/extensions` | Extensiones registradas |
| GET | `/api/core/secrets` | Secrets Manager |
| WS | `/ws` | WebSocket Event Stream |

### WebSocket Event Stream

```bash
ws://localhost:8000/ws
```

Eventos en tiempo real del EventBus:

| Evento | Descripción |
|--------|-------------|
| `finding:created` | Nuevos findings |
| `finding:status_changed` | Status updates |
| `report:generated` | Reportes auto-generados |
| `opportunity:found` | Nuevas oportunidades |
| `system:*` | Eventos de salud del sistema |
| `agent:*` | Eventos multi-agente |
| `financial:*` | Eventos de sync financiero |
| `revenue:*` | Revenue pipeline events |
| `workflow:*` | Workflow execution events |

---

## 12. Rutina Diaria Recomendada

### Mañana (5 min)

```bash
# 1. Verificar que el sistema está vivo
curl http://localhost:8000/api/health

# 2. Revisar findings pendientes
curl http://localhost:8000/api/findings?status=open

# 3. Ver Capital Dashboard
curl http://localhost:8000/api/revenue/capital-dashboard

# 4. Check Hermes
python run.py --hermes health
```

### Tarde (10 min)

```bash
# 1. Validar findings nuevos
curl -X PUT http://localhost:8000/api/findings/$ID/status \
  -H "Content-Type: application/json" \
  -d '{"status": "confirmed"}'

# 2. Verificar integraciones
curl http://localhost:8000/api/financial/integrations/status

# 3. Revisar oportunidades priorizadas por ORION
curl http://localhost:8000/api/financial/opportunities

# 4. Ver KYC pendientes
curl http://localhost:8000/api/financial-hub/verifications/pending
```

### Noche (2 min)

```bash
# Backup automático
python run.py --backup

# Resumen del día
python run.py --hermes status
```

---

## 13. Mantenimiento

### Backup

```bash
# Backup completo (DB + config + logs)
python run.py --backup

# Restore
python run.py --restore /path/to/backup.zip

# Los backups se guardan en:
# ~/.orion/backups/orion_backup_YYYYMMDD_HHMMSS/
```

### Logs

```
~/.orion/logs/cateye.log          (logs de aplicación)
~/.orion/audit.jsonl              (eventos de seguridad, 10MB rotación)
~/.orion/hermes_actions.jsonl     (acciones de Hermes)
```

### Base de datos

```bash
# WAL checkpoint manual (se ejecuta automáticamente en cada ciclo)
python -c "from database import db; db.SessionLocal().execute(text('PRAGMA wal_checkpoint(TRUNCATE);'))"
```

### Health Checks automáticos

Health Center ejecuta checks cada 5 minutos:

- Backend: HTTP 200
- Base de datos: query `SELECT 1`
- Agentes: estado de cada agente
- Integraciones: conexión con servicios externos
- Memoria: RSS < 1GB
- EventBus: conectividad

### ORION Auto-Prioritization

ORION prioriza targets usando:

1. **EconomicMemory** ROI histórico por programa
2. **TargetPrioritizer** EV-based ranking con señales económicas
3. **RewardLearner** ajustes por historial de payout por vulnerabilidad
4. **ORION next_action** 1.5x boost para targets recomendados

---

## 14. Troubleshooting

### Diagnóstico rápido

```bash
python run.py --hermes doctor
```

### Tabla de problemas comunes

| Síntoma | Causa probable | Solución |
|---------|----------------|----------|
| `Connection refused` en :8000 | Backend no iniciado | `python run.py` |
| Findings no aparecen | DB no inicializada | `python run.py` inicia automáticamente |
| CoinGecko prices en 0 | Sin conexión a API | Verificar internet |
| Takenos sin balance | Sin datos cargados | Usar balance manual o CSV |
| CSRF 403 | Token faltante | Usar `fetch()` con credentials |
| `useUIStore` error | Cache de Vite | Borrar `node_modules/.vite` |
| Scheduler no ejecuta etapas | Cooldown activo | Verificar logs `\| grep SCHEDULER` |
| COPILOT unavailable | Dependencias faltantes | Verificar logs de inicialización |
| Frontend no carga | Build no generado | `cd frontend && npm run build` |
| Hermes no ejecuta | Safe Mode activo | `HERMES_SAFE_MODE=false` |
| Auth 401 | Token expirado | `/api/auth/login` de nuevo |

### Reset Procedures

```bash
# Reset vault (regenera key, pierde credenciales)
rm ~/.orion/identity_vault.key

# Clear sessions
rm ~/.orion/sessions.json

# Clear evidence
rm -rf ~/.orion/evidence/*

# Reset DB (pierde todos los datos)
rm ~/.orion/database/cateye.db

# Factory reset
rm -rf ~/.orion
```

---

## 15. Extensions & Desktop

### Extension SDK

Las extensions viven en `extensions/*/manifest.py`. Auto-descubrimiento al iniciar.

```bash
# Ver extensiones registradas
curl http://localhost:8000/api/core/extensions

# Secrets Manager
curl http://localhost:8000/api/core/secrets
```

### Desktop App

```bash
# Build distributable
pyinstaller ORION.spec -y

# Run en modo browser (sin tray)
python run.py --browser

# Run con tray
python run.py --tray

# Service mode (Windows)
python run.py --install-service
```

### Watchdog

El watchdog (`desktop/watchdog.py`) monitorea el backend + EventBus cada 10s.

### Performance Tuning

```bash
# SQLite WAL tuning
PRAGMA journal_mode=WAL;
PRAGMA synchronous=NORMAL;
PRAGMA cache_size=-64000;  -- 64MB cache
```

El scheduler corre `PRAGMA wal_checkpoint(TRUNCATE)` automáticamente después de cada ciclo.

---

## Notas de Versión

**v4.6.0** (Julio 2026)
- ✨ Financial Hub: KYC Manager, Route Optimizer, Documents Checklist, Tax Notes
- ✨ Revenue Pipeline: Finding → Evidence → Report → Platform → Payout
- ✨ Capital Dashboard: unified view with program ranking, hot targets, economic memory
- ✨ EconomicMemory: ROI scoring por programa y vulnerabilidad
- ✨ Attack Pipeline: 6 reasoners (IDOR, SSRF, XSS, SQLi, Auth, Web3)
- ✨ AI Router: failover automático entre providers
- ✨ Target Intelligence: EV-based prioritizer
- ✨ Web3: Smart contract analysis + DeFi yield tracking
- ✨ 2330+ tests, Ruff clean
- 🔒 Security hardening: HMAC, machine-id, CSRF, OAuth2, rate limiting, audit log
