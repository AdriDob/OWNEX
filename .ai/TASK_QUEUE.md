# OWNEX Task Queue — Product Core

> **REGLAS:**
> 1. No más infraestructura. Solo producto. Si no es visible en Mission Control, no existe.
> 2. Cada sprint debe responder "¿qué oportunidad tengo hoy y cuál es la mejor acción?"
> 3. Si ya hay capital técnico (Rastro), usarlo. No crear desde cero.
> 4. Un Work Cycle funcionando > 5 a medias.
> 5. Dashboard primero, automatización después.

> **⚠️ AUDITORÍA 2026-07-31 (LEER ANTES DE PROGRAMAR):** La auditoría real del código
> (ver `.ai/CURRENT_STATE.md` → sección "AUDITORÍA 2026-07-31") muestra que muchas
> tareas listadas abajo ya están IMPLEMENTADAS. Antes de escribir código nuevo, verificá
> qué existe: `core/cycles/`, `cores/cycles/stages/`, `core/opportunity/`, `core/execution/`,
> `core/autonomy/`, `apps/*`. El pipeline CATEYE real corre en `api/scheduler.py`.

## OWNEX Architecture

```
                  OWNEX
                     |
              Mission Control
              (Dashboard Throughput)
                     |
     -------------------------------
     |              |               |
 Security        Forge          Wealth
 Cycle           Cycle           Cycle
     |              |               |
   Rastro        Forge          Vault
     |
 Knowledge Engine
     |
 Memory Layer
```

## ESTADO REAL AUDITADO (2026-07-31)

### ✅ COMPLETO y funcional (NO reprogramar)

| Componente | Dónde | Verificado |
|---|---|---|
| Pipeline bug bounty CATEYE real (discover→recon→hypo→validate→report→ai_bounty) | `api/scheduler.py` (`ScanScheduler`) | ✅ corre en runtime |
| 7 stage executors del Security Cycle (recon, attack_surface, hypothesis, validation, evidence, report, learning) | `cores/cycles/stages/` | ✅ tests E2E pasan (8/8) |
| Cycle CRUD + estado + métricas | `core/cycles/service.py`, `models.py`, router `/api/cycles` | ✅ |
| SecurityCycle/ForgeCycle/PulseCycle (bookkeeping DB: start, advance, tasks) | `core/cycles/security.py`, `forge.py`, `pulse.py` | ✅ |
| Executive Dashboard backend (CEO view, "¿ganamos plata?") | `core/cycles/executive_dashboard.py` | ✅ expuesto en `/api/cycles/{security,forge}/dashboard` |
| KnowledgeCapture / capture_learning / capture_payout_learning | `core/cycles/knowledge_capture.py` | ✅ (⚠️ en memoria, no persiste) |
| Execution layer: executors Algora/Freelancer/Opire/IssueHunt/Mindrift/Outlier | `core/opportunity/executors/` | ✅ tests pasan |
| BrowserAgent + workers, CoderAgent, AutonomousWorkflow, CredentialsVault | `core/automation/`, `core/autonomy/`, `core/credentials/` | ✅ |
| OpportunityOrchestrator | `core/opportunity/engine.py` | ✅ |
| core/execution (compiler + runtime state machine) | `core/execution/` | ✅ 169 tests |
| Apps ORION reales (aegis, atlas, odyssey, hermes) | `apps/` | ✅ routers + engines |
| Scheduler jobs (26 jobs definidos con handlers existentes) | `core/scheduler/jobs.py` | ✅ definidos |
| Frontend: 60+ rutas, ~97 páginas, build válido | `frontend/` | ✅ dist generado 31-07 |
| Frontend páginas reales con API (Settings, Capital, Intelligence, Reports, Operations, Copilot, SecurityCycle...) | `frontend/src/pages/` | ✅ |
| Android APK debug compila | `android/` | ✅ APK 31-07 |
| Desktop real (PyInstaller) | `dist/CATEYE` | ✅ |
| Tauri v2 deps | `src-tauri/` | ⚠️ no compila (ver abajo) |

