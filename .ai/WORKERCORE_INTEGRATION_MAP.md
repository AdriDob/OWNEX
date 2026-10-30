# WorkerCore Integration Map

> TASK 01 Output — Read-only audit of all component interfaces
> Date: 2026-09-01

## Executive Summary

**WorkerCore is REAL and CONNECTED.** The orchestrator has a complete 8-phase loop with real engine integrations. The main gap is SkillEngine not being wired into the PREPARE phase.

| Component | Status | Connected to WorkerCore |
|-----------|--------|------------------------|
| WorkerCore | ✅ REAL | — (orchestrator) |
| UniversalDiscovery | ✅ REAL | ✅ YES |
| DirectWorkEvaluationEngine | ✅ REAL | ✅ YES |
| DirectWorkExecutionEngine | ✅ REAL | ✅ YES |
| DirectWorkDeliveryEngine | ✅ REAL | ✅ YES |
| DirectWorkLearningEngine | ✅ REAL | ✅ YES |
| SkillEngine | ✅ REAL | ❌ NOT CONNECTED |
| Checkpoint Persistence | ✅ REAL | ✅ YES |
| Human Gate | ✅ REAL | ✅ YES |
| Autonomy Levels | ✅ REAL | ✅ YES |

---

## 1. WorkerCore (Orchestrator)

**File:** `cores/worker_core/orchestrator.py`
**Class:** `WorkerCore`
**Status:** ✅ REAL — Full implementation

### Loop
```
DISCOVER → EVALUATE → SELECT → PREPARE → EXECUTE → VALIDATE → DELIVER → LEARN
```

### Public Methods
| Method | Input | Output | Status |
|--------|-------|--------|--------|
| `start()` | — | — | ✅ REAL |
| `stop()` | — | — | ✅ REAL |
| `pause()` | — | — | ✅ REAL |
| `resume()` | — | — | ✅ REAL |
| `set_goal(goal: WorkGoal)` | WorkGoal | — | ✅ REAL |
| `set_discovery_engine(engine)` | Any | — | ✅ REAL |
| `set_evaluation_engine(engine)` | Any | — | ✅ REAL |
| `set_execution_engine(engine)` | Any | — | ✅ REAL |
| `set_delivery_engine(engine)` | Any | — | ✅ REAL |
| `set_learning_engine(engine)` | Any | — | ✅ REAL |
| `connect_real_engines()` | — | — | ✅ REAL |
| `get_status()` | — | dict | ✅ REAL |
| `approve_work(work_id)` | str | bool | ✅ REAL |
| `reject_work(work_id, reason)` | str, str | bool | ✅ REAL |
| `check_human_gate(work_item, action)` | WorkItem, str | (bool, str) | ✅ REAL |
| `requires_human_approval(action)` | str | bool | ✅ REAL |
| `resume_open_work_items()` | — | list[tuple[str,str]] | ✅ REAL |
| `execute_ai_task(task_type, messages, ...)` | str, list, ... | dict | ✅ REAL |

### Internal Phases
| Phase | Method | Delegates to | Status |
|-------|--------|--------------|--------|
| DISCOVER | `_discover_work()` | `_discovery_engine.discover_all()` | ✅ REAL |
| EVALUATE | `_evaluate_work()` | `_evaluation_engine.evaluate()` | ✅ REAL |
| SELECT | (inline) | — | ✅ REAL |
| PREPARE | `_prepare_work()` | (basic) | ⚠️ PARTIAL |
| EXECUTE | `_execute_work()` | `_execution_engine.execute()` | ✅ REAL |
| VALIDATE | `_validate_work()` | `_evaluation_engine.evaluate()` (quality gate) | ✅ REAL |
| DELIVER | `_deliver_work()` | `_delivery_engine.deliver()` | ✅ REAL |
| LEARN | `_learn_from_work()` | `_learning_engine.learn()` | ✅ REAL |

---

## 2. UniversalDiscovery

