# OWNEX Architecture Map (v1.0) — index, not duplicate

Full architecture docs already exist in `.ai/` (the project's source of truth). This file is the navigation index + verified entry points.

## Canonical sources

| Topic | Document |
|---|---|
| Product vision | `.ai/OWNEX_VISION_CHARTER.md` |
| Agent rules | `.ai/AGENT_CHARTER.md`, `AGENTS.md` (repo root) |
| Production rules | `.ai/PRODUCTION_RULES.md` |
| Verified state | `.ai/CURRENT_STATE.md` |
| Task backlog | `.ai/TASK_QUEUE.md`, `.agents/TASK_BOARD.md` |
| Decisions | `.ai/DECISIONS.md`, `docs/architecture/ARCHITECTURE_DECISIONS.md` |
| Debt | `.ai/TECHNICAL_DEBT.md`, `.ai/KNOWN_DEBT.md` |
| Duplication audit | `.ai/OWNEX_DUPLICATION_CONSOLIDATION.md`, `.ai/OWNEX_GLOBAL_ARCHITECTURE_AUDIT.md` |
| Canonical components | `docs/architecture/CANONICAL_COMPONENTS.md` |
| Multi-agent governance | `.agents/AGENT_REGISTRY.md`, `.agents/INTEGRATION_PROTOCOL.md` |

## Runtime shape (verified)

- **Backend**: FastAPI monolith (`api/main.py`), ~80 routers under `/api/*`, SQLAlchemy + SQLite dev / Postgres prod.
- **Twin trees**: `core/` (runtime scheduler lives here) and `cores/` (newer connections/finance work) — consolidation pending; see CANONICAL_COMPONENTS for which side owns each responsibility.
- **Frontend**: `frontend/` Vue 3 + TS + Vite + Tailwind v4, ~92 routed pages, builds green.
- **Data**: `database/catseye.db` (SQLite) for core entities; JSON files under OWNEX data dir for connections snapshots/normalized/imports/sync_history/mcp audit/user profile/remote jobs.
- **Scheduler**: `core/scheduler/jobs.py`.
- **Agents**: OAR runtime + OWNEX MCP stdio server for external agents.

## Data flows (verified)

```
Provider API/import → snapshot → financial_normalizer → normalized store
  → portfolio_view (read-model) → API → frontend
  → income_candidates → POST .../import → cores/ledger (human-triggered)

Job feeds → job_feeds → remote_job_matcher (+user_profile) → ranked
  → POST /remote-jobs/save → job_tracker pipeline → application_drafter (drafts only)
```
