# GLOSSARY.md — OWNEX Canonical Definitions

**Version**: 1.0 · **Date**: 2026-09-30

---

## Core Domain Terms

| Term | Definition | Lifecycle | Owner | DB Model | API Model | UI Representation |
|------|------------|-----------|-------|----------|-----------|-------------------|
| Source | External platform/program emitting opportunities (GitHub, HackerOne, Algora, etc.) | ACTIVE → CONDITIONAL → BLOCKED → DEPRECATED | SourceRegistry | `sources` table + `SourceRegistry` JSON | `SourceDTO` | SourceCard in Opportunities view |
| Opportunity | Canonical, deduplicated work unit with reward, requirements, eligibility, evidence | DISCOVERED → QUALIFIED → RECOMMENDED → READY → RUNNING → SUBMITTED → ACCEPTED → AWARDED → PAID | OpportunityEngine | `opportunities` table + `Opportunity` model | `OpportunityDTO` | OpportunityCard in list/detail |
| Work | Task derived from an Opportunity, assigned to human, with clear deliverable | READY → RUNNING → WAITING → SUBMITTED → ACCEPTED → AWARDED → PAID | WorkEngine | `work_items` table + `WorkItem` model | `WorkItemDTO` | WorkCard in Work view |
| Task | Atomic unit of work within a Work item | PENDING → RUNNING → DONE / BLOCKED | WorkEngine | `tasks` table | `TaskDTO` | TaskItem in Work detail |
| Mission | User-defined goal grouping Work items (e.g., "$1,000 this month") | ACTIVE → COMPLETED → ARCHIVED | MissionEngine | `missions` table | `MissionDTO` | MissionCard in Missions view |
| Execution | Act of performing Work (coding, writing, testing, submitting) | PREPARED → RUNNING → WAITING → COMPLETED / FAILED | ExecutionService | `executions` table | `ExecutionDTO` | ExecutionPanel in Work detail |
| Result | Delivered artifact (PR, report, fix, document, exploit) | DELIVERED → VALIDATED → ACCEPTED | WorkEngine | `results` table | `ResultDTO` | ResultCard in Work detail |
| Evidence | Verifiable proof that Work was done correctly (logs, screenshots, diffs, hashes) | CREATED → ATTACHED → VERIFIED | EvidenceService | `evidence_bundles` table | `EvidenceBundleDTO` | EvidencePanel in Result view |
| Payment | Money transferred from platform to user | INITIATED → PROCESSING → COMPLETED / FAILED | PaymentService | `payments` table | `PaymentDTO` | PaymentRow in Revenue view |
| Revenue | Economic event: POTENTIAL → EXPECTED → SUBMITTED → ACCEPTED → AWARDED → PAID | EXPECTED → SUBMITTED → ACCEPTED → AWARDED → PAID | RevenueEngine | `revenue_events` table | `RevenueEventDTO` | RevenueRow in Revenue view |
| Capital | Post-payment economic state (cash, liquidity, investments, runway) | ACCUMULATING | CapitalEngine | `capital_events` table | `CapitalSnapshotDTO` | CapitalCard in Capital view |
| Finding | Security: technically confirmed vulnerability with EvidenceBundle | DISCOVERED → VALIDATED → REPORTED | SecurityEngine | `findings` table | `FindingDTO` | FindingCard in Security view |
| Security | Domain: Observation → Hypothesis → Candidate → Validation → Evidence → Verdict → Finding → Report | OBSERVATION → HYPOTHESIS → CANDIDATE → VALIDATION → EVIDENCE → VERDICT → FINDING → REPORT | SecurityEngine | `security_observations`, `hypotheses`, `candidates`, `validations`, `evidence_bundles`, `verdicts`, `findings`, `reports` | `SecurityFindingDTO` | SecurityDashboard |
| Source | External platform/program emitting opportunities | ACTIVE → CONDITIONAL → BLOCKED → DEPRECATED | SourceRegistry | `sources` table + `SourceRegistry` JSON | `SourceDTO` | SourceCard in Sources view |
| Adapter | Code translating a Source into canonical Opportunity | ACTIVE → DEPRECATED | SourceRegistry | `adapters/` modules | `AdapterConfigDTO` | AdapterConfig in Sources view |
| Human Gate | Mandatory human approval before irreversible external action | REQUESTED → APPROVED / DENIED / EXPIRED | HumanGateService | `human_gates` table | `HumanGateRequestDTO` | ApprovalDialog in UI |
| EvidenceBundle | Verifiable proof package (request, response, diff, hashes, provenance) | CREATED → ATTACHED → VERIFIED | EvidenceService | `evidence_bundles` table | `EvidenceBundleDTO` | EvidencePanel in UI |
| PolicyEngine | Decides ALLOW / DENY / REQUIRE_APPROVAL for every external action | ALLOW / DENY / REQUIRE_APPROVAL | PolicyEngine | `policies` table | `PolicyDecisionDTO` | PolicyBanner in UI |
| EvidenceBundle | Verifiable proof package (request, response, diff, hashes, provenance) | CREATED → ATTACHED → VERIFIED | EvidenceService | `evidence_bundles` table | `EvidenceBundleDTO` | EvidencePanel in UI |

