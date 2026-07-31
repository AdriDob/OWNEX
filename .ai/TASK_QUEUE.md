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

### ⚠️ A MEDIAS / CON BUGS — los siguientes trabajos están a medio camino

| Área | Problema real encontrado | Dónde |
|---|---|---|
| **Scheduler de ciclos DESCONECTADO en runtime** | `api/main.py:905-913` accede `job_def["job_id"]` sobre objetos `JobDefinition` (no subscriptables) → `TypeError` tragado como "non-fatal" → CoreScheduler nunca arranca. Además el evento `scheduler:job_due` (main.py:902) NO tiene suscriptores → **ninguno de los 26 jobs ejecuta sus handlers jamás** | `api/main.py`, `core/interfaces/scheduler.py` |
| **SecurityCycle NO conecta con los stage executors** | `advance_stage()` solo marca tareas COMPLETED/RUNNING en DB. No llama a recon/attack_surface/hypothesis/validation/evidence/report. No existe `run_pipeline()` (los tests lo referencian). Los 7 executors solo los usan los tests | `core/cycles/security.py:125-175`, `cores/cycles/stages/` |
| **KnowledgeCapture en memoria** | `self._entries: list` no persiste → se pierde al reiniciar | `core/cycles/knowledge_capture.py:56` |
| **pulse.capture_learning es stub** | retorna `None` | `core/cycles/pulse.py:177-179` |
| **Mission Control frontend roto** | `/classic` (MissionControl.vue): fetch `/activity` (endpoint NO existe), `<NextBestAction action=...>` (prop no existe, es `title/description/confidence`), `<AgentFleet>` recibe status `online/offline/limited` pero el componente espera `idle/thinking/working/complete/error` | `frontend/src/pages/MissionControl.vue`, `components/mission-control/` |
| **GamingConsole = MOCK** | `/dashboard`: activityLog hardcodeado, agent fleet hardcodeado, `weeklyRevenue` siempre $0 (nunca se setea), "v4.7.0" hardcodeado (real 7.0.0) | `frontend/src/pages/GamingConsole.vue` |
| **Executive Dashboard sin frontend** | backend completo pero ninguna página/llamada frontend lo consume | `frontend/src/` |
| **test_version_backup: 13 fallan** | `[Errno 17] File exists` al copiar directorios en `create_backup` → backups acumulados/colisión | `cores/version_backup/backup_system.py` |
| **Manifests de apps con clases inexistentes** | `apps/forge|pulse|vault/manifest.py` referencian clases/adapters que no existen | `apps/*/manifest.py` |
| **apps/odyssey import roto (FIXED)** | `providers.kelly` no existía (solo `providers.py` módulo) → convertido a paquete + `KellyProvider` creado. La app odyssey ahora carga | `apps/odyssey/providers/` |
| **core/ vs cores/ duplicación divergente** | dos árboles paralelos (`core/opportunity` vs `cores/opportunity`, etc.) con lógica distinta | `core/`, `cores/` |
| **Android crash on launch** | 3 identificadores distintos: `ai.rastro.app` (build.gradle) vs `ai.catseye.app` (MainActivity.java) vs `ai.CATEYE.app` (capacitor.config.json) | `android/`, `capacitor.config.json` |
| **WearOS no es buildable** | solo 4 archivos, sin build.gradle/manifest; MainActivity.kt es MOCK (5 tareas/3 hábitos/😊) | `wearos/` |
| **Supabase no configurado** | `VITE_SUPABASE_URL`/`VITE_SUPABASE_KEY` no están en ningún .env → MobileCompanion no funciona | `frontend/.env*` |
| **Tauri no compila** | `main.rs` llama `orion_desktop_lib::run()` pero el crate es `ownex_desktop`; versión Cargo 5.3.0 vs conf 7.0.0 | `src-tauri/` |
| **VaultCycle y AtlasCycle no existen como clases** | solo seeds DB + jobs; no hay `/api/cycles/vault` ni `/api/cycles/atlas` (pulse tampoco); `forge_cycle.py` existe pero no está montado en main.py | `core/cycles/`, `api/routers/forge_cycle.py` |
| **31+ páginas frontend huérfanas** | no ruteadas (LifeManagement, TaskHub, TaskQueue, RevenueDashboard, WelcomePage...) | `frontend/src/pages/` |
| **console.log en frontend móvil** | MobileCompanion.vue, MobileCompanionJarvis.vue, ModernNavbar.vue, SteamBigPictureSplash.vue | `frontend/src/` |
| **QA cycle no conectado** | `core/cycles/qa.py` (1100 líneas) sin callers | `core/cycles/qa.py` |

### ❌ NO existe (crear desde cero si se quiere)

- `ActivityTimeline` (frontend)
- endpoint `/api/activity`
- adapters bug bounty del manifest vault (HackerOne, Bugcrowd, Intigriti, Synack, YesWeHack, Immunefi)
- frontend Executive Dashboard (CEO view)
- `run_pipeline()` en SecurityCycle

---

## PRÓXIMAS TAREAS POR PRIORIDAD (actualizado 2026-07-31)

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
| AUD-8 | Montar routers de ciclos faltantes: `/api/cycles/forge` (existe sin montar), crear pulse/vault/atlas | ⚠️ PARCIAL 2026-07-31 — forge montado (3 endpoints 200); pulse_cycle router creado y montado (3 endpoints 200); vault/atlas NO tienen clase de ciclo (`VaultCycle`/`AtlasCycle` no existen) → sin motor no hay router | S |
### P2 — Estabilidad / limpieza

| ID | Task | Estado real | Esfuerzo |
|----|------|-------------|----------|
| AUD-9 | Limpiar 424 errores de lint en código nuevo | ⚠️ PARCIAL 2026-07-31 — de 457 → 30 errores. Fix: field_validator parse_config en CycleRead (500→200 en /api/cycles); B904 `from None` en 9 routers; OWNEX_VERSION hardcodeada 5.0.0→eliminada (usar import 7.0.0) en backup/engine.py; F821 `session`→`sessions` typo en life_management; F811 duplicados en orion_cli.py y operations.py; E402 en __init__.py per-file-ignores. 30 errores restantes son legacy (E741 `l`, F401 extension imports, F841 `bus`) — no código nuevo | M |
| AUD-10 | Commitear cambios sin commitear (README, assets, tests scheduler/vision, fixes auth/supabase/revenue) | ✅ COMPLETADO 2026-07-31 | S |
| AUD-11 | Decidir core/ vs cores/: elegir uno como SSOT | ✅ COMPLETADO 2026-07-31 — **cores/ es SSOT** (845 archivos vs 533, 2x más imports en API, contiene pipeline productivo CATEYE). core/ se migrará gradualmente a cores/ | L |
| AUD-12 | Android namespace unificado (ai.rastro/catseye/CATEYE) | ⏳ Pendiente | S |
| AUD-13 | Tauri: fix lib name + versión | ⏳ Pendiente | S |
| AUD-14 | WearOS real o descartar | ⏳ Pendiente | L |

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
