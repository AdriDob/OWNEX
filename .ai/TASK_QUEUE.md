> **Rotas tablas de auditoría ya cerradas**: el histórico completo está en `.ai/archive/TASK_QUEUE.md` (24,173 B, 6 secciones). Este archivo conserva 7 de 13.
> **Regla**: grepeá `.ai/archive/TASK_QUEUE.md` antes de contradecir una regla histórica.

## REFERENCIAS

- `.ai/CURRENT_STATE.md` — Estado real auditado (sección "AUDITORÍA 2026-07-31")
- `.ai/OWNEX_ARCHITECTURE.md` — 4 capas, 3 motores, ciclos de trabajo
- `.ai/OWNEX_MISSION_CONTROL_SPEC.md` — Spec detallada Mission Control
- `.ai/ROADMAP.md` — Roadmap general con fases
- `.ai/STRATEGIC_AUDIT.md` — Marco de auditoría estratégica

## REVENUE MULTIPLIER v2 — plan revisión externa (2026-08-25)
| # | Item | Estado |
|---|------|--------|
| 1 | Revenue Optimizer $/h humano | ✅ economics.compute_expected_human_value |
| 2 | Human-Time breakdown manual/auto/review | 🟡 parcial |
| 3 | Portfolio NOW/WAITING/LONG | ✅ base income_plan.phases |
| 4 | Adaptive Earnings | ✅ feedback loop existente |
| 5 | Personal Income Model c/ confidence | 🟡 parcial |
| 6 | **Availability Intelligence** | 🔴 GAP P0 — próxima sesión |
| 7 | Execution Automation gate unificado | 🟡 piezas |
| 8 | Income Experiments KEEP/DROP/SCALE | ❌ nuevo |
Bloqueantes release previos: TODOS remediados (commits 9f4d3f45…83ac9dc7).

## EXECUTION LAYER v1 — plan revisión externa (2026-08-25)
Auditar antes: BrowserAgent (EXEC-3) + PlatformBrowserWorkers (EXEC-8) + Evidence
Composer ya existen → NO reconstruir; el gap real es UNIFICARLOS.
| # | Pieza | Estado |
|---|-------|--------|
| 1 | Execution Queue (DISCOVERED→PAID, retries/idempotency/DLQ) | 🔴 P0 nuevo |
| 2 | Human Gate unificado (WAITING_HUMAN + approvals) | 🟡 piezas existentes |
| 3 | Evidence Vault (screenshot+URL+ts+metadata por ejecución) | 🟡 Evidence Composer existe, falta vínculo por-ejecución |
| 4 | Revenue Ledger (expected→committed→earned→pending→paid→net) | 🟡 RevenueTracker parcial |
| 5 | Trading Intelligence como MÓDULO EXTERNO (Freqtrade), nunca en núcleo | 🟠 post-queue |
| 6 | Autonomous Scheduler (score×avail×acceptance→prioridad) | 🟡 income_plan ya calcula; falta drive la queue |
| 1a | ✅ State machine pura + persistencia JSON (`cores/execution_queue/models.py::ExecutionQueueStore`, 13 estados) + adapters a 10 executors (`cores/execution_queue/driver.py`, score×avail×acceptance) + scheduler driver (3 jobs: process/retry/dlq, `get_execution_queue_jobs()`) — verificado 2026-09-09 |
| 1b | ✅ Handlers de ciclo porteados (`cores/cycles/tasks.py`: auto_start, auto_submit sweep, market_evolution, task_refresh, qa, evolution_report) + 10 jobs muertos eliminados (coder_autopilot, arbitrage, 8 trading — sin runner; ver DECISIONS 2026-09-09) — test de resolución de TODOS los handlers (`test_cycle_task_handlers.py`) |
| 1c | ⏳ Follow-up: runners reales para jobs removidos (coder autopilot batch ≤$200 vía DevBountyPipeline+discovery; arbitrage scan; 8 fns trading) — re-agregar job SOLO con runner testeado |

