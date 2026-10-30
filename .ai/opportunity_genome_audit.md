# Opportunity Genome — Model Audit Matrix

> Generated from actual code inspection. This is the source of truth for migration.

---

## Three Models Compared

| Aspect | `database/models.py` (SQLAlchemy) | `cores/direct_work_engine/models.py` (DWE) | `cores/opportunity/models.py` (Legacy Intel) |
|--------|-----------------------------------|--------------------------------------------|---------------------------------------------|
| **Type** | ORM (SQLite/PostgreSQL) | Dataclasses (in-memory) | Dataclasses (backward compat) |
| **Purpose** | Persistence layer | Active discovery/execution engine | Legacy API compatibility |
| **Consumers** | All API routers, services | DirectWorkEngine, WorkBank, Recommender, API `/direct-work/*` | `/opportunity-intelligence/*`, Top5Engine, scoring |

---

## Field-by-Field Mapping

### Core Identity

| Concept | DB Model | DWE Model | Legacy Intel |
|---------|----------|-----------|--------------|
| **Canonical ID** | `Target.id`, `Finding.id`, `Report.id` | `Opportunity.id` (string: `platform_external_id`) | `Opportunity.id` |
| **External ID** | — | implicit in `id` | — |
| **Source/Platform** | `Target.name`, `Target.domain` | `Opportunity.platform` (WorkPlatform enum) | `Opportunity.platform` (string) |
| **Source Metadata** | — | `OpportunitySource` not used | `OpportunitySource` (type, name, url, confidence) |

### Basic Info

| Field | DB Model | DWE Model | Legacy Intel |
|-------|----------|-----------|-------------|
| **Title/Name** | `Target.name` | `Opportunity.title` | `Opportunity.name` |
| **Description** | `Finding.description` | `Opportunity.description` | — |
| **URL** | — | `Opportunity.url` | `Opportunity.public_url` |
| **Category** | — | `Opportunity.category` (OpportunityCategory enum, 58 values) | `Opportunity.category` (free string) |
| **Subcategory** | — | via `specialization` (GameDev only) | `Opportunity.subcategory` |
| **Scope/Summary** | `Investigation.pipeline_state` | `Opportunity.description` | `Opportunity.scope_summary` |
| **Company** | — | `Opportunity.company` | — |

### Financial

| Field | DB Model | DWE Model | Legacy Intel |
|-------|----------|-----------|-------------|
| **Reward/Payment** | `Report.estimated_reward`, `Report.confirmed_reward` | `Opportunity.payment` (float) | `Opportunity.reward` |
| **Currency** | `Report.currency` | `Opportunity.currency` (default USD) | — |
| **Payment Method** | — | `Opportunity.payment_method` (PaymentMethod enum) | — |
| **Time to Payout** | — | `Opportunity.time_to_payout_days` | `Opportunity.estimated_effort_hours` (misused) |
| **EV/hour** | — | `RankedOpportunity.htroi` (HumanTimeAdjustedROI) | `OpportunityScore.evh` |

### Barrier / Entry Model (DWE unique)

| Field | DB Model | DWE Model | Legacy Intel |
|-------|----------|-----------|-------------|
| **Experience Required** | — | `ExperienceLevel` enum (NONE/JUNIOR/MID/SENIOR) + `experience_requirement` | — |
| **Portfolio Required** | — | `Opportunity.portfolio_required` | — |
| **Interview Required** | — | `Opportunity.interview_required` | — |
| **Technical Test Required** | — | `Opportunity.technical_test_required` | — |
| **Registration Required** | — | `Opportunity.registration_required` | — |
| **Entry Mechanism** | — | `EntryMechanism` enum (DIRECT/ASSESSMENT/TRAINING/TEST/INTERVIEW/...) | — |
| **Barrier Score** | — | `ZeroBarrierScore` (0-100, factors, weights, enablers, blockers) | — |
| **Is Zero Experience** | — | `Opportunity.is_zero_experience` (property) | — |
| **Is Zero Barrier** | — | `Opportunity.is_zero_barrier` (property) | — |

### Scoring / Evaluation

| Field | DB Model | DWE Model | Legacy Intel |
|-------|----------|-----------|-------------|
| **Difficulty** | — | `DifficultyLevel` enum (BEGINNER→EXPERT) | — |
| **Reputation** | — | `Opportunity.reputation` (0.5 default) | — |
| **Risk** | — | `Opportunity.risk` (0.5 default) | — |
| **Payment Proven** | — | `Opportunity.payment_proven` | — |
| **Stability** | — | `Opportunity.stability` | — |
| **Compatibility** | — | `Opportunity.compatibility` | — |
| **Acceptance Probability** | — | `RankedOpportunity.acceptance_probability` | `UnifiedScore.acceptance_probability` |
| **Expected Value** | — | `RankedOpportunity.expected_value` | `UnifiedScore.expected_value` |
| **Overall Score** | — | `RankedOpportunity.overall_recommendation_score` | `UnifiedScore.overall` |

### Skill / Compatibility

| Field | DB Model | DWE Model | Legacy Intel |
|-------|----------|-----------|-------------|
| **Technology Tags** | `Endpoint.params` (JSON) | `Opportunity.technology_tags` | `Opportunity.technology_tags` |
| **Language Required** | — | `Opportunity.language_required` | — |
| **Estimated Hours** | — | `Opportunity.estimated_time_hours` | `Opportunity.estimated_effort_hours` |
| **User Skills** | — | `UserProfile.skills` | `PersonalHistory.by_vuln_type` |

