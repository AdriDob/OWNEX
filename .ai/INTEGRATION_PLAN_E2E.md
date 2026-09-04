# OWNEX — PLAN DE INTEGRACIÓN E2E
## Operational Loop: connect what exists, don't rebuild

> **Date:** 2026-09-04
> **Mode:** READ-ONLY / PLAN MODE
> **Principle:** If it exists, use it. If isolated, connect it. If connected but skippable, enforce it.

---

## A. CURRENT STATE — What actually exists

### Component Classification (A-F Scale)

| Component | Exists | Integrated | Enforced | E2E Tested | Used by real flow | Classification |
|-----------|--------|------------|----------|------------|-------------------|----------------|
| **WorkerCore** | ✅ YES | ⚠️ Lifespan init only | ❌ Not started by scheduler | ⚠️ Unit tests only | ❌ No real flow uses it | **B** — Exists but isolated |
| **Opportunity Genome** | ✅ YES (models + mapper) | ⚠️ Mappers exist | ❌ Not used in DWE flow | ⚠️ Unit tests | ❌ DWE uses own Opportunity model | **B** — Exists but isolated |
| **Direct Work Engine** | ✅ YES (48 files) | ✅ Used by API endpoints | ✅ Scoring, recommendations | ✅ 100+ tests | ✅ API serves data | **D** — Integrated but WorkerCore bypass |
| **CATEYE Pipeline** | ✅ YES (scheduler + stages) | ✅ Runs via ScanScheduler | ✅ 7 stages execute | ✅ E2E tests (8/8) | ✅ Scheduler runs it | **F** — Fully operational |
| **CoderAgent** | ✅ YES (5 sub-components) | ⚠️ Referenced by execution engine | ⚠️ Called via execute() | ⚠️ Unit tests | ❌ Never triggered by real flow | **B** — Exists but isolated |
| **Quality Gate** | ✅ YES (evaluation.py) | ✅ Called by WorkerCore._validate_work | ✅ Blocks delivery if fails | ⚠️ Unit tests | ❌ WorkerCore not running | **C** — Connected but unenforced |
| **Human Gate** | ✅ YES (autopilot/gates/) | ✅ Gate system exists | ✅ Auto-approval rules | ⚠️ Unit tests | ❌ Not connected to WorkerCore | **B** — Exists but isolated |
| **Checkpoints** | ✅ YES (persistence.py) | ✅ WorkerCore saves/loads | ✅ Resume from checkpoint | ⚠️ Unit tests | ❌ WorkerCore not running | **C** — Connected but unenforced |
| **Revenue Tracker** | ✅ YES (multiple systems) | ✅ API endpoints exist | ⚠️ No enforcement | ✅ E2E income chain test | ⚠️ Manual only | **C** — Connected but unenforced |
| **Learning/Calibration** | ✅ YES (calibration.py) | ✅ Learning engine records | ⚠️ No trigger from flow | ⚠️ Unit tests | ❌ Not triggered | **B** — Exists but isolated |
| **Observability** | ✅ YES (audit trail, trace_id) | ⚠️ WorkerCore has audit | ⚠� No correlation IDs | ❌ No E2E | ❌ Not connected | **B** — Exists but isolated |
| **Cost Control** | ✅ YES (OAR CostTracker) | ✅ Wired to WorkerCore | ⚠️ No budget enforcement | ⚠️ Unit tests | ❌ Not triggered | **C** — Connected but unenforced |
| **Self-Repair** | ✅ YES (core.self_repair + cores.recovery) | ✅ WorkerCore tries to connect | ⚠️ Fallback to None | ❌ No E2E | ❌ Not triggered | **B** — Exists but isolated |
| **Scheduler** | ✅ YES (75 jobs, 13 cycles) | ✅ Runs via lifespan | ✅ Jobs execute | ✅ Tests | ✅ Real runtime | **F** — Fully operational |
| **Frontend** | ✅ YES (279 components) | ✅ Routes + API calls | ✅ Build works | ⚠️ vue-tsc only | ✅ User interacts | **E** — Integrated but no WorkerCore UI |

