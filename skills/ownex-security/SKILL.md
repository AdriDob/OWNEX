# OWNEX Security Cycle — Security Triage

**Goal**: Daily vulnerability triage — scan new findings, validate evidence, prioritize by severity, and escalate critical items.

**App**: cateye · **Cadence**: 1d · **Risk**: high

## Default Phases

report → discover → triage → classify → act → notify

## Human Gates

- Critical-severity findings (require human confirmation)
- Payout decisions
- Program boundary decisions (scope edge cases)

## Required Skills

- `loop-triage` — General triage capability
- `evidence-quality` — Score evidence completeness per finding
- `report-draft` — Draft validation reports for confirmed findings
- `priority-score` — Compute CVSS + context priority

## State File

```markdown
# Security Cycle State
Last run: <timestamp>
High Priority:
  - F-001: Critical RCE in auth endpoint — awaiting human review
Watch List:
  - F-003: Medium XSS — 48h without action
Recent Noise:
  - F-004: False positive (WAF bypass, tested negative)
```

## Success Metrics

- Time from finding creation to triage
- % of findings validated vs rejected
- Payout rate from triaged findings
- False positive rate reduction

## Budget

- Daily cap: 100k tokens
- Max runs: 2/day
- L1: report only (first week)
- L2: auto-draft reports (after quality validation)
