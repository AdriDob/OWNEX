# Revenue Execution Plan — ORION → Income

> **Last updated**: July 2026
> **Status**: Phase 1 — Preparation
> **North star**: 30K USD financial independence

---

## Mission

Transform ORION from a technical project into a **personal revenue engine**.
Not a scanner collection, not a framework — a system that produces accepted reports and growing income.

---

## Core Strategy

### Primary: Bug Bounty
Bug bounty as the first and main income source.
ORION exists to find, evidence, report, and collect on vulnerabilities.

### Secondary: AI Engineering
- AI agent development for clients
- Automation consulting
- Custom dashboards and integrations
- Open-source reputation → consulting opportunities

---

## The Revenue Loop

```
Target → Recon → Hypothesis → HTTP Probe → Validation
→ Evidence → Acceptance Check → Report → Submit → Accept → Payout
→ Learn → Better next time
```

Every USD in the system flows through this loop. If any step is broken, revenue stops.

---

## Current Pipeline Analysis

### What exists (verified working)

| Step | Status | Bottleneck |
|---|---|---|
| Target selection | ⚠️ Partial | No Expected Value formula — static priority |
| Recon (15 tools) | ✅ Complete | Good |
| Hypothesis generation (5 reasoners) | ✅ Complete | No HTTP confirmation — hypotheses stay theoretical |
| Evidence composer | ⚠️ Broken | PoC missing headers/auth/body — not copy-paste ready |
| Report quality gate | ✅ Complete | Good, but never calibrated against real outcomes |
| Report submission | ⚠️ Stub | Only manual — no platform API integration |
| Payout tracking | ✅ RevenuePipeline | Works for manual entries |
| Learning | 🔴 Broken | 8 open feedback loops — data collected but not consumed |

### What's missing (blocks revenue)

| Gap | Impact | Fix |
|---|---|---|
| HTTP probe module | 🔴 Critical | Hypotheses never confirmed → no real findings |
| Report templates (H1/BC/Inti) | 🔴 Critical | No submission-ready output |
| Hypothesis → Finding promotion | 🔴 Critical | Manual copy-paste between stages |
| Platform connectors (Immunefi/C4) | 🔴 High | Manual submission only |
| Acceptance learning | 🔴 High | Every rejection teaches nothing |
| PoC generation fix | 🔴 High | Evidence not usable as-is |

---

## Revenue Projection

Based on market analysis, hunter experience curves, and ORION's current capability:

### Scenario: Conservative (learning mode)

| Period | Monthly | Annual | Cumulative |
|---|---|---|---|
| Months 1-3 | $0-100 | $0-300 | $0-300 |
| Months 4-6 | $100-300 | $1,200-3,600 | $1,200-3,900 |
| Months 7-12 | $300-800 | $3,600-9,600 | $4,800-13,500 |
| Year 2 | $800-2,000 | $9,600-24,000 | $14,400-37,500 |
| Year 3 | $2,000-4,000 | $24,000-48,000 | $38,400-85,500 |

### Scenario: Optimistic (fast learning)

| Period | Monthly | Annual | Cumulative |
|---|---|---|---|
| Months 1-3 | $200-500 | $600-1,500 | $600-1,500 |
| Months 4-6 | $500-1,500 | $6,000-18,000 | $6,600-19,500 |
| Months 7-12 | $1,500-3,000 | $18,000-36,000 | $24,600-55,500 |
| Year 2 | $3,000-7,000 | $36,000-84,000 | $60,600-139,500 |
| Year 3 | $5,000-12,000 | $60,000-144,000 | $120,600-283,500 |

### Key metrics

| Metric | Conservative | Optimistic |
|---|---|---|
| Time to first $1,000 | 6-9 months | 3-4 months |
| Time to $1,000/mo consistent | 12-18 months | 6-9 months |
| Time to 30K total | ~2.5-3 years | ~12-18 months |
| Reports/month at 12mo | 3-5 | 8-15 |
| Acceptance rate at 12mo | 15-25% | 30-50% |

---

## Execution Phases

### Phase 0 — Foundation (THIS WEEK)

**Goal**: System is stable, data persists, nothing crashes.

| Task | Effort | Status |
|---|---|---|
| Fix RewardLearner persistence | 15min | ✅ Done |
| Fix withdrawal persistence (dict→JSON) | 1h | ✅ Done |
| Fix `if False` event bug | 5min | ✅ Done |
| Ruff + pytest green | — | ✅ 549 tests pass |

### Phase 1 — Revenue Ready (Weeks 1-3)

**Goal**: Pipeline produces submission-ready reports.

