# OWNEX Vault Cycle — Data Vault

**Goal**: Ensure data integrity — verify database consistency, validate backups, and manage credential rotation schedules.

**App**: vault · **Cadence**: 6h · **Risk**: low

## Default Phases

discover → triage → act → verify → notify

## Human Gates

- Credential rotation (API keys, tokens)
- Data restoration events
- Schema migration validation

## Required Skills

- `integrity-check` — Verify database integrity and consistency
- `backup-verify` — Validate recent backup completeness and freshness
- `credential-rotate` — Detect and manage expiring credentials

## Checks

- Database WAL integrity
- Backup file age (<24h for daily, <1h for WAL)
- Credential expiry dates
- Encryption key rotation schedule
- Configuration file consistency

## State File

```markdown
# Vault Cycle State
Last run: <timestamp>
Backups:
  daily: ✅ complete (last: 2026-07-28 02:00)
  WAL: ✅ streaming (last: 2026-07-28 10:30)
Credentials:
  API_KEY_PROD: 🔴 expires in 3 days — ROTATE
  DB_PASSWORD: 🟢 expires in 60 days
  JWT_SECRET: 🟢 expires in 180 days
Integrity:
  DB check: ✅ passed (no corruption)
  Schema: ✅ up to date
```

## Success Metrics

- Backup freshness (% within SLA)
- Credential expiry lead time
- DB integrity check pass rate
- Time to detect data inconsistency

## Budget

- Daily cap: 30k tokens
- Max runs: 4/day
- L1: report + alert
- L2: auto-rotate credentials (with confirmation gate)
