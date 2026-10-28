# OWNEX MEGA AUDIT — 100/100 PLANNING DOCUMENT

> **Date:** 2026-09-04
> **Method:** Codebase analysis via graft graph, AST analysis, file counting, grep
> **Verdict:** OWNEX has massive surface area (2,834 Python files, 279 Vue components, 1,539 API endpoints, 6,148 test symbols) but critical structural issues prevent it from being a revenue-generating work OS.

---

## A. EXECUTIVE VERDICT

OWNEX is an extraordinarily ambitious project — a Personal Work OS for autonomous income generation. The codebase is enormous: **2,834 Python files**, **1,539 API endpoints**, **279 Vue components**, **6,148 test symbols** across 245 test files.

**The core problem is not missing code. It's missing integration.**

The system has:
- ✅ Opportunity discovery (real adapters for H1, BC, IW, YWH + GitHub bounty-targets-data)
- ✅ Revenue tracking (RevenueTracker, PayoutRecord, payment pipeline)
- ✅ Work bank with scoring (EVH, barrier, confidence)
- ✅ Execution layer (WorkerCore orchestrator, CoderAgent, BrowserAgent)
- ✅ Memory/Learning (UnifiedMemoryStore, LearningEngine, calibration)
- ✅ Desktop (PySide6 + Tauri v2 dual-mode)
- ✅ Frontend (Vue 3 + TypeScript + Tailwind v4)

**But critically broken:**
- ❌ **Twin trees** (core/ = 649 files, cores/ = 1,147 files) with near-duplicate modules
- ❌ **149 TODO/FIXME/HACK** markers indicating incomplete work
- ❌ **Zero real external API integrations that actually submit work**
- ❌ **No real money has ever flowed through the system**
- ❌ **Discovery → Execution → Delivery pipeline is not end-to-end wired**
- ❌ **Human control layer is absent** (no approval gates, no LITE/ASSISTED/AUTONOMOUS modes)

**Current score: ~28/100.** The bones are extraordinary. The wiring is not.

---

## B. CURRENT ARCHITECTURE

```
┌─────────────────────────────────────────────────────────────┐
│                      OWNEX System                            │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │  Frontend     │  │  Desktop      │  │  Mobile       │      │
│  │  Vue 3 + TS   │  │  PySide6 +    │  │  Tauri v2 +   │      │
│  │  Tailwind v4  │  │  Tauri v2     │  │  Android      │      │
│  │  279 components│  │  36 py files  │  │  16 files     │      │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘      │
│         │                  │                  │               │
│  ┌──────┴──────────────────┴──────────────────┴───────┐     │
│  │              API Layer (1,539 endpoints)            │     │
│  │              181 router files                        │     │
│  └──────────────────────┬─────────────────────────────┘     │
│                         │                                    │
│  ┌──────────────────────┴─────────────────────────────┐     │
│  │         cores/ (1,147 files) ← CANONICAL            │     │
│  │  ┌─────────┐ ┌──────────┐ ┌──────────┐ ┌────────┐ │     │
│  │  │Discovery │ │Work Bank │ │ Worker   │ │Revenue │ │     │
│  │  │Engine   │ │48 files  │ │Core 7fil │ │Tracker │ │     │
│  │  └─────────┘ └──────────┘ └──────────┘ └────────┘ │     │
│  │  ┌─────────┐ ┌──────────┐ ┌──────────┐ ┌────────┐ │     │
│  │  │Memory   │ │Scheduler │ │Learning  │ │Identity│ │     │
│  │  │System   │ │49 jobs   │ │Engine    │ │Vault   │ │     │
│  │  └─────────┘ └──────────┘ └──────────┘ └────────┘ │     │
│  │  ┌─────────┐ ┌──────────┐ ┌──────────┐ ┌────────┐ │     │
│  │  │Platform │ │Adapters  │ │Executors │ │Events  │ │     │
│  │  │Connect  │ │H1/BC/IW  │ │5 executors│ │EventBus│ │     │
│  │  └─────────┘ └──────────┘ └──────────┘ └────────┘ │     │
│  └────────────────────────────────────────────────────┘     │
│                                                              │
│  ┌────────────────────────────────────────────────────┐     │
│  │         core/ (649 files) ← LEGACY TWIN            │     │
│  │  Duplicates: opportunity, scheduler, memory,        │     │
│  │  execution, events, credentials, cycles              │     │
│  └────────────────────────────────────────────────────┘     │
│                                                              │
│  ┌────────────────────────────────────────────────────┐     │
│  │         Database: SQLite (dev) / PostgreSQL (prod)   │     │
│  │         models.py: targets, findings, verdicts,      │     │
│  │         scan_runs, reports, programs, memory_records  │     │
│  └────────────────────────────────────────────────────┘     │
│                                                              │
│  ┌────────────────────────────────────────────────────┐     │
│  │         Scheduler: LifeScheduler                     │     │
│  │         13 cycles × 49 jobs                          │     │
│  │         security, forge, pulse, vault, atlas,        │     │
│  │         direct_work, investment, qa, evolution,      │     │
│  │         knowledge, trading, integrations, execution   │     │
│  └────────────────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────────────┘
```

---

## C. VERIFIED REAL (What Actually Works)

