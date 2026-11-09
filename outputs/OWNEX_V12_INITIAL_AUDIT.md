# OWNEX v12.0 — Initial Audit (verified against code, 2026-11-09)

## Architecture
- Backend: FastAPI (`api/main.py`), twin trees `core/` + `cores/` (cores partially quarantined; `.quarantine/` and `work/ownex-economy-active-earn/` contain parallel copies — NOT canonical).
- Frontend: Vue 3 + TS + Vite + Tailwind v4 (`frontend/`). Canonical pages include CommandCenter, WorkQueue, WorkDetail, ApplicationAssistant, IncomeHome, Connections, Capital, InvestmentHub, Trading.
- Persistence: SQLite dev (`database/catseye.db`), SQLAlchemy. Connections data: JSON files under OWNEX data dir (snapshots/normalized/imports/sync_history) + canonical ledger DB.
- Scheduler: `core/scheduler/jobs.py` is the runtime one (cores/ copy is stale).

## Connections (P1–P13, committed this session)
- VERIFIED-by-tests: catalog (16+ providers), IOL REST OAuth2+refresh+quotes+WS client, PPI REST, Binance read-only, manual import CSV/JSON/XLSX, normalizer, consolidated portfolio, income→ledger bridge, OWNEX MCP server + consent + audit.
- NOT verified live: zero real credentials tested. IOL WS implemented from official docs, untested against real endpoint.
- States honest: everything is IMPLEMENTED+unit-tested, none VALIDATED against real accounts.

## Work Discovery
- Adapters registered in `core/opportunity/adapters/__init__.py`: security, forge (algora/opire/superteam), issuehunt, opire/opyre, linkedin, freelancer(+microtask), opencollective, fiverr, and more.
- **MOCK**: `core/opportunity/adapters/jobs/{indeed,bumeran,computrabajo,glassdoor,infojobs}.py` return hardcoded fake jobs and are NOT registered in the adapter registry → cannot pollute Work Bank, but must not be wired without real feeds.
- WorkPlatform enum includes UPWORK (historical). `core/platform_connectors.py` has `"upwork": {"enabled": False}` — already disabled; no frontend references found. Exclusion satisfied at connector level; enum value retained for historical records only.
- Eligibility: `cores/zero_barrier_eligibility.py` + `core/opportunity/mercenary_filter.py` exist.
- **NEW**: `cores/opportunity/remote_job_matcher.py` — explainable weighted scorer (geo/requirements/language/modality/compensation/selection/payout), hard fails, UNKNOWN=neutral. PARTIAL: needs real job feeds wired in.

## Finance / Investments / Crypto / Agents
- Ledger canonical (`cores/ledger`), income candidates bridge committed. Payment compatibility engine exists (`core/opportunity/payment_methods.py`, `payment_trail.py`).
- Investments: IOL/PPI/Binance clients + normalized portfolio view; capital engines (runway/risk) not yet consuming consolidated data (needs FX policy decision).
- Agents: OWNEX MCP server done; PerchAI/Windows Terminal MCP/Ponytail/OpenMausBot NOT evaluated yet.

## Tests / Lint
- 4404 passed / 0 failed at last full run; connections slice 46 passed; matcher 5 passed. Ruff clean. Frontend biome clean on touched files. Vite build previously blocked by unrelated `Discovery.vue` WIP from parallel session.

## Duplications / Risks
- Dirty worktree: many modified files from parallel sessions — commits must stay scoped.
- `cores/` vs `core/` twin trees still diverge in places; `.quarantine/` + `work/` copies increase confusion.
- Mock job adapters + `fallback_data` patterns elsewhere risk fake opportunities if registered.

## Execution plan (remaining)
1. Wire real job feeds into remote_job_matcher (sources need verification — no invented APIs).
2. User credentials → live sync validation IOL/PPI/Binance.
3. FX policy decision → capital engines wiring.
4. Evaluate PerchAI/WinTermMCP/Ponytail/OpenMausBot (external research).
5. Fix parallel-session Discovery.vue → unblocked vite build.
