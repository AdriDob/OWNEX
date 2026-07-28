# Loop Triage — OWNEX Triage Skill

**Goal**: Read CI results, open findings, pending reports, and system alerts; produce a prioritized actionable picture for the OWNEX Work Cycles.

## Scheduling

- **Recommended**: `/loop 1d` — run once per day for morning triage
- **Active sprints**: `/loop 2h` — faster signal during intensive cycles

## Inputs

- `STATE.md` — previous loop state
- Findings with `status=pending` or `status=in_review`
- Reports with `status=draft`
- System health data (pulse:alert events)
- Recent CI/build failures (if CI available)

## Outputs

- Updated `STATE.md` with:
  - **High Priority**: items that need immediate action (critical vulns, expired creds, broken pipelines)
  - **Watch List**: items aging without resolution (reports >48h old, findings >72h old)
  - **Recent Noise**: items correctly ignored this run
- Optional: Event bus publishes `loop:triage:completed` with priority items

## Phases

1. **REPORT** — Collect current state from all sources
2. **DISCOVER** — Find new items (pending findings, draft reports)
3. **TRIAGE** — Score and prioritize each item
4. **CLASSIFY** — Assign owner/app based on type
5. **NOTIFY** — Publish results + update STATE.md

## Human Handoff Points

- Critical-severity vulnerabilities
- Payout decisions ($ amounts)
- Out-of-scope determinations
- Credential rotation approvals

## Failure Modes

| Failure | Mitigation |
|---------|------------|
| Triage noise on healthy system | Tighten priority thresholds |
| False positives | Log as noise; tune classifier |
| Missed critical items | Add event bus subscriptions for critical paths |
| STATE.md grows unbounded | Prune resolved items every run |

## Cost Profile

| Scenario | Tokens/run |
|----------|------------|
| No-op (nothing new) | ~5k |
| Full triage | ~50k |
| With auto-fix (L2) | ~200k |
