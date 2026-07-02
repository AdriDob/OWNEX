# ORION — Sistema de Inteligencia para Bug Bounties

**Versión:** 1.6.0 | **Licencia:** MIT | **Stack:** Python 3.14 + FastAPI + Vue 3 + SQLAlchemy + SQLite/PostgreSQL

---

## 1. Filosofía

ORION no es un escáner de vulnerabilidades. Es un **sistema de inteligencia económica para bug bounties**.

- **100% local** — ningún dato sale de tu máquina
- **Privacidad total** — credenciales cifradas con AES-256-GCM
- **Sin suscripciones** — código abierto, autónomo
- **Pasivo por diseño** — ZAP solo en modo spider + passive scan. Nunca lanza exploits.
- **Enfoque económico** — toda decisión se mide en USD/hora, probabilidad de éxito, retorno esperado

---

## 2. Arquitectura General

```
DESKTOP (main_desktop.py)
  PyWebView | SystemTray | Uvicorn (thread) | Watchdog
       |
FASTAPI (api/main.py)
  38+ Routers | Auth+Rate Middleware | Scheduler 6-stage | WebSocket
       |
CORE ENGINES (core_engines/)
  Contracts | Artifacts | Intelligence | Agents (8)
  Economic  | Opportunity | Hypothesis | Validation
  Recovery  | Learning    | ScopeReader | Screenshot
       |
DATABASE (SQLite/PostgreSQL)
  targets | endpoints | findings | reports
  programs | bounty_tier | scope_doc | program_intel
  financial | memory_patterns | report_priorities
       |
FRONTEND (Vue 3 + Tailwind v4)
  MissionControl | MoneyRadar | OpportunityRadar | Reports
  HotPaths | Findings | ProgramIntel | VerificationGuide
```

---

## 3. Backend

**Framework:** FastAPI + Uvicorn + Pydantic v2 + SQLAlchemy 2.0

### Entry Points
- `run.py` — Launcher state machine (`--install`, `--tray`, `--browser`, `--service`, `--build`, `--safe-mode`)
- `launcher/start.py` — Launcher unificado con seed de datos demo
- `desktop/main_desktop.py` — Entry point desktop (uvicorn in-process, PyWebView, system tray)

### main.py
- Lifespan: `init_db()` → `start_scheduler()` → `OrionState.start()`
- CORS all origins, AuthMiddleware, RateLimitMiddleware
- 65+ routers, WebSocket `/api/ws`

### Scheduler (`api/scheduler.py`)
Pipeline autónomo de 5 etapas:
```
DISCOVER → RECON → HYPOTHESIS → VALIDATE → REPORT
```
Cada etapa con intervalo independiente, forcéable manualmente, try/except por etapa.

### Routers (38+)

| Router | Prefix | Key Endpoints |
|---|---|---|
| `targets` | `/api/targets` | CRUD, trigger scan |
| `endpoints` | `/api/endpoints` | CRUD, search |
| `findings` | `/api/findings` | CRUD, generate report, export md/pdf |
| `evidence` | `/api/evidence` | CRUD, file upload |
| `reports` | `/api/reports` | CRUD, submit, reward learning |
| `hypotheses` | `/api/hypotheses` | CRUD, generation, ZAP source |
| `roi` | `/api/roi` | ROI calculations |
| `orion` | `/api/orion` | Orion context, next action |
| `assistant` | `/api/assistant` | Copilot chat |
| `economic` | `/api/economic` | Economic intelligence (1180+ lines) |
| `zap` | `/api/zap` | ZAP passive integration |
| `auth` | `/api/auth` | Login, session |
| `validation` | `/api/validation` | Validation recording |
| `attack` | `/api/attack` | Attack decision engine |

---

## 4. Base de Datos

### models.py (20+ ORM models)
User, Target, Endpoint, Finding, Verdict, Evidence, ScanRun, PipelineState, Investigation, Hypothesis, Identity, BountySignal, TargetIntel, Notification, QuickWin, Opportunity, MemoryRecord, Report, SubmissionRecord, ReportVersion, Favorite, Task, Session, Notification