---

## Economic Terms

| Term | Definition | Key Rule |
|------|------------|----------|
| POTENTIAL | Theoretical max reward if everything goes perfectly | Never shown as money |
| EXPECTED | Statistically expected value after eligibility | `p_cash × reward` |
| SUBMITTED | Work delivered, awaiting platform response | Not money |
| ACCEPTED | Platform accepted deliverable | Not money |
| AWARDED | Platform confirmed reward amount | Not money until PAID |
| PAID | Money transferred to user | **ONLY THIS = REALIZED_CASH** |
| REALIZED_CASH | Money in user's account | **ONLY PAID = REALIZED_CASH** |
| NET_CASH | PAID − fees − taxes | What user actually keeps |
| MONEY/HOUR | REALIZED_CASH ÷ human hours invested | Primary efficiency metric |
| TIME_TO_CASH | Discovery → PAID | Speed metric |
| ACCEPTANCE_RATE | SUBMITTED → ACCEPTED | Quality metric |
| REPEATABILITY | Can user do it again? | Sustainability metric |

---

## Execution Terms

| Term | Definition |
|------|------------|
| ExecutionMode | `DRAFT` \| `AUTO_REVERSIBLE` \| `HUMAN_APPROVAL` (never `AUTO`) |
| HumanGate | Mandatory approval before irreversible external action |
| PolicyEngine | Decides ALLOW / DENY / REQUIRE_APPROVAL per action |
| EvidenceBundle | Verifiable proof: request, response, diff, hashes, provenance |
| Provenance | WHO, WHAT, WHEN, WHERE FROM, WHICH EXECUTION, REAL/SYNTHETIC |
| ExecutionMode | `REAL` \| `SIMULATION` \| `TEST` |
| SyntheticEvidence | Evidence from SIMULATION mode — never becomes Finding |
| HumanGate | Mandatory approval before irreversible external action |
| PolicyEngine | Decides ALLOW / DENY / REQUIRE_APPROVAL per action |
| EvidenceBundle | Verifiable proof: request, response, diff, hashes, provenance |
| Provenance | WHO, WHAT, WHEN, WHERE FROM, WHICH EXECUTION, REAL/SYNTHETIC |

---

## Security Terms

| Term | Definition |
|------|------------|
| Observation | Raw data point (port open, header present, version detected) |
| Hypothesis | Interpretation of observation (not yet validated) |
| Candidate | Hypothesis warranting validation |
| ValidationPlan | Steps to prove/refute candidate |
| Execution | Running validation steps |
| EvidenceBundle | Proof package from validation |
| Verdict | CONFIRMED / REJECTED / INSUFFICIENT |
| Finding | Technically confirmed vulnerability with EvidenceBundle |
| Report | Structured deliverable for submission |