### Workflow / Status

| Field | DB Model | DWE Model | Legacy Intel |
|-------|----------|-----------|-------------|
| **Status** | `Investigation.status`, `ScanRun.status` | `WorkItem.state` (DISCOVERED→PAID) | `Opportunity.priority` |
| **Discovered At** | `Target.created_at` | implicit in `WorkItem` | `Opportunity.created_at` |
| **Updated At** | `Target.updated_at` | — | — |
| **Metadata** | JSON columns | `Opportunity.metadata` | `Opportunity.metadata` |

### Platform-Specific

| Field | DB Model | DWE Model | Legacy Intel |
|-------|----------|-----------|-------------|
| **WorkPlatform** | — | `WorkPlatform` enum (26 values) | string |
| **Employment Type** | — | `EmploymentType` enum (8 values) | — |
| **Payment Method** | — | `PaymentMethod` enum (9 values) | — |
| **Hourly Rate** | — | `Opportunity.hourly_rate_usd` | — |
| **Time to First Work** | — | `Opportunity.time_to_first_work_hours` | — |
| **Rate Source** | — | `Opportunity.rate_source` (platform/ownex_history/unknown) | — |

---

## Duplicates / Conflicts

1. **Category**: DWE has 58 enum values; Legacy has free string; DB has none
2. **Platform**: DWE has `WorkPlatform` enum (26); Legacy uses string; DB uses Target.name
3. **Scoring**: DWE has `ZeroBarrierScore` + `RankedOpportunity`; Legacy has `UnifiedScore` + `OpportunityScore`; DB has none
4. **Payment**: DWE has `payment_method` enum; Legacy has none; DB has `Report.currency`
5. **Experience/Barrier**: DWE has full entry model; Legacy has none; DB has none
6. **EV/hour**: DWE has `HumanTimeAdjustedROI`; Legacy has `EVHCalculation`; DB has none

---

## Consumers by Model

### `database/models.py` (SQLAlchemy)
- All API routers via `SessionLocal`
- `cores/financial/scheduler.py` (PayoutRecord sync)
- `core/scheduler.py` (ScanScheduler)
- `cores/orchestrator/scan_service.py`
- `core/cycles/security.py` (SecurityCycle)

### `cores/direct_work_engine/models.py`
- `cores/direct_work_engine/engine.py` (DirectWorkEngine)
- `cores/direct_work_engine/workbank.py` (WorkBank)
- `cores/direct_work_engine/recommendation.py` (IntelligentRecommender)
- `cores/direct_work_engine/scoring.py` (ZeroBarrierScorer)
- `cores/direct_work_engine/discovery.py` (UniversalDiscovery)
- `cores/direct_work_engine/delivery.py` (DirectWorkDeliveryEngine)
- `cores/direct_work_engine/execution.py` (DirectWorkExecutionEngine)
- `api/routers/direct_work.py` (all endpoints)
- `api/adapters/legacy.py` (adapter bridge)

### `cores/opportunity/models.py`
- `api/routers/opportunity_intelligence.py` (`/web3`, `/independent`, `/by-category`)
- `api/routers/pillars.py` (`/high-value/web3`)
- `cores/opportunity/engine.py` (OpportunityOrchestrator)
- `cores/opportunity/scoring2.py` (Top5Engine, scoring)
- Tests: `test_opportunity_engine*.py`

---

## Migration Target: OpportunityGenome

The Genome must be a **single unified model** that:
1. Can be persisted to DB (SQLAlchemy)
2. Can be used in-memory by DWE engines
3. Can be serialized for API responses
4. Replaces ALL three models over time

### Genome Fields (from plan + audit)

```python
# Core Identity
id: str                          # UUID
external_id: str                 # platform-specific ID
source: str                      # "hackerone", "immunefi", "opire", "code4rena", "direct_work", "legacy"
platform: str                    # WorkPlatform enum value
title: str
description: str
url: str

# Categorization
category: str                    # OpportunityCategory enum value
subcategory: str | None

# Financial
reward: float                    # estimated average payout
currency: str                    # USD, USDC, etc.
payment_method: str              # PaymentMethod enum value
time_to_payout_days: float | None

# Scoring
zero_barrier_score: ZeroBarrierScore | None
expected_value: float
acceptance_probability: float
risk_score: float
barrier_score: float

# Entry Model (DWE unique)
experience_required: str         # ExperienceLevel enum
experience_requirement: str      # ExperienceRequirement enum
entry_mechanism: str             # EntryMechanism enum
portfolio_required: bool
interview_required: bool
technical_test_required: bool
registration_required: bool
is_zero_experience: bool
is_zero_barrier: bool

# Skill / Compatibility
technology_tags: list[str]
language_required: str
estimated_time_hours: float
difficulty: str                  # DifficultyLevel enum

# Workflow
status: str                      # DISCOVERED, QUALIFIED, SELECTED, PREPARED, EXECUTING, VALIDATING, DELIVERING, LEARNED, PAID
work_stream: str                 # WorkStream enum

# Metadata
discovered_at: datetime
updated_at: datetime
metadata: dict
```

---

## Migration Strategy

**Phase 1**: Create Genome as new standalone module (`cores/opportunity_genome/`)
**Phase 2**: Build mappers from each legacy model → Genome
**Phase 3**: Update DWE engines to use Genome internally
**Phase 4**: Update API routers to return Genome
**Phase 5**: Deprecate legacy models (keep for backward compat)

**NO BIG BANG REMOVAL** — each phase must pass all tests.