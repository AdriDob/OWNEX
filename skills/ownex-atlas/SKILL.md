# OWNEX Atlas Cycle — Target Intelligence

**Goal**: Expand bug bounty coverage — discover new targets, update intelligence profiles, and identify coverage gaps in existing programs.

**App**: atlas · **Cadence**: 1d · **Risk**: low

## Default Phases

discover → triage → classify → report

## Human Gates

- New target approval (requires program manager sign-off)
- Program policy changes
- Scope expansion decisions

## Required Skills

- `target-discover` — Discover new potential targets (domains, subdomains, APIs)
- `intel-update` — Refresh target intelligence profiles
- `coverage-scan` — Identify gaps in current coverage

## Data Sources

- Censys / Shodan API
- Certificate transparency logs
- DNS enumeration results
- Program scope definitions from HackerOne / Bugcrowd
- Existing target database

## State File

```markdown
# Atlas Cycle State
Last run: <timestamp>
New Discoveries:
  - api.staging.example.com — not in scope (flag for review)
  - admin-dashboard.example.com — new subdomain, unknown service
Intelligence Updates:
  - example.com: updated tech stack (Vue 3 → React 18)
  - api.partner.com: added new endpoint /v3/graphql
Coverage Gaps:
  - Mobile API (iOS) — no coverage
  - WebSocket endpoints — partially covered
Pending Approval:
  - Target: api.staging.example.com (proposed addition)
```

## Success Metrics

- New targets discovered per week
- Intelligence profiles updated on schedule
- Coverage gap closure rate
- % of discovered targets that are in-scope

## Budget

- Daily cap: 60k tokens
- Max runs: 1/day
- L1: report only
- L2: auto-submit target addition proposals