| # | Task | Effort | Impact |
|---|---|---|---|
| 1 | HTTP probe module | 3d | ⭐⭐⭐⭐⭐ |
| 2 | Fix PoC generation (headers/auth/body) | 1d | ⭐⭐⭐⭐ |
| 3 | Report templates (H1/BC/Inti) | 2d | ⭐⭐⭐⭐⭐ |
| 4 | Hypothesis→Finding endpoint | 1d | ⭐⭐⭐⭐⭐ |
| 5 | Immunefi connector | 2d | ⭐⭐⭐⭐⭐ |
| 6 | Code4rena connector | 2d | ⭐⭐⭐⭐ |

**Phase 1 done when**: ORION can take a target → produce a submission-ready report → send it to a platform.

### Phase 2 — Acceptance Engine (Weeks 3-6)

**Goal**: Reports get accepted. Learn from every rejection.

| # | Task | Effort | Impact |
|---|---|---|---|
| 7 | Acceptance Intelligence module | 1-2w | ⭐⭐⭐⭐⭐ |
| 8 | Auto feedback loop (finding:status_changed) | 1d | ⭐⭐⭐⭐ |
| 9 | Target ROI Engine (reward × acceptance_prob) | 2d | ⭐⭐⭐⭐ |
| 10 | Evidence Critic (pre-submission quality check) | 3d | ⭐⭐⭐⭐ |

**Phase 2 done when**: ORION predicts acceptance probability and learns from every outcome.

### Phase 3 — Feedback Loops (Weeks 6-10)

**Goal**: Every execution teaches the system. Improvement compounds.

| # | Task | Effort | Impact |
|---|---|---|---|
| 11 | RewardLearner outcome recording | 1d | ⭐⭐⭐⭐ |
| 12 | Bayesian FeedbackLearner (replace LLM) | 3d | ⭐⭐⭐ |
| 13 | COPILOT decisions with memory+KG+Rewards | 3d | ⭐⭐⭐⭐ |
| 14 | Learnable NextAction weights | 2d | ⭐⭐⭐ |

**Phase 3 done when**: System measurably improves with each cycle.

### Phase 4 — Scale (Weeks 10-16)

**Goal**: Handle more targets, produce more reports, reduce human time.

| # | Task | Effort | Impact |
|---|---|---|---|
| 15 | New reasoners (CSRF, LFI, CMDi, GraphQL) | 1-2w | ⭐⭐⭐⭐ |
| 16 | Expected Value prioritizer | 2d | ⭐⭐⭐⭐ |
| 17 | Docker + docker-compose | 2d | ⭐⭐⭐ |
| 18 | Auto-backup | 1d | ⭐⭐⭐ |

---

## Metrics Dashboard

### Daily tracking

```yaml
targets_analyzed: count
endpoints_processed: count
hypotheses_generated: count
hypotheses_confirmed: count
reports_created: count
reports_submitted: count
reports_accepted: count
reports_rejected: count
revenue_generated: USD
hours_invested: hours
```

### Weekly review

```yaml
acceptance_rate: accepted / (accepted + rejected)
avg_payout_per_report: total_revenue / accepted
revenue_per_hour: total_revenue / hours_invested
top_program_by_roi: program_name
top_vuln_by_payout: vulnerability_type
improvement_week_over_week: +/-
```

### Monthly targets

| Month | Min target | Stretch target |
|---|---|---|
| Month 1 | System stable, first test report | First submission |
| Month 2 | 3 reports submitted | 1 accepted |
| Month 3 | 5 reports, 1 accepted | 2 accepted, $200 |
| Month 4 | 8 reports, 2 accepted | $500 |
| Month 5 | 10 reports, 3 accepted | $800 |
| Month 6 | 15 reports, 4 accepted | $1,500 |

---

## Risk Register

| Risk | Probability | Impact | Mitigation |
|---|---|---|---|
| Reports rejected for reasons ORION can't learn | High | High | Manual review first 20 reports |
| Platform API changes break connectors | Medium | High | Wrappers with adaptation layer |
| LLM costs exceed bounty income | Low | Medium | Local models (Ollama) for routine tasks |
| Burnout from running both ORION + research | Medium | High | Automate everything possible |
| Target selection misses real bugs | Medium | High | Start with proven programs |
| ORION becomes a "toy" — never used | Low | Critical | Daily usage commitment |

---

## Commitment

1. **Ship phase 1 before adding new modules.** No new reasoners, no new features until HTTP probe + report templates + connectors work.
2. **First 20 reports are manual review.** Every rejection is data. Every acceptance is a pattern to learn.
3. **Run the loop daily.** Not "work on ORION" — use ORION to find bugs. If ORION isn't finding bugs, fix ORION.
4. **Revenue is the score.** Not test count, not modules, not architecture elegance. USD in bank.
5. **If it doesn't increase one of the 6 indicators, don't build it.**

---

## The 6 Indicators

1. **More vulnerabilities detected** — quantity
2. **Better evidence** — acceptance probability per report
3. **Higher acceptance rate** — accepted / submitted
4. **Less time per investigation** — efficiency
5. **Higher revenue potential** — USD per target
6. **Better financial decisions** — ROI-based targeting

ORION is winning when all six improve month over month.