| Component | Status | Evidence | Files |
|-----------|--------|----------|-------|
| **Opportunity Discovery** | ✅ REAL | Adapters for H1, BC, IW, YWH, Fiverr, Outlier, Mindrift fetch real data (some via GitHub bounty-targets-data) | `cores/opportunity/adapters/`, `core/opportunity/adapters/` |
| **Work Bank** | ✅ REAL | 48 files in `cores/direct_work_engine/`, daily_cycle, scoring, recommendations | `cores/direct_work_engine/workbank.py`, `engine.py` |
| **EVH Scoring** | ✅ REAL | Expected Value per Hour with versioning (HTROI-V1), confidence scoring (CONF-V1) | `cores/direct_work_engine/economics.py`, `confidence.py` |
| **Revenue Tracking** | ✅ REAL | RevenueTracker with PayoutRecord, payment pipeline, financial truth snapshot | `cores/revenue_tracker/`, `api/routers/revenue.py`, `financial_truth.py` |
| **Memory Store** | ✅ REAL | SQLite-backed MemoryRecord, MemoryStore with category+key query | `cores/memory/memory_store.py`, `system.py` |
| **Learning Engine** | ✅ REAL | Calibration with predicho-vs-real JSONL, platform_factor | `cores/direct_work_engine/calibration.py` |
| **Event Bus** | ✅ REAL | Singletons in both core/ and cores/, 89+ callers | `cores/events/event_bus.py` |
| **Identity Vault** | ✅ REAL | 47 callers, credential storage | `cores/identity_vault.py` |
| **Security Scan** | ✅ REAL | SecretScanner, vault scanning | `api/routers/knowledge_bridge.py` |
| **Desktop** | ✅ REAL | PySide6 dual-mode (API + local), Tauri v2 shell, MSI/NSIS installers | `desktop/native/`, `src-tauri/` |
| **Frontend** | ✅ REAL | Vue 3, 279 components, 83 pages, 362 TS/Vue files | `frontend/src/` |
| **Profile Kit** | ✅ REAL | Multi-platform profiles (12 platforms × ES/EN) | `cores/direct_work_engine/profile_kit.py` |
| **Scheduler** | ✅ REAL | 49 jobs across 13 cycles, anti-overlap, flock | `core/scheduler/jobs.py` |
| **Application Assistant** | ✅ REAL | 5 platforms, 19 steps, pre-filled from Profile Kit | `core/application_assistant.py` |
| **Auto-Submit Engine** | ✅ REAL | API delivery with idempotency keys, retry, DLQ | `core/opportunity/executors/auto_submit.py` |
| **Dev Bounty Pipeline** | ✅ REAL | 6-phase pipeline: clone → analyze → fix → test → PR → submit | `core/autonomy/dev_bounty_pipeline.py` |
| **Knowledge Graph** | ✅ REAL | Cytoscape UI, singleton graph, export JSON/PNG | `api/routers/knowledge_graph.py` |
| **Tax/Compliance** | ✅ REAL | W-8BEN, W-9, AFIP Facturas, deadlines | `cores/compliance/tax_automation.py` |
| **Finding Marketplace** | ✅ REAL | Listings, offers, counter, escrow, reputation | `cores/marketplace/finding_market.py` |
| **Quick Capture** | ✅ REAL | URL → Work Bank with hotkeys (Ctrl+Shift+O/P) | `cores/intake/quick_capture.py` |
| **Platform Webhooks** | ✅ REAL | HMAC verification, event normalization | `api/routers/platform_webhooks.py` |
| **Predictive Prioritizer** | ✅ REAL | 7-day forecast with P(accepted) empirical | `cores/learning/predictive_prioritizer.py` |

---

## D. PARTIAL / STUB / MOCK / DEAD / MISSING

### PARTIAL (Exists but not fully integrated)

| Component | What Exists | What's Missing | Impact |
|-----------|-------------|----------------|--------|
| **WorkerCore** | Orchestrator with circuit breaker, skill engine | `_execute_work` has circuit breaker but no real executor wiring | Cannot actually do work |
| **Execution Layer** | `core/execution/runtime/worker.py` with 17 opcodes | Bytecode VM exists but no real execution paths | System can't execute anything autonomously |
| **CoderAgent** | Referenced in execution.py | No real LLM integration for code generation | No automated coding |
| **BrowserAgent** | Referenced in execution.py | No real Playwright/Puppeteer integration | No automated browsing |
| **Profile Optimizer** | Profile Kit generates content | No automated posting/submission to platforms | Profile optimization is manual |
| **Calibration** | JSONL predicho-vs-real | No feedback loop that actually adjusts scoring | Learning is one-way |

### STUB (Structure exists, no real functionality)

| Component | Location | Verdict |
|-----------|----------|---------|
| `commander.py` `_on_opportunity_discovered` | `cores/commander.py:725` | `pass` — empty handler |
| `voice_department/integrations.py` `execute_with_execution_layer` | Line 120 | Returns placeholder `{status: "queued"}` |
| `get_expected_vs_realized` | `api/routers/unified_income.py:232` | Returns hardcoded zeros |
| `infinite_sources.py` discovery | `api/routers/infinite_sources.py:67` | In-memory list, no real sources |
| `core/opportunity/executors/` | 5 executor files | Platform executors exist but submit via API calls that require real credentials (never tested end-to-end) |

### MOCK / FAKE (Test doubles, not production code)

| What | Where | Note |
|------|-------|------|
| `_FakeVault` | test files | Used extensively in tests |
| `_FakeApi` | desktop tests | Simulates API responses |
| `_FakeMission` | desktop tests | Simulates mission control data |
| `_FakeTransport` | desktop tests | Simulates HTTP transport |

