# OWNEX Roadmap

> **Revenue Rule:** No feature enters the roadmap unless it increases at least one of: vulnerability detection, evidence quality, acceptance probability, or system learning. No exceptions.

## Architecture Overview

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

## Work Cycles

| Cycle | Name | Status | Priority |
|-------|------|--------|----------|
| 🔵 | **Rastro** (Security) | ✅ Active — 24/7 Scheduling | **PHASE 1** |
| 🟣 | **Forge** (Dev Bounty) | ✅ Execution Layer — 8 adapters, 23 handlers | **PHASE 2.5 ✅** |
| ⚡ | **Pulse** (AI Work) | ✅ Execution Layer — executors ready | **PHASE 2.5 ✅** |
| 🛡️ | **Atlas** (System) | ✅ Health checks + Scheduler monitor | **PHASE 2.5 ✅** |
| 💰 | **Vault** (Wealth) | ✅ Backup + Revenue tracking | **PHASE 2.5 ✅** |
| 🟢 | **CoderAgent** (Dev) | ✅ 6 autonomous modules | **PHASE 2.5 ✅** |
| 🟡 | **Pulse Frontend** (AI Work) | ✅ Frontend Done | PHASE 2.1 ✅ |
| ⚪ | **Wealth Consolidation** | ⚠️ Partial | PHASE 4 |
| 🤖 | **Orion** (Coordinator) | ✅ Exists | Cross-cutting |

---

## Implementation Phases

### PHASE 0 — OWNEX Foundation ✅ COMPLETED
- [x] Branding + Design System (black/blue/white/gold)
- [x] SplashScreen, AppSidebar, OrionSidebar, MissionControl
- [x] Stable infra: Ollama (1 model), FCC (router), Hermes, OpenCode, Cline
- [x] Document memory in `.ai/`
- [x] **OWNEX_DESIGN_SYSTEM.md** — Complete Design System v1 documentation

### PHASE 1 — Mission Control v1 ⭐⭐⭐⭐⭐ ✅ COMPLETED

Create the central interface answering in 5 seconds: **"What opportunities exist today?"**

- [x] **Throughput Dashboard**: opportunities detected, prioritized, active cycles, pending tasks, recommended actions, agent status (`ThroughputCore.vue`, `WorkCyclesGrid.vue`)
- [x] **Agent Fleet**: simple view of each agent status (Hermes 🟢, OpenCode 🟢, Cline 🟢, Ollama 🟢, FCC 🟡) (`AgentFleet.vue`)
- [x] **Opportunity Engine v0**: opportunity data model (type, source, reward, difficulty, confidence, recommended_action) without external APIs yet (`OpportunityRadar.vue`, `DirectWorkRadar.vue`)
- [x] **Activity Timeline**: what happened, when, what's pending (`/api/activity` endpoint created in AUD-4)
- [x] **Command Palette** as primary navigation (Ctrl+K) (`CommandPalette.vue` exists)

**Target tests:** 20-25 new tests  
**Max new files:** 3-4

### PHASE 2 — Security Cycle v1 ⭐⭐⭐⭐⭐ ✅ COMPLETED

Migrate Rastro as first OWNEX Work Cycle. Don't create new, convert.

- [x] Pipeline E2E: Recon → Attack Surface → Hypothesis → Validation → Evidence → Report → Learning (AUD-2: `run_pipeline()` created, stages connected)
- [x] Executive Dashboard (CEO view): "Did we make money this week?" (AUD-6: frontend created in `/security/executive`)
- [x] Knowledge capture: every finding leaves learning metadata (AUD-3: persisted in DB via UnifiedMemoryStore)
- [x] Pipeline E2E working without manual intervention (scheduler connected: `advance_security_pipeline` calls `run_pipeline()` every 30min)

**Target tests:** 30-40 tests (reusing + extending existing Rastro)  
**Max new files:** 2-3 (adapters + wiring)

### PHASE 2.5 — Execution Layer (CRITICAL FOR REAL AUTONOMY) ⭐⭐⭐⭐⭐⭐ ✅ COMPLETED

**ABSOLUTE BLOCKER:** Without execution layer, OWNEX only discovers opportunities, does NOT execute them. Maximum priority.

