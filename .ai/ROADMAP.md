# Roadmap — OWNEX Platform

> **Regla de Oro:** Revenue Rule — Ninguna feature entra al roadmap si no aumenta al menos uno de: detección de vulnerabilidades, calidad de evidencia, probabilidad de aceptación, o aprendizaje del sistema. No hay excepciones.

## Arquitectura OWNEX

```
OWNEX
    |
Mission Control
(Throughput Dashboard)
    |
------------------------
|       |       |       |
Security Forge   Wealth  Intelligence
Cycle    Cycle    Cycle    Cycle
  |       |        |        |
Rastro  Forge    Vault    Atlas
  |
Knowledge Engine
  |
Memory Layer
```

## Ciclos de Trabajo (Work Cycles)

| Ciclo | Nombre | Estado | Prioridad |
|-------|--------|--------|-----------|
| 🔵 | **Rastro** (Security) | ✅ FASE 1 Activo — Scheduling 24/7 | **FASE 1** |
| 🟣 | **Forge** (Dev Bounty) | ✅ Execution Layer — 8 adapters, 23 handlers | **FASE 2.5 ✅** |
| ⚡ | **Pulse** (AI Work) | ✅ Execution Layer — executors listos | **FASE 2.5 ✅** |
| 🛡️ | **Atlas** (System) | ✅ Health checks + Scheduler monitor | **FASE 2.5 ✅** |
| 💰 | **Vault** (Wealth) | ✅ Backup + Revenue tracking | **FASE 2.5 ✅** |
| 🟢 | **CoderAgent** (Dev) | ✅ 6 módulos autónomos | **FASE 2.5 ✅** |
| 🟡 | **Pulse Frontend** (AI Work) | ✅ Frontend Done | FASE 2.1 ✅ |
| ⚪ | **Wealth Consolidation** | ⚠️ Parcial | FASE 4 |
| 🤖 | **Orion** (Coordinator) | ✅ Existe | Transversal |

---

## FASES DE IMPLEMENTACIÓN

### FASE 0 — OWNEX Foundation ✅ COMPLETADA
- [x] Branding + Design System (negro/azul/blanco/dorado)
- [x] SplashScreen, AppSidebar, OrionSidebar, MissionControl
- [x] Infra estable: Ollama (1 modelo), FCC (router), Hermes, OpenCode, Cline
- [x] Memoria documental en `.ai/`
- [x] **OWNEX_DESIGN_SYSTEM.md** — Documentación completa del Design System v1

### FASE 1 — Mission Control v1 ⭐⭐⭐⭐⭐ (EN CURSO)

Crear la interfaz central que responda en 5 segundos: **"¿Qué oportunidades hay hoy?"**

- [ ] **Dashboard Throughput**: oportunidades detectadas, priorizadas, ciclos activos, tareas pendientes, acciones recomendadas, estado de agentes
- [ ] **Agent Fleet**: vista simple del estado de cada agente (Hermes 🟢, OpenCode 🟢, Cline 🟢, Ollama 🟢, FCC 🟡)
- [ ] **Opportunity Engine v0**: modelo de datos de oportunidad (type, source, reward, difficulty, confidence, recommended_action) sin APIs externas todavía
- [ ] **Activity Timeline**: qué pasó, cuándo, qué falta
- [ ] **Command Palette** como navegación principal (Ctrl+K)

**Tests objetivo:** 20-25 tests nuevos
**Archivos nuevos máx:** 3-4

### FASE 2 — Security Cycle v1 ⭐⭐⭐⭐⭐ (SIGUIENTE)

Migrar Rastro como primer Work Cycle de OWNEX. No crear nada nuevo, convertir.

- [ ] Pipeline E2E: Recon → Attack Surface → Hypothesis → Validation → Evidence → Report → Learning
- [ ] Executive Dashboard (CEO view): "¿Esta semana ganamos plata?"
- [ ] Knowledge capture: cada finding deja metadata de aprendizaje
- [ ] Pipeline E2E funcionando sin intervención manual