### DEAD CODE (Exists but not part of any active flow)

| Component | Evidence |
|-----------|----------|
| `core/` twin tree (649 files) | Near-duplicate of `cores/` — scheduler only uses `core/scheduler/jobs.py` |
| `omega_archived_20260826/` | 20 files, explicitly archived |
| `desktop-legacy/` | 36 files, superseded by `desktop/native/` |
| `merlin_system.py` (root) | 33 symbols, no callers from active code |
| `OWNEX_OMEGA_DEMO.py` | Demo file, no production use |
| `self_evolution_engine.py` (root) | Self-evolution logic not wired into any loop |
| `self_update.py` (root) | 25 symbols, no active callers |
| `go.py` | CLI entry point, not used by scheduler |

### MISSING (Does not exist)

| Component | Impact |
|-----------|--------|
| **Real platform API submissions** | No adapter actually submits a report/PR/application via platform API |
| **Human control layer** | No LITE/ASSISTED/AUTONOMOUS/EXPERT modes |
| **Approval gates** | No approval workflow for external actions |
| **Work Quality Gate** | No universal quality check before delivery |
| **Daily Operating System** | No "TODAY" action list generation |
| **Artifact Store** | No unified storage for findings, reports, evidence, deliverables |
| **Cost Control** | No token/API cost tracking |
| **Model Router** | No intelligent model selection |
| **Cross-workflow Memory** | Memory exists but doesn't learn across workflows |
| **Self-Repair** | No crash recovery, stale job detection, or workflow resume |
| **Observability** | No structured logs, trace IDs, metrics |
| **Mobile Companion** | Android app has 16 files but no functional Companion |
| **Wear OS** | 7 files, no functional watch app |

---

## E. CURRENT SCORE

| Dimension | Score | Evidence |
|-----------|-------|----------|
| **Autonomy** | 25/100 | Scheduler runs, but execution layer is unwired. No real autonomous work. |
| **Reliability** | 35/100 | Tests pass (fast 100/1), but twin trees create import confusion. No crash recovery. |
| **Recovery** | 10/100 | No self-repair, no stale job detection, no workflow resume. |
| **Intelligence** | 40/100 | EVH scoring, calibration, predictive prioritizer exist. But no real learning loop from outcomes. |
| **Work Execution** | 15/100 | WorkerCore exists but executor wiring is incomplete. No real work has been executed. |
| **Human Guidance** | 5/100 | No approval gates, no autonomy levels, no human control layer. |
| **Storage** | 45/100 | SQLite DB, MemoryStore, ArtifactStore exists. But no unified artifact storage. |
| **Memory** | 35/100 | MemoryStore works, LearningEngine exists. But cross-workflow learning is absent. |
| **Revenue Readiness** | 20/100 | RevenueTracker exists, financial truth snapshot works. But zero real revenue. |
| **Security** | 40/100 | IdentityVault, SecretScanner, CSRF middleware. But no sandboxing, no audit logs. |
| **Desktop** | 50/100 | PySide6 + Tauri v2 functional. MSI/NSIS installers work. |
| **Mobile** | 10/100 | 16 Android files, no functional Companion. Wear OS is placeholder. |
| **UX/UI** | 30/100 | 279 Vue components, but 3 conceptual homes (Home, Dashboard, Mission Control). 1,073 hardcoded hex colors. |
| **Accessibility** | 5/100 | `useReducedMotion` composable exists. No ARIA, no keyboard nav, no screen reader support. |
| **Observability** | 10/100 | Basic logging. No structured logs, trace IDs, metrics, or dashboards. |
| **Extensibility** | 35/100 | Adapter pattern exists. But adding a new platform requires modifying core files. |
| **Cost Efficiency** | 5/100 | No token tracking, no API cost measurement, no ROI calculation per AI call. |
| **Testing** | 40/100 | 245 test files, 6,148 symbols. But many tests are contract tests, not integration tests. |
| **Future Proofing** | 25/100 | Architecture is flexible. But hardcoded platform lists and no plugin system. |
| **Daily Usability** | 15/100 | Dashboard shows data but doesn't answer "what should I do now?" |

### **GLOBAL SCORE: 24/100**

---

## F. GAP TO 100/100

### Critical Gaps (Must fix to reach 50/100)

1. **Twin Tree Consolidation** — core/ and cores/ must merge. Currently 1,796 files doing what 800 should.
2. **Execution Wiring** — WorkerCore → Executor → Platform API must be end-to-end.
3. **Human Control Layer** — LITE/ASSISTED/AUTONOMOUS/EXPERT modes with approval gates.
4. **Real Platform Integration** — At least ONE adapter must actually submit work via API.
5. **Daily Operating System** — "What should I do now?" with ranked actions.

### High Gaps (Must fix to reach 75/100)

6. **Work Quality Gate** — Universal quality check before delivery.
7. **Learning Loop** — Outcomes must feed back into scoring.
8. **Observability** — Structured logs, trace IDs, metrics.
9. **Cost Control** — Token/API cost tracking.
10. **Artifact Store** — Unified storage for all work products.
11. **Self-Repair** — Crash recovery, stale job detection.
12. **UX Consolidation** — Single navigation, no triple-home.

### Medium Gaps (Must fix to reach 100/100)