---

## Economic State Machine

```
OPPORTUNITY
    ↓
WORK
    ↓
EXECUTION
    ↓
RESULT
    ↓
PAYMENT
    ↓
REVENUE
    ↓
CAPITAL
```

**Only PAID = REALIZED_CASH**. Everything else is pipeline.

### Revenue States (Canonical)

| State | Meaning | Is Money? |
|-------|---------|-----------|
| EXPECTED | Statistical expectation | No |
| PROJECTED | Model projection | No |
| PENDING | Awaiting platform response | No |
| SUBMITTED | Delivered, awaiting response | No |
| ACCEPTED | Platform accepted | No |
| AWARDED | Platform confirmed reward | No |
| PAID | Money received | **YES** |
| REALIZED | In user's account | **YES** |

**Rule**: `PAID → REALIZED_REVENUE`. Nothing else counts.

---

## Source Registry Terms

| Term | Definition |
|------|------------|
| Source | External platform/program emitting opportunities |
| Source Registry | Canonical list of all known sources with metadata |
| Source Adapter | Code translating Source → canonical Opportunity |
| Normalizer | Converts raw source data → canonical Opportunity |
| Deduplicator | Merges same opportunity from multiple sources |
| Eligibility | Country, skills, KYC, interview, portfolio, cert requirements |
| SourceAdmissionTest | P0: REALITY / P1: ELIGIBILITY / P2: TECHNICAL / P3: ECONOMIC |
| Source Status | ACTIVE / CONDITIONAL / BLOCKED / UNKNOWN / DEPRECATED |

---

## UI/UX Terms

| Term | Definition |
|------|------------|
| Command Center | Primary screen: "WHAT NOW?" — next action, money, status |
| Opportunity Card | Title, Source, Tech, Reward, Time-to-Cash, Eligibility, Risk, Next Action, Evidence |
| Command Palette | `Ctrl+K` — universal search + actions |
| Progressive Disclosure | First: NOW/MONEY/STATUS/NEXT. Then: evidence, tech details, source, logs |
| Empty State | Meaningful guidance when no data |
| Loading State | Skeleton or spinner, never blank |
| Error State | What happened, why, what user should do |
| Offline State | Clear indicator, queue local actions |

---

## Desktop Terms

| Term | Definition |
|------|------------|
| Tauri v2 | Rust shell + WebView frontend + Python sidecar |
| Sidecar | Python FastAPI backend bundled as ONEFILE |
| IPC | Tauri commands/events (preferred over HTTP for local) |
| Resource Dir | `binaries/ownex-backend-<triple>` (sidecar) + `frontend/dist` |
| Data Dir | `~/.ownex/` (user data) + `~/.orion/` (vault) |

---

## Testing Terms

| Term | Definition |
|------|------------|
| Vertical Slice | SOURCE → OPPORTUNITY → WORK → EXECUTION → VALIDATION → PAYMENT → REVENUE |
| Release Smoke | install → launch → demo → close → reopen → persistence → backup → restore → uninstall → reinstall |
| Synthetic Evidence | Evidence from SIMULATION mode — never becomes Finding |
| Contract Test | API request/response shape verification |
| Integration Test | DB + adapters + pipeline + revenue + capital |
| Desktop Test | Tauri commands, IPC, startup, shutdown, persistence |

---

## Versioning & Release

| Term | Definition |
|------|------------|
| SSOT | Single Source of Truth (one version everywhere) |
| Semantic Versioning | MAJOR.MINOR.PATCH (breaking / feature / fix) |
| Release Candidate | All gates pass, ready for install test |
| Release | Signed artifacts + checksums + release notes |
| Version SSOT | `.VERSION.txt` / `VERSION.txt` / `pyproject.toml` / `package.json` / `Cargo.toml` / `tauri.conf.json` |

---

## Key Principle

> **One canonical definition per concept.** If you find two definitions for the same term, it's a bug — consolidate.