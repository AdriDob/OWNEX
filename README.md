# OWNEX

**Personal Work & Income Operating System**  
**Version:** 9.0.0 · **Python:** 3.11+ · **Stack:** FastAPI · Vue 3 · TypeScript · Tauri v2  
**Status:** Active development

OWNEX is a local-first personal system for discovering work opportunities, evaluating requirements, preparing applications and deliverables, tracking income, connecting financial data, and orchestrating selected workflows under explicit human control.

> **Reality rule:** an opportunity is not income. An application is not a payout. A code-complete connector is not a live-validated integration.

## What works today

| Capability | Status | Evidence / limits |
|---|---|---|
| Opportunity catalog and discovery | Implemented | 150+ source definitions in the catalog; catalog presence does not prove country eligibility, active inventory, or payout access |
| Remote-job pipeline | Implemented | Five feeds (Remotive, Arbeitnow, RemoteOK, Jobicy, WeWorkRemotely), explainable matching, profile, tracker, and draft preparation; final submission remains human-controlled |
| Employment classification | Implemented | Permanent, temporary, independent, microtask, and bounty work are classified separately; contracts/freelance can be excluded by default |
| Unified income plan | Implemented | Aggregates first-day actions, accepted streams, Work Bank, and remote-job signals; estimated opportunity value is not realized cash |
| Income ledger | Implemented | Distinguishes potential, expected, approved, pending, paid, and withdrawn states |
| Financial connections | Integration pending | IOL OAuth2/refresh/quotes/WebSocket, PPI, Binance read-only, and manual CSV/JSON/XLSX imports exist; real-account validation is still required |
| Portfolio normalization | Implemented with limits | Keeps currencies separate and records provenance; no invented FX conversions |
| OWNEX MCP server | Implemented, read-oriented | Nine read-only tools, consent scopes, audit log; no trade or withdrawal tools |
| Security workflows | Implemented in parts | Reconnaissance, hypothesis, validation, evidence, and report pipeline; inspect current tests and runtime status |
| Frontend | Build status varies | Vue 3 + TypeScript + Vite; check current CI/build rather than relying on a stale route count |
| Desktop / Android | Build work exists | Tauri v2 and Capacitor Android projects; verify current release artifacts and device flows |
| Wear OS | Experimental | Partial implementation; not install-verified |
| Quant strategies | Planned | Presence of directories is not an implemented or validated strategy |

The detailed, dated record is [`.ai/CURRENT_STATE.md`](.ai/CURRENT_STATE.md). Architecture findings are documented in the audit and decision records.

For the full economic assessment, including the 176-source adaptation snapshot, high-ceiling revenue models, USD 10K/month unit economics, and a phased validation plan, see [**Deep Revenue Opportunity Study**](docs/DEEP_REVENUE_OPPORTUNITY_STUDY.md).

## What is not claimed

- Verified recurring income attributable to OWNEX is currently **USD 0**.
- No external broker integration is claimed as production-validated without a real credential-based end-to-end test.
- No source is considered fully eligible merely because it is listed.
- No real-money trade, withdrawal, or final application submission is implied by discovery or preparation features.
- Source counts, adapter counts, tests, routes, and advertised rates are snapshots, not evidence of real-world earnings.

## Core principles

- **Local-first:** personal data stays local by default.
- **Evidence before ranking:** expose country eligibility, experience, interview, assessment, payout, and uncertainty.
- **Human approval:** keep the user in control of applications, sensitive access, and financial actions.
- **One source of truth:** avoid duplicate engines, registries, event buses, and stores.
- **Honest accounting:** potential, expected, approved, pending, paid, and withdrawn are distinct states.

## Architecture

OWNEX is designed as a modular monolith: one FastAPI backend, a Vue 3 + TypeScript frontend, a shared data layer, and optional desktop/mobile shells.

- Backend: Python 3.11+, FastAPI
- Frontend: Vue 3, TypeScript, Vite
- Desktop: Tauri v2
- Mobile: Capacitor Android
- Data: SQLite for local development; PostgreSQL support exists
- Integrations: provider-specific connectors and manual import paths
- AI: local-first routing with optional external providers

**Known structural debt:** `core/` and `cores/` remain intertwined, and two event-bus implementations have been identified. Consolidation is domain-by-domain and must follow the architecture decisions and current audit. Do not assume these are already unified.

## Opportunity sources

OWNEX is intended to organize opportunities across:

- Permanent remote employment and junior roles
- Software development and open-source bounties
- Bug bounty and application security programs
- AI coding and code-evaluation tasks
- QA and software testing
- Developer platforms and paid issue programs
- Freelance marketplaces such as Fiverr and Freelancer (kept separate from employment)

**Upwork is intentionally excluded** from active discovery and recommendations.

Every source must be checked independently for Argentina eligibility, experience requirements, interviews/video, assessments, work type, payment rails, fees, minimum withdrawal, and actual payout availability. See [Income and opportunity validation](docs/INCOME_AND_OPPORTUNITY_VALIDATION.md).

## Financial integrations

The connection layer includes integration work for:

- InvertirOnline (IOL)
- Portfolio Personal (PPI)
- Binance (read-only)
- Manual imports for providers without a supported public API

**Important:** mocked tests and implementation against documentation do not equal live validation. Real credentials, provider permissions, terms, and end-to-end reconciliation remain necessary. Financial MCP access is deny-by-default until consent is granted. The read-only MCP server does not expose trading or withdrawal tools.

## Quick start

### Linux development

```bash
git clone https://github.com/AdriDob/OWNEX.git
cd OWNEX

python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cd frontend
npm install
cd ..

python run.py
```

In a second terminal:

```bash
cd frontend
npm run dev
```

Check dependency files and scripts before running commands. Back up valuable local data before migrations or destructive maintenance.

## Verification

Typical checks (use the repository's current scripts where applicable):

```bash
python scripts/dev test
python scripts/dev test-fast
make check
cd frontend && npm run build
```

Test and build results have changed during parallel development. Check the latest CI run and [current engineering state](.ai/CURRENT_STATE.md); this README intentionally avoids freezing an unverified test count.

## Documentation

- [Current engineering state](.ai/CURRENT_STATE.md)
- [Architecture audit](.ai/OWNEX_GLOBAL_ARCHITECTURE_AUDIT.md)
- [Duplication and consolidation plan](.ai/OWNEX_DUPLICATION_CONSOLIDATION.md)
- [Income and opportunity validation](docs/INCOME_AND_OPPORTUNITY_VALIDATION.md)

## License

See [LICENSE](LICENSE) and [LICENSE-MIT-legacy.txt](LICENSE-MIT-legacy.txt). The repository documents a license transition: versions distributed under MIT retain the permissions granted under that license; later versions are marked proprietary. See `outputs/OWNEX_V15/LICENSE_DECISION.md` for the project's own decision record.

---

**Built for personal leverage, with evidence over hype.**
