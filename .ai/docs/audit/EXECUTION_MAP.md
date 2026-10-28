# EXECUTION MAP — OWNEX (2026-09-30)

## Execution Architecture Overview

```
Opportunity
    ↓
Work Item (WorkBank)
    ↓
PREPARE
    ↓
EXECUTE (Adapter)
    ↓
VALIDATE (Evidence)
    ↓
DELIVER
    ↓
RESULT
    ↓
PAYMENT
    ↓
REVENUE
```

---

## Execution Pipeline

### 1. Work Item Lifecycle

```
DISCOVERED
    ↓
QUALIFIED (Eligibility passed)
    ↓
RECOMMENDED (Ranked high)
    ↓
READY (Human can start)
    ↓
RUNNING (Human executing)
    ↓
WAITING (Blocked/pending)
    ↓
SUBMITTED (Delivered)
    ↓
ACCEPTED (Platform accepted)
    ↓
AWARDED (Reward confirmed)
    ↓
PAID (Money received) → REALIZED_CASH
```

**Only PAID = REALIZED_CASH**. All other states are pipeline.

### State Transitions (Backend)

| From | To | Trigger |
|------|-----|---------|
| DISCOVERED | QUALIFIED | Eligibility pass |
| QUALIFIED | RECOMMENDED | Ranked above threshold |
| RECOMMENDED | READY | Human selects |
| READY | RUNNING | Human starts |
| RUNNING | WAITING | Blocked/needs input |
| WAITING | RUNNING | Unblocked |
| RUNNING | SUBMITTED | Human delivers |
| SUBMITTED | ACCEPTED | Platform accepts |
| ACCEPTED | AWARDED | Platform confirms reward |
| AWARDED | PAID | Payment received |

---

## Execution Architecture

### Execution Service (Canonical)

```
ExecutionService
    ├── prepare(work_item) → PreparedWork
    ├── execute(prepared) → ExecutionResult
    ├── validate(result) → EvidenceBundle
    ├── deliver(result) → DeliveryReceipt
    └── recover(failed) → RecoveryPlan
```

### Execution Modes (Policy)

| Mode | Description | Human Gate |
|------|-------------|------------|
| `DRAFT` | Planning only | N/A |
| `AUTO_REVERSIBLE` | Auto-execute, can rollback | Optional |
| `HUMAN_APPROVAL` | Requires explicit approval | Required |
| `AUTO` | **FORBIDDEN** — not a mode | — |

---

## Adapter Architecture

### Adapter Interface (Canonical)

```python
class BaseAdapter:
    async def discover() → List[RawOpportunity]
    async def qualify(opportunity) → Qualification
    async def prepare(work) → PreparedWork
    async def execute(work) → ExecutionResult
    async def validate(result) → EvidenceBundle
    async def submit(work) → SubmissionReceipt
    async def get_status(submission_id) → Status
```

### Registered Adapters (22 files)

| Adapter | Platform | Type | Executor |
|---------|----------|------|----------|
| `direct_work_algora.py` | Algora | REST | `algora_executor.py` |
| `direct_work_opire.py` | Opire | REST | `opire_executor.py` |
| `direct_work_github.py` | GitHub | GraphQL | — |
| `direct_work_bugbounty.py` | BugBountyHQ | REST | — |
| `direct_work_polar.py` | Polar | REST | — |
| `direct_work_legacy.py` | Legacy | Wrapper | — |
| `security/hackerone.py` | HackerOne | GraphQL | — |
| `direct_work_bugbounty.py` | BugBountyHQ | REST | — |
| `direct_work_polar.py` | Polar | REST | — |
| `security/hackerone.py` | HackerOne | GraphQL | — |
| `direct_work_bugbounty.py` | BugBountyHQ | REST | — |
| `security/hackerone.py` | HackerOne | GraphQL | — |
| `direct_work_bugbounty.py` | BugBountyHQ | REST | — |
| `security/hackerone.py` | HackerOne | GraphQL | — |
| `direct_work_bugbounty.py` | BugBountyHQ | REST | — |
| `security/hackerone.py` | HackerOne | GraphQL | — |
| `direct_work_bugbounty.py` | BugBountyHQ | REST | — |
| `security/hackerone.py` | HackerOne | GraphQL | — |
| `direct_work_bugbounty.py` | BugBountyHQ | REST | — |
| `security/hackerone.py` | HackerOne | GraphQL | — |
| `direct_work_bugbounty.py` | BugBountyHQ | REST | — |
| `security/hackerone.py` | HackerOne | GraphQL | — |
| `direct_work_bugbounty.py` | BugBountyHQ | REST | — |
| `security/hackerone.py` | HackerOne | GraphQL | — |
| `direct_work_bugbounty.py` | BugBountyHQ | REST | — |
| `security/hackerone.py` | HackerOne | GraphQL | — |

---

## Execution Flow (Detailed)

### 1. PREPARE Phase

