# OWNEX

**Personal Work & Income Operating System**  
**Status:** Active development · **Default branch:** `main`

OWNEX is a local-first system for discovering work opportunities, evaluating their requirements, preparing work, connecting selected services, and tracking financial outcomes. It combines opportunity intelligence, automation, security workflows, integrations, and an income ledger under human control.

> **Reality rule:** an opportunity is not income. A projection is not a payout. A connected integration is not a production-validated integration.

## Current status

The repository is under active development. The latest engineering state is documented in [`.ai/CURRENT_STATE.md`](.ai/CURRENT_STATE.md). That document is the source of truth for implementation details and known limitations.

| Area | Current, evidence-based description |
|---|---|
| Opportunity discovery | Multiple source adapters and discovery flows exist; source presence does not prove eligibility or active access |
| Work Bank | Discovery, scoring, preparation, and human review workflows are implemented in parts of the system |
| Income tracking | Ledger and financial tracking distinguish potential, expected, pending, and paid amounts |
| Financial connections | IOL, PPI, and Binance read-oriented connectors are implemented; real-account validation remains pending |
| Manual imports | CSV, JSON, and XLSX import flows with deduplication and provenance are implemented |
| MCP | A read-oriented OWNEX MCP server exists with consent checks and audit logging |
| Desktop / mobile / Wear OS | Do not assume release readiness from source code alone; consult build and device validation records |

### What is not claimed

- No verified recurring income is currently attributed to OWNEX.
- No external broker connection is represented as production-validated without a real credential-based test.
- No source is marked fully eligible merely because it appears in the catalog.
- No automated real-money trading, withdrawal, or final job application is implied.
- Counts of sources, adapters, tests, routes, or scheduled jobs are snapshots, not proof of successful real-world outcomes.

## Core principles

- **Local-first and privacy-aware:** keep personal data local by default.
- **Evidence before ranking:** show requirements, eligibility, payment method, and uncertainty.
- **Human approval:** preserve user control over applications, sensitive access, and financial actions.
- **One source of truth:** avoid duplicate engines, registries, event buses, and data stores.
- **Honest accounting:** potential, expected, approved, pending, paid, and withdrawn are different states.

## Architecture

OWNEX is intended to be a modular monolith with a FastAPI backend, a Vue 3 + TypeScript frontend, and a Tauri desktop shell.

- Backend: Python 3.11+, FastAPI
- Frontend: Vue 3, TypeScript, Vite
- Desktop: Tauri v2
- Data: SQLite for local development; PostgreSQL support is present in the codebase
- Integrations: provider-specific connectors and manual import paths
- AI: local-first provider routing with optional external providers

Architecture consolidation is still an active engineering concern. In particular, the relationship between `core/` and `cores/`, the event bus, scheduler ownership, and worktree boundaries must be resolved according to the current audit before further consolidation.

## Opportunity and income model

OWNEX can organize opportunities across:

- Software development and open-source bounties
- Bug bounty and application security programs
- AI coding and code-evaluation tasks
- QA and software testing
- Developer platforms and paid issue programs
- Freelance marketplaces (Fiverr and Freelancer; **Upwork is intentionally excluded**)

Every source needs independent checks for country eligibility, experience requirements, interviews, assessments, payment rails, fees, and actual withdrawal availability in Argentina.

See [Income and opportunity validation](docs/INCOME_AND_OPPORTUNITY_VALIDATION.md) for the current accounting rules and planning assumptions.

## Financial integrations

The connection layer currently includes read-oriented integration work for:

- InvertirOnline (IOL)
- Portfolio Personal (PPI)
- Binance (read-only)
- Manual imports for providers without a supported public API

**Important:** implementation and mocked tests do not equal live validation. Real credentials, account permissions, provider terms, and end-to-end reconciliation are still required. Financial MCP access defaults to deny until consent is granted. OWNEX does not expose trading or withdrawal tools through its read-only MCP server.

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

The exact setup may change. Check the repository's dependency files and scripts before running commands. Do not run migrations or destructive maintenance commands against valuable local data without a backup.

## Verification

Run the checks that match the area you changed. Typical commands include:

```bash
# Backend
python -m pytest

# Frontend
cd frontend
npm run build
```

The full suite and frontend build have had changing results during parallel development. Check the latest CI run and `.ai/CURRENT_STATE.md`; this README intentionally does not freeze an unverified test count.

## Documentation

- [Current engineering state](.ai/CURRENT_STATE.md)
- [Architecture audit](.ai/OWNEX_GLOBAL_ARCHITECTURE_AUDIT.md)
- [Duplication and consolidation plan](.ai/OWNEX_DUPLICATION_CONSOLIDATION.md)
- [Income and opportunity validation](docs/INCOME_AND_OPPORTUNITY_VALIDATION.md)

## License

The repository currently contains a `LICENSE` file whose legal terms must be treated as authoritative until the owner resolves the mismatch between that file and older README wording. Do not infer proprietary status from this README.

---

**Built for personal leverage, with evidence over hype.**