## BACKEND ALPHA 1.0 — spec maestro producción (2026-08-25 noche)
Spec completo del owner: auditoría total + Revenue Orchestrator + Economic Engine único
+ Zero-Barrier normalizado + Platform Intelligence + Availability Engine + Execution
Automation levels 0-4 + Revenue Ledger + scheduler idempotente + sidecar lifecycle +
persistencia %LOCALAPPDATA% + observabilidad estructurada + E2E sin internet.
**Solapamiento**: CORS/sidecar/EV-único/availability-honesto ya remediados hoy
(9f4d3f45…83ac9dc7) — verificar contra código antes de re-implementar.
Base ya construida esta sesión: `core/execution_queue.py` (13 estados, 9/9 tests)
= esqueleto del flujo canónico DISCOVERED→…→PAID.
Orden propuesto: (1) AUDIT_BACKEND_ALPHA_1.0.md ← primera acción próxima sesión,
(2) revenue ledger sobre execution queue, (3) adapters executors, (4) scheduler driver.

## APP FACTORY VALIDATION EXPERIMENT — NEXA vs FOCUS (Etapa 3)

> **Objetivo**: Validar demanda ANTES de construir Flutter MVP. $0 desarrollo, 2 semanas tráfico real.

| ID | Task | Estado | Esfuerzo |
|----|------|--------|----------|
| AF-1 | Landing NEXA: hero + demo interactiva (goal→plan→today→action) + price intent + email | ✅ READY TO DEPLOY | S |
| AF-2 | Landing FOCUS: hero + demo interactiva (capture→prioritize→time/energy→next) + price intent + email | ✅ READY TO DEPLOY | S |
| AF-3 | Analytics Python: 7 eventos + Demand Score JSONL + veredicto | ✅ COMPLETADO | S |
| AF-4 | API REST: POST /ingest, POST /import, GET /overview, GET /experiments | ✅ COMPLETADO + MONTADO | S |
| AF-5 | Frontend Mission: factory visible si backend trae datos | ✅ INTEGRADO | S |
| AF-6 | **Deploy Netlify + 2 semanas tráfico real (CONTENT_CALENDAR.md)** | ⏳ PENDING DEPLOY | S |
| AF-7 | **Decision rule**: Demand Score ≥40 + emails≥5 → BUILD Flutter MVP; <15 → KILL | ⏳ PENDING DATA | S |

---

### PENDIENTE — Unified Agenda & Goals System (desktop app)

> Los módulos existen dispersos pero NO están conectados como agenda unificada.
> El usuario pidió explícitamente: tareas diarias + objetivos corto/mediano/largo plazo.

**Qué existe (conectar, no reconstruir):**
- Life Management Tasks (`/life-management/tasks`) — tareas diarias
- Life Management Goals (`/life-management/goals`) — objetivos genéricos
- Capital Savings Goals (`cores/capital/allocation`) — objetivos financieros
- Career Roadmap (`/career/roadmap`) — plan de skills
- Income Target Engine (`income_target.py`) — planes semanales/mensuales
- Revenue Timeline (`/revenue-timeline/calculate`) — proyecciones
- Daily Companion (`daily_companion.py`) — briefing diario
- Outlook Calendar Sync (`/outlook/*`) — calendario externo

**Qué falta construir:**
- [ ] Modelo `AgendaItem` unificado: {date, horizon(corto/medio/largo), source(work/capital/career/personal), title, progress}
- [ ] Vista calendario semanal/mensual/anual en frontend
- [ ] Conexión: IncomeTarget.milestones → AgendaItems automáticos
- [ ] Conexión: CareerRoadmap.skills → AgendaItems (learning schedule)
- [ ] Conexión: CapitalSavings.deadlines → AgendaItems
- [ ] Notificaciones de deadlines próximos (Watch + Mobile)
- [ ] Vista timeline: "en X meses deberías estar en $Y"

**Dónde:** nuevo módulo `cores/agenda/` + router `/api/agenda` + página `/agenda`
**Prioridad:** Media-Alta (mejora retención diaria del usuario)
**Esfuerzo estimado:** 2-3 días

## SECURE INCOME — especificación owner (2026-09-10)

> Objetivo: máxima P(cobrar) + mínimo tiempo sin ingresos + varias fuentes + aprendizaje rápido. Bug bounty = upside, nunca renta base.

