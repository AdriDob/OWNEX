# OWNEX V12 - FASE 0: Work Bank y Discovery Report

**Generated:** 2026-11-09T19:49:52.356561

## Discovery → Work Bank Pipeline
The opportunity discovery engine connects 16+ platform adapters to the Work Bank pipeline:

### Adapter Performance (Top by discoveries)
- hackerone: bug bounty opportunities
- bugcrowd: security bug bounty
- freelancer: dev/tasks micro-work
- linkedin: professional roles
- indeed: job platform opportunities
- computrabajo: Argentina job market
- bumeran: Latinoamérica jobs
- glassdoor: company reviews + jobs
- infojobs: Argentina market leader

### Opportunity States
- FULLY_ELIGIBLE - Evidence sufficient for full eligibility
- CONDITIONAL - Meets basic criteria, pending verification
- UNKNOWN - Insufficient data to determine
- INELIGIBLE - Does not meet minimum criteria

⚠️ No utilizar FULLY_ELIGIBLE sin evidencia suficiente.

### Argentina Compatibility
All job platform adapters now support:
- argentina_ok: True/False flag
- no_experience_required: True/False flag
- Idioma: Español/English filtering
- remote: True/False for remote work

### Pipeline Flow
1. Adapter.fetch_opportunities() → RawOpportunity[]
2. source_discovery.normalize() → Standardized format
3. engine.score() → ScoredOpportunity with priority
4. human_gate.review() → Approval/rejection tracking
5. revenue_ledger.record() → Potential vs approved vs paid separation
6. payout_recommender.suggest() → Next actions

## Current Metrics
- Discovery volume: 945 opportunities across 16 adapters
- Conversion rate (human gate → paid): 0,0% (needs tracking activation)
- Active adapters: 24 total (16 opportunity + 8 other types)
- Tests passing: 100/100 (make test-fast)

## FASE 1 Priorities
- [ ] Human gate tracking: Implement stats collection in production flow
- [ ] Revenue dashboard: discoveries → approvals → payouts visualization
- [ ] 2-3 new adapter expansions: upwork + kaggle + intigriti decision
- [ ] Normalize 300 sources in Source Discovery Registry
- [ ] IP pinning/robust DNS resolution in source discovery probe

**P0 Action:** Activate human gate tracking + measure baseline revenue
**P1 Action:** Deploy 2-3 new adapter expansions
**P2 Action:** Build revenue dashboard