### ✅ ESTADO REAL VERIFICADO (2026-08-04) — los ítems de la auditoría 2026-07-31 están resueltos

> Auditoría completa de la sección anterior (obsoleta): cada ítem fue re-verificado
> con código + tests. Todos están COMPLETADOS (ver tabla AUD-1..AUD-14 abajo).

| Área | Estado real (verificado 2026-08-04) | Evidencia |
|---|---|---|
| Scheduler de ciclos en runtime | ✅ COMPLETADO — `api/main.py:1014-1028` usa `isinstance(job_def, JobDefinition)` (sin subíndices); `_on_job_due` publica `scheduler:job_due` Y ejecuta `_run_job`; CoreScheduler arranca y corre el loop | `tests/test_scheduler.py` + `test_scheduler_jobs.py`: 54 passed |
| SecurityCycle ↔ stage executors | ✅ COMPLETADO — `run_pipeline()` (security.py:306) ejecuta los 7 stages con `get_executor`, propaga contexto, avanza tareas en DB | `tests/test_e2e_security_pipeline.py`: 8 passed |
| KnowledgeCapture en memoria | ✅ COMPLETADO — mirror a UnifiedMemoryStore (SQLite, namespace `cateye`), sobrevive restart | AUD-3 |
| pulse.capture_learning stub | ✅ COMPLETADO | AUD-3 |
| Mission Control frontend roto | ✅ COMPLETADO — `/api/activity` creado, NextBestAction props mapeadas, AgentFleet normalizado | AUD-4 |
| GamingConsole = MOCK | ✅ COMPLETADO — conecta a 8 endpoints; el bloqueo real era `/api/cycles` 500 (config JSON string vs dict) → fix `field_validator` en `CycleRead` | AUD-7 |
| Executive Dashboard sin frontend | ✅ COMPLETADO — `ExecutiveDashboard.vue` + ruta `/security/executive` + sidebar "CEO View" | AUD-6 |
| test_version_backup 13 fallan | ✅ COMPLETADO — 24/24 pasan (era estado residual `.ownex_backups`; `_calculate_checksum` volvió a excluir `manifest.json`) | AUD-5 |
| Manifests de apps con clases inexistentes | ⚠️ PENDIENTE | FASE 4 |
| core/ vs cores/ duplicación | ✅ DECIDIDO — `cores/` es SSOT; `core/` se migra gradualmente | AUD-11 |
| Android crash on launch | ✅ COMPLETADO — namespace unificado `ai.rastro.app` | AUD-12 |
| WearOS no buildable | ✅ RESUELTO — descartado (ROI negativo, redundante con OMEGA mobile) | AUD-14 |
| Supabase no configurado | ⚠️ PENDIENTE (solo MobileCompanion depende) | FASE 6 |
| Tauri no compila | ✅ COMPLETADO — `main.rs` corregido `orion_desktop::run()`, cargo check OK | AUD-13 |
| VaultCycle/AtlasCycle no existen | ✅ COMPLETADO — creados + routers montados; 6 ciclos operativos | AUD-8 |
| 31+ páginas frontend huérfanas | ⚠️ PENDIENTE (menor, depende de decisión de producto) | — |
| console.log en frontend móvil | ⚠️ PENDIENTE (menor, limpieza) | — |
| QA cycle no conectado | ⚠️ PENDIENTE (`core/cycles/qa.py` 1100 líneas sin callers) | — |
| OAR + Career Engine sin API | ✅ COMPLETADO 2026-08-04 — routers `/oar/*` y `/career/*` creados y montados; 14 tests nuevos pasan | `tests/test_oar_api.py` + `test_career_api.py` |
| QA cycle no conectado | ✅ COMPLETADO 2026-08-04 — router `api/routers/qa_cycle.py` (start/status/stage/cases/run) montado en `api/main.py`; scheduler job `qa_daily_cycle` (cron 08:30, handler `run_qa_cycle`); `get_all_jobs()` → 7 ciclos / 28 jobs; 7 tests nuevos. 71+56 passed, ruff limpio | `tests/test_qa_cycle_api.py` |

