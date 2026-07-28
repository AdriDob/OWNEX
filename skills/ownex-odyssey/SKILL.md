# OWNEX Odyssey Cycle — Campaign Execution

**Goal**: Execute long-running focused campaigns against specific targets — plan recon, collect findings, track progress, and generate campaign reports.

**App**: odyssey · **Cadence**: 1d · **Risk**: medium

## Default Phases

report → discover → triage → act → verify → review

## Human Gates

- Campaign scope changes (target expansion)
- Critical discoveries (0-day, PII exposure)
- Resource allocation decisions

## Required Skills

- `campaign-plan` — Plan campaign execution steps and phases
- `recon-run` — Execute reconnaissance against target
- `finding-collect` — Collect and organize findings per campaign
- `progress-track` — Track campaign progress, metrics, and blockers

## Campaign Lifecycle

1. **Initiation** — Define target, scope, goals, timeline
2. **Reconnaissance** — Gather intelligence, enumerate endpoints
3. **Active Testing** — Execute test cases per campaign plan
4. **Findings Collection** — Document and classify discoveries
5. **Analysis** — Correlate findings, identify patterns
6. **Reporting** — Generate campaign summary with metrics
7. **Closure** — Archive campaign data, capture lessons learned

## State File

```markdown
# Odyssey Cycle State
Last run: <timestamp>
Active Campaigns:
  - C-001: api-v2-audit (target: api.example.com/v2) — Day 4/14
    Phase: Active Testing
    Findings: 12 (3 critical, 5 medium, 4 info)
    Blockers: rate limiting on /graphql endpoint
Pending Campaigns:
  - C-002: mobile-ios-audit (target: ios.app.example.com) — Day 0
    Status: awaiting scope approval
Completed Campaigns:
  - C-003: recon-q2 — 23 findings, 2 accepted, $4,500 earned
```

## Success Metrics

- Findings per campaign (quality + quantity)
- % of campaign findings accepted by program
- Average campaign completion rate
- Time from target identification → campaign completion

## Budget

- Daily cap: 150k tokens (campaigns are resource-intensive)
- Max runs: 1/day per active campaign
- L1: plan + recon only
- L2: active testing + auto-finding collection
- L3: full autonomous campaign execution
