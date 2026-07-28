# OWNEX Task Queue — Product Core

> **REGLAS:**
> 1. No más infraestructura. Solo producto. Si no es visible en Mission Control, no existe.
> 2. Cada sprint debe responder "¿qué oportunidad tengo hoy y cuál es la mejor acción?"
> 3. Si ya hay capital técnico (Rastro), usarlo. No crear desde cero.
> 4. Un Work Cycle funcionando > 5 a medias.
> 5. Dashboard primero, automatización después.

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

## PRÓXIMOS SPRINTS (orden estricto)

### FASE 0 — OWNEX Foundation ✅
- [x] Branding + Design System (negro/azul/blanco/dorado)
- [x] SplashScreen, AppSidebar, OrionSidebar, MissionControl
- [x] Infra estable: Ollama (1 modelo), FCC (router), Hermes, OpenCode, Cline
- [x] Memoria documental en `.ai/`
- [x] **OWNEX_DESIGN_SYSTEM.md** — Design System v1 completo

### FASE 1 — Mission Control v1 ⭐⭐⭐⭐⭐ (COMPLETADO)

Crear la interfaz central que responda en 5 segundos: "¿Qué oportunidades hay hoy?"

- [x] **Opportunity Engine v0**: modelo de datos de oportunidad + scoring personalizado + Top 5 diversificado + API + Adapter CATEYE→OWNEX + Frontend fetch
- [x] **Throughput Dashboard**: oportunidades detectadas, priorizadas, ciclos activos, tareas pendientes, acciones recomendadas, estado de agentes
- [x] **Agent Fleet**: vista simple del estado de cada agente (Hermes 🟢, OpenCode 🟢, Cline 🟢, Ollama 🟢, FCC 🟡)
- [x] **Activity Timeline**: qué pasó, cuándo, qué falta
- [x] **Command Palette** como navegación principal (Ctrl+K)

**Tests objetivo:** 20-25 tests nuevos  
**Archivos nuevos máx:** 3-4  
**Budget:** 2 archivos, 1 dep, 1 evento, 1 capability, 1 contrato, 20 tests

### FASE 2 — Security Cycle v1 ⭐⭐⭐⭐⭐ (SIGUIENTE)

Migrar Rastro como primer Work Cycle de OWNEX. No crear nada nuevo, convertir.

- [ ] Recon → Attack Surface → Hypothesis → Validation → Evidence → Report → Learning
- [ ] Executive Dashboard (CEO view): "¿Esta semana ganamos plata?"
- [ ] Knowledge capture: cada finding deja metadata de aprendizaje
- [ ] Pipeline E2E funcionando sin intervención

**Tests objetivo:** 30-40 tests (reutilizando + extendiendo Rastro existente)  
**Archivos nuevos máx:** 2-3 (adapters + wiring)

### FASE 2.5 — Execution Layer ✅ COMPLETADO

**Toda la capa de ejecución autónoma está construida y verificada.**

|- [x] **EXEC-1: AlgoraExecutor** — ✅ Código base creado
|- [x] **EXEC-2: FreelancerExecutor** — ✅ Código base creado
|- [x] **EXEC-3: BrowserAgent Base** — Playwright + login persistence ✅
|- [x] **EXEC-4: AutonomousWorkflow Engine** — discover→select→plan→execute→learn ✅
|- [x] **EXEC-5: CoderAgent Especializado** — 6 módulos (repo_analyzer, issue_analyzer, code_generator, test_runner, pr_builder, orchestrator) ✅
|- [x] **EXEC-6: OpireExecutor** — claim_bounty + submit_work ✅
|- [x] **EXEC-7: IssueHuntExecutor** — claim_issue + submit_pr ✅
|- [x] **EXEC-8: PlatformBrowserWorkers** — Outlier, Mindrift workers ✅
|- [x] **EXEC-9: Credentials Vault** — vault.py, health.py, scheduler backup ✅
|- [x] **EXEC-10: Scheduler Integration** — 23 jobs, 4 ciclos (Forge/Pulse/Vault/Atlas) ✅

### FASE 3 — Opportunity Engine v1 ⭐⭐⭐⭐

- [ ] Modelo de scoring: $ esperado × (1 - dificultad) × prob. aceptación
- [ ] Inputs: dinero, dificultad, tiempo, competencia, experiencia previa, historial
- [ ] Output: top 5 oportunidades para hoy
- [ ] Integrar con TargetPrioritizer existente
- [ ] Feedback loop: lo que se aceptó/rechazó alimenta el score
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

## COMPLETED (no tocar)

