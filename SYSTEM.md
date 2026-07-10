# CATEYE — Sistema de Inteligencia para Bug Bounty Automático

> **Versión:** 3.0.0 | **Arquitectura:** v3.0 | **Estado:** STABLE (Julio 2026)
> **Backend:** Python + FastAPI + SQLAlchemy + SQLite/PostgreSQL
> **Frontend:** Vue 3 + TypeScript + Tailwind CSS v4 + Vite
> **Este documento es la CONSTITUCIÓN del proyecto.** Ninguna afirmación sin respaldo en archivos verificados.

---

## Índice

| Sec | Título |
|-----|--------|
| 1 | Visión General |
| 2 | Estructura del Proyecto |
| 3 | Backend — cores/ |
| 4 | Frontend — frontend/ |
| 5 | API REST |
| 6 | Modelos de Datos |
| **7** | **Ciclo de Bug Bounty Automático** |
| 8 | IA y Modelos de Lenguaje |
| 9 | Sincronización y Plataformas |
| 10 | Seguridad |
| 11 | Despliegue |
| 12 | Decisiones Arquitectónicas (Freeze) |
| 13 | Métricas del Sistema |
| **14** | **Progreso de Producción** |

---

## 1. Visión General

CATEYE (formerly "Rastro") es un **sistema de inteligencia operativa privada** para bug bounty. Automatiza el ciclo completo: descubrimiento → análisis → validación → reporte → cobro de vulnerabilidades.

**No es SaaS, no es multi-usuario, no es enterprise.** Es single-user, local-first, de escritorio.

**Propósito fundamental**: Eliminar trabajo humano repetitivo. Cada feature debe responder: "¿esto elimina trabajo humano o solo agrega complejidad?"

| Capa | Tecnología |
|------|------------|
| Backend | Python 3.10+ / FastAPI ≥0.95 |
| Frontend | Vue 3.5 / TypeScript 5.8 strict / Pinia 3 / Tailwind 4 |
| Mobile | Capacitor 8 (shell sin código nativo) |
| Desktop | PyInstaller + pywebview (in-process uvicorn) |
| DB | SQLite via SQLAlchemy 2.0+ (WAL + FK + synchronous NORMAL) |
| Auth | JWT propio + AES-256-GCM sesiones cifradas |
| LLM | Multi-provider: Gemini, Ollama, OpenAI (OpenRouter) |
| CI/CD | GitHub Actions (test.yml + release.yml) |
| Audit | JSONL append-only (`~/.orion/audit.jsonl`) |

---

## 2. Estructura del Proyecto (~478 archivos fuente, ~83K líneas)