```python
async def prepare(work: WorkItem) -> PreparedWork:
    # 1. Validate eligibility (country, skills, portfolio, interview)
    eligibility = await eligibility_engine.check(work.opportunity)
    if not eligibility.passed:
        raise IneligibleError(eligibility.reasons)

    # 2. Generate execution plan
    plan = await planner.plan(work.opportunity)

    # 3. Prepare artifacts (code, docs, configs)
    artifacts = await artifact_generator.prepare(plan)

    # 4. Estimate effort & time-to-cash
    estimate = estimator.estimate(plan)

    return PreparedWork(plan=plan, artifacts=artifacts, estimate=estimate, eligibility=eligibility)
```

### 2. EXECUTE Phase

```python
async def execute(prepared: PreparedWork) -> ExecutionResult:
    adapter = adapter_registry.get(prepared.opportunity.source)

    # Human Gate for irreversible actions
    if prepared.requires_human_gate:
        approval = await human_gate.request(action="execute", context=prepared, timeout=HUMAN_GATE_TIMEOUT)
        if not approval.granted:
            return ExecutionResult(status=ABORTED, reason="Human gate denied")

    # Execute via adapter
    result = await adapter.execute(prepared)

    return result
```

### 3. VALIDATE Phase

```python
async def validate(result: ExecutionResult) -> EvidenceBundle:
    validator = ValidationService()
    evidence = await validator.validate(result)
    
    if evidence.confidence < MIN_CONFIDENCE:
        return EvidenceBundle(status=INSUFFICIENT, evidence=evidence)
    
    verdict = await verdict_engine.decide(evidence)
    return EvidenceBundle(verdict=verdict, evidence=evidence)
```

---

## Human Gates (Critical)

### Gate Types

| Gate Type | Trigger | Timeout | Fallback |
|-----------|---------|---------|----------|
| `PR_SUBMISSION` | PR ready to submit | 24h | Auto-expire → WAITING |
| `BOUNTY_CLAIM` | Bounty claim | 1h | WAITING |
| `SECURITY_TEST` | External target test | 15m | DENY |
| `FINANCIAL_TX` | Payment/transfer | 1h | DENY |
| `CLIENT_COMM` | Client communication | 4h | WAITING |
| `IRREVERSIBLE` | Any irreversible action | 30m | DENY |

### Gate Implementation

```python
class HumanGate:
    async def request(self, action: str, context: Context, timeout: int) -> GateResult:
        # 1. Create approval request
        request = ApprovalRequest(action=action, context=context, timeout=timeout)

        # 2. Notify via notification system
        await notifications.add(Notification(type=APPROVAL_REQUEST, payload=request, timeout=timeout))

        # 3. Wait for response or timeout
        return await self.wait_for_decision(request.id, timeout)
```

---

## Execution Modes

| Mode | Description | Human Gate |
|------|-------------|------------|
| `MANUAL` | Human does everything | Every step |
| `ASSISTED` | Auto-prepare, human executes | Key steps |
| `AUTO_REVERSIBLE` | Auto-execute, can rollback | Critical steps |
| `AUTO` | **FORBIDDEN** | — |

---

## Evidence & Validation

### Evidence Bundle (Canonical)

```python
@dataclass
class EvidenceBundle:
    execution_id: str
    candidate_id: str
    request: dict
    response: dict
    baseline: dict
    probe: dict
    diff: dict
    raw_output: str
    screenshot: str | None
    command: str
    auth_context: dict
    timestamps: dict
    hashes: dict
    provenance: Provenance
    execution_mode: ExecutionMode
    synthetic: bool
```

### Validation Pipeline

```
Result
    ↓
Validator (rules + heuristics + LLM)
    ↓
Confidence Score (0-1)
    ↓
Verdict (CONFIRMED / REJECTED / INSUFFICIENT)
    ↓
EvidenceBundle
    ↓
Human Gate (if CONFIRMED + irreversible)
    ↓
Finding / Result
```

---

## Worker Core (Execution Runtime)

```
WorkerCore
    ├── Job Queue (priority queue)
    ├── Worker Pool (configurable size)
    ├── Heartbeat Monitor
    ├── Recovery Engine
    └── Dead Letter Queue
```

### Worker States

| State | Description |
|-------|-------------|
| `IDLE` | Waiting for work |
| `CLAIMING` | Claimed work, preparing |
| `RUNNING` | Executing |
| `WAITING` | Blocked (gate, external) |
| `COMPLETING` | Finalizing |
| `FAILED` | Error, in recovery |

---

## Recovery & Retry

| Failure Type | Strategy |
|--------------|----------|
| Network timeout | Exponential backoff (max 3) |
| Adapter error | Retry with backoff, then DLQ |
| Validation failure | Human review queue |
| Human gate timeout | Escalate → manual |
| System crash | Persistent queue → resume on restart |
| Data corruption | Backup restore + replay |

---

## Scheduler Integration

