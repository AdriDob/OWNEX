# OWNEX Work System

> **Generated from actual codebase** — This document reflects the real implementation.

## Overview

The Work System is the operational core of OWNEX. It transforms opportunities into revenue through a structured lifecycle from discovery to payment.

## Work Lifecycle

```
DISCOVERED → QUALIFIED → RECOMMENDED → READY → RUNNING → SUBMITTED → ACCEPTED → PAID
     │            │            │          │        │           │           │        │
     ▼            ▼            ▼          ▼        ▼           ▼           ▼        ▼
  Universal    ZeroBarrier  Intelligent  WorkBank  Assisted   Human Gate  Revenue   Payout
Discovery    Scorer       Recommender  Cycle     Executor   (Approval)  Tracker   Received
```

## Core Components

### 1. Universal Discovery (`cores/direct_work_engine/discovery.py`)

```python
class UniversalDiscovery:
    async def discover_all(self, category: OpportunityCategory | None = None) -> list[Opportunity]:
        # Iterates registered adapters, isolates errors
        # Returns normalized Opportunity objects
```

**Registered Adapters** (auto-discovered):
- Opire (dev bounties)
- IssueHunt (dev bounties)
- Freelancer (freelance projects)
- Bug Bounty (HackerOne, Bugcrowd, Intigriti, YesWeHack)
- Algora (OSS bounties)
- OpenCollective (OSS funding)

### 2. Zero Barrier Scorer (`cores/direct_work_engine/scoring.py`)

**15 Weighted Factors** (sum = 1.0):
| Factor | Weight | Description |
|--------|--------|-------------|
| `remote` | 0.15 | Fully remote work |
| `international_payment` | 0.12 | Payment to AR possible |
| `payment_method` | 0.10 | Crypto/bank/processor |
| `time_to_payment` | 0.10 | Days to payout |
| `interview_required` | 0.10 | No interview = higher |
| `portfolio_required` | 0.08 | No portfolio = higher |
| `technical_test` | 0.08 | No test = higher |
| `registration_complexity` | 0.07 | Simple signup |
| `reputation_risk` | 0.05 | Platform trust |
| `skill_match` | 0.05 | User skills align |
| `competition_level` | 0.04 | Low competition |
| `legal_accessibility` | 0.03 | AR legal access |
| `historical_success` | 0.02 | User's past wins |
| `payment_compat` | 0.01 | PaymentCompatibilityEngine |

**Output**: `ZeroBarrierScore` (0-100) + `enablers`/`blockers` + `reasoning`

### 3. Intelligent Recommender (`cores/direct_work_engine/recommendation.py`)

**Modes**:
| Mode | Weights (sum=1.0) | Use Case |
|------|-------------------|----------|
| `balanced` | EV 0.25, Accept 0.20, Barrier 0.15, Speed 0.10, Compat 0.10, Rep 0.10, Risk 0.10 | Default |
| `fast_income` | EV 0.30, Accept 0.25, Speed 0.25, Barrier 0.10, Rep 0.10 | Quick cash |
| `max_success` | Accept 0.40, Barrier 0.25, EV 0.15, Compat 0.10, Rep 0.10 | High acceptance |

**Filters**:
- `min_zero_barrier_score` (default 40)
- `min_expected_value` (default 50)
- `min_acceptance_probability` (default 0.3)
- `enforce_acceptance_floor` (bool)

### 4. Work Bank (`cores/direct_work_engine/workbank.py`)

**Daily Cycle** (scheduler: `15 6 * * *`):
1. Discover opportunities
2. Score with ZeroBarrierScorer
3. Filter by `min_zero_barrier_score`
4. Rank by recommender
5. Generate `WorkItem` with deliverables
6. Classify: `ready_to_deliver` / `needs_access`
7. Persist to `data/workbank.json`

**WorkItem States**:
| State | Description | Next Action |
|-------|-------------|-------------|
| `discovered` | Found, not scored | → Score |
| `qualified` | Passed barrier filter | → Recommend |
| `recommended` | Ranked by EV | → Prepare |
| `ready_to_deliver` | Deliverables generated | → Human Gate |
| `delivered` | Submitted, awaiting response | → Track |
| `accepted` | Platform accepted | → Track payout |
| `paid` | Money received | → RevenueTracker |
| `rejected` | Platform rejected | → Feedback loop |
| `needs_access` | Requires API key/setup | → User config |

**Targets** (configurable):
```python
TARGETS = {"daily": 10, "weekly": 100, "monthly": 1000}
```

### 5. Feedback Loop (`cores/direct_work_engine/feedback.py`)