- [x] **EXEC-1: AlgoraExecutor** — `claim_issue()` + `create_pr()` + `submit_pr()` (real API write, highest immediate ROI) ✅ **EXISTS**
- [x] **EXEC-2: FreelancerExecutor** — `bid_on_project()` + `submit_deliverable()` + `request_milestone_release()` ✅ **EXISTS**
- [x] **EXEC-3: BrowserAgent Base** — Playwright + login persistence + session management (unlocks LinkedIn, DataAnnotation, Outlier, Remotasks, Mindrift) ✅ **EXISTS**
- [x] **EXEC-4: AutonomousWorkflow Engine** — discover→select→plan→execute→learn unified loop ✅ **EXISTS**
- [x] **EXEC-5: Specialized CoderAgent** — **CRITICAL** write fix, tests, PR for real issues (force multiplier) ✅ **EXISTS** (`cores/autonomy/coder_agent.py` + 5 components: repo_analyzer, issue_analyzer, code_generator, test_runner, pr_builder)
- [x] **EXEC-6: OpireExecutor** — `claim_bounty()` + `submit_work()` (API write, 2nd highest ROI OSS) ✅ **EXISTS** (`cores/opportunity/executors/opire_executor.py`)
- [x] **EXEC-7: IssueHuntExecutor** — `claim_issue()` + `submit_pr()` (API write) ✅ **EXISTS** (`cores/opportunity/executors/issuehunt_executor.py`)
- [x] **EXEC-8: PlatformBrowserWorkers** — DataAnnotationWorker, OutlierWorker, MindriftBrowserWorker, RemotasksWorker ✅ **EXISTS** (`cores/opportunity/executors/platform_workers.py`)
- [x] **EXEC-9: Credentials Vault** — vault.py with backup + health.py with check_secrets_health ✅ **COMPLETED**
- [x] **EXEC-10: Scheduler Integration** — 27 jobs, 6 cycles (Security/Forge/Pulse/Vault/Atlas/DirectWork), E2E verified ✅ **COMPLETED (AUD-8)**

**Target tests:** 35-45 tests (unit + integration with real APIs)  
**Max new files:** 8 (executors 5 + browser 1 + workflow 1 + coder 1)  
**Strict budget:** 1 file per executor, 1 browser agent, 1 workflow, 1 coder = 8 files total

---

### PHASE 2.6 — CoderAgent (THE MISSING BRAIN) ⭐⭐⭐⭐⭐⭐⭐ ✅ COMPLETED

**Without CoderAgent, executors claim issues but nobody writes the code. It's the force multiplier.**

| Component | Responsibility | File |
|-----------|----------------|------|
| **RepoCloner** | Clone shallow, detect language/setup, run tests | `cores/autonomy/repo_analyzer.py` |
| **IssueAnalyzer** | Parse issue → extract bug/feature, reproduction steps, affected files | `cores/autonomy/issue_analyzer.py` |
| **CodeGenerator** | Write fix/patch based on analysis + repo context | `cores/autonomy/code_generator.py` |
| **TestRunner** | Execute test suite, capture failures, iterate fix | `cores/autonomy/test_runner.py` |
| **PRBuilder** | Create branch, commit, push, open PR with description | `cores/autonomy/pr_builder.py` |
| **CoderAgent** | Orchestrates all above end-to-end | `cores/autonomy/coder_agent.py` |

**New files: 6 (1 per component)**  
**Tests: 20-30 (unit + integration with real repos)**

### PHASE 3 — Opportunity Engine v1 ⭐⭐⭐⭐ ✅ COMPLETED
- [x] Scoring model: expected $ × (1 - difficulty) × acceptance prob. ✅ (`cores/opportunity/scoring2.py`)
- [x] Inputs: money, difficulty, time, competition, prior experience, history ✅
- [x] Output: top 5 opportunities for today ✅ (`cores/opportunity/engine.py`, `generate_recommendations`)
- [x] Integrate with existing TargetPrioritizer ✅
- [x] Feedback loop: accepted/rejected feeds score ✅ (`cores/opportunity/feedback.py`)
- [x] Tests ✅ (`tests/test_opportunity_feedback.py` — 10/10 pass)