**Tests objetivo:** 30-40 tests (reutilizando + extendiendo Rastro existente)
**Archivos nuevos máx:** 2-3 (adapters + wiring)

### FASE 2.5 — Execution Layer (CRÍTICO PARA AUTONOMÍA REAL) ⭐⭐⭐⭐⭐⭐ — **SPRINT ACTUAL (BASE CREADA)**

**BLOQUEANTE ABSOLUTO:** Sin capa de ejecución, OWNEX solo descubre oportunidades, NO las ejecuta. Prioridad máxima.

- [ ] **EXEC-1: AlgoraExecutor** — `claim_issue()` + `create_pr()` + `submit_pr()` (API write real, mayor ROI inmediato) ✅ **Código base creado**
- [ ] **EXEC-2: FreelancerExecutor** — `bid_on_project()` + `submit_deliverable()` + `request_milestone_release()` ✅ **Código base creado**
- [ ] **EXEC-3: BrowserAgent Base** — Playwright + login persistence + session management (desbloquea LinkedIn, DataAnnotation, Outlier, Remotasks, Mindrift) ✅ **Código base creado**
- [ ] **EXEC-4: AutonomousWorkflow Engine** — discover→select→plan→execute→learn loop unificado ✅ **Código base creado**
- [ ] **EXEC-5: CoderAgent Especializado** — **CRÍTICO** write fix, tests, PR para issues reales (fuerza multiplicadora) ❌ **NO EXISTE — PRIORIDAD #1**
- [ ] **EXEC-6: OpireExecutor** — `claim_bounty()` + `submit_work()` (API write, segundo mayor ROI OSS) ❌ **NO EXISTE**
- [ ] **EXEC-7: IssueHuntExecutor** — `claim_issue()` + `submit_pr()` (API write) ❌ **NO EXISTE**
- [ ] **EXEC-8: PlatformBrowserWorkers** — DataAnnotationWorker, OutlierWorker, MindriftWorker, RemotasksWorker ❌ **NO EXISTE**
- [x] **EXEC-9: Credentials Vault** — vault.py con backup + health.py con check_secrets_health ✅ **COMPLETADO**
- [x] **EXEC-10: Scheduler Integration** — 23 jobs, 4 ciclos (FORGE/PULSE/VAULT/ATLAS), verificado E2E ✅ **COMPLETADO**

**Tests objetivo:** 35-45 tests (unit + integration con APIs reales)  
**Archivos nuevos máx:** 8 (executors 5 + browser 1 + workflow 1 + coder 1)  
**Budget estricto:** 1 archivo por executor, 1 browser agent, 1 workflow, 1 coder = 8 archivos totales

---

### FASE 2.6 — CoderAgent (EL CEREBRO QUE FALTA) ⭐⭐⭐⭐⭐⭐⭐ — **MÁXIMA PRIORIDAD DESPUÉS DE EXEC-1/2/3/4**

**Sin CoderAgent, los executors claim issues pero nadie escribe el código. Es el multiplicador de fuerza.**

| Componente | Responsabilidad | Archivo |
|------------|-----------------|---------|
| **RepoCloner** | Clone shallow, detect language/setup, run tests | `core/autonomy/repo_analyzer.py` |
| **IssueAnalyzer** | Parse issue → extract bug/feature, reproduction steps, affected files | `core/autonomy/issue_analyzer.py` |
| **CodeGenerator** | Write fix/patch based on analysis + repo context | `core/autonomy/code_generator.py` |
| **TestRunner** | Execute test suite, capture failures, iterate fix | `core/autonomy/test_runner.py` |
| **PRBuilder** | Create branch, commit, push, open PR with description | `core/autonomy/pr_builder.py` |
| **CoderAgent** | Orquesta todo lo anterior end-to-end | `core/autonomy/coder_agent.py` |

