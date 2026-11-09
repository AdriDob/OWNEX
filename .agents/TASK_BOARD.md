# OWNEX Task Board — Multi-Agent Coordination (v1.0)

Prioritized queue. Single write-owner per task. Check `.ai/TASK_QUEUE.md` for the strategic backlog — this board tracks *agent assignments*.

## Priority order (from governance §19)

1. Security & data integrity
2. Critical errors
3. Architecture stability
4. Broken core functionality
5. Frontend↔backend integration
6. Persistence & contracts
7. Real connections
8. New features
9. Optimizations
10. Experiments

## Board

| # | Task | Owner | Depends on | Files | State | Notes |
|---|------|-------|-----------|-------|-------|-------|
| 1 | Live-validate IOL/PPI/Binance sync | user+agent | user credentials | `cores/brokers/` | BLOCKED | needs real creds |
| 2 | FX policy decision → capital engines wiring | user decision | #1 optional | `cores/capital/`, `core/investment/` | BLOCKED | currency mixing forbidden until decided |
| 3 | Remote jobs: AR/ES-specific feeds | Work Intelligence | — | `cores/opportunity/job_feeds.py` | TODO | current feeds are EN-first |
| 4 | Perch E2E verification of OWNEX MCP | Connections | Perch install | `core/mcp_ownex_server.py` | TODO | consent flow ready |
| 5 | Consolidate `core/` vs `cores/` twin trees | Coordinator | full audit | both trees | TODO | `.ai/OWNEX_DUPLICATION_CONSOLIDATION.md` exists |
| 6 | npm audit fix (devDeps) | Frontend | — | `frontend/package*.json` | TODO | `npm audit fix` crashes; needs lockfile regen or --force |
| 7 | Crypto/quant: real strategies | Finance | capital data flow | `core/quant/` (empty dirs) | DEFERRED | dirs exist but empty — don't build until income flows |

## Rules

- Before starting: record commit base, declare files, check registry for conflicts.
- Before finishing: run relevant tests + ruff/biome, file completion report, update this board.