### models_economic.py (7 modelos)
- **Program** — Programa bug bounty (nombre, plataforma, URL, scope, rewards, exclusions, tecnologías, activos, orion_score)
- **BountyTier** — Escalas de recompensa por programa
- **ScopeDocument** — Scope descargado, parseado, resumido, con hash + cambios
- **ProgramIntel** — Dossier permanente (AI summary, tecnologías, cambios históricos, bugs públicos, hipótesis, notas IA, dificultad, competencia, velocidad, probabilidad de éxito)
- **FinancialMetric** — Métricas time-series (USD/hora, USD/programa)
- **MemoryPattern** — Patrones aprendidos (categoría, observación, confianza, evidencia)
- **ReportPriority** — Cola de reportes priorizada (expected_value, priority_score, time_to_submit)

---

## 5. Core Engines (67 subpaquetes)

### Foundation
- `contracts/` — Interfaces canónicas: Artifact, Bundle, protocols
- `artifacts/` — 10 artefactos canónicos (Pipeline, EvidenceGraph, Screenshot, Differential, QuickWins, ExecutionPlan, AIInsight, AttackSurface, ROI, Hypothesis)

### Intelligence Layer
- `unified_orchestrator.py` — Orquestador central, managea lifecycle de artefactos
- `dependency_graph.py` — Grafo de dependencias
- `event_system.py` — Bus FIFO (max 500 eventos)
- `adaptive_memory.py` — Memoria a corto y largo plazo
- `reward_learning.py` — RewardLearner, ProgramRewardMetrics, VulnTypeStats
- `priority_engine.py` — Scoring de prioridad
- `bounty_intel.py` — Inteligencia de plataformas bounty

### Hypothesis Engine
9 generadores basados en reglas (IDOR, Auth Bypass, SSRF, XSS, SQLi, Open Redirect, SSTI, LFI, Info Disclosure) + enriquecimiento LLM + generador ZAP + campos didácticos.

### Multi-Agent System
8 agentes como daemon threads, coordinados por CoordinatorAgent via event bus:
- CoordinatorAgent, ResearchAgent, ValidatorAgent, ExploitAgent, DocumentationAgent, StrategyAgent, MemoryAgent, FinancialAgent

### Scope Reader
Descarga (urllib), parsea HTML (stdlib) y PDF (regex), extrae assets, hashea, detecta cambios, resume con AI.

### Otros
- `opportunity/` — OpportunityEngine con 4 providers
- `validation/` — VerdictHandler, EvidenceBuilder, Replayer, LoopEngine, Confidence
- `recovery/` — RecoveryEngine, CircuitBreaker, HealthMonitor
- `learning/` — InvestigatorProfile, AdaptivePrioritizer, MemoryBuilder
- `identity_vault.py` — AES-256-GCM encrypted credential storage

---

## 6. Frontend

**Stack:** Vue 3 + TypeScript + Vite + Tailwind v4 + Pinia + ShadCN Vue + Lucide icons

### Páginas

| Ruta | Página | Propósito |
|---|---|---|
| `/` | MissionControl.vue | Dashboard principal: KPIs, pipeline, actividad, controles de cacería |
| `/money-radar` | MoneyRadar.vue | Programas rankeados por ORION SCORE con EVH |
| `/radar` | OpportunityRadar.vue | Oportunidades descubiertas automáticamente |
| `/hot-paths` | HotPaths.vue | Rutas de ataque priorizadas |
| `/findings` | Findings.vue | Pipeline de hallazgos detected→validated→confirmed→reported |
| `/reports` | ReportCenter.vue | Reportes con generación AI, exportación, envío |
| `/programs/:id` | ProgramIntel.vue | Dossier de inteligencia por programa |
| `/verify` | VerificationGuide.vue | Guía paso a paso de validación |
| `/settings` | Settings.vue | Configuración del sistema |