13. **Model Router** — Intelligent model selection by task/cost/quality.
14. **Cross-Workflow Memory** — Learn from ALL outcomes, not just current workflow.
15. **Mobile Companion** — Functional Android app.
16. **Wear OS** — Functional watch app.
17. **Plugin System** — Add platforms without modifying core.
18. **Accessibility** — ARIA, keyboard nav, screen reader.
19. **Offline Mode** — Service worker exists but not functional.
20. **Self-Optimization** — "Where should I invest my next 2 hours?"

---

## G. TARGET ARCHITECTURE

```
┌─────────────────────────────────────────────────────────────┐
│                    OWNEX v2.0 (Target)                       │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────────────────────────────────────────┐      │
│  │                 Presentation Layer                │      │
│  │  Frontend (Vue 3) · Desktop (Tauri v2) · Mobile   │      │
│  │  Single navigation · Work Room per opportunity     │      │
│  │  Daily Brief · Mission Control · Command Palette   │      │
│  └──────────────────────┬───────────────────────────┘      │
│                         │                                    │
│  ┌──────────────────────┴───────────────────────────┐      │
│  │              API Layer (FastAPI)                    │      │
│  │  REST + WebSocket · Auth · Rate Limiting            │      │
│  │  ~200 endpoints (consolidated from 1,539)           │      │
│  └──────────────────────┬───────────────────────────┘      │
│                         │                                    │
│  ┌──────────────────────┴───────────────────────────┐      │
│  │              Core Engine (single tree)              │      │
│  │                                                    │      │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐          │      │
│  │  │ Discovery │ │  Work    │ │ Execution│          │      │
│  │  │ Engine    │ │  Bank    │ │ Engine   │          │      │
│  │  │ (adapters)│ │ (scoring)│ │(WorkerCore│          │      │
│  │  └──────────┘ └──────────┘ │→Executor)│          │      │
│  │                             └──────────┘          │      │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐          │      │
│  │  │ Revenue   │ │ Memory   │ │ Learning │          │      │
│  │  │ Tracker   │ │ Store    │ │ Engine   │          │      │
│  │  │(PayoutRec)│ │(SQLite)  │ │(calibr.) │          │      │
│  │  └──────────┘ └──────────┘ └──────────┘          │      │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐          │      │
│  │  │ Human     │ │ Quality  │ │ Self-    │          │      │
│  │  │ Control   │ │ Gate     │ │ Repair   │          │      │
│  │  │(approval) │ │(validate)│ │(recover) │          │      │
│  │  └──────────┘ └──────────┘ └──────────┘          │      │
│  └──────────────────────────────────────────────────┘      │
│                                                              │
│  ┌──────────────────────────────────────────────────┐      │
│  │              Infrastructure                        │      │
│  │  Scheduler · EventBus · SecretsManager · DB        │      │
│  │  Observability · CostControl · ModelRouter          │      │
│  └──────────────────────────────────────────────────┘      │
└─────────────────────────────────────────────────────────────┘
```

---

## H. PRIORITY MATRIX

### P0 — CRITICAL (Revenue-blocking)

| # | Change | Files | Why |
|---|--------|-------|-----|
| 1 | **Consolidate twin trees** | core/ → cores/ | Cannot maintain two parallel codebases. Import confusion, bug duplication. |
| 2 | **Wire WorkerCore → real executor** | `cores/worker_core/orchestrator.py`, `cores/opportunity/executors/` | System cannot execute any work without this. |
| 3 | **Human control layer** | NEW `cores/human_control/` | Without approval gates, system cannot safely take external actions. |
| 4 | **Real API submission** (at least H1 or one dev bounty platform) | `cores/opportunity/executors/` adapters | Zero revenue without real submission. |
| 5 | **Daily Brief generator** | NEW `cores/daily_brief/` | System must answer "what do I do now?" |

### P1 — HIGH (Quality-blocking)

| # | Change | Files | Why |
|---|--------|-------|-----|
| 6 | **Work Quality Gate** | NEW `cores/quality_gate/` | Cannot deliver work without quality validation. |
| 7 | **Learning feedback loop** | `cores/direct_work_engine/calibration.py`, `cores/learning/` | Scoring never improves without real outcome data. |
| 8 | **Observability** | `cores/observability/` | Cannot debug or optimize without logs/metrics. |
| 9 | **Cost control** | NEW `cores/cost_control/` | Must track AI costs to calculate ROI. |
| 10 | **Self-repair** | `cores/recovery/` | System must recover from failures. |

### P2 — MEDIUM (UX-blocking)

| # | Change | Files | Why |
|---|--------|-------|-----|
| 11 | **UX consolidation** | Frontend navigation | Triple-home (Home/Dashboard/MissionConf) is confusing. |
| 12 | **Work Room** | Frontend | Each opportunity needs a dedicated workspace. |
| 13 | **Plugin system** | `cores/plugins/` | Adding platforms shouldn't require core changes. |
| 14 | **Artifact Store** | `cores/artifact_store/` | Unified storage for all work products. |

### P3 — NICE-TO-HAVE

| # | Change | Files | Why |
|---|--------|-------|-----|
| 15 | **Mobile Companion** | Android/ | Useful but not revenue-blocking. |
| 16 | **Wear OS** | Android/ | Useful but not revenue-blocking. |
| 17 | **Accessibility** | Frontend | Important but not revenue-blocking. |
| 18 | **Model Router** | NEW `cores/model_router/` | Optimization, not blocking. |
| 19 | **Offline Mode** | Frontend service worker | Useful but not blocking. |
| 20 | **Self-Optimization** | NEW `cores/self_optimizer/` | Advanced feature. |

