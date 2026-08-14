# OWNEX Consolidation Plan — From 130 Systems to Unified Intelligence

> **Goal**: Unify existing components so OWNEX becomes a tool you open daily — not a project you maintain.

---

## Current State Mapping (What Already Exists)

| Vision Area | Existing Component(s) | Location | Status |
|-------------|----------------------|----------|--------|
| **1. Cerebro / Decision Engine** | `DecisionEngine`, `PriorityEngine`, `UnifiedOrchestrator` | `cores/decision_core.py`, `cores/intelligence/` | ✅ Strong core, needs wiring |
| **2. Motor Económico** | `RevenueEngine`, `RevenuePipeline`, `scoring.py`, `economic_memory.py` | `cores/revenue/`, `cores/opportunity/` | ✅ Complete pipeline, needs unified scoring |
| **3. Sistema de Agentes** | `AssistantOrchestrator`, `ScanService`, agent stores | `cores/orchestrator/`, frontend stores | ⚠️ Fragmented (backend + frontend separate) |
| **4. Tool Registry** | `ToolRegistry` (massive — 20K lines) | `cores/tool_registry.py` | ✅ Exists, over-engineered |
| **5. Memoria (3 niveles)** | `KnowledgeGraph`, `DecisionJournal`, `memory.py` (system), `learning_scorer.py`, `pattern_extractor.py` | `cores/knowledge_core.py`, `cores/decision_journal/`, `cores/memory/` | ⚠️ 5+ separate memory systems |
| **6. UX / Cockpit** | `MissionControl.vue`, `Capital.vue`, `InvestmentHub.vue`, `IntelligenceDashboard.vue` | `frontend/src/pages/` | ⚠️ 40+ pages, no unified "Today" view |
| **7. Autonomía con límites** | EventBus workflow (9 phases), permission checks scattered | `cores/revenue/RevenueEngine.py`, `cores/events/` | ⚠️ Partial, no explicit levels |
| **8. Evidencia / Explainability** | `EvidenceCenter.vue`, artifact lineage in `UnifiedOrchestrator` | `cores/intelligence/`, frontend | ⚠️ Lineage exists, no "Why?" API |
| **9. Consolidación (Auth, Events, Config, Logging, Errors, Providers, Tools, Metrics, UI)** | Multiple duplicated across `core/` + `cores/` | Twin trees problem | 🔴 Critical |

---

## Consolidation Strategy: 4 Phases

### Phase 1: Unify the Twin Trees (Week 1) — **Highest Leverage**

**Problem**: `core/` and `cores/` are near-duplicates. Runtime uses `cores/` only. Imports from `core.investment` edit BOTH.