**File:** `cores/direct_work_engine/discovery.py`
**Class:** `UniversalDiscovery`
**Status:** ✅ REAL

### Interface
```python
async def discover_all(
    categories: list[OpportunityCategory] | None = None,
    platforms: list[WorkPlatform] | None = None,
) -> list[Opportunity]
```

### Input
- `categories`: Optional filter by category enum
- `platforms`: Optional filter by platform enum

### Output
- `list[Opportunity]` — Each Opportunity has: id, title, platform, category, payment, estimated_time_hours, difficulty, experience_required, etc.

### Dependencies
- `BaseDiscoveryAdapter` (abstract) — platform-specific adapters
- `DiscoverySource` — source configuration

### Callers
- WorkerCore `_discover_work()` ✅
- DirectWorkEngine `discover_all()` ✅

### Tests
- `tests/test_direct_work_engine.py` ✅

---

## 3. DirectWorkEvaluationEngine

**File:** `cores/direct_work_engine/evaluation.py`
**Class:** `DirectWorkEvaluationEngine`
**Status:** ✅ REAL

### Interface
```python
def evaluate(self, work_item: Any, profile: Any = None) -> dict[str, Any]
```

### Input
- `work_item`: WorkItem or Opportunity with attributes
- `profile`: Optional UserProfile

### Output
```python
{
    "passed": bool,
    "score": float,
    "reasons": list[str],
    "barrier_score": float,
    "expected_value_usd_per_hour": float,
    "acceptance_probability": float,
    "compatibility_score": float,
    "speed_score": float,
    "reputation_score": float,
    "risk_score": float,
    "strict_filter_rejected": bool,
    "strict_filter_reasons": list[str],
    "quality_gate_result": {"passed": bool, "reason": str}
}
```

### Dependencies
- `ZeroBarrierScorer` — scores opportunities
- `IntelligentRecommender` — ranks by recommendation
- `StrictFilter` — hard rejects
- `IntelligentProfileBuilder` — builds user profile

### Callers
- WorkerCore `_evaluate_work()` ✅
- WorkerCore `_validate_work()` (quality gate) ✅

### Tests
- `tests/test_direct_work_engine.py` ✅

---

## 4. DirectWorkExecutionEngine

**File:** `cores/direct_work_engine/execution.py`
**Class:** `DirectWorkExecutionEngine`
**Status:** ✅ REAL

### Interface
```python
def execute(self, work_item: Any, profile: Any = None) -> dict[str, Any]
```

### Input
- `work_item`: WorkItem with platform, category, title, description
- `profile`: Optional UserProfile

### Output
```python
{
    "success": bool,
    "artifacts": list[str],
    "evidence": list[str],
    "output": str,
    "error": str | None,
    "execution_time_s": float
}
```

### Execution Strategy
1. `_is_coding_task()` → CoderAgent
2. `_is_browser_task()` → BrowserAgent
3. `_is_desktop_task()` → ComputerUseTool
4. Platform executor → registered handler
5. Generic fallback → prepared for manual

### Dependencies
- `CoderAgent` (optional)
- `BrowserAgent` (optional)
- `ComputerUseTool` (optional)
- Platform executors (optional)

### Callers
- WorkerCore `_execute_work()` ✅

### Tests
- `tests/test_direct_work_engine.py` ✅

---

## 5. DirectWorkDeliveryEngine

**File:** `cores/direct_work_engine/delivery.py`
**Class:** `DirectWorkDeliveryEngine`
**Status:** ✅ REAL

### Interface
```python
def deliver(self, work_item: Any, approved_by_human: bool = True) -> dict[str, Any]
```

### Input
- `work_item`: WorkItem to deliver
- `approved_by_human`: Must be True for delivery

### Output
```python
{
    "success": bool,
    "submission_id": str | None,
    "submission_url": str | None,
    "platform_response": dict,
    "error": str | None
}
```

### Delivery Strategy
1. AutoSubmit (if available)
2. Platform-specific handler
3. Manual delivery package