**Archivos nuevos: 6 (1 por componente)**  
**Tests: 20-30 (unit + integration con repos reales)**

### FASE 3 — Opportunity Engine v1 ⭐⭐⭐⭐

- [ ] Modelo de scoring: $ esperado × (1 - dificultad) × prob. aceptación
- [ ] Inputs: dinero, dificultad, tiempo, competencia, experiencia previa, historial
- [ ] Output: top 5 oportunidades para hoy
- [ ] Integrar con TargetPrioritizer existente
- [ ] Feedback loop: lo aceptado/rechazado alimenta el score
- [ ] Tests

### FASE 4 — Work Cycle Expansion ⭐⭐⭐⭐

Solo después de que Security Cycle funcione E2E sin intervención.

- [ ] **Forge Adapter**: Superteam Earn, Opire
- [ ] **Pulse Adapter**: Outlier, DataAnnotation, Mindrift
- [ ] **Wealth Consolidation**: CoinGecko + Firefly III dashboard

### FASE 5 — Automatización ⭐⭐⭐⭐⭐

- [ ] Decisión autónoma: ¿local vs FCC según tarea?
- [ ] Auto-submission pipeline (Finding → Evidence → Report → Submit → Payout)
- [ ] Agentes independientes por ciclo con coordinador multi-agente

### FASE 6 — Tauri Desktop + Android Companion ⭐⭐⭐⭐

- [ ] Tauri + Vue 3 build (OWNEX.exe)
- [ ] Python backend como sidecar
- [ ] Android Companion app (notificaciones, approvals, métricas, wallet, agent status)
- [ ] Sincronización WebView / WebSocket

---

## ARCHITECTURE BUDGET (por feature)

- Máximo: 2 archivos nuevos, 1 dependencia, 1 evento, 1 capability, 1 contrato, 20 tests
- Si necesita más → la feature está mal diseñada

---

## PRIORIDADES REVENUE RULE

| Pregunta | Respuesta Actual |
|----------|------------------|
| ¿Qué parte aumenta la detección? | Mission Control v1 → Opportunity Engine |
| ¿Qué parte reduce falsos positivos? | Security Cycle v1 → Knowledge Engine |
| ¿Qué parte mejora la aceptación? | Report Optimizer → Acceptance Intelligence |
| ¿Qué parte mejora el aprendizaje? | Knowledge Engine → Evolution Engine |
| ¿Qué parte mejora la autonomía? | Agent Fleet → Multi-agent Coordinator |
| ¿Qué parte mejora Expected Revenue? | Opportunity Score Engine |
| ¿Qué parte solo mejora arquitectura? | ❌ EVITAR — no entra al sprint |

---

## SPRINT ACTUAL: FASE 1 — Mission Control v1

| Task | Estado | Tests | Owner |
|------|--------|-------|-------|
| Throughput Dashboard | ⏳ Pendiente | 8-10 | Frontend |
| Agent Fleet View | ⏳ Pendiente | 4-5 | Frontend |
| Opportunity Engine v0 (Data Model) | ⏳ Pendiente | 6-8 | Backend |
| Activity Timeline | ⏳ Pendiente | 3-4 | Frontend |
| Command Palette as Primary Nav | ⏳ Pendiente | 4-5 | Frontend |

---

## REFERENCIAS

- `.ai/OWNEX_ARCHITECTURE.md` — 4 capas, 3 motores, ciclos de trabajo
- `.ai/OWNEX_DESIGN_SYSTEM.md` — Design System v1 completo
- `.ai/OWNEX_MISSION_CONTROL_SPEC.md` — Spec detallada Mission Control
- `.ai/TASK_QUEUE.md` — Cola de tareas priorizada
- `.ai/CURRENT_STATE.md` — Estado verificado actual
- `.ai/STRATEGIC_AUDIT.md` — Marco de auditoría estratégica (10 preguntas + 18 dimensiones)