### ✅ NO existe — VERIFICADO 2026-08-04

- adapters bug bounty del manifest vault (HackerOne, Bugcrowd, Intigriti, Synack, YesWeHack, Immunefi) — crear desde cero si se quiere
- `ActivityTimeline` / `/api/activity` / Executive Dashboard frontend / `run_pipeline()` → todos creados en AUD-2/AUD-4/AUD-6 (fila "NO existe" obsoleta)

---

## PRÓXIMAS TAREAS POR PRIORIDAD (actualizado 2026-08-01)

> Basado en la auditoría real, NO en el plan original. Orden = impacto en producto.

### P0 — Conectar lo que ya está construido (REVENUE RULE: hace visible el trabajo hecho)

| ID | Task | Estado real | Esfuerzo |
|----|------|-------------|----------|
| AUD-1 | **Fix scheduler runtime**: arreglar `api/main.py:905-913` (acceso dict sobre JobDefinition) + suscribir handler a `scheduler:job_due` para que los 26 jobs corran | ✅ COMPLETADO 2026-07-31 — verificado en runtime: 26 jobs registrados, loop activo. Handler `vault_backup_2h` (`core.credentials.vault.backup_vault`, sin `:`) resuelve vía fallback dotted-path | S |
| AUD-2 | **Conectar SecurityCycle con stage executors**: crear `run_pipeline()` que ejecute los 7 stages en orden y persista resultados | ✅ COMPLETADO 2026-07-31 | M |
| AUD-3 | **Persistir KnowledgeCapture** en DB (no en memoria) | ✅ COMPLETADO 2026-07-31 — mirror a UnifiedMemoryStore (SQLite, namespace `cateye`), sobrevive restart, dedup por id en getters | S |
| AUD-4 | **Fix Mission Control frontend** (3 bugs de wiring) + crear endpoint `/api/activity` | ✅ COMPLETADO 2026-07-31 — `/api/activity` creado (event bus → timeline), NextBestAction props mapeadas, AgentFleet status normalizado (mapAgentStatus) | M |
| AUD-5 | **Fix test_version_backup** (Errno 17, backup_system.py) | ✅ COMPLETADO 2026-07-31 — 24/24 pasan (era estado residual `.ownex_backups`). Además `_calculate_checksum` volvió a excluir `manifest.json` (lo hasheaba desde un commit previo → verify_backup fallaba en backups reales) | S |

### P1 — Producto visible (REVENUE RULE)

| ID | Task | Estado real | Esfuerzo |
|----|------|-------------|----------|
| AUD-6 | **Executive Dashboard frontend** (CEO view): página + ruta + llamada a `/api/cycles/security/dashboard` | ✅ COMPLETADO 2026-07-31 — `frontend/src/pages/ExecutiveDashboard.vue` + ruta `/security/executive` + ítem sidebar "CEO View"; contrato verificado con token real (200, 9 keys) | M |
| AUD-7 | **GamingConsole con datos reales**: conectar a API (hoy es mock, muestra $0) | ✅ COMPLETADO 2026-07-31 — el servicio ya conectaba a 8 endpoints; el bloqueo real era `/api/cycles` (500: `config: Text` JSON string vs schema `dict`). Fix: field_validator en `CycleRead` → 200 con 5 ciclos; GamingConsole mostraba fallbacks solo por ese 500. 8/8 endpoints verificados con token | S |
| AUD-8 | Montar routers de ciclos faltantes: `/api/cycles/forge` (existe sin montar), crear pulse/vault/atlas | ✅ COMPLETADO 2026-08-01 — `VaultCycle` y `AtlasCycle` creados en `core/cycles/vault.py` y `core/cycles/atlas.py`; routers `vault_cycle.py` y `atlas_cycle.py` creados y montados en `api/main.py`. Forge y Pulse ya estaban montados. 6 ciclos operativos (security, forge, pulse, vault, atlas, direct_work). | S |
### P2 — Estabilidad / limpieza