### Diseño UX
- **Paleta:** Fondo oscuro `#0a0b14` / `#11131f`, texto `#e8e9f0`, acento primary `#6c5ce7` (púrpura)
- **Layout:** Sidebar colapsable + contenido principal, breadcrumbs sutiles
- **Estilo:** Glassmorphism en cards (fondos semi-transparentes `bg-[#11131f]/40`, backdrop-blur), bordes sutiles `border-border/40`, hover effects con glow
- **Iconos:** Lucide icons (Radar, DollarSign, TrendingUp, Brain, Target, etc.)
- **Tipografía:** `font-display` para títulos, monospace para datos financieros, sans-serif para cuerpo
- **Estados:** Loading con Skeleton, empty states con icono + mensaje, errores silenciosos

### Componentes UI (15)
Button (variants: default, destructive, outline, secondary, ghost, link), Card, Badge (success, info, warning, destructive, default, outline), Input, Avatar, Table, Separator, ScrollArea, Skeleton, CommandPalette

### Stores (Pinia)
- `hunt.ts` — Cacería autónoma (start/pause/resume/stop)
- `findings.ts` — Findings CRUD, pipeline stages
- `report.ts` — Report draft generation, export

### API Client (`lib/api.ts`)
~517 lines. Fetch wrapper con auto-auth, loading tracker, métodos get/post/put/delete.

---

## 7. Desktop

| Archivo | Propósito |
|---|---|
| `main_desktop.py` | Entry point: uvicorn in-process, PyWebView, system tray, auto-auth |
| `service.py` | Windows Service (pywin32) |
| `tray.py` | System tray icon with menu |
| `watchdog.py` | Background health check |
| `updater.py` | Auto-update con rollback |

---

## 8. Pipeline Autónomo

Ejecutado por `ScanScheduler` en loop infinito:

| Etapa | Cada | Qué hace |
|---|---|---|
| DISCOVER | 1h | Scrapea HackerOne, Bugcrowd, Intigriti, YesWeHack |
| RECON | 30min | subfinder, amass, httpx, katana, gau, wayback, LinkFinder, ffuf, Dalfox, sqlmap, nuclei, ZAP passive |
| HYPOTHESIS | 15min | Genera hipótesis desde recon + ZAP |
| VALIDATE | 2h | Validación activa solo si hay scope document |
| REPORT | 1h | Genera reportes para high/critical |

Seguridad: la validación activa requiere scope document explícito. Nunca auto-envía reportes.

---

## 9. Economic Intelligence

Capa transversal que impregna todo el sistema.

### ORION SCORE
Algoritmo 0.0-1.0 con 6 factores:
- Reward potential (30%) — de bounty tiers
- Historical success (20%) — acceptance rate
- Competition (15%) — por plataforma + reward
- Time efficiency (15%) — estimated effort
- Experience (10%) — earnings previos
- Technologies (10%) — diversidad tecnológica

### Money Radar
Todos los programas rankeados por ORION SCORE con Expected Value per Hour (EVH).

### ROI Engine
USD/hora, USD/programa, USD/plataforma, USD/vulnerabilidad, tasa de aceptación, tiempo promedio respuesta.

### Report Queue Intelligence
Reportes priorizados por expected value (estimated_reward × acceptance_probability). Clasificación: immediate, today, this_week, this_month.

### Memory & Pattern Engine
Patrones aprendidos: "Las fintechs pagan mejor los IDOR", "GraphQL da mejores resultados". Cada vez que ocurre un match, la confianza aumenta.

### Opportunity Planner
Genera misión automática para cada programa: por dónde empezar, qué endpoints revisar, qué técnicas usar, checklist, ROI estimado.

---

## 10. Seguridad

- ZAP solo pasivo (spider + passive scan, NO active)
- Identity Vault: AES-256-GCM para credenciales
- Auto-submit bloqueado
- Scope-aware validation
- JWT + device-based auth
- Rate limiting por path/IP

---

## 11. Scripts (27)