---

## I. IMPLEMENTATION ROADMAP

### Phase 0: CONSOLIDATION (Week 1-2)
**Goal:** Single codebase, no twin trees, no dead code

```
Phase 0.1: Audit core/ vs cores/ — identify what's actually used
Phase 0.2: Merge critical paths (scheduler, opportunity, memory)
Phase 0.3: Delete dead code (omega_archived, desktop-legacy, root stubs)
Phase 0.4: Verify all imports work from single tree
Phase 0.5: Run full test suite, fix regressions
```

**Files affected:** ~500 files (merge/delete)
**Dependencies:** None
**Tests:** Full regression suite
**Risk:** HIGH — import breakage possible
**Acceptance:** `make check` passes, `import api.main` OK, no circular imports

### Phase 1: EXECUTION WIRING (Week 3-4)
**Goal:** WorkerCore can actually execute work through real executors

```
Phase 1.1: Wire WorkerCore._execute_work to real executors
Phase 1.2: Implement CoderAgent with LLM integration (Ollama/FCC Proxy)
Phase 1.3: Implement BrowserAgent with Playwright
Phase 1.4: Wire AutoSubmit → real platform APIs (start with GitHub PRs)
Phase 1.5: Add circuit breaker, retry, timeout to execution
```

**Files affected:** ~20 files
**Dependencies:** Phase 0 complete
**Tests:** E2E test: discover → execute → deliver (at least one platform)
**Risk:** MEDIUM — external API calls
**Acceptance:** Can submit a real GitHub PR via the system

### Phase 2: HUMAN CONTROL (Week 5-6)
**Goal:** Safe autonomous operation with approval gates

```
Phase 2.1: Define action risk levels (read/analyze/generate/execute/submit/transfer)
Phase 2.2: Implement LITE/ASSISTED/AUTONOMOUS/EXPERT modes
Phase 2.3: Add approval gates to all external actions
Phase 2.4: Implement notification system for approvals
Phase 2.5: Add audit log for all actions
```

**Files affected:** ~15 files
**Dependencies:** Phase 1 complete
**Tests:** Test each autonomy level, test approval flow
**Risk:** LOW — additive feature
**Acceptance:** System asks for approval before submitting work

### Phase 3: REVENUE LOOP (Week 7-8)
**Goal:** First real money flows through the system

```
Phase 3.1: Wire Discovery → Work Bank → Execute → Submit → Track
Phase 3.2: Implement Work Quality Gate (tests, lint, typecheck, security)
Phase 3.3: Add revenue tracking for real submissions
Phase 3.4: Implement learning feedback loop (outcome → scoring)
Phase 3.5: Generate first Daily Brief with ranked actions
```

**Files affected:** ~25 files
**Dependencies:** Phase 2 complete
**Tests:** E2E: discover opportunity → execute → submit → track revenue
**Risk:** MEDIUM — real external actions
**Acceptance:** Can discover, execute, submit, and track at least one opportunity end-to-end

### Phase 4: UX & DAILY OS (Week 9-10)
**Goal:** Usable interface that answers "what should I do now?"

```
Phase 4.1: Consolidate navigation (single sidebar, no triple-home)
Phase 4.2: Implement Daily Brief view
Phase 4.3: Implement Work Room per opportunity
Phase 4.4: Clean up hardcoded colors (Tesla design system)
Phase 4.5: Add loading/empty/error states
```

**Files affected:** ~50 frontend files
**Dependencies:** Phase 3 complete
**Tests:** Visual regression, accessibility audit
**Risk:** LOW — frontend only
**Acceptance:** User can open app → see Daily Brief → click action → execute

### Phase 5: LEARNING & OPTIMIZATION (Week 11-12)
**Goal:** System improves from real outcomes

```
Phase 5.1: Cross-workflow memory (learn from ALL outcomes)
Phase 5.2: Cost control (track AI costs per workflow)
Phase 5.3: Model router (select model by task/cost/quality)
Phase 5.4: Self-optimization ("where should I invest next?")
Phase 5.5: Self-repair (crash recovery, stale job detection)
```

**Files affected:** ~20 files
**Dependencies:** Phase 4 complete
**Tests:** Verify learning improves scoring over time
**Risk:** LOW — additive features
**Acceptance:** System recommends better opportunities after 10+ outcomes

---

## J. FILE-LEVEL PLAN

### Critical File Changes