| ID | Task | Estado real | Esfuerzo |
|----|------|-------------|----------|
| AUD-9 | Limpiar 424 errores de lint en código nuevo | ✅ COMPLETADO 2026-08-04 — 117→0 errores. Fix: 77 E402 (per-file ignores en core/__init__.py), 4 F841 (variables no usadas), 6 N803/N806 (nombres mayúsculas→minúsculas), 1 N999 (RevenueTracker.py→revenue_tracker.py), 1 F811 (OWNEX_VERSION duplicada), 1 SIM103 (retorno redundante), 1 E402 (cli.py). Tests fast actualizados (86/87 pasan, 1 skip por schema DB) | M |
| AUD-10 | Commitear cambios sin commitear (README, assets, tests scheduler/vision, fixes auth/supabase/revenue) | ✅ COMPLETADO 2026-07-31 | S |
| AUD-11 | Decidir core/ vs cores/: elegir uno como SSOT | ✅ COMPLETADO 2026-07-31 — **cores/ es SSOT** (845 archivos vs 533, 2x más imports en API, contiene pipeline productivo CATEYE). core/ se migrará gradualmente a cores/ | L |
| AUD-12 | Android namespace unificado (ai.rastro/catseye/CATEYE) | ✅ COMPLETADO 2026-08-01 — namespace unificado `ai.rastro.app` en build.gradle, MainActivity, manifest, capacitor.config.json, strings.xml | S |
| AUD-13 | Tauri: fix lib name + versión | ✅ COMPLETADO 2026-08-01 — main.rs corregido `orion_desktop::run()`, cargo check OK | S |
| AUD-14 | WearOS real o descartar | ✅ COMPLETADO 2026-08-01 — Descartado (commit c420f8fb): ROI negativo, redundante con OMEGA mobile, < 1% market share | L |
| AUD-15 | Limpieza de lint pendiente + fix contrato AgentFactory + bugs runtime | ✅ COMPLETADO 2026-08-08 — commit `4e75db59` (14 archivos, +1533/−470, pusheado). Fix: **F821** en `core/investment/adapters/agent_factory_adapter.py` (faltaban `AgentSpec`/`AgentStatus`/`AgentType` que el contrato de `adapters/__init__.py` y `api/routers/investment.py` importan; `openai` → `httpx`, tools str/dict normalizados); **F811** en `api/routers/obsidian_sync.py` (imports inexistentes → API real: `_list_all_files`, `_load_state`, `sync_full`, `sync_markdown_to_json`); **SIM105** en `core/auto_dispute.py` (`contextlib.suppress`); **shadowing** en `core/obsidian_sync.py` (`_sync_state` dict pisaba la función → `_state_path()` + `_record_sync`). Verificación: `ruff check .` = **All checks passed!**, `import api.main` OK, smoke fast **89 passed / 1 skipped**. Suite completa: 3154 passed, 14 failed — TODOS preexistentes (verificado con stash; sin relación con módulos tocados: desktop_release, e2e_copilot, event_foundation, ai_router, vision_gateway, backup_setup, command_system, executors_base) | S |

---

## PLAN ORIGINAL (REFERENCIA — muchas fases ya están hechas)

### FASE 0 — OWNEX Foundation ✅
- [x] Branding + Design System (negro/azul/blanco/dorado)
- [x] SplashScreen, AppSidebar, OrionSidebar, MissionControl
- [x] Infra estable: Ollama (1 modelo), FCC (router), Hermes, OpenCode, Cline
- [x] Memoria documental en `.ai/`
- [x] **OWNEX_DESIGN_SYSTEM.md** — Design System v1 completo