---

## B. VERIFIED GAPS — What's actually missing

### Gap 1: WorkerCore never starts (CRITICAL)
- `_init_worker_core()` calls `connect_real_engines()` but does NOT call `worker.start()`
- No scheduler job triggers WorkerCore
- No API endpoint auto-starts it
- **Impact:** The entire 8-phase loop never runs

### Gap 2: Scheduler runs independently of WorkerCore (CRITICAL)
- `api/scheduler.py` (ScanScheduler) runs CATEYE pipeline directly
- `core/scheduler/jobs.py` defines 75 jobs that run via CoreScheduler
- Neither system activates WorkerCore
- **Impact:** Two parallel execution paths, no unified orchestration

### Gap 3: Opportunity Genome not in the main flow (HIGH)
- DWE uses its own `Opportunity` model (from `cores/direct_work_engine/models.py`)
- Genome mappers exist but are never called in the discovery→work flow
- **Impact:** No canonical opportunity representation across systems

### Gap 4: Delivery doesn't update Revenue (HIGH)
- WorkerCore `_deliver_work()` calls delivery engine
- Delivery engine calls AutoSubmit
- But no event/state update reaches RevenueTracker after delivery
- **Impact:** Revenue tracking requires manual intervention

### Gap 5: Learning never triggers from real outcomes (HIGH)
- Learning engine exists and can record to calibration
- But `_learn_from_work()` is never called because WorkerCore never runs
- **Impact:** No calibration improvement, no scoring refinement

### Gap 6: No workflow correlation IDs (MEDIUM)
- WorkerCore has `trace_id`, `workflow_id`, `execution_id`
- But these don't propagate to delivery, revenue, or learning
- **Impact:** Cannot trace a workflow from discovery to payment

### Gap 7: Human Gate not connected to WorkerCore (MEDIUM)
- `cores/autopilot/gates/human_gate.py` has full gate system
- WorkerCore has its own `AutonomyLevel` + `requires_human_approval()`
- They don't talk to each other
- **Impact:** Two separate approval systems

---

## C. FALSE GAPS — Things the audit said were missing but exist

| Claimed Gap | Reality | Evidence |
|-------------|---------|----------|
| Opportunity Genome missing | EXISTS: `cores/opportunity_genome/models.py` + `mapper.py` | 4 mappers, 15+ fields |
| Checkpoint persistence missing | EXISTS: `cores/worker_core/persistence.py` | save_checkpoint, resume_from, rehydrate |
| Quality Gate missing | EXISTS: `cores/direct_work_engine/evaluation.py` + `cores/validation/` | _run_quality_gate, contradiction runner |
| Human Control missing | EXISTS: `cores/autopilot/gates/human_gate.py` + WorkerCore AutonomyLevel | GateRequest, GateDecision, auto-approval |
| Revenue tracking missing | EXISTS: RevenueTracker + PayoutRecord + payment_tracker | Multiple systems, API endpoints |
| Learning loop missing | EXISTS: `cores/direct_work_engine/learning.py` + `calibration.py` | learn(), record() |
| Cost control missing | EXISTS: `cores/ai/runtime/cost.py` (CostTracker) | Token tracking, budget limits |
| Observability missing | EXISTS: WorkerCore audit trail + trace_id | create_audit_entry, trace_context |
| Self-repair missing | EXISTS: `core/self_repair/engine.py` + `cores/recovery/` | RecoveryEngine, HealthMonitor |

---

## D. INTEGRATION GRAPH