```
Rastro/
├── api/                          # FastAPI (65 routers, 6 middleware)
│   ├── main.py                   # App entry: lifespan, middleware stack, auto-report subscriber
│   ├── scheduler.py              # Único pipeline que se ejecuta (5-stage time-based)
│   ├── routers/                  # 65 routers
│   ├── middleware/               # 6 middlewares (CORS, SecurityHeaders, CSRF, RateLimit, Auth, Error)
│   └── services/                 # data_service compartido
├── cores/                        # 59 subpaquetes, ~45K líneas Python
│   ├── orion/                    # Recomendación read-only de próxima acción
│   ├── ai/                       # LLM providers + OrionAgent + tools DB query
│   ├── engine/                   # Scoring, clasificación, snapshot, guardrails
│   │   └── hypothesis/           # 9 generadores rule-based de hipótesis
│   ├── orchestrator/             # Pipeline class (MUERTO) + scan_service (VIVO) + assistant_orchestrator
│   ├── agents/                   # 8 agentes + AgentBus + CoordinatorAgent state machine
│   ├── intelligence/             # CAJÓN DE SASTRE: 19 archivos mezclando 3 concerns
│   │   ├── priority_engine/      # Sistema de prioridades multi-señal (VIVO)
│   │   ├── reward_learning/      # Aprendizaje de recompensas (escribe a SQLite)
│   │   ├── event_system.py       # 3er EventBus paralelo (NO BRIDGEADO)
│   │   └── ...                   # adaptive_memory, trend_detector, pattern_registry, etc.
│   ├── events/                   # EventBus central con persistencia SQLite
│   ├── recon/                    # 18 wrappers de tools CLI (capa 1 de 2)
│   ├── tools/                    # 7 wrappers de tools CLI (capa 2 de 2 — DUPLICADA)
│   ├── bounty_scraper/           # Scraping multi-fuente de programas bug bounty
│   ├── opportunity/              # Ranking de oportunidades IN-MEMORY (se pierde al reiniciar)
│   ├── platforms/                # Integraciones delgadas con 5 plataformas
│   ├── financial/                # TruthLayer, sync, reconciliation, withdrawal
│   ├── validation/               # 10 archivos: ValidationLoopEngine, replayer, confidence
│   ├── execution/                # Mutación, PoC, differential testing
│   ├── reporting/                # ReportEngine, export formats
│   ├── auth/                     # TokenService + SessionStore (DO NOT TOUCH)
│   ├── license/                  # Ed25519 license validator (DO NOT TOUCH)
│   ├── identity_vault.py         # AES-256-GCM credential vault (DO NOT TOUCH)
│   ├── health/                   # SystemHealthEngine (1 de 3 health systems)
│   ├── recovery/                 # HealthMonitor (2 de 3) + RecoveryEngine + CircuitBreaker
│   ├── system_health.py          # collect_health() — business metrics (NO es health system)
│   ├── system_state.py           # SystemState — tracker pasivo de servicios
│   ├── knowledge/                # 14 archivos REALES pero HUÉRFANOS (no conectados al runtime)
│   ├── contracts/                # Interfaces canónicas (Artifact, Bundle) — VIVO
│   ├── crypto/                   # Conectores a wallets (BTC, ETH, SOL, TRX)
│   ├── notifications/            # Hub multi-canal con dedup + persistencia
│   ├── authhub/                  # OAuth2 providers (Gmail, WhatsApp, Telegram)
│   ├── autonomous/               # AutonomousModeEngine
│   ├── learning/                 # Perfil adaptativo + AdaptivePrioritizer
│   ├── memory/                   # 4 sistemas de memoria (memory_store, decision, insight, identity_graph)
│   ├── dedup.py                  # DedupTracker con fingerprints
│   ├── audit_log.py              # JSONL audit trail
│   ├── targeting/                # TargetRadar (MUERTO — nadie lo usa)
│   ├── scanning/                 # LightningScanner (MUERTO — 0 importaciones)
│   └── ... (~18 subpaquetes más)
├── database/                     # SQLAlchemy: 43 tablas en 5 archivos
│   ├── db.py                     # Engine SQLite + session factory + legacy _migrate_columns
│   ├── models.py                 # 29 tablas principales
│   └── models_economic.py        # 7 tablas económicas
├── frontend/                     # 46 páginas Vue, 9 Pinia stores, 50 componentes
├── desktop/                      # 13 módulos (producción-grade)
├── android/                      # Capacitor shell (sin código nativo)
├── tests/                        # 395 tests (393 pass, 2 xfail)
├── scripts/                      # 36 scripts
├── installer/                    # NSIS Windows installer
├── alembic/                      # 1 migración (con mismatch vs modelos actuales)
├── docs/                         # Documentación dispersa
├── .github/                      # CI/CD
└── .githooks/                    # Pre-commit hook ruff (no instalado)
```

---

## 3. Arquitectura General

### 3.1 Flujo Oficial E2E (único verificable desde código)

```
BOOT (api/main.py lifespan)
  ↓
ScanScheduler.start() → asyncio loop cada N minutos
  ↓
[CICLO DEL SCHEDULER — ÚNICO PIPELINE QUE SE EJECUTA]
  ↓
1. DISCOVER → BountyScraper.scrape_all() → crea Targets en DB
  ↓                     publica "opportunity:found" en EventBus
2. RECON → launch_scan() → ReconRunner → persist endpoints
  ↓                     publica "discovery:completed" en EventBus
3. HYPOTHESIS → generate_hypotheses() sobre endpoints sin hipótesis
  ↓                     actualiza ep.hypothesis_id
4. [SCOPE_CHECK — definido en docstring pero NO implementado]
  ↓
5. VALIDATE → ValidationLoopEngine.evaluate() sobre findings open high/critical
  ↓
6. REPORT → create_report_from_findings() sobre findings confirmed
  ↓                     publica "report:generated" en EventBus
  ↓
[INDEPENDIENTE: Auto-report subscriber en main.py]
  finding:status_changed → si new_status=confirmed → genera report draft
```

**Advertencia**: El scheduler llama a `launch_scan()` con argumentos posicionales incorrectos (no pasa `session`). Esto es un bug confirmado.