```
FILE: core/ (entire directory)
CURRENT: 649 files, near-duplicate of cores/
CHANGE: Merge into cores/, delete core/ (keep only core/scheduler/jobs.py)
WHY: Twin trees violate One Source of Truth, create import confusion
DEPENDENCIES: All imports from core.* must be updated
TESTS: Full regression suite
RISK: HIGH

FILE: cores/worker_core/orchestrator.py
CURRENT: _execute_work has circuit breaker but no real executor wiring
CHANGE: Wire to real executors (CoderAgent, BrowserAgent, platform executors)
WHY: System cannot execute any work without this
DEPENDENCIES: CoderAgent, BrowserAgent must be implemented
TESTS: E2E execution test
RISK: MEDIUM

FILE: cores/opportunity/executors/ (all 5 files)
CURRENT: Platform executors exist but submit via API calls never tested
CHANGE: Implement real API submission for at least one platform
WHY: Zero revenue without real submission
DEPENDENCIES: Platform credentials, API documentation
TESTS: Integration test with real API (or sandbox)
RISK: MEDIUM

FILE: NEW cores/human_control/
CURRENT: Missing
CHANGE: Create approval gate system with LITE/ASSISTED/AUTONOMOUS/EXPERT modes
WHY: System cannot safely take external actions without human oversight
DEPENDENCIES: None
TESTS: Unit tests for each mode, approval flow test
RISK: LOW

FILE: NEW cores/daily_brief/
CURRENT: Missing
CHANGE: Create daily action generator with ranked opportunities
WHY: System must answer "what do I do now?"
DEPENDENCIES: Work Bank, Revenue Tracker, Learning Engine
TESTS: Unit test for brief generation
RISK: LOW

FILE: cores/direct_work_engine/calibration.py
CURRENT: JSONL predicho-vs-real exists but no feedback loop
CHANGE: Wire outcomes back into scoring (platform_factor, acceptance_rate)
WHY: Scoring never improves without real outcome data
DEPENDENCIES: Revenue Tracker must have real outcomes
TESTS: Verify scoring improves after 10+ outcomes
RISK: LOW
```

---

## K. TEST PLAN

### Phase 0 Tests
- [ ] `make check` passes with single tree
- [ ] No circular imports
- [ ] All existing tests pass (regression)
- [ ] Import test: `import api.main` OK

### Phase 1 Tests
- [ ] WorkerCore → executor wiring test
- [ ] CoderAgent generates code from prompt
- [ ] BrowserAgent navigates to URL
- [ ] AutoSubmit sends real API request (sandbox)
- [ ] Circuit breaker triggers on failure

### Phase 2 Tests
- [ ] LITE mode: all actions require approval
- [ ] ASSISTED mode: read/analyze auto, execute requires approval
- [ ] AUTONOMOUS mode: low-risk auto, high-risk requires approval
- [ ] EXPERT mode: all auto, audit log
- [ ] Approval notification sent
- [ ] Audit log records all actions

### Phase 3 Tests
- [ ] E2E: discover → execute → submit → track
- [ ] Quality Gate catches lint errors
- [ ] Quality Gate catches test failures
- [ ] Revenue tracking records real submission
- [ ] Learning feedback loop adjusts scoring

### Phase 4 Tests
- [ ] Daily Brief shows ranked actions
- [ ] Work Room shows opportunity details
- [ ] Navigation: single sidebar, no triple-home
- [ ] Loading states render
- [ ] Empty states render
- [ ] Error states render

### Phase 5 Tests
- [ ] Cross-workflow memory queries across workflows
- [ ] Cost control tracks AI token usage
- [ ] Model router selects by task/cost
- [ ] Self-repair recovers from crashed job
- [ ] Self-optimization recommends next action

---

## L. UX/UI PLAN

### Current State (Problems)
- 3 conceptual homes: Home, Dashboard, Mission Control
- 1,073 hardcoded hex colors (not Tesla design system)
- 279 Vue components (many duplicated)
- 83 pages (many overlapping)
- No single navigation hierarchy

### Target State
- **Single sidebar** with sections: Today, Work, Income, Intel, Settings
- **Daily Brief** = home screen (ranked actions with EV, probability, time estimate)
- **Work Room** = per-opportunity workspace (overview, requirements, execution, evidence, submission)
- **Mission Control** = system health dashboard
- **Command Palette** = Cmd+K search for everything

### Navigation Structure
```
Sidebar:
├── 🏠 Today (Daily Brief)
├── 💼 Work
│   ├── Work Bank
│   ├── Active Work
│   └── Completed
├── 💰 Income
│   ├── Revenue Tracker
│   ├── Payouts
│   └── Financial Truth
├── 🔍 Intel
│   ├── Opportunities
│   ├── Knowledge Graph
│   └── Market Intel
├── 🛡️ Security
│   ├── Findings
│   ├── Reports
│   └── Submissions
├── ⚙️ Settings
│   ├── Platforms
│   ├── Profile
│   └── System
```

### Pages to Eliminate
- Home (merge into Daily Brief)
- Dashboard (merge into Daily Brief)
- Classic (delete)
- Welcome (delete)
- Duplicate opportunity views (consolidate)

### Pages to Keep/Modify
- Mission Control → System Health (simplified)
- IncomeHome → Daily Brief (enhanced with actions)
- Work Bank → keep, enhance
- All Work Room pages → consolidate into Work Room

---

## M. REVENUE PLAN

### Stage 1: $0 → First Submission (Week 1-4)
- Wire execution layer to at least one platform
- Submit first real work (GitHub PR via dev bounty, or bug bounty report)
- Track submission in RevenueTracker

### Stage 2: First Revenue (Week 5-8)
- Accept/reject outcomes feed into calibration
- PayoutRecord updated with real payments
- Financial Truth snapshot shows real numbers

### Stage 3: Optimization (Week 9-12)
- Learning engine improves opportunity selection
- Cost control ensures positive ROI
- Model router optimizes AI spend

### Stage 4: Scale (Month 4+)
- Multiple platforms active
- Automated execution for low-risk work
- Human approval for high-value work
- Revenue per hour tracked and optimized