| # | Pieza | Estado |
|---|-------|--------|
| S1 | P(CASH) en economics.py (PCASH-V1) + wiring recommender + `p_cash/p_cash_band` en `/recommend` | ✅ HECHO 2026-09-10 (`tests/test_secure_income.py` 10/10) |
| S2 | Modo `secure_income` (accept .35/speed .25, floor 0.50, diversidad 2/3) | ✅ HECHO 2026-09-10 |
| S3 | Modo `secure_plus_upside` (accept .30/EV .25, piso 0.30, floor OFF — modo normal) | ✅ HECHO 2026-09-10 |
| S4 | Splitter automático por horas (2h base / 1.5h dev / 0.5h upside) | ⏳ follow-up (guía de uso en docstring del preset; NO código hasta validar presets en uso real) |
| S5 | `P(monthly ≥ $X)` desde outcomes reales ($500 → $1k → $2k → $5k) | ⏳ follow-up (base existe: tiers `income_target.py` + `identify_repeatable`; construir SOLO cuando haya outcomes PAID reales que calibrar) |

---

## BUG BOUNTY / AI SECURITY — dirección estratégica (2026-09-20)

> **Regla de oro**: OWNEX no persigue "el bounty más grande", persigue **EV por hora humana**.
> Dos capas separadas:
> - **HIGH_EXPECTED_VALUE** (70-80%): AI security, API/web, IDOR/auth, cloud, OSS, model supply chain
> - **HIGH_UPSIDE / JACKPOT** (15-25%): Microsoft, Google, GitHub, AI frontier labs
> - **JACKPOT RESEARCH** (5-10%): Microsoft Hyper-V ($250k), Chrome RCE ($250k), OpenAI Bio ($50k)

### Capa 1: HIGH_EXPECTED_VALUE (donde OWNEX encaja hoy)

| Área | Payout | Dificultad | Encaje | Acción |
|---|---:|---|---:|---|
| **AI Agent Security** | Alto | Alta | ⭐⭐⭐⭐⭐ | Prioridad #1 — reasoners + discovery + evidence ya listos |
| **AI Safety / Bio** | $50k | Extrema | ⭐⭐⭐⭐ | Capa 2 — mantener radar |
| **Web/API Critical** | $5k–$50k+ | Media/Alta | ⭐⭐⭐⭐⭐ | Capa 1 — discovery activo |
| **OSS / Model Supply Chain** | $1k–$30k+ | Media/Alta | ⭐⭐⭐⭐⭐ | Capa 1 — discovery activo |
| **Microsoft Cloud/Identity** | $100k+ | Extrema | ⭐⭐⭐⭐ | Capa 2 — radar + scope matching |

### Capa 2: JACKPOT (moonshot, 5-10% tiempo)

| Programa | Payout max | Dificultad | Nota |
|---|---:|---|---|
| **Microsoft Hyper-V** | $250k | Extrema | RCE guest escape |
| **Google Chrome VRP** | $250k | Extrema | RCE/sandbox escape |
| **Microsoft Identity** | $100k | Extrema | Auth/MFA bypass |
| **OpenAI Bio Bounty** | $50k | Extrema | Universal jailbreak (privado) |
| **Anthropic Model Safety** | $35k | Extrema | Universal jailbreak CBRN |

### Scores independientes en Opportunity Engine

```text
APPROVAL_SCOPE = scope_certainty × technical_fit × reproducibility × evidence_quality
JACKPOT_SCORE = max_reward × severity × impact × uniqueness × technical_fit
EV = payout × P(valid) × P(unique) × P(accept) × P(reward) × speed
```

### Integración requerida

- [ ] Extender `Opportunity` con: `expected_cash`, `max_reward`, `p_success`, `time_to_cash`, `estimated_hours`, `technical_fit`, `repeatability`, `competition`, `scope_confidence`, `payout_confidence`, `jackpot_score`, `expected_value`
- [ ] Crear dos rankings en `/recommend`: `high_expected_value` + `high_upside_90d` + `jackpot_research`
- [ ] Mantener `P(cash)` honesto desde outcomes reales (nunca inventado)
- [ ] `P(accept)` aprendido de outcomes verificados (UNKNOWN hasta datos reales)

### Próximos pasos inmediatos (sin código nuevo, solo wiring)

1. Wiring `PromptInjectionReasoner` → discovery de OpenAI/Anthropic/Microsoft AI
2. Extender `global_sources.py` con programas AI frontier (OpenAI Safety, Anthropic Model Safety, Microsoft AI)
3. `HIGH_UPSIDE_90D` preset ya existe → confirmar wiring en `/recommend`
4. `JACKPOT` mode → mode separado, nunca default
5. Métrica principal: **`money_per_human_hour`** (ya en `cores/cycles/metrics.py`)