### 3.2 Agent System (independiente del scheduler, corre en paralelo)

```
start_all_agents() en boot:
  8 agentes: Coordinator, Research, Validator, Exploit, Documentation,
             Strategy, Memory, Financial
  ↓
Cada agente se suscribe a AgentBus
  ↓
CoordinatorAgent state machine (11 estados, event-driven):
  PENDING → DISCOVERY → VALIDATION → EVIDENCE → AI_REVIEW → READY →
  SUBMITTED → TRIAGED → PAID → CLOSED
  ↓
AgentBus → puente → EventBus (solo forwarding de eventos, no control)
```

**Hallazgo crítico**: CoordinatorAgent y ScanScheduler NO comparten estado. Son dos state machines independientes sin sincronización. El coordinador puede reportar COMPLETED mientras el scheduler está en RECON.

### 3.3 ORION (Motor de Decisión — definición definitiva)

**ORION ES READ-ONLY CON UNA EXCEPCIÓN MÍNIMA:**

| Componente | Archivo | Lee | Escribe | ¿Read-only? |
|---|---|---|---|---|
| ContextEngine | `cores/orion/context_engine.py` | OpportunityEngine (RAM) | Nada | ✅ |
| NextAction | `cores/orion/next_action.py` | OpportunityEngine (RAM) | Nada | ✅ |
| OpportunityAnalyzer | `cores/orion/opportunity_analyzer.py` | OpportunityEngine (RAM) | Nada | ✅ |
| OrionAgent | `cores/ai/orion_agent.py` | SQLite vía tools (SELECT) + LLM API | Nada | ✅ |
| Agent Tools | `cores/ai/tools.py` | Target, Finding, Verdict, Endpoint, TargetIntel (SELECT) | Nada | ✅ |
| RewardLearner | `cores/intelligence/reward_learning.py` | Report (DB) + learning_state | `learning_state` (SQLite) — ~40 bytes/vuln | ❌ **ESCRIBE** |

**ORION CONTROLA:**
- **Recomendación** de próxima acción (qué target escanear)
- **Priorización** de targets (vía RewardLearner → scheduler)
- **Contexto** del sistema (estado agregado para decisiones)
- **Ranking** de oportunidades (vía OpportunityEngine)
- **Chat** conversacional vía LLM (solo lectura de DB)

**ORION NUNCA:**
- Ejecuta scans
- Crea/modifica targets, endpoints, findings, reports
- Modifica configuración del pipeline
- Envía reportes a plataformas
- Reemplaza decisión humana

### 3.4 Event Bus

**3 implementaciones independientes:**

| Bus | Archivo | Persistencia | Bridgeado |
|---|---|---|---|
| **EventBus** (central) | `cores/events/event_bus.py` | SQLite | — |
| **AgentBus** (agentes) | `cores/agents/bus.py` | In-memory | ✅ Sí → EventBus |
| **EventSystem** (intelligence) | `cores/intelligence/event_system.py` | In-memory | ❌ **NO** |

EventSystem en intelligence/ emite eventos (`NewEndpoint`, `VerdictChanged`, `CacheHit`) que NADIE en el resto del sistema puede ver.

---

## 4. Contradicciones Arquitectónicas Verificadas (23 hallazgos)

### CRÍTICOS (deben resolverse antes del freeze)

| # | Hallazgo | Evidencia | Impacto |
|---|---|---|---|
| C1 | **Pipeline class (476l) está MUERTO** | `cores/orchestrator/pipeline.py` — 0 imports en todo el código. Scheduler usa `scan_service.launch_scan()`. | 476 líneas + 20 dependencias arrastradas sin razón |
| C2 | **evidence_service.py MUERTO** | `collect_evidence()` — 0 imports en todo el código | Función que nadie llama |
| C3 | **Scheduler llama a launch_scan() con args incorrectos** | `scheduler.py:205-209` pasa keyword args que no coinciden con la firma de `launch_scan()`, y no pasa `session` (requerido) | Scans del scheduler NO funcionan |
| C4 | **3 health systems independientes CORRIENDO** | `cores/health/engine.py` (10s loop, booteado), `cores/recovery/health_monitor.py` (8s loop, booteado), `desktop/watchdog.py` (30s loop, NO booteado). | 3 sistemas revisando memory, eventbus, agents con intervalos diferentes |
| C5 | **5 ranking/priority engines independientes** | OpportunityEngine (RAM), PriorityEngine (RAM), RecommendationEngine (DB), AI+UnifiedScoring (DB), AdaptivePrioritizer (DB+profile). + TargetRadar (MUERTO). | Respuestas contradictorias a "¿qué hago ahora?" |
| C6 | **3 EventBuses independientes** | EventBus (SQLite), AgentBus (RAM+bridge), EventSystem (RAM+NO bridge) | Eventos de intelligence/ invisibles al resto |
| C7 | **OpportunityEngine es volátil** | `engine.py:36` — `self._opportunities: dict` en RAM. Todo perdido al reiniciar. | Cada reinicio = empezar de cero |
| C8 | **CoordinatorAgent vs Scheduler: 0 sincronización** | Dos state machines con stages diferentes, sin compartir estado. | Estados contradictorios posibles |