### Revenue Tracking Model
```
Opportunity → Expected Value (EVH × probability)
     ↓
Work → Human Hours + AI Hours + Cost
     ↓
Submission → Platform → Triage
     ↓
Outcome → Accepted/Rejected
     ↓
Payment → PayoutRecord → Financial Truth
     ↓
Learning → Calibration → Better Scoring
```

---

## N. AUTONOMY PLAN

### LITE Mode (Default for new users)
- System discovers and recommends
- Human does everything manually
- System tracks outcomes

### ASSISTED Mode
- System discovers, evaluates, prepares
- Human approves all external actions
- System executes after approval

### AUTONOMOUS Mode
- System executes low-risk actions (read, analyze, generate)
- Human approves medium-risk (submit PR, apply to platform)
- Human approves high-risk (financial transfers)

### EXPERT Mode
- System executes everything
- Audit log for review
- Human can override at any time

### Risk Classification
| Action | Risk | LITE | ASSISTED | AUTONOMOUS | EXPERT |
|--------|------|------|----------|------------|--------|
| Read API | Low | Auto | Auto | Auto | Auto |
| Analyze code | Low | Auto | Auto | Auto | Auto |
| Generate code | Medium | Manual | Manual | Auto | Auto |
| Run tests | Low | Manual | Auto | Auto | Auto |
| Create PR | Medium | Manual | Approve | Approve | Auto |
| Submit report | High | Manual | Approve | Approve | Auto |
| Apply to platform | High | Manual | Approve | Approve | Auto |
| Financial transfer | Critical | Manual | Manual | Manual | Approve |

---

## O. RISK REGISTER

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Twin tree merge breaks imports | High | High | Incremental merge, test after each step |
| Real API submission fails | Medium | High | Sandbox testing, circuit breaker, retry |
| Platform TOS violation | Low | Critical | Read-only first, manual approval for submissions |
| AI cost exceeds revenue | Medium | High | Cost control, budget limits, ROI tracking |
| Security breach (credentials) | Low | Critical | IdentityVault, SecretScanner, audit logs |
| Data loss | Low | High | SQLite backups, migration export/import |
| User overwhelm (too many features) | High | Medium | UX consolidation, Daily Brief, simplified nav |
| Flaky tests block CI | Medium | Medium | Pre-commit excludes known flaky tests |
| Desktop crash on Windows | Medium | High | Boot guard, init_db at module level, try/except |
| Scheduler stuck jobs | Medium | Medium | Stale job detection, timeout, circuit breaker |

---

## P. DEPRECATION PLAN

### DELETE (No longer needed)
- `omega_archived_20260826/` — archived, 20 files
- `desktop-legacy/` — superseded by `desktop/native/`, 36 files
- `merlin_system.py` (root) — no callers
- `OWNEX_OMEGA_DEMO.py` — demo file
- `self_evolution_engine.py` (root) — not wired
- `self_update.py` (root) — not wired
- `go.py` — CLI entry point, unused
- `OWNEX-Launcher.bat`, `OWNEX-Launcher.ps1` — replaced by Tauri
- `CATEYE.spec`, `ORION.spec` — old build specs

### MERGE (Consolidate)
- `core/` → `cores/` (entire tree, keep only `core/scheduler/jobs.py`)
- `core/opportunity/` → `cores/opportunity/` (merge adapters, executors)
- `core/credentials/` → `cores/credentials/` (merge with identity_vault)
- `core/events/` → `cores/events/` (merge event buses)
- `core/memory/` → `cores/memory/` (merge stores)

### KEEP (Active)
- `cores/` — canonical source
- `api/` — API layer
- `frontend/` — Vue frontend
- `desktop/native/` — PySide6 desktop
- `src-tauri/` — Tauri shell
- `tests/` — test suite
- `scripts/` — dev scripts
- `apps/` — Atlas, Forge, etc.
- `database/` — DB layer

### REFACTOR (Clean up)
- `api/routers/control.py` — 120 endpoints, split into focused routers
- `cores/direct_work_engine/` — 48 files, some overlap
- `cores/opportunity/` — 20 files, merge scoring

---

## Q. FINAL 100/100 CHECKLIST

### Discovery
- [ ] Real opportunity discovery from multiple platforms
- [ ] GitHub bounty-targets-data integration
- [ ] HackerOne/Bugcrowd/Intigriti/YesWeHack program discovery
- [ ] AI training platform discovery (Outlier, Mindrift, etc.)
- [ ] Freelance platform discovery (Fiverr, etc.)

### Evaluation
- [ ] EVH (Expected Value per Hour) scoring
- [ ] Barrier profile (entry difficulty)
- [ ] Confidence scoring (CONF-V1)
- [ ] Platform factor calibration
- [ ] Historical outcome data

### Skill Matching
- [ ] User skill profile
- [ ] Opportunity requirement extraction
- [ ] Skill gap analysis
- [ ] AI-assisted capability estimation
- [ ] Probability of completion

### Profile Optimization
- [ ] Multi-platform profile generation
- [ ] Cover letter / proposal generation
- [ ] Portfolio evidence assembly
- [ ] No credential fabrication

### WorkerCore
- [ ] Real executor wiring
- [ ] CoderAgent with LLM
- [ ] BrowserAgent with Playwright
- [ ] Platform executors (real API calls)
- [ ] Circuit breaker, retry, timeout

### Execution
- [ ] Code generation from issue description
- [ ] Test generation and validation
- [ ] PR creation and submission
- [ ] Report writing and submission
- [ ] Application filling and submission

