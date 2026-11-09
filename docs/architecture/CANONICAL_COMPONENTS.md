# OWNEX Canonical Components — Single Source of Truth (v1.0)

Verified against code on 2026-11-09. When two implementations exist, this table says which is canonical. Update on any architecture change.

| Responsibility | Canonical implementation | Compatibility / twin | State |
|---|---|---|---|
| API surface | `api/main.py` + `api/routers/*` | — | VERIFIED |
| Connection framework | `api/routers/connection_manager.py` + `cores/connections/` (catalog, snapshots, sync_history, importer, financial_normalizer, portfolio_view, mcp_consent) | — | VERIFIED (unit) |
| Broker clients | `cores/brokers/{iol_client,iol_stream,ppi_client,binance_client}.py` | — | IMPLEMENTED (mocks only) |
| Identity/secrets vault | `cores/identity_vault.py` | `core/credentials/vault.py` (legacy) | CANONICAL = cores |
| External portfolio read-model | `cores/connections/portfolio_view.py` | — | VERIFIED |
| Income ledger | `cores/ledger/__init__.py` (`record_event`, `LedgerEvent`) | — | VERIFIED |
| Income candidates bridge | `POST /api/connection-manager/portfolio/income-candidates/import` | — | VERIFIED |
| OWNEX MCP server (for Perch/agents) | `core/mcp_ownex_server.py` | `core/mcp_rastro.py` (untracked WIP, NOT canonical) | VERIFIED |
| Remote job matcher | `cores/opportunity/remote_job_matcher.py` | — | VERIFIED |
| Job feeds (real) | `cores/opportunity/job_feeds.py` (Remotive, Arbeitnow, RemoteOK, Jobicy, WeWorkRemotely RSS) | `core/opportunity/adapters/jobs/*` = MOCK, unregistered, NOT canonical | VERIFIED |
| Job tracker (application pipeline) | `cores/opportunity/job_tracker.py` | — | VERIFIED |
| Application drafter | `cores/opportunity/application_drafter.py` | — | VERIFIED |
| User profile (matcher/drafter) | `cores/opportunity/user_profile.py` + `GET/PUT /api/opportunities/profile` | — | VERIFIED |
| Work Platform enum | `cores/direct_work_engine/models.py::WorkPlatform` | `core/` twin | CANONICAL = cores |
| Adapter registry | `core/opportunity/adapters/__init__.py` (`_seed_defaults`) | `cores/opportunity/` twins exist | CANONICAL = core |
| Zero-barrier eligibility | `cores/zero_barrier_eligibility.py` | — | IMPLEMENTED |
| Mercenary scorer | `core/opportunity/mercenary_filter.py` | — | IMPLEMENTED |
| Scheduler runtime | `core/scheduler/jobs.py` | `cores/` copy is STALE | CANONICAL = core |
| Frontend | `frontend/` (Vue3+Vite+Tailwind4) | — | VERIFIED (build green) |
| Trading engine | `core/trading/` (default DRY_RUN) | `cores/trading/` twin | CANONICAL = core; consolidation pending |
| Capital engines | `cores/capital/*` (runway, risk, allocation…) | `core/investment/*` | PARTIAL — not wired to external portfolio (FX decision pending) |
| Crypto data | `cores/crypto/*` (coingecko, evm, solana, tron…) | — | PARTIAL |
| Quant strategies | `core/quant/{strategies,research,performance}` — EMPTY dirs | — | NOT_IMPLEMENTED |

## Explicitly NOT canonical / do not use

- `work/ownex-economy-active-earn/` — parallel copy, ignore.
- `.quarantine/` — archived duplicates, ignore.
- `core/opportunity/adapters/jobs/*.py` — mock data, unregistered; never wire without real feeds.
- `api/routers/opportunity.py` — dead router (not in `main.py`, broken import); use `opportunities.py`.
- Upwork — excluded (`platform_connectors` enabled=False; enum kept for history only).