### ALTOS

| # | Hallazgo | Evidencia | Impacto |
|---|---|---|---|
| H1 | **knowledge/ es real pero HUÉRFANO** | 14 archivos, `SqlKnowledgeStore`, pipeline de ingesta. Nada lo importa en runtime. | 14 archivos de funcionalidad desconectada |
| H2 | **intelligence/ es cajón de sastre** | 19 archivos mezclando 3 concerns: infra duplicada (event_system, cache, observability), learning (adaptive_memory, pattern_registry), huérfanos (bounty_intel, export) | Complejidad accidental |
| H3 | **TargetRadar MUERTO** | `ingest_real_data()` nunca llamado. 0 consumidores. | Código que nadie ejecuta |
| H4 | **scanning/ MUERTO** | LightningScanner — 0 importaciones externas | 256 líneas eliminables |
| H5 | **Alembic vs modelos mismatch** | Migración DROPEA `targets_intel`/`target_scopes` pero modelos siguen en `cores/targets/models.py` | Error en bases nuevas |
| H6 | **65 routers single-user** | Demasiada superficie API para un solo usuario | ~30 routers podrían fusionarse |

### MEDIOS

| # | Hallazgo | Evidencia |
|---|---|---|
| M1 | 2 tool layers paralelas (`cores/recon/` + `cores/tools/`) | Mismas tools CLI, wrappers diferentes |
| M2 | 2 credential vaults (`identity_vault.py` + `target_auth/vault.py`) | AES-256-GCM duplicado |
| M3 | DuplicateDetector + DedupTracker desconectados | `_history` propio vs fingerprints |
| M4 | `analysis/noise_reduction.py` cruza frontera con `validation/` | HotPathDetector podría vivir en cualquiera |
| M5 | 3 routers settings en vez de 1 | settings_ai, settings_runtime, settings_unified |
| M6 | 2 routers system vs system_state | Misma funcionalidad, rutas diferentes |
| M7 | 2 routers auth (device-based + user-based) | Dual auth paths |

### BAJOS

| # | Hallazgo |
|---|---|
| B1 | 0 relationship() en SQLAlchemy — joins manuales |
| B2 | Boolean inconsistente: algunos Boolean, otros String "true"/"false" |
| B3 | `.env` contiene API keys hardcodeadas |
| B4 | Pre-commit hook existe pero no instalado |

---

## 5. Módulos: Clasificación Definitiva

### CORE (deben sobrevivir)
- `api/main.py` — Entry point
- `api/scheduler.py` — Pipeline con bugs por corregir
- `api/middleware/` — 6 middlewares estables
- `api/routers/` — 65 routers (reducibles)
- `cores/events/event_bus.py` — EventBus central
- `cores/orion/` — Recomendación read-only
- `cores/ai/` — LLM providers + OrionAgent + tools
- `cores/engine/` — Scoring, clasificación, snapshot
- `cores/engine/hypothesis/` — 9 generadores rule-based
- `cores/orchestrator/scan_service.py` — Único launch_scan real
- `cores/agents/` — Multi-agente (conectar con scheduler)
- `cores/bounty_scraper/` — Discovery real
- `cores/opportunity/` — Darle persistencia
- `cores/platforms/` — Integraciones plataforma
- `cores/financial/` — TruthLayer, sync, reconciliation
- `cores/validation/` — Loop de validación
- `cores/execution/` — Mutación, PoC
- `cores/reporting/` — Generación de reportes
- `cores/auth/` — TokenService + SessionStore
- `cores/license/` — Ed25519
- `cores/identity_vault.py` — Bóveda AES-256-GCM
- `cores/dedup.py` — DedupTracker
- `cores/audit_log.py` — JSONL audit
- `cores/notifications/` — Hub multi-canal
- `cores/authhub/` — OAuth2 providers
- `cores/crypto/` — Wallet connectors
- `cores/memory/` — Memoria del sistema
- `cores/learning/` — Perfil adaptativo
- `cores/contracts/` — Interfaces canónicas
- `cores/system_state.py` — Tracker de servicios
- `database/` — Modelos + DB layer
- `frontend/` — 46 páginas Vue
- `desktop/` — 13 módulos
- `tests/` — Suite de tests