### Dependencies
- `AutoSubmitEngine` (optional)
- Platform handlers (optional)

### Callers
- WorkerCore `_deliver_work()` ✅

### Tests
- `tests/test_direct_work_engine.py` ✅

---

## 6. DirectWorkLearningEngine

**File:** `cores/direct_work_engine/learning.py`
**Class:** `DirectWorkLearningEngine`
**Status:** ✅ REAL

### Interface
```python
def learn(self, work_item: Any, outcome: str, details: dict[str, Any] | None = None) -> dict[str, Any]
```

### Input
- `work_item`: Completed work item
- `outcome`: "completed", "failed", "accepted", "paid", etc.
- `details`: Optional additional info

### Output
```python
{
    "success": bool,
    "lessons": list[str],
    "skill_updates": dict[str, float],
    "platform_updates": dict[str, float],
    "category_updates": dict[str, float],
    "error": str | None
}
```

### Dependencies
- `RevenueTracker` (optional) — for verified outcomes
- `build_history_from_revenue_tracker()` — builds learning records
- `apply_learning()` — applies updates

### Callers
- WorkerCore `_learn_from_work()` ✅

### Tests
- `tests/test_direct_work_engine.py` ✅

---

## 7. SkillEngine

**File:** `cores/worker_core/skill_engine.py`
**Class:** `SkillEngine`
**Status:** ✅ REAL — NOT CONNECTED TO WORKERCORE

### Interface
```python
def analyze(self, work_item: Any, user_profile: UserProfile) -> SkillAnalysisResult
```

### Input
- `work_item`: WorkItem with opportunity info
- `user_profile`: UserProfile with skills

### Output
```python
SkillAnalysisResult(
    work_item_id: str,
    opportunity_id: str,
    skill_gap_report: SkillGapReport | None,
    profile_assets: ProfileAssets | None,
    optimized_profile: UserProfile | None,
    readiness_score: float,
    can_execute: bool,
    missing_critical_skills: list[str]
)
```

### Dependencies
- `SkillAmplifier` — analyzes skill gaps
- `IntelligentProfileBuilder` — builds profile assets

### Callers
- ❌ NOT CONNECTED — should be called in WorkerCore PREPARE phase

### Tests
- `tests/test_direct_work_engine.py` (partial)

---

## 8. Checkpoint Persistence

**File:** `cores/worker_core/persistence.py`
**Status:** ✅ REAL

### Interface
```python
def save_checkpoint(work_item_id, phase, data, ...) -> None
def get_latest_checkpoint(work_item_id) -> WorkerCheckpoint | None
def get_all_checkpoints(work_item_id) -> list[WorkerCheckpoint]
def get_active_work_items() -> list[str]
def resume_from(checkpoint) -> str | None
def checkpoint_data_dict(checkpoint) -> dict | None
```

### Database Model
- `WorkerCheckpoint` in `database/models.py`
- Fields: work_item_id, work_item_title, work_item_platform, work_item_category, phase, checkpoint_data (JSON), phase_completed, error, retry_count

### Callers
- WorkerCore `_persist_one_checkpoint()` ✅
- WorkerCore `resume_open_work_items()` ✅
- WorkerCore `_rehydrate_work_item()` ✅

### Tests
- `tests/test_worker_core.py` ✅

---

## 9. Models

### WorkItem (worker_core/models.py)
```python
@dataclass
class WorkItem:
    id: str
    goal_id: str
    opportunity_id: str
    title: str
    description: str
    platform: str
    category: str
    estimated_reward_usd: float
    estimated_hours: float
    risk_score: float
    acceptance_probability: float
    expected_value_usd_per_hour: float
    phase: WorkPhase
    state: WorkState
    checkpoints: list[dict]
    artifacts: list[str]
    evidence: list[str]
    error: str | None
    human_action_required: bool
    human_action_description: str
    approved_by_human: bool
```

