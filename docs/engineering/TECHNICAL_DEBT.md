# OWNEX Technical Debt Register (v1.0)

Canonical detailed registers: `.ai/TECHNICAL_DEBT.md` and `.ai/KNOWN_DEBT.md` (source of truth). This file tracks **active, agent-relevant** debt with priorities P0–P4.

| ID | Problem | Sev | Module | Risk | Proposed fix | Status |
|----|---------|-----|--------|------|--------------|--------|
| TD-01 | `core/` vs `cores/` twin trees diverge; unclear ownership per module | P2 | repo-wide | agents edit wrong copy | audit done → `docs/architecture/TWIN_TREE_AUDIT.md` (421 common paths, 115 divergent, both trees live at runtime); consolidate per-file in dedicated worktree | AUDITED |
| TD-02 | `core/quant/{strategies,research,performance}` empty dirs | P3 | quant | dead structure implies features that don't exist | implement or remove | OPEN |
| TD-03 | `core/opportunity/adapters/jobs/*` return mock data | P1 | work discovery | fake opportunities if ever registered | keep unregistered; replace with real feeds or delete | OPEN |
| TD-04 | External portfolio not wired to `cores/capital` engines | P2 | finance | capital runway/risk ignore real balances | needs FX policy decision (user) | BLOCKED |
| TD-05 | npm audit: 9 moderate vulns remain (vitest mocker, glob, minimatch — devDeps) | P3 | frontend | dev-server/test-only attack surface | `audit fix --force` would bump vue-tsc etc.; low risk for local app | OPEN |
| TD-06 | Parallel-session WIP files break vue-tsc (type errors) | P3 | frontend | typecheck noise hides real errors | owners fix their WIP | OPEN |
| TD-07 | ~~`api/routers/opportunity.py`~~ | — | api | — | DELETED (zero refs, broken import, not in main.py) | CLOSED |
| TD-08 | `work/ownex-economy-active-earn/` + `.quarantine/` copies in repo | P3 | repo | agent confusion, repo bloat | move out of repo or document as frozen | OPEN |
| TD-09 | Job feeds mostly EN-first; Jobicy adds LATAM geo but no ES-native board verified | P3 | work discovery | matcher penalizes ES-only AR jobs | add Computrabajo/Bumeran manual import or verified API | OPEN (improved) |
| TD-10 | IOL/PPI/Binance never validated with real credentials | P1 | connections | "implemented" ≠ "works" | user provides creds → live sync test | BLOCKED |