### PHASE 4 — Work Cycle Expansion ⭐⭐⭐⭐ ✅ COMPLETED

Only after Security Cycle works E2E without intervention.

- [x] **Forge Adapter**: Superteam Earn, Opire ✅ (already implemented in `cores/opportunity/adapters/forge/`)
- [x] **Pulse Adapter**: Outlier, DataAnnotation, Mindrift ✅ (7 adapters in `cores/opportunity/adapters/pulse/`)
- [x] **Wealth Consolidation**: CoinGecko + Firefly III dashboard ✅ (adapters registered in registry)

### PHASE 4.5 — Revenue Maximization Tools ⭐⭐⭐⭐⭐ ✅ COMPLETED

Critical tools to triple revenue capacity.

- [x] **CoderAgent E2E Integration**: BountyPipeline with 7 phases (Clone → Analyze → Generate → Test → PR → Claim → Submit) ✅
- [x] **BrowserAgent Automation**: Real workers for DataAnnotation/Outlier with login/fetch/submit ✅
- [x] **Multi-Agent Coordinator**: Parallelization of 3-5 simultaneous bounties with EVH queue ✅
- [x] **Auto-Submission Pipeline**: Elite quality gate + manual/automatic approvals ✅
- [x] **Credential Vault Automation**: Auto-rotation of API keys (90 days max) + alerts ✅
- [x] **Mobile Companion Approvals**: Unified namespace + WebSocket push notifications ✅
- [x] **Voice Assistant Integration**: Voice commands for executors ✅

**Impact:** $400-$2,800/mo → $10,000-$20,000/mo (~10x multiplier)

### PHASE 5 — Automation ⭐⭐⭐⭐⭐
- [ ] Autonomous decision: local vs FCC based on task?
- [ ] Auto-submission pipeline (Finding → Evidence → Report → Submit → Payout)
- [ ] Independent agents per cycle with multi-agent coordinator

### PHASE 6 — Tauri Desktop + Android Companion ⭐⭐⭐⭐
- [ ] Tauri + Vue 3 build (OWNEX.exe)
- [ ] Python backend as sidecar
- [ ] Android Companion app (notifications, approvals, metrics, wallet, agent status)
- [ ] WebView / WebSocket synchronization

---

## Architecture Budget (per feature)
- Maximum: 2 new files, 1 dependency, 1 event, 1 capability, 1 contract, 20 tests
- If it needs more → the feature is poorly designed

---

## Revenue Rule Priorities

| Question | Current Answer |
|----------|----------------|
| What increases detection? | Mission Control v1 → Opportunity Engine |
| What reduces false positives? | Security Cycle v1 → Knowledge Engine |
| What improves acceptance? | Report Optimizer → Acceptance Intelligence |
| What improves learning? | Knowledge Engine → Evolution Engine |
| What improves autonomy? | Agent Fleet → Multi-agent Coordinator |
| What improves Expected Revenue? | Opportunity Score Engine |
| What only improves architecture? | ❌ AVOID — doesn't enter sprint |

---

## Current Sprint: PHASE 1 — Mission Control v1

| Task | Status | Tests | Owner |
|------|--------|-------|-------|
| Throughput Dashboard | ⏳ Pending | 8-10 | Frontend |
| Agent Fleet View | ⏳ Pending | 4-5 | Frontend |
| Opportunity Engine v0 (Data Model) | ⏳ Pending | 6-8 | Backend |
| Activity Timeline | ⏳ Pending | 3-4 | Frontend |
| Command Palette as Primary Nav | ⏳ Pending | 4-5 | Frontend |

---

## References
- `.ai/OWNEX_ARCHITECTURE.md` — 4 layers, 3 engines, work cycles
- `.ai/OWNEX_DESIGN_SYSTEM.md` — Complete Design System v1
- `.ai/OWNEX_MISSION_CONTROL_SPEC.md` — Detailed Mission Control spec
- `.ai/TASK_QUEUE.md` — Prioritized task queue
- `.ai/CURRENT_STATE.md` — Current verified state
- `.ai/STRATEGIC_AUDIT.md` — Strategic audit framework (10 questions + 18 dimensions)