### Opportunity (direct_work_engine/models.py)
```python
@dataclass
class Opportunity:
    id: str
    title: str
    platform: WorkPlatform
    category: OpportunityCategory
    url: str
    description: str
    payment: float
    currency: str
    estimated_time_hours: float
    difficulty: DifficultyLevel
    experience_required: ExperienceLevel
    # ... 30+ fields
```

### WorkPhase Enum
```python
IDLE → DISCOVER → EVALUATE → SELECT → PREPARE → EXECUTE → VALIDATE → DELIVER → LEARN
```

### WorkState Enum
```python
STOPPED | RUNNING | PAUSED | DEGRADED | ERROR | IDLE
```

### AutonomyLevel Enum
```python
NONE → DISCOVER → PREPARE → EXECUTE → FULL
```

---

## 10. Gaps Found

### Gap 1: SkillEngine Not Connected
- **Impact:** PREPARE phase doesn't analyze skill gaps
- **Fix:** Wire SkillEngine into WorkerCore `_prepare_work()`
- **Effort:** Small (10 lines)

### Gap 2: connect_real_engines() May Not Be Called
- **Impact:** Engines might not be connected on startup
- **Fix:** Verify call in `api/main.py` or startup sequence
- **Effort:** Small (verify)

### Gap 3: Quality Gate Could Be More Robust
- **Impact:** Currently only checks evidence existence
- **Fix:** Add lint/typecheck/security checks
- **Effort:** Medium

### Gap 4: No Cost Tracking Integration
- **Impact:** `execute_ai_task()` has cost tracker but main loop doesn't
- **Fix:** Wire cost tracker into main loop
- **Effort:** Small

---

## 11. Integration Map (Visual)

```
┌─────────────────────────────────────────────────────────────┐
│                      WorkerCore                              │
│                    (orchestrator.py)                          │
│                                                              │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │ DISCOVER │→ │ EVALUATE │→ │  SELECT  │→ │ PREPARE  │   │
│  └────┬─────┘  └────┬─────┘  └──────────┘  └────┬─────┘   │
│       │              │                            │          │
│       ▼              ▼                            ▼          │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │Universal │  │DirectWork│  │          │  │  Skill   │   │
│  │Discovery │  │Evaluation│  │          │  │  Engine  │   │
│  └──────────┘  └──────────┘  │          │  └──────────┘   │
│                               │          │                   │
│  ┌──────────┐  ┌──────────┐  │          │  ┌──────────┐   │
│  │ EXECUTE  │→ │ VALIDATE │→ │ DELIVER  │→ │  LEARN   │   │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘   │
│       │              │             │              │          │
│       ▼              ▼             ▼              ▼          │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │DirectWork│  │Quality   │  │DirectWork│  │DirectWork│   │
│  │Execution │  │Gate      │  │Delivery  │  │Learning  │   │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘   │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │              Checkpoint Persistence                    │   │
│  │         (SQLite worker_checkpoints table)             │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │              Human Gate + Autonomy Levels              │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

---

## 12. Recommendations for TASK 02+

### TASK 02: Define Contracts
- Use existing models (WorkItem, Opportunity, EvaluationResult, etc.)
- Add Protocol classes for type safety
- Don't create new abstractions — extend existing ones

### TASK 03: Connect Discovery
- Already connected! Verify `connect_real_engines()` is called
- Add tests for the full discovery → WorkItem flow

### TASK 04: Connect Evaluation
- Already connected! Quality gate exists
- Enhance gate with lint/typecheck/security checks

### TASK 05: Quality Gate
- Gate exists in `_validate_work()`
- Add more checks (lint, typecheck, security)
- Add tests proving gate blocks delivery

### TASK 06: Checkpoints
- Already implemented! `save_checkpoint()`, `resume_from()`
- Add crash simulation test

### TASK 07: E2E Test
- Create `tests/integration/test_worker_core_full_cycle_e2e.py`
- Use real engines, minimal mocks