```
                    ┌──────────────┐
                    │   Scheduler  │
                    │  (75 jobs)   │
                    └──────┬───────┘
                           │
              ┌────────────┼────────────┐
              │            │            │
              ▼            ▼            ▼
        ┌──────────┐ ┌──────────┐ ┌──────────┐
        │ CATEYE   │ │ Direct   │ │ WorkerCore│
        │ Pipeline │ │ Work Eng │ │ (ORPHAN)  │
        └──────────┘ └──────────┘ └──────────┘
              │            │            │
              │            │      ┌─────┴─────┐
              │            │      │  NOT      │
              │            │      │  STARTED  │
              │            │      └───────────┘
              │            │
              ▼            ▼
        ┌──────────────────────────────────┐
        │         WHAT SHOULD HAPPEN       │
        │                                  │
        │  Scheduler ──→ WorkerCore        │
        │       │           │              │
        │       │     ┌─────┴─────┐       │
        │       │     │ DISCOVER  │       │
        │       │     │ EVALUATE  │       │
        │       │     │ SELECT    │       │
        │       │     │ PREPARE   │       │
        │       │     │ EXECUTE   │──→ CoderAgent
        │       │     │ VALIDATE  │──→ Quality Gate
        │       │     │ DELIVER   │──→ AutoSubmit
        │       │     │           │──→ Revenue Tracker
        │       │     │ LEARN     │──→ Calibration
        │       │     │ OPTIMIZE  │
        │       │     │ REPAIR    │──→ Self-Repair
        │       │     └───────────┘
        │       │
        │       └──→ CATEYE (specialized security)
        │
        └──→ Other jobs (health, notifications, etc.)
```

---

## E. CRITICAL PATH — The 5 changes that close the circuit

### Change 1: Wire Scheduler → WorkerCore (P0)
**What:** Add a scheduler job that starts WorkerCore on boot
**Why:** WorkerCore exists but never runs
**Files:** `core/scheduler/jobs.py`, `api/lifespan.py`
**Risk:** LOW — additive, no existing behavior changes

### Change 2: Wire Delivery → Revenue (P0)
**What:** After successful delivery, update RevenueTracker with EXPECTED state
**Why:** Revenue tracking requires manual intervention today
**Files:** `cores/direct_work_engine/delivery.py`
**Risk:** LOW — additive event emission

### Change 3: Wire Learning ← Outcome (P0)
**What:** After delivery (success or failure), trigger learning engine
**Why:** Calibration never improves without outcome data
**Files:** `cores/worker_core/orchestrator.py` (already calls _learn_from_work)
**Risk:** LOW — already wired, just needs WorkerCore to run

### Change 4: Enforce Quality Gate in delivery path (P1)
**What:** Make Quality Gate mandatory before ANY delivery, not just WorkerCore
**Why:** Direct Work Engine delivery bypasses quality checks
**Files:** `cores/direct_work_engine/delivery.py`
**Risk:** MEDIUM — could block existing deliveries

### Change 5: Add workflow correlation ID propagation (P1)
**What:** Generate workflow_id at discovery, propagate through all phases
**Why:** Cannot trace discovery→payment without correlation
**Files:** `cores/worker_core/orchestrator.py`, `cores/direct_work_engine/`
**Risk:** LOW — additive metadata

---

## F. FILES TO MODIFY

### F1. `core/scheduler/jobs.py`
- **Current:** Defines 75 jobs across 13 cycles
- **Change:** Add `worker_core_cycle` job (every 15 min) that starts WorkerCore if not running
- **Reason:** WorkerCore needs a trigger to start
- **Risk:** LOW

### F2. `api/lifespan.py`
- **Current:** `_init_worker_core()` connects engines but doesn't start
- **Change:** Optionally auto-start WorkerCore in ASSISTED mode
- **Reason:** For dev/testing, auto-start is useful
- **Risk:** LOW — can be gated by env var

### F3. `cores/direct_work_engine/delivery.py`
- **Current:** `deliver()` calls AutoSubmit but doesn't emit events
- **Change:** After successful delivery, emit `delivery:completed` event with workflow_id
- **Reason:** Revenue tracker needs to know about deliveries
- **Risk:** LOW — additive

### F4. `cores/direct_work_engine/learning.py`
- **Current:** `learn()` records to calibration but is never triggered
- **Change:** Already wired in WorkerCore._learn_from_work — just needs WorkerCore to run
- **Reason:** Learning loop closes automatically once WorkerCore runs
- **Risk:** NONE — already implemented