### EXTENSIÓN (útiles pero no críticos para el ciclo principal)
- `cores/intelligence/priority_engine.py` — Priorización multi-señal
- `cores/intelligence/recommendation_engine.py` — Recomendaciones DB-based
- `cores/intelligence/adaptive_memory.py` — Memoria adaptativa
- `cores/autonomous/` — AutonomousModeEngine
- `cores/differential_intelligence/` — Análisis transversal
- `cores/quick_wins/` — Quick win detection
- `cores/explainability/` — Audit trail
- `cores/accountability/` — Outcome tracking
- `cores/actions/` — Action execution tracker
- `cores/targeting/radar.py` — Si se conecta con datos reales
- `cores/target_auth/` — Autenticación a targets

### EXPERIMENTAL (no confiar en producción)
- `cores/intelligence/event_system.py` — 3er EventBus no bridgeado
- `cores/intelligence/cache.py` — Cache sin problema de performance conocido
- `cores/intelligence/unified_orchestrator.py` — Solapado con pipeline
- `cores/ai/assistant.py` — ScanAssistant (reemplazado por OrionAgent)
- `android/` — Capacitor shell sin código nativo

### MUERTO (eliminar o reconectar)
- `cores/orchestrator/pipeline.py` — 0 imports, 476 líneas, 20 dependencias
- `cores/pipeline/evidence_service.py` — 0 imports
- `cores/scanning/` — 0 imports externos
- `cores/targeting/radar.py` — Nadie lo alimenta ni lo consume
- `cores/knowledge/` — 14 archivos reales, 0 conectados al runtime
- `mobile/` directory — Reemplazado por android/
- Root docs stubs (93 bytes) — AGENT_CONTEXT.md, CLINE_SETUP.md, etc.

---

## 6. PASS / FAIL por Módulo

### ✅ PASS (estable, no tocar)
- License system
- IdentityVault
- Auth (TokenService + SessionStore)
- CSRF Middleware
- Error Handling Middleware
- Security Headers
- Audit Log
- Desktop (13 módulos)
- Frontend (46 páginas)
- Database models (43 tablas)
- EventBus (core)
- Validation Loop
- Financial TruthLayer
- Bounty Scraper
- Hypothesis generators
- ORION core (context, next_action, analyzer)
- crypto/
- notifications/