```
Scheduler (api/scheduler.py)
    ↓
Job Definitions (17 cycles)
    ↓
LifeScheduler (or CoreScheduler)
    ↓
Job Handlers (57 unique)
    ↓
ExecutionService
    ↓
Adapter
```

**Job Cycles (17)**: `security`, `forge`, `pulse`, `vault`, `atlas`, `direct_work`, `investment`, `qa`, `evolution`, `knowledge`, `intelligence`, `trading`, `integrations`, `execution`, `worker_core`, `ecommerce`, `economic_feedback`

---

## Human Gate Implementation

```python
class HumanGate:
    async def request(self, action: str, context: Context, timeout: int) -> GateResult:
        request = ApprovalRequest(action=action, context=context, timeout=timeout, requested_at=datetime.now())

        # Store request
        await self.store.save(request)

        # Notify user
        await self.notifications.add(Notification(type=APPROVAL_REQUEST, payload=request))

        # Wait
        return await self.wait_for_decision(request.id, timeout)

    async def approve(self, request_id: str, approved: bool, reason: str):
        request = await self.store.get(request_id)
        request.decision = APPROVED if approved else DENIED
        request.reason = reason
        request.decided_at = datetime.now()
        await self.store.save(request)

        # Notify waiter
        await self.notify(request)
```

---

## Evidence & Provenance

### EvidenceBundle Fields

| Field | Type | Required |
|-------|------|----------|
| `execution_id` | UUID | ✅ |
| `candidate_id` | UUID | ✅ |
| `request` | dict | ✅ |
| `response` | dict | ✅ |
| `baseline` | dict | ✅ |
| `probe` | dict | ✅ |
| `diff` | dict | ✅ |
| `raw_output` | str | ✅ |
| `screenshot` | str | Optional |
| `command` | str | ✅ |
| `auth_context` | dict | ✅ |
| `timestamps` | dict | ✅ |
| `hashes` | dict | ✅ |
| `provenance` | Provenance | ✅ |
| `execution_mode` | Enum | ✅ |
| `synthetic` | bool | ✅ |

---

## Recovery & Resilience

| Scenario | Strategy |
|----------|----------|
| Network timeout | Exponential backoff (3 retries) |
| Adapter crash | Restart worker, re-queue |
| Validation timeout | Human review queue |
| Human gate timeout | Escalate → manual |
| Power loss | Persistent queue + replay on restart |
| Data corruption | Backup restore + replay from ledger |

---

## Dead Letter Queue (DLQ)

```
Failed Work
    ↓
DLQ (persistent)
    ↓
Retry (max 3, exponential backoff)
    ↓
Still failing → Human review queue
    ↓
Manual intervention
```

---

## Observability

### Required Metrics

| Metric | Source | Alert Threshold |
|--------|--------|-----------------|
| `execution.duration` | ExecutionService | > 1h |
| `validation.confidence` | ValidationService | < 0.7 |
| `human_gate.latency` | HumanGate | > 30m |
| `adapter.error_rate` | AdapterRegistry | > 5% |
| `queue.depth` | JobQueue | > 100 |
| `recovery.success_rate` | RecoveryEngine | < 90% |

---

## Testing Requirements

| Layer | Scope |
|-------|-------|
| Unit | Domain logic, state machines, adapters |
| Integration | API contracts, adapters, DB |
| Desktop | Tauri commands, IPC, startup/shutdown, persistence |
| Frontend | Components, stores, view models, interactions |
| E2E | Critical flows (login → discover → work → paid) |
| Security | Policy, scope, auth, evidence, human gates |
| Migration | Schema, data, settings |
| Packaging | Installer, uninstaller, update, rollback |
| Recovery | Crash, network, auth, data corruption |

---

## Failure Testing Scenarios

| Scenario | Expected Behavior |
|----------|-------------------|
| Network unavailable | Retry with backoff, then queue |
| API unavailable | Queue, alert, retry |
| Database locked | Retry, then alert |
| Migration failure | Rollback, alert |
| Invalid credentials | Human gate, alert |
| Expired credentials | Refresh, then human gate |
| Invalid opportunity | Reject, log, continue |
| Duplicate opportunity | Dedup, merge, alert |
| Failed execution | Retry, then DLQ |
| Partial execution | Checkpoint, resume |
| AI unavailable | Degrade gracefully |
| LLM timeout | Fallback, alert |
| External API timeout | Retry, circuit breaker |
| Permission denied | Human gate, audit |
| Human Gate rejected | Log, notify, stop |
| App restart | Resume from last checkpoint |
| OS restart | Full recovery |
| Offline | Queue local, sync on reconnect |
| Online after offline | Flush queue, sync |

---

## Evidence Retention

| Type | Retention | Storage |
|------|-----------|---------|
| Execution logs | 90 days | SQLite + JSONL |
| Evidence bundles | 365 days | Filesystem + DB |
| Audit logs | 365 days | SQLite (immutable) |
| Payment records | 7 years | SQLite (immutable) |
| Credentials | Indefinite | Vault (encrypted) |
| Test artifacts | 30 days | Temp |