### F5. `cores/worker_core/orchestrator.py`
- **Current:** Has workflow_id but doesn't propagate to delivery/learning
- **Change:** Pass workflow_id to delivery engine and learning engine
- **Reason:** Correlation across phases
- **Risk:** LOW — additive parameter

---

## G. FILES TO CREATE

**None.** All components exist. The task is pure wiring.

---

## H. FILES NOT TO TOUCH

| File | Reason |
|------|--------|
| `database/models.py` | Stable schema, many dependents |
| `api/main.py` | Router registration — fragile |
| `frontend/src/router/index.ts` | Navigation — user-facing |
| `cores/events/event_bus.py` | Core infrastructure |
| `core/scheduler/scheduler.py` | Core scheduler — stable |
| `cores/direct_work_engine/models.py` | Data models — many consumers |
| `core/opportunity/engine.py` | Opportunity engine — stable |

---

## I. TEST PLAN

### Unit Tests (per change)
1. **F1:** Test scheduler job resolves and calls worker_core
2. **F3:** Test delivery emits event with workflow_id
3. **F5:** Test workflow_id propagation through phases

### Integration Tests
4. **E2E Golden Path:** Discover → Evaluate → Execute → Validate → Deliver → Learn
5. **E2E Failure Path:** Execute fails → checkpoint → recovery
6. **E2E Quality Gate:** Quality gate rejects → no delivery → reason persisted

### Regression
7. Run `python scripts/dev test-fast` after each change
8. Run `python -m ruff check` after each change

---

## J. ROLLBACK PLAN

Each change is independent and additive:
- **F1:** Remove the scheduler job entry
- **F2:** Remove the auto-start call
- **F3:** Remove the event emission
- **F5:** Remove the workflow_id parameter

No schema changes. No destructive operations. Each change can be reverted with a single `git revert`.

---

## K. EXECUTION ORDER

```
1. Add worker_core_cycle scheduler job (F1)
   → Verify: job appears in get_all_jobs(), worker starts on boot
   
2. Wire delivery → event emission (F3)
   → Verify: delivery emits delivery:completed event
   
3. Add workflow_id propagation (F5)
   → Verify: workflow_id appears in delivery and learning logs
   
4. Write E2E golden path test (I.4)
   → Verify: full cycle completes with all phases logged
   
5. Write E2E failure path test (I.5)
   → Verify: checkpoint created, recovery possible
   
6. Run full test suite (I.7)
   → Verify: no regressions
```

---

## L. DEFINITION OF DONE

The Operational Loop E2E is complete when:

- [ ] WorkerCore starts automatically on API boot
- [ ] Discovery finds opportunities
- [ ] Evaluation scores and filters them
- [ ] Selection picks the best one
- [ ] Preparation sets up the work environment
- [ ] Execution uses CoderAgent (for coding tasks)
- [ ] Quality Gate validates before delivery
- [ ] Delivery submits via AutoSubmit
- [ ] Revenue state updates after delivery
- [ ] Learning records outcome to calibration
- [ ] Checkpoints persist at each phase
- [ ] Recovery resumes from last checkpoint
- [ ] Workflow ID correlates all phases
- [ ] All existing tests still pass
- [ ] E2E golden path test passes

---

## DECISION SUMMARY

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Orchestrator | WorkerCore (existing) | Already has 8 phases, circuit breakers, audit trail |
| Opportunity model | DWE Opportunity (existing) | Genome mappers exist but DWE model is the one used |
| Quality Gate | _run_quality_gate (existing) | Multi-signal check, already in evaluation.py |
| Revenue tracking | RevenueTracker (existing) | Already has PayoutRecord, payment pipeline |
| Learning | DirectWorkLearningEngine (existing) | Already records to calibration |
| New files needed | NONE | Pure wiring task |

---

*Generated by Codebuff 🤖 — READ-ONLY analysis phase*