### Validation
- [ ] Work Quality Gate (tests, lint, typecheck)
- [ ] Security scan (no secrets in output)
- [ ] Requirements coverage check
- [ ] Regression test
- [ ] Human review option

### Delivery
- [ ] Platform-specific submission format
- [ ] Idempotency keys
- [ ] Retry with backoff
- [ ] Delivery confirmation
- [ ] Submission tracking

### Approval Gates
- [ ] LITE mode (human does everything)
- [ ] ASSISTED mode (approve external actions)
- [ ] AUTONOMOUS mode (auto low-risk, approve high-risk)
- [ ] EXPERT mode (auto everything, audit log)
- [ ] Risk classification per action

### Revenue Tracking
- [ ] Expected Value tracking
- [ ] Committed Value tracking
- [ ] Earned Value tracking
- [ ] Pending Payment tracking
- [ ] Paid tracking
- [ ] Net Revenue (after fees/costs/FX)
- [ ] Revenue per platform
- [ ] Revenue per skill
- [ ] Revenue per hour

### Outcome Learning
- [ ] Calibration (predicted vs actual)
- [ ] Platform factor adjustment
- [ ] Category success rate tracking
- [ ] Time-to-payout tracking
- [ ] Cross-workflow learning

### Recovery
- [ ] Crash recovery
- [ ] Stale job detection
- [ ] Workflow resume from checkpoint
- [ ] Executor failure recovery
- [ ] API failure handling

### Self-Optimization
- [ ] "Where should I invest next 2 hours?"
- [ ] Historical success data
- [ ] Automation potential assessment
- [ ] Learning value assessment
- [ ] Payout delay consideration

### Daily OS
- [ ] Daily Brief with ranked actions
- [ ] Expected value per action
- [ ] Time estimate per action
- [ ] Probability per action
- [ ] Next button for each action

### UX/UI
- [ ] Single navigation hierarchy
- [ ] Daily Brief as home
- [ ] Work Room per opportunity
- [ ] Command Palette (Cmd+K)
- [ ] Loading states
- [ ] Empty states
- [ ] Error states
- [ ] Tesla design system (no arbitrary colors)

### Mobile
- [ ] Functional Companion app
- [ ] Dashboard view
- [ ] Approval notifications
- [ ] COPILOT chat
- [ ] System health

### Desktop
- [ ] PySide6 + Tauri v2 functional
- [ ] MSI/NSIS installers
- [ ] Auto-update
- [ ] System tray
- [ ] Offline mode

### Security
- [ ] IdentityVault for credentials
- [ ] SecretScanner
- [ ] CSRF protection
- [ ] Rate limiting
- [ ] Audit logs
- [ ] No secrets in logs/prompts/reports

### Testing
- [ ] Unit tests for all core modules
- [ ] Integration tests for all APIs
- [ ] E2E tests for critical flows
- [ ] Security tests
- [ ] Performance tests
- [ ] >80% coverage on critical paths

### Observability
- [ ] Structured logs
- [ ] Workflow IDs
- [ ] Execution traces
- [ ] Metrics (success rate, latency, cost)
- [ ] Revenue attribution

### Extensibility
- [ ] Plugin system for new platforms
- [ ] Adapter pattern for new sources
- [ ] Executor pattern for new work types
- [ ] No core changes for new platforms

### Cost Control
- [ ] Token usage tracking
- [ ] API cost tracking
- [ ] Local compute cost
- [ ] ROI per workflow
- [ ] Budget limits

### Future Proofing
- [ ] No hardcoded platform lists
- [ ] No hardcoded category enums
- [ ] Configurable discovery sources
- [ ] Pluggable executors
- [ ] Pluggable validators

---

## R. DEPRECATION SUMMARY

| Action | Count | Risk |
|--------|-------|------|
| DELETE files | ~100 | Low (archived/legacy) |
| MERGE directories | ~500 | High (import breakage) |
| REFACTOR files | ~30 | Medium |
| KEEP as-is | ~2,200 | None |

**Total files affected by consolidation:** ~630 (22% of codebase)
**Net result:** From 2,834 Python files → ~2,200 (22% reduction)

---

## S. REVENUE RULE COMPLIANCE

Every proposed feature evaluated against the Revenue Rule:

| Feature | Increases Detection? | Increases Evidence? | Increases Acceptance? | Increases Learning? | Verdict |
|---------|---------------------|--------------------|-----------------------|--------------------|---------| 
| Twin tree merge | No | No | No | No | **Architecture only — but BLOCKING** |
| Execution wiring | Yes (can execute) | Yes (can produce) | Yes (can submit) | Yes (outcomes) | ✅ CRITICAL |
| Human control | No | No | Yes (safe submission) | No | ✅ HIGH |
| Quality gate | No | Yes (better quality) | Yes (higher acceptance) | Yes (failure data) | ✅ HIGH |
| Daily Brief | Yes (better selection) | No | No | No | ✅ MEDIUM |
| Learning loop | No | No | No | Yes (calibration) | ✅ HIGH |
| Cost control | No | No | No | No | **Revenue protection** |
| UX consolidation | No | No | No | No | **Usability** |
| Mobile Companion | No | No | No | No | **Nice to have** |
| Wear OS | No | No | No | No | **Nice to have** |

**The critical path is: Execution Wiring → Quality Gate → Learning Loop → Revenue.**

Everything else is optimization or nice-to-have.

---

*End of Mega Audit. Generated by Codebuff 🤖*