`seed.py`, `bootstrap.py`, `build_release.py`, `release.py`, `autorelease.py`, `build_android.py`, `build_linux.sh`, `build_windows.ps1`, `install.py`, `install_windows.py`, `migrate_to_postgres.py`, `package_portable.py`, `smoke_test.py`, `smoke_test_playwright.py`, `real_world_validation.py`, `generate_release_report.py`, `generate_screenshots.py`, `generate_icon.py`, `prebuild.py`, `test_desktop_boot.py`, `test_installer.py`, `test_portable.py`, `assemble_output.py`, `audit_imports.py`, `validate_assets.py`, `gen_build_info.py`, `release_isolation.py`

---

## 12. Tests (15)

`conftest.py`, `test_agents.py`, `test_api_endpoints.py`, `test_auth_users.py`, `test_contracts.py`, `test_desktop_release.py`, `test_e2e_flow.py`, `test_intelligence_loop.py`, `test_learning.py`, `test_new_integrations.py`, `test_pipeline_e2e.py`, `test_scheduler.py`, `test_scoring.py`, `test_security.py`, `test_tools.py`

---

## 13. Estado del Frontend — Informe

### Diseño visual
- Tema oscuro consistente, glassmorphism, animaciones sutiles (animate-in)
- Sidebar con iconos + tooltips, breadcrumbs en títulos
- KPIs con colores semánticos (success=verde, warning=amarillo, destructive=rojo, info=azul)
- Badges para scores, severidades, estados
- Tablas responsive con skeleton loading

### Páginas — Estado

| Página | Estado | Observaciones |
|---|---|---|
| **MissionControl** | ✅ Completo | KPIs, pipeline bars, activity log, hunt controls. El KPI grid es informativo pero el dashboard económico podría ser más agresivo |
| **MoneyRadar** | ✅ Completo | Filtros por score/plataforma, sorting por score/EVH/reward, recalcular scores. Diseño sólido |
| **OpportunityRadar** | ✅ Completo | Radar de oportunidades |
| **HotPaths** | ✅ Completo | Rutas de ataque |
| **Findings** | ✅ Completo | Pipeline con drawer de detalle |
| **ReportCenter** | ✅ Completo | CRUD + AI generation |
| **ProgramIntel** | ✅ Completo | Dossier completo con analyze, scope reader, tiers, histórico. Bien estructurado |
| **VerificationGuide** | ✅ Completo | Paso a paso con estados |
| **Settings** | ✅ Completo | Configuración |

### Lo que se pasa por alto

1. **No hay EconomicDashboard** — La home es MissionControl (técnico). No responde "cuánto gané, qué programa conviene, qué hago ahora". El usuario quiere una home económica.
2. **OpportunityPlanner** — No existe como página. El endpoint `/api/economic/programs/{id}/plan` está creado pero no hay frontend.
3. **Report Queue** — El endpoint `/api/economic/report-queue` está creado pero no hay componente frontend.
4. **Memory Patterns** — El CRUD de patrones existe en API pero no hay interfaz para ver/crear patrones.
5. **La home no prioriza dinero** — MissionControl muestra métricas técnicas (endpoints, findings, scans). No muestra USD/hora, mejor programa hoy, próximo reporte a enviar.
6. **Sin navegación a EconomicDashboard** — No hay link en sidebar ni ruta registrada.
7. **Sin vista de "Top 5 programas para hoy"** — El Money Radar existe pero no hay una vista curada tipo "estos son los 5 que deberías estar mirando ahora".

### Recomendación

Para alinear con la filosofía económica:
1. Crear `EconomicDashboard.vue` como nueva home (reemplazar o aumentar MissionControl)
2. Crear `OpportunityPlanner.vue` para la vista de misión
3. Agregar componente de Report Queue en el dashboard o página separada
4. Agregar panel de Memory Patterns en Settings o página dedicada
5. Registrar rutas y links en sidebar

---

*Documento generado el 2026-06-30. Mantener actualizado con cada cambio significativo.*