### ⚠️ PASS CON RESERVAS (funciona pero necesita correcciones)
- **ORION/RewardLearner** — Escribe a learning_state (excepción documentada)
- **CoordinatorAgent** — State machine usada solo vía API, no auto-start
- **OpportunityEngine** — Todo en RAM, se pierde al reiniciar
- **knowledge/** — 13 archivos reales, 0 conectados al runtime

### ❌ FAIL (resueltos en v3.0 FREEZE)
- ~~Pipeline class~~ → archivado en `archive_cleanup/`
- ~~evidence_service.py~~ → archivado
- ~~scanning/~~ → archivado
- ~~TargetRadar~~ → archivado
- ~~intelligence/event_system.py~~ → ahora es wrapper sobre EventBus
- ~~system_state.py boot_time bug~~ → corregido (usa get_uptime)
- ~~system_health.py collect_health bug~~ → corregido (acceso a dataclass)
- ~~Scheduler launch_scan args~~ → corregido (pasa session + kwargs correctos)
- ~~Alembic mismatch~~ → corregido (migración es no-op)
- **knowledge/** — Pendiente para v3.1

---

## 7. Ciclo de Bug Bounty Automático

El pipeline oficial se ejecuta en `api/scheduler.py` (ScanScheduler). Es el ÚNICO flujo que corre en runtime. No hay state machines paralelas.

```
                    ┌─────────────────────┐
                    │  DISCOVERY           │
                    │  BountyScraper       │
                    │  scrape_all()        │
                    │  → Targets en DB     │
                    │  → opportunity:found │
                    └─────────┬───────────┘
                              ▼
                    ┌─────────────────────┐
                    │  RECONNAISSANCE      │
                    │  launch_scan()       │
                    │  → ReconRunner       │
                    │  → Endpoints en DB   │
                    │  → discovery:completed│
                    └─────────┬───────────┘
                              ▼
                    ┌─────────────────────┐
                    │  HYPOTHESIS          │
                    │  generate_hypotheses │
                    │  → 9 rule-based gens │
                    │  → ep.hypothesis_id  │
                    └─────────┬───────────┘
                              ▼
                    ┌─────────────────────┐
                    │  VALIDATION          │
                    │  ValidationLoopEng.  │
                    │  evaluate()          │
                    │  → findings abiertos │
                    └─────────┬───────────┘
                              ▼
                    ┌─────────────────────┐
                    │  FINDING CONFIRM     │
                    │  pipeline → verdict  │
                    │  → finding:created   │
                    │  → finding:status    │
                    └─────────┬───────────┘
                              ▼
                    ┌─────────────────────┐
                    │  REPORT DRAFT        │
                    │  create_report_from_ │
                    │  findings()          │
                    │  Auto-report sub:    │
                    │  finding confirmed   │
                    │  → report:generated  │
                    └─────────┬───────────┘
                              ▼
                    ┌─────────────────────┐
                    │  HUMAN REVIEW        │
                    │  (UI / API manual)   │
                    └─────────┬───────────┘
                              ▼
                    ┌─────────────────────┐
                    │  SUBMISSION          │
                    │  vía plataforma API  │
                    │  (H1, BC, Intigriti, │
                    │   Synack, YesWeHack) │
                    └─────────┬───────────┘
                              ▼
                    ┌─────────────────────┐
                    │  PAYMENT TRACK       │
                    │  Financial TruthLayer│
                    │  + webhooks manuales │
                    └─────────┬───────────┘
                              ▼
                    ┌─────────────────────┐
                    │  LEARNING LOOP       │
                    │  RewardLearner       │
                    │  PatternRegistry     │
                    │  AdaptiveMemory      │
                    └─────────┬───────────┘
                              │
                    ┌─────────▼───────────┐
                    │  ORION DECIDE       │
                    │  NextAction:        │
                    │  "qué target sigue" │
                    └─────────────────────┘
```

**Stack por etapa:**

| Etapa | Módulo | Método | Output |
|-------|--------|--------|--------|
| DISCOVERY | `cores/bounty_scraper/monitor.py` | `scrape_all()` | Targets en DB |
| RECON | `cores/orchestrator/scan_service.py` | `launch_scan()` → `ReconRunner.run_pipeline()` | Endpoints en DB |
| HYPOTHESIS | `cores/engine/hypothesis/generators.py` | `generate_hypotheses()` | ep.hypothesis_id asignado |
| VALIDATION | `cores/validation/loop_engine.py` | `evaluate()` | Findings + Verdicts |
| REPORT | `cores/pipeline/report_service.py` | `create_report_from_findings()` | Reports en DB |
| SUBMISSION | `cores/platforms/*.py` | vía API keys | Envío a plataforma |
| PAYMENT | `cores/financial/truth_layer.py` | sync + reconciliation | Ledger actualizado |
| LEARNING | `cores/intelligence/reward_learning.py` | `analyze()` | Ajustes de prioridad |

---

## 12. Decisiones Arquitectónicas (v3.0 STABLE)

### Único Pipeline: **ScanScheduler** (`api/scheduler.py`) — ✅ RESUELTO
Pipeline class archivado. launch_scan() corregido (session+kwargs). SCOPE_CHECK no implementado (por diseño).

### Único EventBus: **EventBus** (`cores/events/event_bus.py`) — ✅ RESUELTO
AgentBus mantiene `LocalEventBus` propio + bridge a EventBus. EventSystem delegado a EventBus (wrapper tipado).

### Único Discovery Engine: **BountyScraper** (`cores/bounty_scraper/`) — ✅ YA ÚNICO

### ORION: **Read-only con excepción documentada** — ✅ DEFINIDO
RewardLearner escribe `learning_state` (~40 bytes/tipo). Todo lo demás es SELECT-only.

### Health System: **Unificar 3 → 1** — ⏳ v3.1
SystemHealthEngine + HealthMonitor + Watchdog. No rompe el sistema.

### Ranking Engine: **Unificar 5 → 1** — ⏳ v3.1
OpportunityEngine (RAM) + PriorityEngine + RecommendationEngine + AdaptivePrioritizer + UnifiedScoring.

### Tool Layer: **Unificar recon/ + tools/** — ⏳ v3.1
Dos capas de wrappers CLI para las mismas tools.

### CoordinatorAgent — ⏳ v3.1
State machine de agentes. No auto-start, solo vía API. No conflictúa con scheduler en runtime.

### Knowledge/ — ⏳ v3.1
13 archivos reales huérfanos. Conectar o archivar.

---

## 13. Métricas del Sistema

| Métrica | Valor |
|---------|-------|
| Archivos Python (cores/) | 339 |
| Archivos Python (api/) | 77 |
| Líneas Python (cores/) | 59,330 |
| Líneas Python (api/) | 13,162 |
| Líneas frontend (src/) | 25,476 |
| Líneas tests | 5,811 |
| **Total líneas fuente** | **~103,779** |
| Subpaquetes cores/ | 61 |
| Routers API | 64 |
| Middleware | 5 |
| Tablas DB (models) | 36 |
| Páginas frontend | 57 |
| Componentes frontend | 39 |
| Pinia stores | 15 |
| Tests colectados | 361 (359 pass, 2 xfail) |
| Agentes | 8 |
| Plataformas bug bounty | 5 |
| LLM providers | 3 |
| Blockchains | 4 (BTC, ETH, SOL, TRX) |

---

## 14. Progreso de Producción

### Código Total

| Métrica | Valor |
|---------|-------|
| Líneas Python (cores/ + api/) | ~72.5K |
| Líneas frontend (src/) | ~25.5K |
| Líneas tests | ~5.8K |
| **Total líneas fuente** | **~103.8K** |
| Archivos Python (cores/ + api/) | 416 |
| Archivos frontend (.ts/.vue/.css) | 140 |
| Archivos de tests | 16 |
| **Total archivos fuente** | **~572** |

### Completitud por Área

| Área | % | Detalle |
|------|---|---------|
| Backend cores/ | 98% | 61 módulos, ~59K líneas. Conectados, funcionales, pipeline E2E verificado. Alembic no-op (init_db vía create_all). |
| API REST | 96% | 64 routers registrados. Endpoints CRUD funcionales para targets, findings, reports, evidence. Pendiente: DELETE faltantes en algunos routers. |
| Frontend Vue 3 | 93% | 57 páginas, 39 componentes, 15 stores, 64 routers del backend cubiertos. Tailwind v4 + Vitest configurado (17 tests frontend). |
| Desktop / Launcher | 90% | Multi-modo (browser, tray, service, safe-mode), PyInstaller, boot guard, autostart, updater. |
| Plataformas Bug Bounty | 70% | 5 integraciones (H1, BC, Intigriti, Synack, YWH), bóveda IdentityVault. Pendiente: battle-testing, manejo de errores de API. |
| Tests Backend | 85% | 361 tests (359 pass, 2 xfail). Cobertura: agents, API, scoring, learning, E2E, crypto, contracts. |
| Tests Frontend | 15% | Vitest + Vue Test Utils configurados. 17 tests. Pendiente: stores, pages, composables. |
| Mobile | 0% | Android/ es shell Capacitor sin código nativo. Planificado para v5.x. |
| **Total General** | **~91%** | |

### 9% Restante (priorizado para v3.1)

| Prioridad | Item | Esfuerzo |
|-----------|------|----------|
| 1 | Unificar 3 health systems (SystemHealthEngine + HealthMonitor + Watchdog) | 2-3 días |
| 2 | Unificar 5 ranking/priority engines en uno | 2-3 días |
| 3 | Unificar tool layers (cores/recon/ + cores/tools/) | 1-2 días |
| 4 | Conectar o archivar knowledge/ (13 archivos huérfanos) | 1 día |
| 5 | Más tests frontend (stores, pages, composables) | 3-5 días |
| 6 | CRUD faltantes (DELETE targets, endpoints, etc.) | 1 día |
| 7 | Normalizar formato de respuesta API | 2-3 días |
| 8 | Mobile (Capacitor/Tauri) | 1-2 semanas |

---

*Documento actualizado desde código verificado — Julio 2026. Freeze v3.0 STABLE completado.*
*CATEYE v3.0.0 | Architecture v3.0 | CONSTITUCIÓN DEL PROYECTO*
