# OWNEX Forge Cycle — Bounty Forge

**Goal**: Process incoming bounty reports — triage submissions, validate scope, verify evidence, and prepare reward recommendations.

**App**: forge · **Cadence**: 2h · **Risk**: medium

## Default Phases

discover → triage → classify → verify → act → notify

## Human Gates

- High-reward bounties (>$1000)
- Out-of-scope determinations
- Dispute resolution

## Required Skills

- `bounty-triage` — Triage incoming bounty submissions
- `scope-check` — Validate target scope and program rules
- `evidence-verify` — Verify reproducibility and evidence quality
- `reward-calc` — Calculate reward based on severity + program

## State File

```markdown
# Forge Cycle State
Last run: <timestamp>
Pending Review:
  - B-042: Auth bypass on api.example.com — reward $500
Watch List:
  - B-038: Info disclosure — awaiting user response (48h)
Escalated:
  - B-040: SSRF with PII exposure — legal review
```

## Success Metrics

- Time from submission to triage completion
- % of submissions accepted / rejected
- Average reward accuracy (vs final payout)
- Submitter satisfaction score

## Budget

- Daily cap: 75k tokens
- Max runs: 6/day (every 2h during active hours)
- L1: report only
- L2: auto-reward calculation (with human approval gate)
