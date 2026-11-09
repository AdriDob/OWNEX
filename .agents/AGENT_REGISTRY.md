# OWNEX Agent Registry — Multi-Agent Coordination (v1.0)

Canonical registry of agents working on OWNEX. Only register agents that have actually been identified — never invent active agents.

## Rules

- One write-owner per file/module per task. No two agents edit the same area simultaneously.
- Prefer branch-per-task + worktree isolation. Shared working tree requires explicit file ownership below.
- States: AVAILABLE → ASSIGNED → IN_PROGRESS → BLOCKED → REVIEW_REQUIRED → COMPLETED | CANCELLED.
- Commit base must be recorded before starting.

## Active agents

| ID | Harness | Model | Task | Branch/Worktree | Files owned | Base commit | State | Updated |
|----|---------|-------|------|-----------------|-------------|-------------|-------|---------|
| devin-session | Devin CLI | SWE-2 | v12 integrations + remote jobs | main (shared tree) | `cores/connections/`, `cores/brokers/`, `core/mcp_ownex_server.py`, `cores/opportunity/{remote_job_matcher,job_feeds,job_tracker,application_drafter,user_profile}.py`, `api/routers/{connection_manager,opportunities}.py`, `frontend/src/pages/RemoteJobs.vue`, `outputs/OWNEX_V12_*` | ebe35600 | IN_PROGRESS | 2026-11-09 |

## Known parallel work (uncommitted, NOT mine — do not touch)

- `frontend/src/components/mission-control/*`, `SourceConnectionConfig.vue`, `dashboard/*` — parallel session WIP (untracked).
- `frontend/src/pages/{Discovery,Trading}.vue`, `stores/discovery.ts` — modified by parallel session.
- Many `core/opportunity/adapters/*` modified — parallel session.
- `.ai/*` docs — shared, append-only style updates OK.

## Role lanes (recommended, not enforced)

| Lane | Scope |
|------|-------|
| Coordinator | architecture, priorities, integration, `.ai/` canon |
| Frontend | `frontend/**` |
| Backend | `api/**`, `core/**`, `cores/**`, `database/**` |
| Work Intelligence | `core/opportunity/**`, `cores/opportunity/**`, `cores/direct_work_engine/**` |
| Connections | `cores/connections/**`, `cores/brokers/**`, `core/mcp_*` |
| Finance | `cores/ledger`, `cores/capital`, `core/investment`, `cores/financial*` |
| QA/Security | `tests/**`, audits, `.ai/` state docs |