```python
def apply_learning(profile: UserProfile, records: list[LearningRecord]):
    # Only terminal states count:
    # ACCEPTED/PAID → success
    # REJECTED/CANCELLED → failure
    # PENDING/REVIEWING → ignored (no invention)
    
    profile.platform_success_rates[platform] = wins / total
    profile.category_success_rates[category] = wins / total
    profile.total_earnings += sum(amount for PAID records)
    profile.avg_time_to_payment = mean(payout_days)
```

### 6. Assisted Executor (`cores/direct_work_engine/assisted_executor.py`)

```python
class AssistedExecutor:
    def prepare_delivery(self, work_item: WorkItem) -> DeliveryPackage:
        # Generates: README.md, proposal.md, work.md
        # Saves to: ~/ownex/submissions/<platform>/<id>_<timestamp>/
        # Returns: package_path, submission_url, guide
    
    def submit(self, work_item: WorkItem, package: DeliveryPackage) -> SubmissionResult:
        # Platform-specific submission (API/browser)
        # Updates WorkItem state → delivered
```

## API Endpoints (`api/routers/direct_work.py`)

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/direct-work/status` | GET | Engine stats, registered adapters |
| `/direct-work/score` | POST | Score opportunities |
| `/direct-work/recommend` | POST | Ranked recommendations (mode param) |
| `/direct-work/learn` | POST | Feedback loop |
| `/direct-work/discover` | POST | Live discovery |
| `/direct-work/workbank/cycle` | POST | Run daily cycle |
| `/direct-work/workbank` | GET | Current work bank state |
| `/direct-work/workbank/{id}/deliver/prepare` | POST | Generate delivery package |
| `/direct-work/workbank/{id}/deliver/approve` | POST | Confirm delivery |
| `/direct-work/deliver/pending` | GET | Items ready to deliver |
| `/direct-work/daily-brief` | POST | Morning radar (top pick + skill gap) |
| `/direct-work/source-intel` | POST | Global Radar (platform analysis) |
| `/direct-work/filter` | POST | Strict filter (hard rejects) |
| `/direct-work/evolution` | POST | Learning report |
| `/direct-work/negotiate` | POST | Term analyzer |
| `/direct-work/skill-gap` | POST | Skill amplifier |

## Platform Access Matrix

| Platform | Category | Access Type | Setup Required |
|----------|----------|-------------|----------------|
| Opire | dev_bounty | PUBLIC | None |
| IssueHunt | dev_bounty | PUBLIC | None |
| Freelancer | freelance | NEEDS_API_KEY | API token |
| Algora | dev_bounty | PUBLIC | None |
| HackerOne | bug_bounty | NEEDS_API_KEY | API token |
| Bugcrowd | bug_bounty | NEEDS_API_KEY | API token |
| Intigriti | bug_bounty | NEEDS_API_KEY | API token |
| YesWeHack | bug_bounty | NEEDS_API_KEY | API token |

## Frontend Integration

### Components
- `DirectWorkRadar.vue` (Mission Control) — Top pick, targets, cycle button
- `WorkBankView` — Full work bank with filters
- `DeliveryQueue` — Items ready to deliver with Prepare/Approve actions

### Service (`frontend/src/services/ownexData.ts`)
```typescript
export async function fetchDirectWorkRecommendations(params?: RecommendParams)
export async function fetchDirectWorkWorkBank(): Promise<WorkBankState>
export async function runDirectWorkCycle(target: number): Promise<WorkBankState>
export async function fetchDirectWorkDailyBrief(limit: number): Promise<DailyBrief>
export async function fetchDeliveryQueue(): Promise<{count, items: DeliverableItem[]}>
```

## Scheduler Integration

| Job | Cron | Handler |
|-----|------|---------|
| `work_bank_daily_cycle` | `15 6 * * *` | `run_daily_cycle()` |
| `delivery_preparation` | `0 8 * * *` | `run_daily_delivery_preparation()` |

## Testing

```bash
# Unit tests
pytest tests/test_direct_work_engine.py    # 39 passed
pytest tests/test_direct_work_api.py       # 44 passed
pytest tests/test_workbank.py              # 18 passed
pytest tests/test_execution_queue.py       # 6 passed
pytest tests/test_income_chain_e2e.py      # 3 passed
```

## Key Metrics

| Metric | Source | Purpose |
|--------|--------|---------|
| `zero_barrier_score` | Scorer | Ranking |
| `expected_value_usd` | Recommender | EV ranking |
| `acceptance_probability` | Feedback loop | Acceptance floor |
| `ev_per_human_hour_usd` | Economics | Human-time EV |
| `cash_speed_days` | Platform history | Time to cash |
| `success_probability` | Feedback loop | Risk assessment |

---

*Document generated from codebase. Last verified: 2026-08-27*