**Action**:
1. Pick `cores/` as canonical (it's what runtime uses)
2. Delete `core/` entirely
3. Fix any remaining imports pointing to `core.`
4. Run `make check` to verify nothing breaks

**Files to delete**: Entire `core/` directory (~50+ files)
**Risk**: Low — runtime already uses `cores/`

---

### Phase 2: Single Memory Layer (Week 1-2)

**Current**: 5+ memory systems
- `KnowledgeGraph` (SQLite, institutional learning)
- `DecisionJournal` (append-only decisions + outcomes)
- `memory.py` (system memory — preferences, operational, strategic)
- `learning_scorer.py` + `pattern_extractor.py` (analysis on top)
- `memory_store.py` + `store.py` (low-level storage)

**Target**: One `UnifiedMemory` with 3 tiers matching your vision:

```python
# cores/memory/unified_memory.py
class UnifiedMemory:
    # Tier 1: Personal (preferences, goals, constraints)
    personal: PersonalMemory

    # Tier 2: Operational (what ran, what worked, what failed)
    operational: OperationalMemory  # wraps DecisionJournal + TaskOutcome

    # Tier 3: Strategic (patterns, platform performance, task-type ROI)
    strategic: StrategicMemory  # wraps KnowledgeGraph + learning_scorer
```

**Migration**:
- `KnowledgeGraph` → `StrategicMemory` (rename, keep API)
- `DecisionJournal` → `OperationalMemory` (rename, keep API)
- `memory.py` → `PersonalMemory` (already has 3 tiers!)
- `learning_scorer` + `pattern_extractor` → methods on `StrategicMemory`

**Benefit**: Single import, single query interface, cross-tier learning automatic.

---

### Phase 3: Single Decision Pipeline (Week 2)

**Current**: Multiple decision entry points
1. `PriorityEngine` → scores opportunities
2. `DecisionEngine` → bayesian task selection
3. `OpportunityEngine` → discovers + evaluates
4. `RevenueEngine` → 9-phase EventBus workflow
5. `UnifiedOrchestrator` → artifact lifecycle

**Target**: One `DecisionPipeline` that chains:

```
Discover (OpportunityEngine)
    → Score (PriorityEngine + DecisionEngine beliefs)
    → Select (DecisionEngine policy)
    → Execute (RevenueEngine 9-phase via EventBus)
    → Learn (UnifiedMemory records outcome → updates beliefs)
```

**Key unification**: `DecisionEngine.get_belief()` already reads from `KnowledgeGraph`. 
Make `PriorityEngine` use `DecisionEngine` beliefs instead of own scoring.

**New file**: `cores/decision/pipeline.py` — orchestrates the flow, single entry point.

---

### Phase 4: Single "Today" Cockpit (Week 2-3)

**Current**: 40+ pages, no unified entry point.

**Target**: One page — `TodayView.vue` — that answers:

```
OWNEX TODAY
─────────────────────────────────────
🟢 7 oportunidades buenas
⚡ 2 cobro rápido
💰 $1,240 potencial
🤖 83% automatizable

PRÓXIMA MEJOR ACCIÓN
─────────────────────────────────────
Implementar X en Plataforma Y
22 min humanos | 78% éxito | $180 EV
[ABRIR]  [EXPLICAR]  [POSPONER]

ACTIVIDAD ▸ RESULTADOS ▸ INGRESOS ▸ AUTOMATIZACIÓN ▸ APRENDIZAJE
```

**Backend**: Single endpoint `/api/today` that composes:
- `DecisionPipeline.get_next_action()` → returns `Decision` with rationale
- `RevenueEngine.summary()` → aggregates
- `UnifiedMemory.strategic.get_patterns()` → automation %, success rates

**Frontend**: 
- Delete `Dashboard.vue`, `MissionControl.vue`, `OpportunityRadar.vue`, `OpportunityPlanner.vue` → merge into `TodayView.vue`
- Keep specialized pages (`Capital.vue`, `InvestmentHub.vue`) as drill-downs from Today tabs

---

## Cross-Cutting Consolidation (Do in Parallel)

| Area | Current State | Target |
|------|---------------|--------|
| **Auth** | `core/auth/`, `cores/auth/`, frontend `auth.ts` | Single `cores/auth/` + frontend store |
| **Events** | `cores/events/event_bus.py`, `core/events/` | Single `cores/events/` (CoreEventBus) |
| **Config** | `core/config/`, `cores/config/`, `settings.ts` | Single `cores/config/` + sync to frontend |
| **Logging** | `cores/logging/`, `core/logging/`, `console.log` everywhere | Structured `cores/observability/` |
| **Errors** | Scattered try/catch | `cores/errors/ErrorHandler` + Result types |
| **AI Providers** | `cores/ai/`, `core/ai/`, FCC proxy, Ollama, OpenCode | Single `cores/providers/` registry |
| **Tools** | `cores/tool_registry.py` (20K lines) | Split: `ToolRegistry` (thin) + `ToolCatalog` (metadata) |
| **Metrics** | `cores/revenue/metrics.py`, `cores/intelligence/observability.py` | Single `cores/metrics/` |
| **UI Components** | 200+ Vue components | Audit: keep < 50 core, rest lazy-loaded |

---

## Architecture After Consolidation

```
cores/
├── auth/              # Single auth (JWT + API keys)
├── config/            # Single config (Pydantic Settings)
├── events/            # Single EventBus (CoreEventBus)
├── errors/            # ErrorHandler, Result<T>, retry policies
├── logging/           # Structured logging (structlog)
├── metrics/           # Prometheus + custom business metrics
├── observability/     # Traces, spans, health checks
├── providers/         # AI provider registry (Ollama, FCC, OpenCode, OpenRouter)
├── tools/
│   ├── registry.py    # Thin: register, get, execute
│   └── catalog.py     # Metadata: cost, speed, risk, credentials
├── memory/
│   ├── unified_memory.py      # Single entry point (3 tiers)
│   ├── personal.py            # Preferences, goals, constraints
│   ├── operational.py         # DecisionJournal + TaskOutcome
│   └── strategic.py           # KnowledgeGraph + patterns
├── decision/
│   ├── pipeline.py            # Single entry: discover → score → select → execute → learn
│   ├── engine.py              # DecisionEngine (bayesian beliefs)
│   └── priority.py            # PriorityEngine (scoring algorithms)
├── revenue/
│   ├── engine.py              # RevenueEngine (9-phase EventBus)
│   ├── pipeline.py            # RevenuePipeline (submit → track → payout)
│   └── scoring.py             # Unified scoring (EV × prob × automation / time)
├── opportunity/
│   └── engine.py              # OpportunityEngine (discovery + evaluation)
├── orchestrator/
│   ├── assistant.py           # AssistantOrchestrator (frontend-facing)
│   └── scan.py                # ScanService (AEGIS)
└── intelligence/
    ├── unified_orchestrator.py # Artifact lifecycle (keep)
    ├── anti_drift.py          # Anti-drift (keep)
    └── observability.py       # Observability (keep)
```

---

## Verification Checklist (After Each Phase)

- [ ] `make check` passes (Ruff + mypy + fast tests)
- [ ] `python scripts/dev test-fast` passes
- [ ] No imports from deleted `core/`
- [ ] Single import path for each capability
- [ ] `/api/today` returns structured decision with rationale
- [ ] Frontend `TodayView.vue` loads in < 500ms
- [ ] Memory tiers queryable via single `UnifiedMemory` instance

---

## Revenue Rule Compliance Check

| Change | Increases Detection? | Reduces False Positives? | Improves Acceptance? | Improves Learning? | Improves Autonomy? | Improves Expected Revenue? |
|--------|---------------------|-------------------------|---------------------|-------------------|-------------------|---------------------------|
| Phase 1: Delete core/ | — | — | — | — | ✅ (less confusion) | — |
| Phase 2: UnifiedMemory | — | — | — | ✅ (cross-tier) | ✅ (single query) | ✅ (better decisions) |
| Phase 3: DecisionPipeline | ✅ (unified scoring) | ✅ (bayesian beliefs) | ✅ (evidence chain) | ✅ (outcome→belief) | ✅ (auto-select) | ✅ (max EV) |
| Phase 4: TodayView | — | — | — | — | ✅ (one action) | ✅ (focus on best) |

---

## Start Order

1. **Today**: Delete `core/` (Phase 1) — 30 min, immediate clarity
2. **This week**: UnifiedMemory (Phase 2) — connects everything
3. **This week**: DecisionPipeline (Phase 3) — the "brain" wiring
4. **Next week**: TodayView (Phase 4) — the daily interface

---

## What NOT to Build

- ❌ New agent frameworks
- ❌ New memory systems
- ❌ New scoring algorithms
- ❌ New UI frameworks
- ❌ New EventBus implementations

**Everything needed already exists.** Consolidation = deletion + wiring.