### FASE 1 — Mission Control v1 ✅ COMPLETADO
- [x] Opportunity Engine v0: modelo de datos + scoring + Top 5 + API + Adapter + Frontend fetch
- [x] Throughput Dashboard
- [x] Agent Fleet
- [x] Activity Timeline
- [x] Command Palette (Ctrl+K)

### FASE 2 — Security Cycle v1 ⚠️ PARCIAL (ver auditoría)
- [x] Backend de ciclo (SecurityCycle, tasks, stages executors, API) — **NO conectado entre sí**
- [x] Executive Dashboard backend (`core/cycles/executive_dashboard.py`)
- [x] Knowledge capture backend (en memoria)
- [ ] Pipeline E2E real SIN intervención (falta conectar: AUD-1 + AUD-2)
- [ ] Executive Dashboard frontend (AUD-6)

### FASE 2.5 — Execution Layer ✅ COMPLETADO
- [x] **EXEC-1: AlgoraExecutor**
- [x] **EXEC-2: FreelancerExecutor**
- [x] **EXEC-3: BrowserAgent Base**
- [x] **EXEC-4: AutonomousWorkflow Engine**
- [x] **EXEC-5: CoderAgent**
- [x] **EXEC-6: OpireExecutor**
- [x] **EXEC-7: IssueHuntExecutor**
- [x] **EXEC-8: PlatformBrowserWorkers**
- [x] **EXEC-9: Credentials Vault**
- [x] **EXEC-10: Scheduler Integration** — 26 jobs, 5 ciclos (Security/Forge/Pulse/Vault/Atlas) — ⚠️ definidos pero no corren en runtime (AUD-1)

### FASE 3 — Opportunity Engine v1 ⚠️ Parcial
- [x] Scoring pipeline, OpportunityOrchestrator, top5 API (`/opportunity-score/top5`)
- [ ] Feedback loop aceptado/rechazado → score
- [ ] Integración plena con TargetPrioritizer

### FASE 4 — Work Cycle Expansion ⚠️ Parcial
- [x] Adapters Forge/Pulse/Vault (fetch + executors)
- [ ] Manifests corregidos (hoy apuntan a clases inexistentes)
- [ ] Wealth Consolidation: CoinGecko + Firefly III dashboard (parcial, apps/atlas)

### FASE 5 — Automatización ⚠️ Parcial
- [x] OpportunityOrchestrator discovery→claim→resolve→deliver
- [x] AutonomousWorkflow discover→select→plan→execute→learn
- [ ] Decisión autónoma local vs FCC
- [ ] Auto-submission pipeline completo
- [ ] Coordinador multi-agente por ciclo

### FASE 6 — Tauri Desktop + Android Companion ⚠️ Parcial
- [x] Android APK debug compila
- [x] MobileCompanion web (UI + Supabase CRUD)
- [ ] Tauri build válido (fix lib name/versión)
- [ ] Android crash on launch (namespace)
- [ ] WearOS real

---

## ARCHITECTURE BUDGET ENFORCEMENT

| Feature | Max Archivos | Max Deps | Max Eventos | Max Capabilities | Max Contratos | Max Tests |
|---------|-------------|----------|-------------|------------------|---------------|-----------|
| Por feature | 2 | 1 | 1 | 1 | 1 | 20 |
| **FASE 1 Total** | 4 | 1 | 1 | 1 | 1 | 25 |

Si una feature necesita más → está mal diseñada.

---

## REFERENCIAS

- `.ai/CURRENT_STATE.md` — Estado real auditado (sección "AUDITORÍA 2026-07-31")
- `.ai/OWNEX_ARCHITECTURE.md` — 4 capas, 3 motores, ciclos de trabajo
- `.ai/OWNEX_MISSION_CONTROL_SPEC.md` — Spec detallada Mission Control
- `.ai/ROADMAP.md` — Roadmap general con fases
- `.ai/STRATEGIC_AUDIT.md` — Marco de auditoría estratégica