| Feature | Estado |
|---------|--------|
| Revenue Pipeline | ✅ Finding → Evidence → Report → Platform → Payout |
| Offensive Intelligence (5 reasoners) | ✅ 101 tests |
| AI Bounty Auto-Hunter | ✅ 29 tests |
| Recon Intelligence (TargetPrioritizer) | ✅ 22 tests |
| Acceptance Intelligence (Learner) | ✅ 18+14 tests |
| Revenue Intelligence (USD/h) | ✅ 70 tests |
| Report Optimizer V2 | ✅ 23 tests |
| Frontend Consolidation Fase 1 | ✅ Capital Dashboard Unificado (5→1 páginas) |
| Frontend Consolidation Fase 2 | ✅ Router 50→8 secciones + Sidebar unificado |
| Execution Layer — 10 EXECs (Algora, Freelancer, Opire, IssueHunt, CoderAgent, BrowserWorkers...) | ✅ 23 handlers, 4 ciclos, probado E2E |
| Screenshots — 7 SVGs demo para README | ✅ docs/screenshots/ |
| Ruff lint — core/ + api/ 0 errores | ✅ 78→0 |
| OWNEX Branding + Design System | ✅ Completo |
| OWNEX Design System Documentation | ✅ `.ai/OWNEX_DESIGN_SYSTEM.md` |
| **Version Engine** — VERSION.txt 4.6.0 SSOT, ownex-version CLI, /api/version | ✅ 11 fuentes sincronizadas |
| **Loop Engineering** — core/loop/ (models, engine, registry, startup) | ✅ 6 patrones OWNEX, wiring lifespan+health, 7 SKILL.md |
| **Temp Manager** — core/system/temp_manager.py | ✅ 5GB quota, per-component cleanup, health API |
| **Full Automation** — scripts/ownex-health, ownex-start | ✅ E2E health check, autonomous startup |
| **PS5 Desktop** — Tauri v2 config + PS5 theme | ✅ src-tauri/ actualizado, #0070d1 accent, card-radius 16px |
| **Code Quality** — ruff core/api/scripts/ | ✅ 0 errores en código nuevo |

---

## TAREAS ACTIVAS (FASE 2 - Security Cycle v1)

| ID | Task | Estado | Tests Estimados | Archivos Estimados | Owner |
|----|------|--------|-----------------|-------------------|-------|
| SC-1 | Security Cycle Pipeline: Recon → Attack Surface → Hypothesis → Validation → Evidence → Report → Learning | ⏳ Pendiente | 15-20 | 2-3 | Backend |
| SC-2 | Executive Dashboard (CEO view): "¿Esta semana ganamos plata?" | ⏳ Pendiente | 5-8 | 1-2 | Frontend |
| SC-3 | Knowledge Capture: cada finding deja metadata de aprendizaje | ⏳ Pendiente | 5-7 | 1 | Backend |
| SC-4 | Pipeline E2E funcionando sin intervención | ⏳ Pendiente | 10-15 | 2-3 | Fullstack |

---

## ARCHITECTURE BUDGET ENFORCEMENT

| Feature | Max Archivos | Max Deps | Max Eventos | Max Capabilities | Max Contratos | Max Tests |
|---------|-------------|----------|-------------|------------------|---------------|-----------|
| Por feature | 2 | 1 | 1 | 1 | 1 | 20 |
| **FASE 1 Total** | 4 | 1 | 1 | 1 | 1 | 25 |

Si una feature necesita más → está mal diseñada.

---

## REVENUE SPRINT REVIEW (obligatorio al final de cada sprint)

| Pregunta | Respuesta |
|----------|-----------|
| ¿Qué parte aumenta la detección? | Execution Layer: 8 plataformas monitoreadas 24/7, scheduling automático |
| ¿Qué parte reduce falsos positivos? | CoderAgent: código generado con tests + lint validación antes de PR |
| ¿Qué parte mejora la aceptación? | CoderAgent: code_generator optimizado, test_runner verifica antes de submit |
| ¿Qué parte mejora el aprendizaje? | AutonomousWorkflow Engine: discover→select→plan→execute→learn |
| ¿Qué parte mejora la autonomía? | **TODA la FASE 2.5** — sistema autónomo 24/7 sin intervención manual |
| ¿Qué parte mejora Expected Revenue? | Scheduler activo 24h, 23 jobs, ciclos Forge+Pulse+Vault+Atlas continuos |
| ¿Qué parte solo mejora arquitectura? | Ruff lint cleanup (necesario para estabilidad) |

---

## REFERENCIAS

- `.ai/OWNEX_ARCHITECTURE.md` — 4 capas, 3 motores, ciclos de trabajo
- `.ai/OWNEX_DESIGN_SYSTEM.md` — Design System v1 completo
- `.ai/OWNEX_MISSION_CONTROL_SPEC.md` — Spec detallada Mission Control
- `.ai/ROADMAP.md` — Roadmap general con fases
- `.ai/CURRENT_STATE.md` — Estado verificado actual
- `.ai/STRATEGIC_AUDIT.md` — Marco de auditoría estratégica